import tkinter as tk
from tkinter import messagebox
from typing import Dict, Any, Optional
from src.core.app_context import AppContext
from src.core.events import (
    EventDispatcher, UIIntegrationsDialogOpenRequestedEvent, UIIntegrationsSaveRequestedEvent,
    UIErrorNotificationEvent, UIGlobalTagAddRequestedEvent, UIGlobalTagDeleteRequestedEvent,
    ModelConflictDetectedEvent, ModelSyncErrorEvent, ModelHierarchyUpdatedEvent, ModelWorkspaceLoadedEvent,
    UISyncMembersRequestedEvent, UISyncLabelsRequestedEvent, UISyncIterationsRequestedEvent
)
from src.core.command_bus import CommandBus
from src.core.commands import SyncWithGitLabCommand
from src.utils.theme_manager import ThemeManager
from src.features.integrations.integrations_dialog import IntegrationsDialog
from src.features.integrations.sync_progress_modal import SyncProgressModal
from src.features.integrations.sync_error_modal import SyncErrorModal
from src.features.integrations.conflict_resolution_modal import ConflictResolutionModal
from src.features.integrations.sync_worker import SyncWorker
from src.infrastructure.api.gitlab_client import GitLabClient
from src.infrastructure.storage.settings_manager import SettingsManager

class IntegrationsController:
    def __init__(self, context: AppContext):
        """
        Initializes the IntegrationsController.

        Args:
            context (AppContext): The application context for dependency injection.
        """
        self.context = context
        self.root: tk.Tk = context.resolve('root_window')
        self.dispatcher: EventDispatcher = context.resolve('event_dispatcher')
        self.command_bus: CommandBus = context.resolve('command_bus')
        self.workspace = context.resolve('workspace')
        self.settings: SettingsManager = context.resolve('settings_manager')
        
        self.context.register('integrations_controller', self)
        self.remote_data_cache: Dict[int, Any] = {} # Maps gitlab_id to domain object
        
        self.progress_modal = None
        self._subscribe_events()
        self._register_commands()

    def _subscribe_events(self):
        self.dispatcher.subscribe(UIIntegrationsDialogOpenRequestedEvent, self.handle_open_dialog)
        self.dispatcher.subscribe(UIIntegrationsSaveRequestedEvent, self.handle_save_settings)
        self.dispatcher.subscribe(UIGlobalTagAddRequestedEvent, self.handle_global_tag_add)
        self.dispatcher.subscribe(UIGlobalTagDeleteRequestedEvent, self.handle_global_tag_delete)
        self.dispatcher.subscribe(ModelConflictDetectedEvent, self.handle_conflict_detected)
        self.dispatcher.subscribe(ModelSyncErrorEvent, self.handle_sync_error)
        self.dispatcher.subscribe(ModelWorkspaceLoadedEvent, self.handle_workspace_loaded)
        self.dispatcher.subscribe(UISyncMembersRequestedEvent, self.handle_sync_members)
        self.dispatcher.subscribe(UISyncLabelsRequestedEvent, self.handle_sync_labels)
        self.dispatcher.subscribe(UISyncIterationsRequestedEvent, self.handle_sync_iterations)

    def _register_commands(self):
        """Registers handlers for integration-related commands."""
        self.command_bus.register(SyncWithGitLabCommand, self.handle_sync_with_gitlab)

    def handle_workspace_loaded(self, event: ModelWorkspaceLoadedEvent):
        """Refreshes the workspace reference."""
        self.workspace = self.context.resolve('workspace')

    def get_latest_remote_copy(self, gitlab_id: int) -> Optional[Any]:
        """Returns a domain object from the latest fetch cache."""
        return self.remote_data_cache.get(gitlab_id)

    def _is_gitlab_configured(self) -> bool:
        """Returns True if essential GitLab credentials are set."""
        url = self.settings.get('auth_url', '')
        pat = self.settings.get('auth_pat', '')
        # Checking for group ID as it's required for epic/feature creation in our current client
        gid = self.settings.get('epic_group_id', '')
        
        return all([url, pat, gid])

    def handle_open_dialog(self, event: UIIntegrationsDialogOpenRequestedEvent = None):
        """Opens the Integrations Dialog. Returns the dialog instance."""
        current_settings = self.settings._settings # Use shared manager
        dialog = IntegrationsDialog(self.root, self.dispatcher, current_settings)
        return dialog

    def handle_sync_with_gitlab(self, command: SyncWithGitLabCommand):
        """Unified sync handler via Command Bus."""
        if command.sync_type == 'push':
            unresolved = [i for i in self.workspace.all_items_iterable() if getattr(i, 'is_conflicted', False)]
            if unresolved:
                messagebox.showerror(
                    "Push Denied", 
                    f"Cannot complete operation. There are {len(unresolved)} unresolved merge conflicts.\n"
                    "Please resolve all highlighted conflicts before pushing changes."
                )
                return

        if not self._is_gitlab_configured():
            if messagebox.askyesno('Configuration Required', 'GitLab integration is not configured. Would you like to configure it now?'):
                dialog = self.handle_open_dialog()
                self.root.wait_window(dialog) # Pause execution until dialog closes
                
                if not self._is_gitlab_configured():
                    return # Still not configured after dialog closed
            else:
                return # User opted out

        if self._initialize_gitlab_client():
            self.progress_modal = SyncProgressModal(self.root, self.dispatcher)
            worker = SyncWorker(self.context, sync_type=command.sync_type)
            worker.start()

    def handle_sync_members(self, event: UISyncMembersRequestedEvent):
        """Fetches members from GitLab."""
        if not self._is_gitlab_configured():
            if messagebox.askyesno('Configuration Required', 'GitLab integration is not configured. Would you like to configure it now?'):
                dialog = self.handle_open_dialog()
                self.root.wait_window(dialog)
                if not self._is_gitlab_configured():
                    return
            else:
                return

        if self._initialize_gitlab_client():
            self.progress_modal = SyncProgressModal(self.root, self.dispatcher)
            worker = SyncWorker(self.context, sync_type='members')
            worker.start()

    def handle_sync_labels(self, event: UISyncLabelsRequestedEvent):
        """Fetches labels from GitLab."""
        if not self._is_gitlab_configured():
            if messagebox.askyesno('Configuration Required', 'GitLab integration is not configured. Would you like to configure it now?'):
                dialog = self.handle_open_dialog()
                self.root.wait_window(dialog)
                if not self._is_gitlab_configured():
                    return
            else:
                return

        if self._initialize_gitlab_client():
            self.progress_modal = SyncProgressModal(self.root, self.dispatcher)
            worker = SyncWorker(self.context, sync_type='labels')
            worker.start()

    def handle_sync_iterations(self, event: UISyncIterationsRequestedEvent):
        """Fetches iterations from GitLab."""
        if not self._is_gitlab_configured():
            if messagebox.askyesno('Configuration Required', 'GitLab integration is not configured. Would you like to configure it now?'):
                dialog = self.handle_open_dialog()
                self.root.wait_window(dialog)
                if not self._is_gitlab_configured():
                    return
            else:
                return

        if self._initialize_gitlab_client():
            self.progress_modal = SyncProgressModal(self.root, self.dispatcher)
            worker = SyncWorker(self.context, sync_type='iterations')
            worker.start()

    def handle_sync_error(self, event: ModelSyncErrorEvent):
        """Closes the progress modal and displays the error resolution modal."""
        if self.progress_modal and self.progress_modal.winfo_exists():
            self.progress_modal.destroy()
            self.progress_modal = None
        
        is_dark = ThemeManager.load_settings()
        SyncErrorModal(
            self.root, 
            event.title, 
            event.error_message, 
            event.suggested_solution, 
            debug_info=event.debug_info,
            is_dark=is_dark
        )

    def handle_conflict_detected(self, event: ModelConflictDetectedEvent):
        """Displays the conflict resolution modal on the main thread."""
        ConflictResolutionModal(self.root, self.dispatcher, event.local_item, event.remote_item)

    def _initialize_gitlab_client(self) -> bool:
        """Loads settings and registers the GitLabClient in the context."""
        active_product_name = self.workspace.active_product_name
        if not active_product_name:
            self.dispatcher.dispatch(UIErrorNotificationEvent(
                title="Selection Required", 
                message="Please select a Product in the tree before syncing with GitLab."
            ))
            return False
            
        # Find product entity in workspace
        product_entity = next((p for p in self.workspace.products if p.name == active_product_name), None)
        if not product_entity or not product_entity.gitlab_project_id:
            self.dispatcher.dispatch(UIErrorNotificationEvent(
                title="Configuration Error", 
                message=f"Product '{active_product_name}' has no GitLab Project ID configured. Configure it in Integrations Settings."
            ))
            return False

        url = self.settings.get('auth_url')
        pat = self.settings.get('auth_pat')
        gid = self.settings.get('epic_group_id')
        pid = str(product_entity.gitlab_project_id)
        
        epic_label = self.settings.get('epic_sync_label', 'Epic')
        feature_label = self.settings.get('feature_sync_label', 'Feature')

        # This check is redundant due to _is_gitlab_configured but kept for robustness
        if not url or not pat:
            self.dispatcher.dispatch(UIErrorNotificationEvent(
                title="Connection Error", 
                message="Please configure GitLab connection settings first."
            ))
            return False
            
        client = GitLabClient(url, pat, gid, pid, epic_sync_label=epic_label, feature_sync_label=feature_label)
        self.context.register('gitlab_client', client)
        return True

    def handle_global_tag_add(self, event: UIGlobalTagAddRequestedEvent):
        ThemeManager.update_integration_tag(event.tag_type, event.tag_value)

    def handle_global_tag_delete(self, event: UIGlobalTagDeleteRequestedEvent):
        ThemeManager.update_integration_tag(event.tag_type, event.tag_value)
        self.workspace.remove_global_tag(event.tag_type, event.tag_value)

    def handle_save_settings(self, event: UIIntegrationsSaveRequestedEvent):
        self.settings.set('auth_url', event.auth_url)
        self.settings.set('auth_pat', event.auth_pat)
        self.settings.set('epic_group_id', event.epic_group_id)
        self.settings.set('product_mappings', event.product_mappings)
        self.settings.set('product_project_ids', event.product_project_ids)
        self.settings.set('product_group_ids', event.product_group_ids)
        self.settings.set('capabilities', event.capabilities)
        self.settings.set('active_product_name', event.active_product_name)
        self.settings.set('epic_sync_label', event.epic_sync_label)
        self.settings.set('feature_sync_label', event.feature_sync_label)
        self.settings.set('legacy_status_enabled', event.legacy_status_enabled)
        self.settings.set('status_label_mappings', event.status_label_mappings)
        self.settings.save()
        
        # Keep ThemeManager in sync for other components that might still use it
        ThemeManager.save_integration_settings(
            auth_url=event.auth_url,
            auth_pat=event.auth_pat,
            epic_group_id=event.epic_group_id,
            product_mappings=event.product_mappings,
            capabilities=event.capabilities,
            product_project_ids=event.product_project_ids
        )

        # Update Workspace Products and Active Product
        from src.domain.entities import Product
        workspace_products = self.workspace.products
        
        # We need to iterate over all products mentioned in either project_ids or group_ids
        all_product_names = set(event.product_project_ids.keys()) | set(event.product_group_ids.keys())

        for name in all_product_names:
            proj_id = event.product_project_ids.get(name)
            grp_id = event.product_group_ids.get(name)
            existing = next((p for p in workspace_products if p.name == name), None)
            if existing:
                existing.gitlab_project_id = proj_id
                existing.gitlab_group_id = grp_id
            else:
                workspace_products.append(Product(name=name, gitlab_project_id=proj_id, gitlab_group_id=grp_id))
        
        self.workspace.products = workspace_products
        self.workspace.active_product_name = event.active_product_name
        
        # Trigger redraw
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
            root_items=self.workspace.get_epics(),
            products=self.workspace.products
        ))
