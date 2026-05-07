from typing import List, Dict, Any
from src.models.entities import Epic, Feature, Story, Team

class HierarchyFlattener:
    @staticmethod
    def flatten(epics: List[Epic]) -> List[Dict[str, Any]]:
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
                    'Team': team_name,
                    'Products': ",".join(getattr(item, 'products', [])),
                    'Capabilities': ",".join(getattr(item, 'capabilities', []))
                })
                
                # Recursive traversal
                if item_type == "Epic" and hasattr(item, 'features'):
                    _flatten(item.features, item.id)
                elif item_type == "Feature" and hasattr(item, 'stories'):
                    _flatten(item.stories, item.id)
        
        _flatten(epics)
        return rows

class HierarchyBuilder:
    @staticmethod
    def build_from_flat_dict(rows: List[Dict[str, Any]]) -> List[Epic]:
        # 1. Create objects and map by ID
        id_map = {}
        parent_map = {}
        root_epics = []
        
        for row in rows:
            item_id = row['ID']
            item_type = row['Item Type']
            parent_id = row['Parent ID']
            title = row['Title']
            description = row['Description']
            team_name = row.get('Team', '')
            products = [p.strip() for p in row.get('Products', '').split(',') if p.strip()]
            capabilities = [c.strip() for c in row.get('Capabilities', '').split(',') if c.strip()]
            
            team = Team(name=team_name) if team_name else None
            
            if item_type == "Epic":
                obj = Epic(id=item_id, title=title, description=description, products=products, capabilities=capabilities)
            elif item_type == "Feature":
                obj = Feature(id=item_id, title=title, description=description, team=team, products=products, capabilities=capabilities)
            elif item_type == "Story":
                obj = Story(id=item_id, title=title, description=description, team=team, products=products, capabilities=capabilities)
            else:
                continue
                
            id_map[item_id] = obj
            parent_map[item_id] = parent_id
            
        # 2. Reconstruct hierarchy
        for item_id, obj in id_map.items():
            parent_id = parent_map[item_id]
            if not parent_id:
                if isinstance(obj, Epic):
                    root_epics.append(obj)
                continue
                
            parent_obj = id_map.get(parent_id)
            if not parent_obj:
                continue
                
            if isinstance(obj, Feature) and isinstance(parent_obj, Epic):
                parent_obj.features.append(obj)
            elif isinstance(obj, Story) and isinstance(parent_obj, Feature):
                parent_obj.stories.append(obj)
        
        return root_epics

    @staticmethod
    def build_from_nested_dict(data: List[Dict[str, Any]]) -> List[Epic]:
        def dict_to_obj(d, item_type):
            products = d.get("products", [])
            capabilities = d.get("capabilities", [])
            if item_type == "Epic":
                features = [dict_to_obj(f, "Feature") for f in d.get("features", [])]
                return Epic(id=d["id"], title=d["title"], description=d["description"], features=features, products=products, capabilities=capabilities)
            elif item_type == "Feature":
                stories = [dict_to_obj(s, "Story") for s in d.get("stories", [])]
                team = Team(**d["team"]) if d.get("team") else None
                return Feature(id=d["id"], title=d["title"], description=d["description"], team=team, stories=stories, products=products, capabilities=capabilities)
            elif item_type == "Story":
                team = Team(**d["team"]) if d.get("team") else None
                return Story(id=d["id"], title=d["title"], description=d["description"], team=team, products=products, capabilities=capabilities)
            return None

        return [dict_to_obj(e_dict, "Epic") for e_dict in data]
