import os
from src.events import (
    EventDispatcher, UISyncRequestedEvent, UIExportCsvRequestedEvent, UIExportJsonRequestedEvent,
    UIImportCsvRequestedEvent, UIImportJsonRequestedEvent, ModelHierarchyUpdatedEvent,
    UIErrorNotificationEvent, UIThemeToggleRequestedEvent, AppThemeChangedEvent
)
from src.models.workspace import Workspace
from .tree_controller import TreeController
from .editor_controller import EditorController
from .menu_controller import MenuController
from .integrations_controller import IntegrationsController
from src.utils.adapters import DataAdapterFactory
from src.utils.theme_manager import ThemeManager

class MainController:
    def __init__(self, dispatcher: EventDispatcher, workspace: Workspace, root_window):
        """
        Initializes the MainController and its sub-controllers.

        Args:
            dispatcher (EventDispatcher): The application's event dispatcher.
            workspace (Workspace): The model representing the agile workspace.
            root_window: The root Tkinter window reference.
        """
        self.dispatcher = dispatcher
        self.workspace = workspace
        self.root = root_window
        
        # Instantiate sub-controllers
        self.tree_controller = TreeController(dispatcher, workspace)
        self.editor_controller = EditorController(dispatcher, workspace)
        self.menu_controller = MenuController(dispatcher, workspace)
        self.integrations_controller = IntegrationsController(self.root, dispatcher, workspace)
        
        self._subscribe_events()

        # Load initial theme state and notify view
        is_dark = ThemeManager.load_settings()
        self.dispatcher.dispatch(AppThemeChangedEvent(is_dark=is_dark))

    def _subscribe_events(self):
        """Subscribes to overarching application events."""
        self.dispatcher.subscribe(UISyncRequestedEvent, self.handle_sync)

    def handle_sync(self, event: UISyncRequestedEvent):
        """Handles synchronization with external services (GitLab)."""
        if self.integrations_controller.validate_sync_readiness(self.workspace):
            # Proceed with sync logic
            pass
