import os
import tkinter as tk
from src.events import (
    EventDispatcher, UISyncRequestedEvent, UIExportCsvRequestedEvent, UIExportJsonRequestedEvent,
    UIImportCsvRequestedEvent, UIImportJsonRequestedEvent, ModelHierarchyUpdatedEvent,
    UIErrorNotificationEvent, UIThemeToggleRequestedEvent, AppThemeChangedEvent,
    ModelWorkspaceLoadedEvent, UIWindowStateChangedEvent
)
from src.models.workspace import Workspace
from .tree_controller import TreeController
from .editor_controller import EditorController
from .menu_controller import MenuController
from .integrations_controller import IntegrationsController
from .settings_controller import SettingsController
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
        self.settings_controller = SettingsController(self.root, dispatcher)
        
        self._subscribe_events()

        # Load initial theme state and notify view
        is_dark = ThemeManager.load_settings()
        self.dispatcher.dispatch(AppThemeChangedEvent(is_dark=is_dark))

        # Load window maximized state
        if ThemeManager.get_window_maximized():
            self._apply_maximized_state()

        # Load last workspace if it exists
        last_workspace = ThemeManager.get_last_workspace()
        if last_workspace and os.path.exists(last_workspace):
            self._load_initial_workspace(last_workspace)

    def _apply_maximized_state(self):
        """Applies the maximized state to the root window."""
        try:
            self.root.state("zoomed")
        except tk.TclError:
            try:
                self.root.attributes("-zoomed", True)
            except tk.TclError:
                pass

    def _load_initial_workspace(self, file_path: str):
        """Loads the workspace data from the provided file path at startup."""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            root_epics = adapter.import_data(file_path)
            
            self.workspace._epics = root_epics
            self.workspace.current_filepath = file_path
            
            # Notify views to update
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=root_epics))
            self.dispatcher.dispatch(ModelWorkspaceLoadedEvent(filepath=file_path))
        except Exception as e:
            # Silently fail initial load if file is corrupt, or notify via event
            print(f"Failed to load initial workspace: {e}")

    def _subscribe_events(self):
        """Subscribes to overarching application events."""
        self.dispatcher.subscribe(UISyncRequestedEvent, self.handle_sync)
        self.dispatcher.subscribe(UIWindowStateChangedEvent, self.handle_window_state_changed)

    def handle_sync(self, event: UISyncRequestedEvent):
        """Handles synchronization with external services (GitLab)."""
        if self.integrations_controller.validate_sync_readiness(self.workspace):
            # Proceed with sync logic
            pass

    def handle_window_state_changed(self, event: UIWindowStateChangedEvent):
        """Saves the window maximized state when it changes."""
        ThemeManager.set_window_maximized(event.is_maximized)
