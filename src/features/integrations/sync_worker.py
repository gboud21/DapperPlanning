import threading
import time
import json
from datetime import datetime
from src.core.app_context import AppContext
from src.core.events import (
    ModelSyncProgressEvent, ModelSyncErrorEvent, ModelConflictDetectedEvent, 
    UIConflictResolvedEvent, ModelHierarchyUpdatedEvent, UISaveWorkspaceRequestedEvent
)
from src.domain.entities import Epic, Feature, Story, Team, Member, Label
from src.infrastructure.storage.transformers import GitLabTransformer
from src.utils.paths import GITLAB_SYNC_OUTPUT_FILE
from src.infrastructure.telemetry.logger import logger

class SyncWorker(threading.Thread):
    def __init__(self, context: AppContext, sync_type: str = 'pull'):
        """
        Initializes the SyncWorker.
        sync_type: 'pull' or 'push'
        """
        super().__init__(daemon=True)
        self.context = context
        self.sync_type = sync_type
        self.dispatcher = context.resolve('event_dispatcher')
        self.workspace = context.resolve('workspace')
        self.gitlab_client = context.resolve('gitlab_client')
        
        self.conflict_event = threading.Event()
        self.last_resolution = None
        self.active_conflict_id = None

        self.dispatcher.subscribe(UIConflictResolvedEvent, self._handle_resolution)

    def _handle_resolution(self, event: UIConflictResolvedEvent):
        if event.item_id == self.active_conflict_id:
            self.last_resolution = event.resolution
            self.conflict_event.set()

    def run(self):
        from src.infrastructure.api.gitlab_client import GitLabBaseError
        
        logger.info(f"SyncWorker started: {self.sync_type}")
        # Prepare basic debug info
        debug_info = {
            "Base URL": self.gitlab_client.base_url,
            "Group ID": self.gitlab_client.group_id,
            "Project ID": self.gitlab_client.project_id,
            "Sync Type": self.sync_type,
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Token": self.gitlab_client.headers.get("PRIVATE-TOKEN", "N/A")
        }

        try:
            if self.sync_type == 'pull':
                self._execute_pull()
            elif self.sync_type == 'push':
                self._execute_push()
            elif self.sync_type == 'members':
                self._execute_member_sync()
            elif self.sync_type == 'labels':
                self._execute_label_sync()
            self._safe_dispatch(ModelSyncProgressEvent(message="Done.", percent=100))
            logger.info(f"SyncWorker finished successfully: {self.sync_type}")
        except GitLabBaseError as e:
            logger.error(f"SyncWorker GitLab Error ({self.sync_type}): {e.error_message}")
            self._safe_dispatch(ModelSyncErrorEvent(
                title="GitLab Sync Error",
                error_message=e.error_message,
                suggested_solution=e.suggested_solution,
                debug_info=debug_info
            ))
        except Exception as e:
            logger.exception(f"SyncWorker Unexpected Error ({self.sync_type}): {e}")
            self._safe_dispatch(ModelSyncErrorEvent(
                title="Unexpected Sync Error",
                error_message=str(e),
                suggested_solution="Check the application logs and verify your network connection.",
                debug_info=debug_info
            ))
        finally:
            self._safe_dispatch(ModelHierarchyUpdatedEvent(root_items=self.workspace.get_epics()))

    def _safe_dispatch(self, event):
        """Dispatches an event via the Main Thread's .after() mechanism."""
        self.dispatcher.dispatch(event)

    def _execute_pull(self, dry_run=False):
        logger.info("Executing Pull Sync...")
        self._safe_dispatch(ModelSyncProgressEvent(message="Fetching remote data...", percent=10))
        
        # Determine current product IDs
        active_product_name = self.workspace.active_product_name
        product_entity = next((p for p in self.workspace.products if p.name == active_product_name), None)
        
        if not product_entity or not product_entity.gitlab_project_id or not product_entity.gitlab_group_id:
            from src.infrastructure.api.gitlab_client import GitLabBaseError
            logger.error(f"Pull Sync failed: Incomplete Product Configuration for '{active_product_name}'")
            raise GitLabBaseError(
                "Incomplete Product Configuration",
                f"Product '{active_product_name}' requires both a GitLab Project ID and Group ID for this sync operation."
            )

        # Fetch from both endpoints
        logger.info(f"Fetching data for product '{active_product_name}' (Project: {product_entity.gitlab_project_id}, Group: {product_entity.gitlab_group_id})")
        remote_epics = self.gitlab_client.fetch_group_epics(product_entity.gitlab_group_id)
        remote_issues = self.gitlab_client.fetch_project_issues(product_entity.gitlab_project_id)
        
        # Audit/Debug Logging: Save raw results to disk
        try:
            dump_data = {
                "timestamp": datetime.now().isoformat(),
                "sync_type": "pull",
                "product": active_product_name,
                "project_id": product_entity.gitlab_project_id,
                "group_id": product_entity.gitlab_group_id,
                "remote_epics": remote_epics,
                "remote_issues": remote_issues
            }
            with open(GITLAB_SYNC_OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(dump_data, f, indent=4)
        except IOError as e:
            logger.warning(f"Failed to write GitLab sync audit log: {e}")

        # Transform to Domain Objects
        logger.debug("Transforming GitLab data to domain objects...")
        transformer = GitLabTransformer()
        transformation_result = transformer.transform_pull_data(remote_epics, remote_issues)
        
        remote_epics_domain = transformation_result['root_epics']
        orphaned_features = transformation_result['orphaned_features']
        orphaned_stories = transformation_result['orphaned_stories']

        # Triage Logic: Safely catch unparented items
        if orphaned_features or orphaned_stories:
            # 1. Search for existing Triage Epic in the newly pulled remote items or local workspace
            triage_title = "[Triage] Unassigned Items"
            triage_epic = next((e for e in remote_epics_domain if e.title == triage_title), None)
            
            if not triage_epic:
                triage_epic = next((e for e in self.workspace.get_epics() if e.title == triage_title), None)
                if triage_epic:
                    # If found locally, ensure it's in the list to be merged
                    remote_epics_domain.append(triage_epic)
            
            # 2. Instantiate if still missing
            if not triage_epic:
                import uuid
                triage_epic = Epic(
                    id=str(uuid.uuid4()), 
                    title=triage_title,
                    description="Automatically created to house items without valid parent links in GitLab."
                )
                remote_epics_domain.append(triage_epic)
            
            # 3. Process Orphaned Features
            for feat in orphaned_features:
                if not any(f.gitlab_id == feat.gitlab_id for f in triage_epic.features):
                    # Set dynamic parent reference for internal tracking
                    feat.parent_epic_id = triage_epic.id
                    triage_epic.features.append(feat)
            
            # 4. Process Orphaned Stories
            if orphaned_stories:
                triage_feat_title = "[Triage] Unparented Stories"
                triage_feat = next((f for f in triage_epic.features if f.title == triage_feat_title), None)
                
                if not triage_feat:
                    import uuid
                    triage_feat = Feature(
                        id=str(uuid.uuid4()), 
                        title=triage_feat_title,
                        description="Stories linked to unknown or missing parent Features in GitLab.",
                        team=Team(name="Unassigned")
                    )
                    triage_feat.parent_epic_id = triage_epic.id
                    triage_epic.features.append(triage_feat)
                
                for story in orphaned_stories:
                    if not any(s.gitlab_id == story.gitlab_id for s in triage_feat.stories):
                        story.parent_feature_id = triage_feat.id
                        triage_feat.stories.append(story)
            
            logger.warning(f"Successfully triaged {len(orphaned_features)} features and {len(orphaned_stories)} stories into '{triage_title}'.")

        # Merge into local Workspace
        logger.info(f"Merging {len(remote_epics_domain)} epics into local workspace...")
        self._safe_dispatch(ModelSyncProgressEvent(message="Merging remote data into Workspace...", percent=95))
        self.workspace.merge_remote_epics(active_product_name, remote_epics_domain)
        
        # Persist the newly pulled data to disk
        self._safe_dispatch(UISaveWorkspaceRequestedEvent())
        
        # UI is automatically updated by Workspace.merge_remote_epics dispatching ModelHierarchyUpdatedEvent
        self._safe_dispatch(ModelSyncProgressEvent(message="Sync Complete!", percent=100))

    def _execute_push(self):
        logger.info("Executing Push Sync...")
        self._safe_dispatch(ModelSyncProgressEvent(message="Pushing local changes...", percent=10))
        
        # Determine active product IDs for context
        active_product_name = self.workspace.active_product_name
        product_entity = next((p for p in self.workspace.products if p.name == active_product_name), None)
        
        if not product_entity or not product_entity.gitlab_project_id:
            from src.infrastructure.api.gitlab_client import GitLabBaseError
            logger.error(f"Push Sync failed: Missing Project ID for product '{active_product_name}'")
            raise GitLabBaseError(
                "Missing Project ID", 
                f"Product '{active_product_name}' must have a GitLab Project ID configured."
            )

        pid = product_entity.gitlab_project_id
        gid = product_entity.gitlab_group_id # May be None for Free Tier
        
        # 1. Sync Labels first
        self._safe_dispatch(ModelSyncProgressEvent(message="Ensuring labels exist on GitLab...", percent=15))
        for label in self.workspace.labels.values():
            if not label.id:
                logger.info(f"Pushing new Label: {label.name}")
                label_data = {
                    "name": label.name,
                    "color": label.color,
                    "description": label.description
                }
                try:
                    if label.scope == 'project':
                        resp = self.gitlab_client.create_project_label(pid, label_data)
                    else:
                        # Default to group if possible, or project if gid is missing
                        target_gid = label.scope_name if label.scope == 'group' and label.scope_name else gid
                        if target_gid:
                            resp = self.gitlab_client.create_group_label(target_gid, label_data)
                        else:
                            resp = self.gitlab_client.create_project_label(pid, label_data)
                    label.id = resp.get('id')
                except Exception as e:
                    logger.warning(f"Failed to create label {label.name}: {e}")

        epics = self.workspace.get_epics()
        total_items = self._count_items(epics)
        processed = 0

        for epic in epics:
            epic_labels = epic.labels + ["Epic"]
            if not epic.gitlab_id:
                logger.info(f"Pushing new Epic: {epic.title}")
                resp = self.gitlab_client.create_group_epic(gid, epic, labels=",".join(epic_labels)) if gid else self.gitlab_client.create_project_task(pid, epic, labels=",".join(epic_labels))
                epic.gitlab_id = resp.get('id')
                epic.gitlab_iid = resp.get('iid')
                epic.last_synced_at = datetime.now().isoformat()
            elif self._has_local_changes(epic):
                logger.info(f"Updating existing Epic IID {epic.gitlab_iid} ({epic.title})...")
                if gid:
                    try:
                        self.gitlab_client.update_group_epic(gid, epic.gitlab_iid, epic, labels=",".join(epic_labels))
                    except Exception as e:
                        logger.warning(f"Group Epic update failed for IID {epic.gitlab_iid}, trying Project Task: {e}")
                        self.gitlab_client.update_project_task(pid, epic.gitlab_iid, epic, labels=",".join(epic_labels))
                else:
                    self.gitlab_client.update_project_task(pid, epic.gitlab_iid, epic, labels=",".join(epic_labels))
                epic.last_synced_at = datetime.now().isoformat()
            
            processed += 1
            self._safe_dispatch(ModelSyncProgressEvent(message=f"Synced Epic: {epic.title}", percent=10 + (processed/total_items * 80)))
            
            for feature in epic.features:
                feature_labels = feature.labels + ["Feature"]
                if not feature.gitlab_id:
                    logger.info(f"Pushing new Feature: {feature.title}")
                    resp = self.gitlab_client.create_group_epic(gid, feature, parent_id=epic.gitlab_id, labels=",".join(feature_labels)) if gid else \
                           self.gitlab_client.create_project_task(pid, feature, is_feature=True, parent_id=str(epic.gitlab_id), labels=",".join(feature_labels))
                    feature.gitlab_id = resp.get('id')
                    feature.gitlab_iid = resp.get('iid')
                    feature.last_synced_at = datetime.now().isoformat()
                elif self._has_local_changes(feature):
                    logger.info(f"Updating existing Feature IID {feature.gitlab_iid} ({feature.title})...")
                    if gid:
                        try:
                            self.gitlab_client.update_group_epic(gid, feature.gitlab_iid, feature, parent_id=epic.gitlab_id, labels=",".join(feature_labels))
                        except Exception as e:
                            logger.warning(f"Group Epic update failed for Feature IID {feature.gitlab_iid}, trying Project Task: {e}")
                            self.gitlab_client.update_project_task(pid, feature.gitlab_iid, feature, parent_id=str(epic.gitlab_id), labels=",".join(feature_labels))
                    else:
                        self.gitlab_client.update_project_task(pid, feature.gitlab_iid, feature, parent_id=str(epic.gitlab_id), labels=",".join(feature_labels))
                    feature.last_synced_at = datetime.now().isoformat()
                
                processed += 1
                self._safe_dispatch(ModelSyncProgressEvent(message=f"Synced Feature: {feature.title}", percent=10 + (processed/total_items * 80)))

                for story in feature.stories:
                    story_labels = story.labels + ["Story"]
                    if not story.gitlab_id:
                        logger.info(f"Pushing new Story: {story.title}")
                        resp = self.gitlab_client.create_story(pid, story, feature.gitlab_iid, labels=",".join(story_labels))
                        story.gitlab_id = resp.get('id')
                        story.gitlab_iid = resp.get('iid')
                        story.last_synced_at = datetime.now().isoformat()
                    elif self._has_local_changes(story):
                        logger.info(f"Updating existing Story IID {story.gitlab_iid} ({story.title})...")
                        self.gitlab_client.update_story(pid, story.gitlab_iid, story, epic_iid=feature.gitlab_iid, labels=",".join(story_labels))
                        story.last_synced_at = datetime.now().isoformat()
                    
                    processed += 1
                    self._safe_dispatch(ModelSyncProgressEvent(message=f"Synced Story: {story.title}", percent=10 + (processed/total_items * 80)))

        # Process remote deletions
        if self.workspace.deleted_remote_items:
            logger.info(f"Processing {len(self.workspace.deleted_remote_items)} remote deletions...")
            self._safe_dispatch(ModelSyncProgressEvent(message="Cleaning up removed items...", percent=95))
            
            for item in self.workspace.deleted_remote_items:
                try:
                    item_type = item['type']
                    item_id = item['id']
                    item_iid = item['iid']
                    item_pid = item['project_id']
                    item_gid = item['group_id']

                    if item_type == 'story':
                        self.gitlab_client.delete_project_task(item_pid, item_iid)
                    else: # feature or epic
                        if item_gid:
                            try:
                                self.gitlab_client.delete_group_epic(item_gid, item_iid)
                            except Exception:
                                self.gitlab_client.delete_project_task(item_pid, item_iid)
                        else:
                            self.gitlab_client.delete_project_task(item_pid, item_iid)
                except Exception as e:
                    logger.warning(f"Failed to delete remote {item['type']} IID {item['iid']}: {e}")

            self.workspace.deleted_remote_items.clear()

        # After push cascade completes, ensure newly assigned IDs are saved locally
        self._safe_dispatch(UISaveWorkspaceRequestedEvent())

    def _count_items(self, epics):
        count = len(epics)
        for e in epics:
            count += len(e.features)
            for f in e.features:
                count += len(f.stories)
        return count

    def _has_local_changes(self, item):
        """Returns True if the item has local changes that need pushing."""
        # If last_synced_at is None, it means the item is new or has been modified locally.
        return getattr(item, 'last_synced_at', None) is None

    def _process_item(self, remote_data, item_type, dry_run):
        gitlab_id = remote_data.get('id')
        local_item = self._find_local_by_gitlab_id(gitlab_id)
        
        if not local_item:
            if not dry_run:
                # Add new remote item to local (Stubbed)
                pass
            return

        # Compare
        if self._has_diff(local_item, remote_data):
            logger.warning(f"Conflict detected for item {local_item.id} ({local_item.title})")
            self.active_conflict_id = local_item.id
            self.conflict_event.clear()
            
            # Create a temporary remote item object for the UI
            remote_item_stub = Story(id="remote", title=remote_data.get('title'), description=remote_data.get('description'), team=local_item.team)
            if hasattr(local_item, 'weight'): remote_item_stub.weight = remote_data.get('weight', 0)
            
            self._safe_dispatch(ModelConflictDetectedEvent(local_item=local_item, remote_item=remote_item_stub))
            
            # Wait for user input
            logger.info(f"Waiting for user resolution for conflict {local_item.id}...")
            self.conflict_event.wait()
            
            logger.info(f"Conflict resolved: {self.last_resolution} for item {local_item.id}")
            if self.last_resolution == 'remote' and not dry_run:
                local_item.title = remote_data.get('title')
                local_item.description = remote_data.get('description')
                local_item.last_synced_at = datetime.now().isoformat()

    def _find_local_by_gitlab_id(self, gitlab_id):
        for epic in self.workspace.get_epics():
            if epic.gitlab_id == gitlab_id: return epic
            for feature in epic.features:
                if feature.gitlab_id == gitlab_id: return feature
                for story in feature.stories:
                    if story.gitlab_id == gitlab_id: return story
        return None

    def _has_diff(self, local, remote):
        if local.title != remote.get('title'): return True
        if local.description != remote.get('description'): return True
        
        # Check assignee
        remote_assignees = remote.get('assignees', [])
        remote_assignee_id = remote_assignees[0].get('id') if remote_assignees else None
        if getattr(local, 'assignee_id', None) != remote_assignee_id: return True

        # Check labels (ignoring architectural labels for comparison)
        reserved_labels = {'Epic', 'Feature', 'Story'}
        remote_labels = [l for l in remote.get('labels', []) if l not in reserved_labels]
        local_labels = sorted(getattr(local, 'labels', []))
        if local_labels != sorted(remote_labels): return True
        
        return False

    def _execute_member_sync(self):
        logger.info("Executing Member Sync...")
        self._safe_dispatch(ModelSyncProgressEvent(message="Fetching group members...", percent=10))
        
        # Determine current product IDs
        active_product_name = self.workspace.active_product_name
        product_entity = next((p for p in self.workspace.products if p.name == active_product_name), None)
        
        if not product_entity or not product_entity.gitlab_project_id or not product_entity.gitlab_group_id:
            from src.infrastructure.api.gitlab_client import GitLabBaseError
            logger.error(f"Member Sync failed: Incomplete Product Configuration for '{active_product_name}'")
            raise GitLabBaseError(
                "Incomplete Product Configuration",
                f"Product '{active_product_name}' requires both a GitLab Project ID and Group ID for member sync."
            )

        group_id = product_entity.gitlab_group_id
        project_id = product_entity.gitlab_project_id

        # Fetch group members
        raw_group_members = self.gitlab_client.fetch_group_members(group_id)
        self._safe_dispatch(ModelSyncProgressEvent(message=f"Processing {len(raw_group_members)} group members...", percent=40))
        
        for m in raw_group_members:
            member = Member(
                id=m['id'],
                name=m['name'],
                username=m['username'],
                group_ids=[int(group_id)]
            )
            self.workspace.add_or_update_member(member)

        # Fetch project members
        self._safe_dispatch(ModelSyncProgressEvent(message="Fetching project members...", percent=60))
        raw_project_members = self.gitlab_client.fetch_project_members(project_id)
        self._safe_dispatch(ModelSyncProgressEvent(message=f"Processing {len(raw_project_members)} project members...", percent=80))

        for m in raw_project_members:
            member = Member(
                id=m['id'],
                name=m['name'],
                username=m['username'],
                project_ids=[int(project_id)]
            )
            self.workspace.add_or_update_member(member)

        # Persist the newly pulled data
        self._safe_dispatch(UISaveWorkspaceRequestedEvent())
        self._safe_dispatch(ModelSyncProgressEvent(message="Member Sync Complete!", percent=100))

    def _execute_label_sync(self):
        logger.info("Executing Label Sync...")
        self._safe_dispatch(ModelSyncProgressEvent(message="Fetching GitLab labels...", percent=10))
        
        active_product_name = self.workspace.active_product_name
        product_entity = next((p for p in self.workspace.products if p.name == active_product_name), None)
        
        if not product_entity or not product_entity.gitlab_project_id or not product_entity.gitlab_group_id:
            from src.infrastructure.api.gitlab_client import GitLabBaseError
            raise GitLabBaseError(
                "Incomplete Product Configuration",
                "Product requires both Project and Group IDs for label sync."
            )

        group_id = product_entity.gitlab_group_id
        project_id = product_entity.gitlab_project_id

        # Fetch group labels
        reserved_labels = {'Epic', 'Feature', 'Story'}
        raw_group_labels = self.gitlab_client.fetch_group_labels(group_id)
        group_labels = [
            Label(
                id=l['id'], name=l['name'], color=l['color'], 
                description=l.get('description', ''), scope='group', scope_name=str(group_id)
            ) for l in raw_group_labels if l['name'] not in reserved_labels
        ]
        self.workspace.merge_labels(group_labels)

        # Fetch project labels
        self._safe_dispatch(ModelSyncProgressEvent(message="Fetching project labels...", percent=50))
        raw_project_labels = self.gitlab_client.fetch_project_labels(project_id)
        project_labels = [
            Label(
                id=l['id'], name=l['name'], color=l['color'], 
                description=l.get('description', ''), scope='project', scope_name=str(project_id)
            ) for l in raw_project_labels if l['name'] not in reserved_labels
        ]
        self.workspace.merge_labels(project_labels)

        self._safe_dispatch(UISaveWorkspaceRequestedEvent())
        self._safe_dispatch(ModelSyncProgressEvent(message="Label Sync Complete!", percent=100))
