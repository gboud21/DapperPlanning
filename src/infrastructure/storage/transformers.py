from typing import List, Dict, Any
from src.domain.entities import Epic, Feature, Story, Team

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
                    'Capabilities': ",".join(getattr(item, 'capabilities', [])),
                    'Weight': getattr(item, 'weight', 0.0),
                    'Status': getattr(item, 'status', 'Backlog'),
                    'Assignee ID': getattr(item, 'assignee_id', "") if item_type == "Story" else ""
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
            weight = float(row.get('Weight', 0.0))
            status = row.get('Status', 'Backlog')
            
            team = Team(name=team_name) if team_name else None
            
            if item_type == "Epic":
                obj = Epic(id=item_id, title=title, description=description, products=products, capabilities=capabilities)
            elif item_type == "Feature":
                obj = Feature(id=item_id, title=title, description=description, team=team, products=products, capabilities=capabilities)
            elif item_type == "Story":
                assignee_id = row.get('Assignee ID')
                if assignee_id and assignee_id != "":
                    assignee_id = int(assignee_id)
                else:
                    assignee_id = None
                obj = Story(id=item_id, title=title, description=description, team=team, products=products, capabilities=capabilities, weight=weight, status=status, assignee_id=assignee_id)
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
            weight = float(d.get("weight", 0.0))
            status = d.get("status", "Backlog")
            
            # Extract Sync Metadata
            gitlab_id = d.get("gitlab_id")
            gitlab_iid = d.get("gitlab_iid")
            last_synced_at = d.get("last_synced_at")

            if item_type == "Epic":
                features = [dict_to_obj(f, "Feature") for f in d.get("features", [])]
                return Epic(
                    id=d["id"], title=d["title"], description=d["description"], 
                    features=features, products=products, capabilities=capabilities,
                    gitlab_id=gitlab_id, gitlab_iid=gitlab_iid, last_synced_at=last_synced_at
                )
            elif item_type == "Feature":
                stories = [dict_to_obj(s, "Story") for s in d.get("stories", [])]
                team = Team(**d["team"]) if d.get("team") else None
                return Feature(
                    id=d["id"], title=d["title"], description=d["description"], 
                    team=team, stories=stories, products=products, capabilities=capabilities,
                    gitlab_id=gitlab_id, gitlab_iid=gitlab_iid, last_synced_at=last_synced_at
                )
            elif item_type == "Story":
                team = Team(**d["team"]) if d.get("team") else None
                return Story(
                    id=d["id"], title=d["title"], description=d["description"], 
                    team=team, products=products, capabilities=capabilities, 
                    weight=weight, status=status, assignee_id=d.get("assignee_id"),
                    gitlab_id=gitlab_id, gitlab_iid=gitlab_iid, last_synced_at=last_synced_at
                )
            return None

        return [dict_to_obj(e_dict, "Epic") for e_dict in data]

class GitLabTransformer:
    def transform_pull_data(self, raw_epics: List[Dict[str, Any]], raw_issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Transforms flat GitLab API data into nested Domain entities.
        Returns a dict with 'root_epics', 'orphaned_features', and 'orphaned_stories'.
        """
        epics_by_gitlab_id = {}
        features_by_iid = {}
        root_epics = []
        orphaned_features = []
        orphaned_stories = []

        # Step A: Process Epics (Root level)
        for r_epic in raw_epics:
            labels = r_epic.get('labels', [])
            parent_id = r_epic.get('parent_id')
            
            is_explicit_epic = any('Epic' in l for l in labels)
            is_root = parent_id is None
            
            if is_explicit_epic or (is_root and not any('Feature' in l for l in labels)):
                epic = Epic(
                    id=f"gl-{r_epic['id']}",
                    title=r_epic.get('title', ''),
                    description=r_epic.get('description', ''),
                    gitlab_id=r_epic['id'],
                    gitlab_iid=r_epic.get('iid')
                )
                epics_by_gitlab_id[r_epic['id']] = epic
                root_epics.append(epic)

        # Step B: Process Features (Sub-epics)
        for r_feat in raw_epics:
            if r_feat['id'] in epics_by_gitlab_id:
                continue # Already processed as a root Epic
                
            labels = r_feat.get('labels', [])
            parent_id = r_feat.get('parent_id')
            
            is_explicit_feature = any('Feature' in l for l in labels)
            has_parent = parent_id is not None
            
            if is_explicit_feature or has_parent:
                feature = Feature(
                    id=f"gl-f-{r_feat['id']}",
                    title=r_feat.get('title', ''),
                    description=r_feat.get('description', ''),
                    team=Team(name=""), # Placeholder
                    gitlab_id=r_feat['id'],
                    gitlab_iid=r_feat.get('iid')
                )
                features_by_iid[r_feat['iid']] = feature
                
                # Link to parent Epic if possible
                if parent_id in epics_by_gitlab_id:
                    epics_by_gitlab_id[parent_id].features.append(feature)
                else:
                    # If parent is not a root Epic or missing, it's an orphan
                    orphaned_features.append(feature)

        # Step C: Process Stories (Issues)
        for r_issue in raw_issues:
            story = Story(
                id=f"gl-s-{r_issue['id']}",
                title=r_issue.get('title', ''),
                description=r_issue.get('description', ''),
                team=Team(name=""), # Placeholder
                weight=float(r_issue.get('weight') or 0.0),
                gitlab_id=r_issue['id'],
                gitlab_iid=r_issue.get('iid')
            )
            
            # Link to Feature via epic_iid (in GitLab Issues response)
            epic_iid = r_issue.get('epic_iid')
            if epic_iid in features_by_iid:
                features_by_iid[epic_iid].stories.append(story)
            elif epic_iid:
                # Linked directly to a root Epic
                parent_epic = next((e for e in root_epics if e.gitlab_iid == epic_iid), None)
                if parent_epic:
                    if not any(f.title == "General Stories" for f in parent_epic.features):
                        gen_feat = Feature(
                            id=f"gen-{parent_epic.id}",
                            title="General Stories",
                            description="Stories linked directly to the Epic in GitLab",
                            team=Team(name="Unassigned")
                        )
                        parent_epic.features.append(gen_feat)
                        features_by_iid[epic_iid] = gen_feat 
                    
                    gen_feat = features_by_iid[epic_iid]
                    gen_feat.stories.append(story)
                else:
                    # Linked to an unknown Epic IID
                    orphaned_stories.append(story)
            else:
                # No parent link at all
                orphaned_stories.append(story)

        return {
            'root_epics': root_epics,
            'orphaned_features': orphaned_features,
            'orphaned_stories': orphaned_stories
        }
