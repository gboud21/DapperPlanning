import threading
import time
from datetime import datetime
from src.core.app_context import AppContext
from src.core.events import (
    ModelSyncProgressEvent, ModelConflictDetectedEvent, UIConflictResolvedEvent,
    UIErrorNotificationEvent, ModelHierarchyUpdatedEvent
)
from src.domain.entities import Epic, Feature, Story

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
        try:
            if self.sync_type == 'pull':
                self._execute_pull()
            elif self.sync_type == 'push':
                self._execute_push()
        except Exception as e:
            self._safe_dispatch(UIErrorNotificationEvent(title="Sync Error", message=str(e)))
        finally:
            self._safe_dispatch(ModelSyncProgressEvent(message="Done.", percent=100))
            self._safe_dispatch(ModelHierarchyUpdatedEvent(root_items=self.workspace.get_epics()))

    def _safe_dispatch(self, event):
        """Dispatches an event via the Main Thread's .after() mechanism."""
        self.dispatcher.dispatch(event)

    def _execute_pull(self, dry_run=False):
        self._safe_dispatch(ModelSyncProgressEvent(message="Fetching remote data...", percent=10))
        remote_epics = self.gitlab_client.get_epics()
        remote_issues = self.gitlab_client.get_issues()
        
        total_items = len(remote_epics) + len(remote_issues)
        if total_items == 0: return

        # Map remote data to objects for comparison
        # (This is simplified for demonstration)
        processed = 0
        for r_epic in remote_epics:
            self._process_item(r_epic, 'Epic', dry_run)
            processed += 1
            self._safe_dispatch(ModelSyncProgressEvent(
                message=f"Syncing Epic: {r_epic.get('title')}", 
                percent=10 + (processed / total_items * 80)
            ))

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
                epic.gitlab_id = resp.get('id')
            else:
                self.gitlab_client.update_epic(epic.gitlab_id, epic)
            
            epic.last_synced_at = datetime.now().isoformat()
            
            for feature in epic.features:
                # Features are mapped to GitLab Epics in this methodology
                if not feature.gitlab_id:
                    resp = self.gitlab_client.create_epic(feature, is_feature=True, parent_id=epic.gitlab_id)
                    feature.gitlab_id = resp.get('id')
                else:
                    self.gitlab_client.update_epic(feature.gitlab_id, feature)
                feature.last_synced_at = datetime.now().isoformat()

                for story in feature.stories:
                    if not story.gitlab_id:
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
