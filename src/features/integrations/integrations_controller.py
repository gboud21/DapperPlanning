import tkinter as tk
from tkinter import messagebox
from src.core.app_context import AppContext
from src.core.events import (
    EventDispatcher, UIIntegrationsDialogOpenRequestedEvent, UIIntegrationsSaveRequestedEvent,
    UIErrorNotificationEvent, UIGlobalTagAddRequestedEvent, UIGlobalTagDeleteRequestedEvent,
    UIGitLabPullRequestedEvent, UIGitLabPushRequestedEvent, ModelConflictDetectedEvent,
    ModelSyncErrorEvent, ModelHierarchyUpdatedEvent
)
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
        self.workspace = context.resolve('workspace')
        self.settings: SettingsManager = context.resolve('settings_manager')
        
        self.progress_modal = None
        self._subscribe_events()

    def _subscribe_events(self):
        self.dispatcher.subscribe(UIIntegrationsDialogOpenRequestedEvent, self.handle_open_dialog)
        self.dispatcher.subscribe(UIIntegrationsSaveRequestedEvent, self.handle_save_settings)
        self.dispatcher.subscribe(UIGlobalTagAddRequestedEvent, self.handle_global_tag_add)
        self.dispatcher.subscribe(UIGlobalTagDeleteRequestedEvent, self.handle_global_tag_delete)
        self.dispatcher.subscribe(UIGitLabPullRequestedEvent, self.handle_pull_request)
        self.dispatcher.subscribe(UIGitLabPushRequestedEvent, self.handle_push_request)
        self.dispatcher.subscribe(ModelConflictDetectedEvent, self.handle_conflict_detected)
        self.dispatcher.subscribe(ModelSyncErrorEvent, self.handle_sync_error)

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

    def handle_pull_request(self, event: UIGitLabPullRequestedEvent):
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
            worker = SyncWorker(self.context, sync_type='pull')
            worker.start()

    def handle_push_request(self, event: UIGitLabPushRequestedEvent):
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
            worker = SyncWorker(self.context, sync_type='push')
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

        # This check is redundant due to _is_gitlab_configured but kept for robustness
        if not url or not pat:
            self.dispatcher.dispatch(UIErrorNotificationEvent(
                title="Connection Error", 
                message="Please configure GitLab connection settings first."
            ))
            return False
            
        client = GitLabClient(url, pat, gid, pid)
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
        self.settings.set('capabilities', event.capabilities)
        self.settings.set('active_product_name', event.active_product_name)
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
        
        for name, proj_id in event.product_project_ids.items():
            existing = next((p for p in workspace_products if p.name == name), None)
            if existing:
                existing.gitlab_project_id = proj_id
            else:
                workspace_products.append(Product(name=name, gitlab_project_id=proj_id))
        
        self.workspace.products = workspace_products
        self.workspace.active_product_name = event.active_product_name
        
        # Trigger redraw
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
            root_items=self.workspace.get_epics(),
            products=self.workspace.products
        ))
