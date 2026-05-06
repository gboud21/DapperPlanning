import os
from src.events import (
    EventDispatcher, UISyncRequestedEvent, UIExportCsvRequestedEvent, UIExportJsonRequestedEvent,
    UIImportCsvRequestedEvent, UIImportJsonRequestedEvent, ModelHierarchyUpdatedEvent,
    UIErrorNotificationEvent, UIThemeToggleRequestedEvent, AppThemeChangedEvent
)
from src.models.workspace import Workspace
from .tree_controller import TreeController
from .editor_controller import EditorController
from src.utils.adapters import DataAdapterFactory
from src.utils.theme_manager import ThemeManager

class MainController:
    def __init__(self, dispatcher: EventDispatcher, workspace: Workspace):
        """
        Initializes the MainController and its sub-controllers.

        Args:
            dispatcher (EventDispatcher): The application's event dispatcher.
            workspace (Workspace): The model representing the agile workspace.
        """
        self.dispatcher = dispatcher
        self.workspace = workspace
        
        # Instantiate sub-controllers
        self.tree_controller = TreeController(dispatcher, workspace)
        self.editor_controller = EditorController(dispatcher, workspace)
        
        self._subscribe_events()

        # Load initial theme state and notify view
        is_dark = ThemeManager.load_settings()
        self.dispatcher.dispatch(AppThemeChangedEvent(is_dark=is_dark))

    def _subscribe_events(self):
        """Subscribes to overarching application events."""
        self.dispatcher.subscribe(UISyncRequestedEvent, self.handle_sync)
        self.dispatcher.subscribe(UIExportCsvRequestedEvent, self.handle_csv_export)
        self.dispatcher.subscribe(UIExportJsonRequestedEvent, self.handle_json_export)
        self.dispatcher.subscribe(UIImportCsvRequestedEvent, self.handle_csv_import)
        self.dispatcher.subscribe(UIImportJsonRequestedEvent, self.handle_json_import)
        self.dispatcher.subscribe(UIThemeToggleRequestedEvent, self.handle_theme_toggle)

    def handle_theme_toggle(self, event: UIThemeToggleRequestedEvent):
        """Handles theme toggle requests from the UI."""
        ThemeManager.save_settings(event.is_dark)
        self.dispatcher.dispatch(AppThemeChangedEvent(is_dark=event.is_dark))

    def handle_sync(self, event: UISyncRequestedEvent):
        """Handles synchronization with external services (GitLab)."""
        # Overarching logic for syncing would remain here or be delegated to a service
        pass

    def handle_csv_export(self, event: UIExportCsvRequestedEvent):
        """
        Flattens the hierarchical data from the workspace and exports it to a CSV file.
        """
        try:
            ext = os.path.splitext(event.file_path)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            adapter.export_data(event.file_path, self.workspace.get_products())
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(title="Export Error", message=str(e)))

    def handle_json_export(self, event: UIExportJsonRequestedEvent):
        """
        Exports the hierarchical data from the workspace to a JSON file.
        """
        try:
            ext = os.path.splitext(event.file_path)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            adapter.export_data(event.file_path, self.workspace.get_products())
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(title="Export Error", message=str(e)))

    def handle_csv_import(self, event: UIImportCsvRequestedEvent):
        """
        Imports entities from a CSV file and reconstructs the hierarchy.
        """
        try:
            ext = os.path.splitext(event.file_path)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            root_products = adapter.import_data(event.file_path)
            
            # Update Workspace
            self.workspace._products = root_products
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=root_products))
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(title="Import Error", message=str(e)))

    def handle_json_import(self, event: UIImportJsonRequestedEvent):
        """
        Imports entities from a JSON file.
        """
        try:
            ext = os.path.splitext(event.file_path)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            root_products = adapter.import_data(event.file_path)
            
            # Update Workspace
            self.workspace._products = root_products
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=root_products))
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(title="Import Error", message=str(e)))
