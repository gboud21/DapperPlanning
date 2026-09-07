import threading
import time
import json
import os
from datetime import datetime
from dataclasses import asdict
from src.core.app_context import AppContext
from src.core.events import (
    ModelSyncProgressEvent, ModelSyncErrorEvent, ModelConflictDetectedEvent, 
    UIConflictResolvedEvent, ModelHierarchyUpdatedEvent, UISaveWorkspaceRequestedEvent,
    ModelDryPushCompletedEvent
)
from src.domain.entities import Epic, Feature, Story, Team, Member, Label, Iteration
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
        
        # Initialize basic debug info (will be updated in run() with fresh timestamps)
        self.debug_info = {
            "Base URL": getattr(self.gitlab_client, 'base_url', 'N/A'),
            "Group ID": getattr(self.gitlab_client, 'group_id', 'N/A'),
            "Project ID": getattr(self.gitlab_client, 'project_id', 'N/A'),
            "Sync Type": self.sync_type,
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Token": "PROTECTED"
        }

    def _handle_resolution(self, event: UIConflictResolvedEvent):
        if event.item_id == self.active_conflict_id:
            self.last_resolution = event.resolution
            self.conflict_event.set()

    def run(self):
        from src.infrastructure.api.gitlab_client import GitLabBaseError
        
        logger.info(f"SyncWorker started: {self.sync_type}")
        # Prepare basic debug info
        self.debug_info = {
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
            elif self.sync_type == 'dry-push':
                self._execute_dry_push()
            elif self.sync_type == 'members':
                self._execute_member_sync()
            elif self.sync_type == 'labels':
                self._execute_label_sync()
            elif self.sync_type == 'iterations':
                self._execute_iteration_sync()
            self._safe_dispatch(ModelSyncProgressEvent(message="Done.", percent=100))
            logger.info(f"SyncWorker finished successfully: {self.sync_type}")
        except GitLabBaseError as e:
            logger.error(f"SyncWorker GitLab Error ({self.sync_type}): {e.error_message}")
            self._safe_dispatch(ModelSyncErrorEvent(
                title="GitLab Sync Error",
                error_message=e.error_message,
                suggested_solution=e.suggested_solution,
                debug_info=self.debug_info
            ))
        except Exception as e:
            logger.exception(f"SyncWorker Unexpected Error ({self.sync_type}): {e}")
            self._safe_dispatch(ModelSyncErrorEvent(
                title="Unexpected Sync Error",
                error_message=str(e),
                suggested_solution="Check the application logs and verify your network connection.",
                debug_info=self.debug_info
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
        
        from src.infrastructure.storage.settings_manager import SettingsManager
        settings = self.context.resolve('settings_manager')
        legacy_enabled = settings.get('legacy_status_enabled', False)
        mappings = settings.get('status_label_mappings', {})
        epic_label = self.gitlab_client.epic_sync_label
        feature_label = self.gitlab_client.feature_sync_label

        transformation_result = transformer.transform_pull_data(epic_label, feature_label, remote_epics,  remote_issues, legacy_enabled=legacy_enabled, mappings=mappings)
        
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
        """Forces an inbound pull pre-fetch, sweeps all items for attribute divergence, and blocks if conflicts are found."""
        logger.info("Executing Secure Push Sync with Pre-fetch...")
        
        # 1. Trigger fresh server fetch (Pull)
        # Reuse _execute_pull logic but handle results locally for scanning
        self._safe_dispatch(ModelSyncProgressEvent(message="Pre-fetching remote state...", percent=5))
        
        active_product_name = self.workspace.active_product_name
        product_entity = next((p for p in self.workspace.products if p.name == active_product_name), None)
        if not product_entity or not product_entity.gitlab_project_id:
             from src.infrastructure.api.gitlab_client import GitLabBaseError
             raise GitLabBaseError("Missing Project ID", f"Product '{active_product_name}' must have a GitLab Project ID configured.")

        remote_epics = self.gitlab_client.fetch_group_epics(product_entity.gitlab_group_id)
        remote_issues = self.gitlab_client.fetch_project_issues(product_entity.gitlab_project_id)
        
        transformer = GitLabTransformer()
        settings = self.context.resolve('settings_manager')
        legacy_enabled = settings.get('legacy_status_enabled', False)
        mappings = settings.get('status_label_mappings', {})
        epic_label = self.gitlab_client.epic_sync_label
        feature_label = self.gitlab_client.feature_sync_label

        transformation_result = transformer.transform_pull_data(epic_label, feature_label, remote_epics,  remote_issues, legacy_enabled=legacy_enabled, mappings=mappings)
        remote_data = transformation_result['root_epics']
        
        # Populate remote cache in controller for UI resolution later
        integrations_controller = self.context.resolve('integrations_controller')
        integrations_controller.remote_data_cache = {}
        
        # Flatten remote data for easy lookup
        remote_lookup = {}
        def _collect_remote(items):
            for i in items:
                remote_lookup[i.gitlab_id] = i
                integrations_controller.remote_data_cache[i.gitlab_id] = i
                if hasattr(i, 'features'): _collect_remote(i.features)
                if hasattr(i, 'stories'): _collect_remote(i.stories)
        _collect_remote(remote_data)

        conflict_detected = False
        # 2. Iterate across all local objects to identify collisions against Shadow
        self._safe_dispatch(ModelSyncProgressEvent(message="Scanning for merge conflicts...", percent=10))
        for local_item in self.workspace.all_items_iterable():
            if not local_item.gitlab_id:
                continue # Skip new local items
                
            shadow_copy = self.workspace.shadow_hierarchy.get(local_item.id)
            remote_copy_obj = remote_lookup.get(local_item.gitlab_id)
            
            if shadow_copy and remote_copy_obj:
                remote_copy_dict = asdict(remote_copy_obj)
                local_item_dict = asdict(local_item)
                
                # Detect if both local working copy and remote server copy have changed from common ancestor
                has_remote_changed = self._check_diff(shadow_copy, remote_copy_dict)
                has_local_changed = self._check_diff(shadow_copy, local_item_dict)
                
                if has_remote_changed and has_local_changed:
                    local_item.is_conflicted = True
                    conflict_detected = True
                    logger.warning(f"Conflict detected for {local_item.id}: {local_item.title}")
                
        if conflict_detected:
            self._safe_dispatch(ModelConflictDetectedEvent())
            self._safe_dispatch(ModelSyncErrorEvent(
                title="Merge Conflict Detected",
                error_message="One or more items have been modified both locally and on GitLab since your last pull.",
                suggested_solution="Resolve the highlighted conflicts in the Agile Planning tree (right-click -> Resolve Merge Conflict) before pushing again.",
                debug_info=self.debug_info
            ))
            self._safe_dispatch(ModelSyncProgressEvent(message="Push Aborted: Conflicts Found.", percent=100))
            return # Block push

        # 3. Proceed with normal push if clean
        self._perform_actual_push(product_entity, settings, legacy_enabled, mappings)

    def _check_diff(self, shadow_dict, current_dict):
        """Compares core agile attributes for divergence."""
        core_fields = ['title', 'description', 'weight', 'status', 'assignee_id', 'iteration_id', 'labels']
        for field in core_fields:
            s_val = shadow_dict.get(field)
            c_val = current_dict.get(field)
            
            if field == 'labels':
                # Sort for comparison
                if sorted(s_val or []) != sorted(c_val or []):
                    return True
            elif s_val != c_val:
                return True
        return False

    def _perform_actual_push(self, product_entity, settings, legacy_enabled, mappings):
        self._safe_dispatch(ModelSyncProgressEvent(message="Pushing local changes...", percent=15))
        pid = product_entity.gitlab_project_id
        gid = product_entity.gitlab_group_id # May be None for Free Tier
        
        # 1. Sync Labels first
        self._safe_dispatch(ModelSyncProgressEvent(message="Ensuring labels exist on GitLab...", percent=20))
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

        epic_label = self.gitlab_client.epic_sync_label
        feature_label = self.gitlab_client.feature_sync_label

        for epic in epics:
            current_labels = epic.labels
            # Epics and Features should NOT apply Status Labels when pushing
            epic_labels = current_labels + [epic_label]
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
            self._safe_dispatch(ModelSyncProgressEvent(message=f"Synced Epic: {epic.title}", percent=20 + (processed/total_items * 70)))
            
            for feature in epic.features:
                current_labels = feature.labels
                # Epics and Features should NOT apply Status Labels when pushing
                feature_labels = current_labels + [feature_label]
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
                self._safe_dispatch(ModelSyncProgressEvent(message=f"Synced Feature: {feature.title}", percent=20 + (processed/total_items * 70)))

                for story in feature.stories:
                    current_labels = story.labels
                    if legacy_enabled:
                        current_labels = self.workspace.sync_legacy_labels(story.status, current_labels, legacy_enabled, mappings)
                    # Removed "Story" label assignment
                    story_labels = current_labels
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
                    self._safe_dispatch(ModelSyncProgressEvent(message=f"Synced Story: {story.title}", percent=20 + (processed/total_items * 70)))

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

        # After push cascade completes, ensure newly assigned IDs and baseline state are saved locally
        self.workspace.save_shadow_hierarchy(self.workspace.get_epics())
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
        if getattr(item, 'last_synced_at', None) is None:
            return True
            
        # Optional: Deep check if sync timestamp logic fails or is not applied everywhere
        return False

    def _find_local_by_gitlab_id(self, gitlab_id):
        for epic in self.workspace.get_epics():
            if epic.gitlab_id == gitlab_id: return epic
            for feature in epic.features:
                if feature.gitlab_id == gitlab_id: return feature
                for story in feature.stories:
                    if story.gitlab_id == gitlab_id: return story
        return None

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
        reserved_labels = {self.gitlab_client.epic_sync_label, self.gitlab_client.feature_sync_label, 'Story'}
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

    def _execute_iteration_sync(self):
        logger.info("Executing Iteration Sync...")
        self._safe_dispatch(ModelSyncProgressEvent(message="Fetching GitLab iterations...", percent=10))
        
        active_product_name = self.workspace.active_product_name
        product_entity = next((p for p in self.workspace.products if p.name == active_product_name), None)
        
        if not product_entity or not product_entity.gitlab_project_id or not product_entity.gitlab_group_id:
            from src.infrastructure.api.gitlab_client import GitLabBaseError
            raise GitLabBaseError(
                "Incomplete Product Configuration",
                "Product requires both Project and Group IDs for iteration sync."
            )

        group_id = product_entity.gitlab_group_id
        project_id = product_entity.gitlab_project_id

        # Fetch group iterations
        raw_group_iterations = self.gitlab_client.fetch_group_iterations(group_id)
        iterations = []
        for i in raw_group_iterations:
            # Map state if it's an integer (1: opened, 2: closed)
            state = i.get('state', 'opened')
            if state == 1: state = "opened"
            elif state == 2: state = "closed"
            
            iterations.append(Iteration(
                id=i.get('id'), 
                iid=i.get('iid'), 
                title=i.get('title') or f"Iteration {i.get('iid')}",
                start_date=i.get('start_date', ''), 
                end_date=i.get('due_date', ''), 
                state=str(state)
            ))
        
        # Also fetch project iterations (though they are often same as group in many setups)
        self._safe_dispatch(ModelSyncProgressEvent(message="Fetching project iterations...", percent=50))
        raw_project_iterations = self.gitlab_client.fetch_project_iterations(project_id)
        for i in raw_project_iterations:
            if not any(it.id == i.get('id') for it in iterations):
                state = i.get('state', 'opened')
                if state == 1: state = "opened"
                elif state == 2: state = "closed"

                iterations.append(Iteration(
                    id=i.get('id'), 
                    iid=i.get('iid'), 
                    title=i.get('title') or f"Iteration {i.get('iid')}",
                    start_date=i.get('start_date', ''), 
                    end_date=i.get('due_date', ''), 
                    state=str(state)
                ))

        self.workspace.merge_iterations(iterations)

        self._safe_dispatch(UISaveWorkspaceRequestedEvent())
        self._safe_dispatch(ModelSyncProgressEvent(message="Iteration Sync Complete!", percent=100))

    def _execute_dry_push(self):
        """Simulates a push to GitLab without mutating domain model flags or modifying server state."""
        logger.info("Executing GitLab Dry-Push Simulation...")
        self._safe_dispatch(ModelSyncProgressEvent(message="Pre-fetching remote state...", percent=5))
        
        # 1. Resolve active product and ensure configuration exists
        active_product_name = self.workspace.active_product_name
        product_entity = next((p for p in self.workspace.products if p.name == active_product_name), None)
        if not product_entity or not product_entity.gitlab_project_id:
             from src.infrastructure.api.gitlab_client import GitLabBaseError
             raise GitLabBaseError("Missing Project ID", f"Product '{active_product_name}' must have a GitLab Project ID configured.")

        # 2. Fetch remote data (simulate push by comparing against fresh remote fetch)
        remote_epics = self.gitlab_client.fetch_group_epics(product_entity.gitlab_group_id)
        remote_issues = self.gitlab_client.fetch_project_issues(product_entity.gitlab_project_id)
        
        transformer = GitLabTransformer()
        settings = self.context.resolve('settings_manager')
        legacy_enabled = settings.get('legacy_status_enabled', False)
        mappings = settings.get('status_label_mappings', {})
        epic_label = self.gitlab_client.epic_sync_label
        feature_label = self.gitlab_client.feature_sync_label

        transformation_result = transformer.transform_pull_data(epic_label, feature_label, remote_epics, remote_issues, legacy_enabled=legacy_enabled, mappings=mappings)
        remote_data = transformation_result['root_epics']
        
        # Populate remote cache in controller (matching normal push behavior)
        integrations_controller = self.context.resolve('integrations_controller')
        integrations_controller.remote_data_cache = {}
        
        # Flatten remote data for easy lookup
        remote_lookup = {}
        def _collect_remote(items):
            for i in items:
                remote_lookup[i.gitlab_id] = i
                integrations_controller.remote_data_cache[i.gitlab_id] = i
                if hasattr(i, 'features'): _collect_remote(i.features)
                if hasattr(i, 'stories'): _collect_remote(i.stories)
        _collect_remote(remote_data)

        # 3. Categorize changes
        creations_list = []
        updates_list = []
        conflicts_list = []
        deletions_list = []

        self._safe_dispatch(ModelSyncProgressEvent(message="Analyzing differences...", percent=50))
        for local_item in self.workspace.all_items_iterable():
            if not local_item.gitlab_id:
                creations_list.append(local_item)
                continue
                
            shadow_copy = self.workspace.shadow_hierarchy.get(local_item.id)
            remote_copy_obj = remote_lookup.get(local_item.gitlab_id)
            
            if shadow_copy and remote_copy_obj:
                remote_copy_dict = asdict(remote_copy_obj)
                local_item_dict = asdict(local_item)
                
                has_remote_changed = self._check_diff(shadow_copy, remote_copy_dict)
                has_local_changed = self._check_diff(shadow_copy, local_item_dict)
                
                if has_remote_changed and has_local_changed:
                    conflicts_list.append(local_item)
                elif has_local_changed:
                    updates_list.append(local_item)
            else:
                if self._has_local_changes(local_item):
                    updates_list.append(local_item)

        # Populate deletions list from workspace.deleted_remote_items
        for item in self.workspace.deleted_remote_items:
            deletions_list.append(item)

        # Log summary and object details
        logger.info(
            f"Dry Push Summary: {len(creations_list)} Creations, "
            f"{len(updates_list)} Updates, {len(conflicts_list)} Conflicts, "
            f"{len(deletions_list)} Deletions"
        )
        
        logger.info(f"Creations ({len(creations_list)}):")
        for item in creations_list:
            logger.info(f"  - {item.__class__.__name__}: {getattr(item, 'title', str(item))} (ID: {getattr(item, 'id', 'N/A')})")

        logger.info(f"Updates ({len(updates_list)}):")
        for item in updates_list:
            logger.info(f"  - {item.__class__.__name__}: {getattr(item, 'title', str(item))} (ID: {getattr(item, 'id', 'N/A')})")

        logger.info(f"Conflicts ({len(conflicts_list)}):")
        for item in conflicts_list:
            logger.info(f"  - {item.__class__.__name__}: {getattr(item, 'title', str(item))} (ID: {getattr(item, 'id', 'N/A')})")

        logger.info(f"Deletions ({len(deletions_list)}):")
        for item in deletions_list:
            if isinstance(item, dict):
                item_type = item.get('type', 'Item').capitalize()
                iid = item.get('iid', 'N/A')
                gid = item.get('id', 'N/A')
                logger.info(f"  - {item_type}: (GitLab IID: {iid}, GitLab ID: {gid})")
            else:
                logger.info(f"  - {item.__class__.__name__}: {getattr(item, 'title', str(item))} (ID: {getattr(item, 'id', 'N/A')})")

        # 4. Generate markdown report
        report_dir = os.path.dirname(self.workspace.current_filepath) if self.workspace.current_filepath else os.getcwd()
        report_path = os.path.join(report_dir, 'gitlab_dry_push_report.md')
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Prepare content lists
        def format_item(item):
            return f"- **{item.__class__.__name__}**: {item.title} (ID: {item.id})"
            
        def format_deleted(item):
            return f"- **{item['type'].capitalize()}**: (GitLab IID: {item['iid']}, GitLab ID: {item['id']})"
            
        creations_str = "\n".join(format_item(i) for i in creations_list) or "*None*"
        updates_str = "\n".join(format_item(i) for i in updates_list) or "*None*"
        conflicts_str = "\n".join(format_item(i) for i in conflicts_list) or "*None*"
        deletions_str = "\n".join(format_deleted(i) for i in deletions_list) or "*None*"
        
        if len(conflicts_list) > 0:
            alert_status = (
                "> [!WARNING]\n"
                "> **Conflicts detected!** A normal push will be blocked. "
                "Please resolve the conflicts before pushing."
            )
        else:
            alert_status = (
                "> [!NOTE]\n"
                "> Dry-push simulated successfully. No conflicts found."
            )

        report_content = f"""# GitLab Dry-Push Simulation Report

Generated on: {timestamp}

## Summary of Changes
- **Creations:** {len(creations_list)}
- **Updates:** {len(updates_list)}
- **Conflicts:** {len(conflicts_list)}
- **Deletions:** {len(deletions_list)}

{alert_status}

## Detailed Log

### Creations ({len(creations_list)})
{creations_str}

### Updates ({len(updates_list)})
{updates_str}

### Conflicts ({len(conflicts_list)})
{conflicts_str}

### Deletions ({len(deletions_list)})
{deletions_str}
"""
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
            
        self._safe_dispatch(ModelSyncProgressEvent(message="Report generated.", percent=95))
        
        # 5. Dispatch completion event
        self._safe_dispatch(ModelDryPushCompletedEvent(
            creations=len(creations_list),
            updates=len(updates_list),
            conflicts=len(conflicts_list),
            deletions=len(deletions_list),
            report_path=report_path,
            creations_list=creations_list,
            updates_list=updates_list,
            conflicts_list=conflicts_list,
            deletions_list=deletions_list
        ))

