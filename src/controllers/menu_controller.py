import os
from src.events import (
    EventDispatcher, UIExportCsvRequestedEvent, UIExportJsonRequestedEvent, 
    UIImportCsvRequestedEvent, UIImportJsonRequestedEvent, ModelHierarchyUpdatedEvent, 
    UIErrorNotificationEvent, UIThemeToggleRequestedEvent, AppThemeChangedEvent
)
from src.models.workspace import Workspace
from src.utils.adapters import DataAdapterFactory
from src.utils.theme_manager import ThemeManager

class MenuController:
    def __init__(self, dispatcher: EventDispatcher, workspace: Workspace):
        """
        Initializes the MenuController.

        Args:
            dispatcher (EventDispatcher): The application's event dispatcher.
            workspace (Workspace): The model representing the agile workspace.
        """
        self.dispatcher = dispatcher
        self.workspace = workspace
        self._subscribe_events()

    def _subscribe_events(self):
        """Subscribes to menu-related application events."""
        self.dispatcher.subscribe(UIExportCsvRequestedEvent, self.handle_csv_export)
        self.dispatcher.subscribe(UIExportJsonRequestedEvent, self.handle_json_export)
        self.dispatcher.subscribe(UIImportCsvRequestedEvent, self.handle_csv_import)
        self.dispatcher.subscribe(UIImportJsonRequestedEvent, self.handle_json_import)
        self.dispatcher.subscribe(UIThemeToggleRequestedEvent, self.handle_theme_toggle)

    def handle_theme_toggle(self, event: UIThemeToggleRequestedEvent):
        """Handles theme toggle requests from the UI."""
        ThemeManager.save_settings(event.is_dark)
        self.dispatcher.dispatch(AppThemeChangedEvent(is_dark=event.is_dark))

    def handle_csv_export(self, event: UIExportCsvRequestedEvent):
        """Handles CSV export requests."""
        try:
            ext = os.path.splitext(event.file_path)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            adapter.export_data(event.file_path, self.workspace.get_epics())
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(title="Export Error", message=str(e)))

    def handle_json_export(self, event: UIExportJsonRequestedEvent):
        """Handles JSON export requests."""
        try:
            ext = os.path.splitext(event.file_path)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            adapter.export_data(event.file_path, self.workspace.get_epics())
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(title="Export Error", message=str(e)))

    def handle_csv_import(self, event: UIImportCsvRequestedEvent):
        """Handles CSV import requests."""
        try:
            ext = os.path.splitext(event.file_path)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            root_epics = adapter.import_data(event.file_path)
            
            # Update Workspace
            self.workspace._epics = root_epics
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=root_epics))
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(title="Import Error", message=str(e)))

    def handle_json_import(self, event: UIImportJsonRequestedEvent):
        """Handles JSON import requests."""
        try:
            ext = os.path.splitext(event.file_path)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            root_epics = adapter.import_data(event.file_path)
            
            # Update Workspace
            self.workspace._epics = root_epics
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=root_epics))
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(title="Import Error", message=str(e)))
