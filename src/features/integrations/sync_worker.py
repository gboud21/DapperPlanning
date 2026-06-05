import threading
import time
import json
from datetime import datetime
from src.core.app_context import AppContext
from src.core.events import (
    ModelSyncProgressEvent, ModelSyncErrorEvent, ModelConflictDetectedEvent, 
    UIConflictResolvedEvent, ModelHierarchyUpdatedEvent
)
from src.domain.entities import Epic, Feature, Story
from src.infrastructure.storage.transformers import GitLabTransformer
from src.utils.paths import GITLAB_SYNC_OUTPUT_FILE

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
            self._safe_dispatch(ModelSyncProgressEvent(message="Done.", percent=100))
        except GitLabBaseError as e:
            self._safe_dispatch(ModelSyncErrorEvent(
                title="GitLab Sync Error",
                error_message=e.error_message,
                suggested_solution=e.suggested_solution,
                debug_info=debug_info
            ))
        except Exception as e:
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
        self._safe_dispatch(ModelSyncProgressEvent(message="Fetching remote data...", percent=10))
        
        # Determine current product IDs
        active_product_name = self.workspace.active_product_name
        product_entity = next((p for p in self.workspace.products if p.name == active_product_name), None)
        
        if not product_entity or not product_entity.gitlab_project_id or not product_entity.gitlab_group_id:
            from src.infrastructure.api.gitlab_client import GitLabBaseError
            raise GitLabBaseError(
                "Incomplete Product Configuration",
                f"Product '{active_product_name}' requires both a GitLab Project ID and Group ID for this sync operation."
            )

        # Fetch from both endpoints
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
            print(f"Warning: Failed to write GitLab sync audit log: {e}")

        # Transform to Domain Objects
        transformer = GitLabTransformer()
        remote_epics_domain = transformer.transform_pull_data(remote_epics, remote_issues)

        # Process the hierarchy
        self._safe_dispatch(ModelSyncProgressEvent(message="Comparing with local state...", percent=90))
        
        # Simple implementation: we flatten the remote tree and process each item
        from src.infrastructure.storage.transformers import HierarchyFlattener
        # Note: we need a way to map remote domain objects back to raw dicts if _process_item expects dicts
        # Or we update _process_item to handle Domain objects. 
        # For now, let's keep the existing logic by converting domain back to simple comparison stubs or updating _process_item.
        
        for r_epic in remote_epics_domain:
            self._process_domain_item(r_epic, dry_run)
            for r_feat in r_epic.features:
                self._process_domain_item(r_feat, dry_run)
                for r_story in r_feat.stories:
                    self._process_domain_item(r_story, dry_run)

    def _process_domain_item(self, remote_item, dry_run):
        """Helper to process domain objects instead of raw dicts."""
        local_item = self._find_local_by_gitlab_id(remote_item.gitlab_id)
        
        if not local_item:
            if not dry_run:
                # Logic to add new item could go here
                pass
            return

        # Compare
        if self._has_diff_domain(local_item, remote_item):
            self.active_conflict_id = local_item.id
            self.conflict_event.clear()
            
            self._safe_dispatch(ModelConflictDetectedEvent(local_item=local_item, remote_item=remote_item))
            
            # Wait for user input
            self.conflict_event.wait()
            
            if self.last_resolution == 'remote' and not dry_run:
                local_item.title = remote_item.title
                local_item.description = remote_item.description
                if hasattr(local_item, 'weight') and hasattr(remote_item, 'weight'):
                    local_item.weight = remote_item.weight
                local_item.last_synced_at = datetime.now().isoformat()

    def _has_diff_domain(self, local, remote):
        if local.title != remote.title: return True
        if local.description != remote.description: return True
        if hasattr(local, 'weight') and hasattr(remote, 'weight'):
            if local.weight != remote.weight: return True
        return False

    def _execute_push(self):
        self._safe_dispatch(ModelSyncProgressEvent(message="Checking for remote conflicts...", percent=5))
        # 1. Dry Pull (Check for conflicts)
        self._execute_pull(dry_run=True)
        
        # 2. Push Local changes
        self._safe_dispatch(ModelSyncProgressEvent(message="Pushing local changes...", percent=50))
        epics = self.workspace.get_epics()
        for epic in epics:
            if not epic.gitlab_id:
                resp = self.gitlab_client.create_epic(epic)
                # For Tasks/Issues, we usually want to store 'id' or 'iid'. 
                # Let's use 'id' for the global unique ID.
                epic.gitlab_id = resp.get('id')
            else:
                self.gitlab_client.update_epic(epic.gitlab_id, epic)
            
            epic.last_synced_at = datetime.now().isoformat()
            
            for feature in epic.features:
                if not feature.gitlab_id:
                    resp = self.gitlab_client.create_epic(feature, is_feature=True, parent_id=epic.gitlab_id)
                    feature.gitlab_id = resp.get('id')
                else:
                    self.gitlab_client.update_epic(feature.gitlab_id, feature)
                feature.last_synced_at = datetime.now().isoformat()

                for story in feature.stories:
                    if not story.gitlab_id:
                        # In Free Tier, we use the feature's iid or id to link
                        resp = self.gitlab_client.create_story(story, feature.gitlab_id)
                        story.gitlab_id = resp.get('id')
                    else:
                        self.gitlab_client.update_story(story.gitlab_id, story)
                    story.last_synced_at = datetime.now().isoformat()

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
            self.active_conflict_id = local_item.id
            self.conflict_event.clear()
            
            # Create a temporary remote item object for the UI
            remote_item_stub = Story(id="remote", title=remote_data.get('title'), description=remote_data.get('description'), team=local_item.team)
            if hasattr(local_item, 'weight'): remote_item_stub.weight = remote_data.get('weight', 0)
            
            self._safe_dispatch(ModelConflictDetectedEvent(local_item=local_item, remote_item=remote_item_stub))
            
            # Wait for user input
            self.conflict_event.wait()
            
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
        return False
