from src.events import (
    EventDispatcher, UIIntegrationsDialogOpenRequestedEvent, UIIntegrationsSaveRequestedEvent,
    UIErrorNotificationEvent
)
from src.utils.theme_manager import ThemeManager
from src.views.integrations_dialog import IntegrationsDialog
import tkinter as tk

class IntegrationsController:
    def __init__(self, root: tk.Tk, dispatcher: EventDispatcher, workspace):
        """
        Initializes the IntegrationsController.

        Args:
            root (tk.Tk): The root Tkinter window.
            dispatcher (EventDispatcher): The application's event dispatcher.
            workspace: The model representing the agile workspace.
        """
        self.root = root
        self.dispatcher = dispatcher
        self.workspace = workspace
        
        self._subscribe_events()

    def _subscribe_events(self):
        self.dispatcher.subscribe(UIIntegrationsDialogOpenRequestedEvent, self.handle_open_dialog)
        self.dispatcher.subscribe(UIIntegrationsSaveRequestedEvent, self.handle_save_settings)

    def handle_open_dialog(self, event: UIIntegrationsDialogOpenRequestedEvent):
        current_settings = ThemeManager.get_integration_settings()
        # Instantiate the dialog, it handles its own UI lifecycle but dispatches save events
        IntegrationsDialog(self.root, self.dispatcher, current_settings)

    def handle_save_settings(self, event: UIIntegrationsSaveRequestedEvent):
        ThemeManager.save_integration_settings(
            auth_url=event.auth_url,
            auth_pat=event.auth_pat,
            epic_group_id=event.epic_group_id,
            product_mappings=event.product_mappings,
            capabilities=event.capabilities
        )

    def validate_sync_readiness(self, workspace) -> bool:
        """
        Stubs validation to ensure all items have mapped products.
        """
        settings = ThemeManager.get_integration_settings()
        mappings = settings.get('product_mappings', {})

        for epic in workspace.get_epics():
            for prod in getattr(epic, 'products', []):
                if prod not in mappings:
                    self.dispatcher.dispatch(UIErrorNotificationEvent(
                        title="Sync Error",
                        message=f"Missing Project ID mapping for Product: {prod}"
                    ))
                    return False
            
            for feature in epic.features:
                for prod in getattr(feature, 'products', []):
                    if prod not in mappings:
                        self.dispatcher.dispatch(UIErrorNotificationEvent(
                            title="Sync Error",
                            message=f"Missing Project ID mapping for Product: {prod}"
                        ))
                        return False
                
                for story in feature.stories:
                    for prod in getattr(story, 'products', []):
                        if prod not in mappings:
                            self.dispatcher.dispatch(UIErrorNotificationEvent(
                                title="Sync Error",
                                message=f"Missing Project ID mapping for Product: {prod}"
                            ))
                            return False
        return True
