from typing import List, Dict, Any
from src.models.entities import Product, Capability, Epic, Feature, Story, Team

class HierarchyFlattener:
    @staticmethod
    def flatten(products: List[Product]) -> List[Dict[str, Any]]:
        rows = []
        def _flatten(items, parent_id=None):
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
                    _flatten(item.capabilities, item.id)
                elif item_type == "Capability" and hasattr(item, 'epics'):
                    _flatten(item.epics, item.id)
                elif item_type == "Epic" and hasattr(item, 'features'):
                    _flatten(item.features, item.id)
                elif item_type == "Feature" and hasattr(item, 'stories'):
                    _flatten(item.stories, item.id)
        
        _flatten(products)
        return rows

class HierarchyBuilder:
    @staticmethod
    def build_from_flat_dict(rows: List[Dict[str, Any]]) -> List[Product]:
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
            team_name = row.get('Team', '')
            
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
        
        return root_products

    @staticmethod
    def build_from_nested_dict(data: List[Dict[str, Any]]) -> List[Product]:
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

        return [dict_to_obj(p_dict, "Product") for p_dict in data]
