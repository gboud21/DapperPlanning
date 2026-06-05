import os
import tkinter as tk
from tkinter import messagebox
from src.core.app_context import AppContext
from src.core.events import (
    EventDispatcher, UISyncRequestedEvent, UIExportCsvRequestedEvent, UIExportJsonRequestedEvent,
    UIImportCsvRequestedEvent, UIImportJsonRequestedEvent, ModelHierarchyUpdatedEvent,
    UIErrorNotificationEvent, UIThemeToggleRequestedEvent, AppThemeChangedEvent,
    ModelWorkspaceLoadedEvent, UIWindowStateChangedEvent, UIAppCloseRequestedEvent,
    UISaveWorkspaceRequestedEvent
)
from src.domain.workspace import Workspace
from src.domain.repositories import WorkspaceRepository
from src.features.agile_planning.tree_controller import TreeController
from src.features.agile_planning.editor_controller import EditorController
from src.core.menu_controller import MenuController
from src.features.integrations.integrations_controller import IntegrationsController
from src.features.settings.settings_controller import SettingsController
from src.utils.theme_manager import ThemeManager

class MainController:
    def __init__(self, context: AppContext):
        """
        Initializes the MainController and its sub-controllers.

        Args:
            context (AppContext): The application context for dependency injection.
        """
        self.context = context
        self.dispatcher: EventDispatcher = context.resolve('event_dispatcher')
        self.workspace: Workspace = context.resolve('workspace')
        self.repository: WorkspaceRepository = context.resolve('workspace_repository')
        self.root: tk.Tk = context.resolve('root_window')
        
        # Instantiate sub-controllers passing the context
        self.tree_controller = TreeController(context)
        self.editor_controller = EditorController(context)
        self.menu_controller = MenuController(context)
        self.integrations_controller = IntegrationsController(context)
        self.settings_controller = SettingsController(context)
        
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
            self._load_initial_workspace()

    def _apply_maximized_state(self):
        """Applies the maximized state to the root window."""
        try:
            self.root.state("zoomed")
        except tk.TclError:
            try:
                self.root.attributes("-zoomed", True)
            except tk.TclError:
                pass

    def _load_initial_workspace(self):
        """Loads the workspace data using the repository at startup."""
        try:
            self.workspace = self.repository.load()
            # Update context to ensure other controllers can resolve the loaded workspace if needed
            self.context.register('workspace', self.workspace)
            
            # Notify views to update
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=self.workspace.get_epics()))
            if self.workspace.current_filepath:
                self.dispatcher.dispatch(ModelWorkspaceLoadedEvent(filepath=self.workspace.current_filepath))
        except Exception as e:
            # Silently fail initial load if file is corrupt, or notify via event
            print(f"Failed to load initial workspace: {e}")

    def _subscribe_events(self):
        """Subscribes to overarching application events."""
        self.dispatcher.subscribe(UISyncRequestedEvent, self.handle_sync)
        self.dispatcher.subscribe(UIWindowStateChangedEvent, self.handle_window_state_changed)
        self.dispatcher.subscribe(UIAppCloseRequestedEvent, self.handle_app_close)

    def handle_app_close(self, event: UIAppCloseRequestedEvent):
        """Intercepts application close to check for unsaved changes."""
        if not self.workspace.has_unsaved_changes():
            self.root.destroy()
            return

        response = messagebox.askyesnocancel(
            "Unsaved Changes",
            "You have unsaved changes. Do you want to save before exiting?"
        )

        if response is True:  # Yes
            # Trigger save via MenuController's logic
            # Since events are dispatched and handled synchronously in the main thread:
            self.dispatcher.dispatch(UISaveWorkspaceRequestedEvent())
            # After save attempt, we check again if it's clean (save might have been cancelled in 'Save As' dialog)
            if not self.workspace.has_unsaved_changes():
                self.root.destroy()
        elif response is False:  # No
            self.root.destroy()
        # If response is None (Cancel), we do nothing, effectively aborting the close.

    def handle_sync(self, event: UISyncRequestedEvent):
        """Handles synchronization with external services (GitLab)."""
        if self.integrations_controller.validate_sync_readiness(self.workspace):
            # Proceed with sync logic
            pass

    def handle_window_state_changed(self, event: UIWindowStateChangedEvent):
        """Saves the window maximized state when it changes."""
        ThemeManager.set_window_maximized(event.is_maximized)
