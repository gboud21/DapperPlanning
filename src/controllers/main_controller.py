import csv
from src.events import (
    EventDispatcher, UISyncRequestedEvent, UIExportCsvRequestedEvent
)
from src.models.workspace import Workspace
from .tree_controller import TreeController
from .editor_controller import EditorController

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

    def _subscribe_events(self):
        """Subscribes to overarching application events."""
        self.dispatcher.subscribe(UISyncRequestedEvent, self.handle_sync)
        self.dispatcher.subscribe(UIExportCsvRequestedEvent, self.handle_csv_export)

    def handle_sync(self, event: UISyncRequestedEvent):
        """Handles synchronization with external services (GitLab)."""
        # Overarching logic for syncing would remain here or be delegated to a service
        pass

    def handle_csv_export(self, event: UIExportCsvRequestedEvent):
        """
        Flattens the hierarchical data from the workspace and exports it to a CSV file.
        """
        fieldnames = ['Item Type', 'ID', 'Parent ID', 'Title', 'Description', 'Team']
        rows = []

        def flatten(items, parent_id=None):
            for item in items:
                item_type = type(item).__name__
                team_name = ""
                if hasattr(item, 'team') and item.team:
                    team_name = item.team.name
                
                rows.append({
                    'Item Type': item_type,
                    'ID': item.id,
                    'Parent ID': parent_id if parent_id else "",
                    'Title': item.title,
                    'Description': item.description,
                    'Team': team_name
                })
                
                # Recursive traversal
                if item_type == "Product" and hasattr(item, 'capabilities'):
                    flatten(item.capabilities, item.id)
                elif item_type == "Capability" and hasattr(item, 'epics'):
                    flatten(item.epics, item.id)
                elif item_type == "Epic" and hasattr(item, 'features'):
                    flatten(item.features, item.id)
                elif item_type == "Feature" and hasattr(item, 'stories'):
                    flatten(item.stories, item.id)

        # Start flattening from root products
        flatten(self.workspace.get_products())

        try:
            with open(event.file_path, mode='w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e:
            # In a real app, we'd dispatch an error event or show a dialog
            print(f"Error exporting CSV: {e}")
