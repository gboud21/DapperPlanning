import os
from tkinter import filedialog, messagebox
from src.core.app_context import AppContext
from src.core.events import (
    EventDispatcher, UIExportCsvRequestedEvent, UIExportJsonRequestedEvent, 
    UIImportCsvRequestedEvent, UIImportJsonRequestedEvent, ModelHierarchyUpdatedEvent, 
    UIErrorNotificationEvent, UIThemeToggleRequestedEvent, AppThemeChangedEvent,
    UIOpenWorkspaceRequestedEvent, UISaveWorkspaceRequestedEvent, UISaveAsWorkspaceRequestedEvent,
    ModelWorkspaceLoadedEvent, UINewWorkspaceRequestedEvent
)
from src.domain.workspace import Workspace
from src.infrastructure.storage.adapters import DataAdapterFactory
from src.utils.theme_manager import ThemeManager

class MenuController:
    def __init__(self, context: AppContext):
        """
        Initializes the MenuController.

        Args:
            context (AppContext): The application context for dependency injection.
        """
        self.context = context
        self.dispatcher: EventDispatcher = context.resolve('event_dispatcher')
        self.workspace: Workspace = context.resolve('workspace')
        self._subscribe_events()

    def _subscribe_events(self):
        """Subscribes to menu-related application events."""
        self.dispatcher.subscribe(UIExportCsvRequestedEvent, self.handle_csv_export)
        self.dispatcher.subscribe(UIExportJsonRequestedEvent, self.handle_json_export)
        self.dispatcher.subscribe(UIImportCsvRequestedEvent, self.handle_csv_import)
        self.dispatcher.subscribe(UIImportJsonRequestedEvent, self.handle_json_import)
        self.dispatcher.subscribe(UIThemeToggleRequestedEvent, self.handle_theme_toggle)
        self.dispatcher.subscribe(UIOpenWorkspaceRequestedEvent, self.handle_open_workspace)
        self.dispatcher.subscribe(UISaveWorkspaceRequestedEvent, self.handle_save_workspace)
        self.dispatcher.subscribe(UISaveAsWorkspaceRequestedEvent, self.handle_save_as_workspace)
        self.dispatcher.subscribe(UINewWorkspaceRequestedEvent, self.handle_new_workspace)

    def handle_theme_toggle(self, event: UIThemeToggleRequestedEvent):
        """Handles theme toggle requests from the UI."""
        ThemeManager.save_settings(event.is_dark)
        self.dispatcher.dispatch(AppThemeChangedEvent(is_dark=event.is_dark))

    def handle_new_workspace(self, event: UINewWorkspaceRequestedEvent):
        """Handles requests to create a new, empty workspace."""
        if self.workspace.has_unsaved_changes():
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before creating a new workspace?"
            )
            if response is True:
                self.handle_save_workspace(UISaveWorkspaceRequestedEvent())
                if self.workspace.has_unsaved_changes():
                    return # Save was cancelled or failed
            elif response is None:
                return # User cancelled the New operation

        self.workspace.clear()
        self.workspace.mark_as_clean()
        self.dispatcher.dispatch(ModelWorkspaceLoadedEvent(filepath=None))
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=[]))

    def handle_open_workspace(self, event: UIOpenWorkspaceRequestedEvent):
        """Handles requests to open a workspace from a file."""
        if self.workspace.has_unsaved_changes():
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before opening a new workspace?"
            )
            if response is True:
                self.handle_save_workspace(UISaveWorkspaceRequestedEvent())
                if self.workspace.has_unsaved_changes():
                    return # Save was cancelled or failed
            elif response is None:
                return # User cancelled the Open operation

        file_path = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        try:
            ext = os.path.splitext(file_path)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            root_epics, active_product, products = adapter.import_data(file_path)
            
            # Update Workspace
            self.workspace._epics = root_epics
            self.workspace.products = products
            self.workspace.active_product_name = active_product
            self.workspace.current_filepath = file_path
            ThemeManager.set_last_workspace(file_path)
            
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=root_epics))
            self.dispatcher.dispatch(ModelWorkspaceLoadedEvent(filepath=file_path))
            self.workspace.mark_as_clean()
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(title="Open Error", message=str(e)))

    def handle_save_workspace(self, event: UISaveWorkspaceRequestedEvent):
        """Handles requests to save the current workspace."""
        if not self.workspace.current_filepath:
            self.handle_save_as_workspace(UISaveAsWorkspaceRequestedEvent())
            return

        try:
            ext = os.path.splitext(self.workspace.current_filepath)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            adapter.export_data(
                self.workspace.current_filepath, 
                self.workspace.get_epics(),
                active_product_name=self.workspace.active_product_name,
                products=self.workspace.products
            )
            self.workspace.mark_as_clean()
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(title="Save Error", message=str(e)))

    def handle_save_as_workspace(self, event: UISaveAsWorkspaceRequestedEvent):
        """Handles requests to save the current workspace to a new file."""
        file_path = filedialog.asksaveasfilename(
            filetypes=[("JSON Files", "*.json"), ("CSV Files", "*.csv")],
            defaultextension=".json"
        )
        if not file_path:
            return

        try:
            ext = os.path.splitext(file_path)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            adapter.export_data(
                file_path, 
                self.workspace.get_epics(),
                active_product_name=self.workspace.active_product_name,
                products=self.workspace.products
            )
            
            self.workspace.current_filepath = file_path
            ThemeManager.set_last_workspace(file_path)
            self.dispatcher.dispatch(ModelWorkspaceLoadedEvent(filepath=file_path))
            self.workspace.mark_as_clean()
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(title="Save As Error", message=str(e)))

    def handle_csv_export(self, event: UIExportCsvRequestedEvent):
        """Handles CSV export requests."""
        try:
            ext = os.path.splitext(event.file_path)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            adapter.export_data(event.file_path, self.workspace.get_epics(), active_product_name=self.workspace.active_product_name, products=self.workspace.products)
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(title="Export Error", message=str(e)))

    def handle_json_export(self, event: UIExportJsonRequestedEvent):
        """Handles JSON export requests."""
        try:
            ext = os.path.splitext(event.file_path)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            adapter.export_data(event.file_path, self.workspace.get_epics(), active_product_name=self.workspace.active_product_name, products=self.workspace.products)
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(title="Export Error", message=str(e)))

    def handle_csv_import(self, event: UIImportCsvRequestedEvent):
        """Handles CSV import requests."""
        try:
            ext = os.path.splitext(event.file_path)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            root_epics, active_product, products = adapter.import_data(event.file_path)
            
            # Update Workspace
            self.workspace._epics = root_epics
            if active_product:
                self.workspace.active_product_name = active_product
            if products:
                self.workspace.products = products
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=root_epics))
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(title="Import Error", message=str(e)))

    def handle_json_import(self, event: UIImportJsonRequestedEvent):
        """Handles JSON import requests."""
        try:
            ext = os.path.splitext(event.file_path)[1].lower()
            adapter = DataAdapterFactory.get_adapter(ext)
            root_epics, active_product, products = adapter.import_data(event.file_path)
            
            # Update Workspace
            self.workspace._epics = root_epics
            if active_product:
                self.workspace.active_product_name = active_product
            if products:
                self.workspace.products = products
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=root_epics))
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(title="Import Error", message=str(e)))
