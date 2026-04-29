import csv
import json
from dataclasses import asdict
from src.events import (
    EventDispatcher, UISyncRequestedEvent, UIExportCsvRequestedEvent, UIExportJsonRequestedEvent,
    UIImportCsvRequestedEvent, UIImportJsonRequestedEvent, ModelHierarchyUpdatedEvent
)
from src.models.workspace import Workspace
from src.models.entities import Product, Capability, Epic, Feature, Story, Team
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
        self.dispatcher.subscribe(UIExportJsonRequestedEvent, self.handle_json_export)
        self.dispatcher.subscribe(UIImportCsvRequestedEvent, self.handle_csv_import)
        self.dispatcher.subscribe(UIImportJsonRequestedEvent, self.handle_json_import)

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

    def handle_json_export(self, event: UIExportJsonRequestedEvent):
        """
        Exports the hierarchical data from the workspace to a JSON file.
        """
        products = self.workspace.get_products()
        data = [asdict(p) for p in products]

        try:
            with open(event.file_path, mode='w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, indent=4)
        except Exception as e:
            print(f"Error exporting JSON: {e}")

    def handle_csv_import(self, event: UIImportCsvRequestedEvent):
        """
        Imports entities from a CSV file and reconstructs the hierarchy.
        """
        try:
            with open(event.file_path, mode='r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                
                # 1. Create objects and map by ID
                id_map = {}
                parent_map = {}
                root_products = []
                
                for row in rows:
                    item_id = row['ID']
                    item_type = row['Item Type']
                    parent_id = row['Parent ID']
                    title = row['Title']
                    description = row['Description']
                    team_name = row['Team']
                    
                    team = Team(name=team_name) if team_name else None
                    
                    if item_type == "Product":
                        obj = Product(id=item_id, title=title, description=description)
                    elif item_type == "Capability":
                        obj = Capability(id=item_id, title=title, description=description)
                    elif item_type == "Epic":
                        obj = Epic(id=item_id, title=title, description=description)
                    elif item_type == "Feature":
                        obj = Feature(id=item_id, title=title, description=description, team=team)
                    elif item_type == "Story":
                        obj = Story(id=item_id, title=title, description=description, team=team)
                    else:
                        continue
                        
                    id_map[item_id] = obj
                    parent_map[item_id] = parent_id
                    
                # 2. Reconstruct hierarchy
                for item_id, obj in id_map.items():
                    parent_id = parent_map[item_id]
                    if not parent_id:
                        if isinstance(obj, Product):
                            root_products.append(obj)
                        continue
                        
                    parent_obj = id_map.get(parent_id)
                    if not parent_obj:
                        continue
                        
                    if isinstance(obj, Capability) and isinstance(parent_obj, Product):
                        parent_obj.capabilities.append(obj)
                    elif isinstance(obj, Epic) and isinstance(parent_obj, Capability):
                        parent_obj.epics.append(obj)
                    elif isinstance(obj, Feature) and isinstance(parent_obj, Epic):
                        parent_obj.features.append(obj)
                    elif isinstance(obj, Story) and isinstance(parent_obj, Feature):
                        parent_obj.stories.append(obj)

                # 3. Update Workspace
                self.workspace._products = root_products
                self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=root_products))
                
        except Exception as e:
            print(f"Error importing CSV: {e}")

    def handle_json_import(self, event: UIImportJsonRequestedEvent):
        """
        Imports entities from a JSON file.
        """
        try:
            with open(event.file_path, mode='r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                def dict_to_obj(d, item_type):
                    if item_type == "Product":
                        caps = [dict_to_obj(c, "Capability") for c in d.get("capabilities", [])]
                        return Product(id=d["id"], title=d["title"], description=d["description"], capabilities=caps)
                    elif item_type == "Capability":
                        epics = [dict_to_obj(e, "Epic") for e in d.get("epics", [])]
                        return Capability(id=d["id"], title=d["title"], description=d["description"], epics=epics)
                    elif item_type == "Epic":
                        features = [dict_to_obj(f, "Feature") for f in d.get("features", [])]
                        return Epic(id=d["id"], title=d["title"], description=d["description"], features=features)
                    elif item_type == "Feature":
                        stories = [dict_to_obj(s, "Story") for s in d.get("stories", [])]
                        team = Team(**d["team"]) if d.get("team") else None
                        return Feature(id=d["id"], title=d["title"], description=d["description"], team=team, stories=stories)
                    elif item_type == "Story":
                        team = Team(**d["team"]) if d.get("team") else None
                        return Story(id=d["id"], title=d["title"], description=d["description"], team=team)
                    return None

                root_products = [dict_to_obj(p_dict, "Product") for p_dict in data]
                
                # Update Workspace
                self.workspace._products = root_products
                self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=root_products))
                
        except Exception as e:
            print(f"Error importing JSON: {e}")
