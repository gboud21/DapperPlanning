from typing import List, Optional, Any, Dict
import json
import re
import copy
import uuid
from datetime import datetime
from dataclasses import asdict
from src.core.events import EventDispatcher, ModelHierarchyUpdatedEvent
from src.domain.entities import Epic, Feature, Story, Product, Member, Label

class Workspace:
    def __init__(self, dispatcher: EventDispatcher):
        """
        Initializes the Workspace.

        Args:
            dispatcher (EventDispatcher): The event dispatcher for notifying
                                          the application about model changes.
        """
        self.dispatcher = dispatcher
        self._epics: List[Epic] = []
        self._products: List[Product] = []
        self._members: Dict[int, Member] = {}
        self.labels: Dict[str, Label] = {}
        self._active_product_name: Optional[str] = None
        self.current_filepath: Optional[str] = None
        self._clean_snapshot: Optional[str] = None
        self.deleted_remote_items: List[dict] = []

    @property
    def members(self) -> Dict[int, Member]:
        return self._members

    @members.setter
    def members(self, value: Dict[int, Member]):
        self._members = value

    def merge_labels(self, labels: List[Label]):
        """Merges fetched labels into the workspace dictionary."""
        for label in labels:
            self.labels[label.name] = label

    def apply_label_recursively(self, item_id: str, item_type: str, label_name: str, add: bool = True):
        """
        Applies or removes a label recursively to an item and its children.
        """
        item = self._find_item_by_id(item_id)
        if not item:
            return

        def _apply(target_item):
            if not hasattr(target_item, 'labels'):
                return
            
            if add:
                if label_name not in target_item.labels:
                    target_item.labels.append(label_name)
                    target_item.last_synced_at = None
            else:
                if label_name in target_item.labels:
                    target_item.labels.remove(label_name)
                    target_item.last_synced_at = None

            # Recursive cascade
            if isinstance(target_item, Epic):
                for f in target_item.features:
                    _apply(f)
            elif isinstance(target_item, Feature):
                for s in target_item.stories:
                    _apply(s)

        _apply(item)
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
            root_items=self._epics,
            products=self._products
        ))

    def add_or_update_member(self, member: Member):
        """Intelligently merges group and project IDs for a member."""
        if member.id in self._members:
            existing = self._members[member.id]
            # Merge group IDs
            for gid in member.group_ids:
                if gid not in existing.group_ids:
                    existing.group_ids.append(gid)
            # Merge project IDs
            for pid in member.project_ids:
                if pid not in existing.project_ids:
                    existing.project_ids.append(pid)
        else:
            self._members[member.id] = member

    def get_members(self) -> List[Member]:
        return list(self._members.values())

    @property
    def products(self) -> List[Product]:
        return self._products

    @products.setter
    def products(self, value: List[Product]):
        self._products = value

    @property
    def active_product_name(self) -> Optional[str]:
        return self._active_product_name

    @active_product_name.setter
    def active_product_name(self, value: Optional[str]):
        if self._active_product_name != value:
            self._active_product_name = value

    def merge_remote_epics(self, active_product_name: str, remote_epics: List[Epic]) -> None:
        """
        Recursively merges remote GitLab data into the local Workspace model.
        
        Matches items by gitlab_id. Updates existing items and appends new ones.
        """
        if not active_product_name:
            return

        # Find the product entity to ensure it exists
        product = next((p for p in self._products if p.name == active_product_name), None)
        if not product:
            return

        # Start recursive merge at the root (Epics)
        self._merge_recursive(self._epics, remote_epics, active_product_name)
        
        # Dispatch update to UI
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
            root_items=self._epics,
            products=self._products
        ))

    def _merge_recursive(self, local_list: List[Any], remote_list: List[Any], active_product_name: str) -> None:
        """Helper to recursively merge items based on gitlab_id."""
        from datetime import datetime
        now_iso = datetime.now().isoformat()

        for r_item in remote_list:
            # Find matching local item by gitlab_id
            l_item = next((l for l in local_list if l.gitlab_id == r_item.gitlab_id), None)
            
            if l_item:
                # Update existing item details
                l_item.title = r_item.title
                l_item.description = r_item.description
                l_item.gitlab_iid = r_item.gitlab_iid
                l_item.last_synced_at = now_iso
                
                # Update specific fields
                if isinstance(l_item, Story):
                    if hasattr(r_item, 'weight'):
                        l_item.weight = r_item.weight
                    if hasattr(r_item, 'assignee_id'):
                        l_item.assignee_id = r_item.assignee_id
                
                # Ensure the product tag is present
                if hasattr(l_item, 'products'):
                    if active_product_name not in l_item.products:
                        l_item.products.append(active_product_name)

                # Recursively merge children
                if hasattr(l_item, 'features') and hasattr(r_item, 'features'):
                    self._merge_recursive(l_item.features, r_item.features, active_product_name)
                elif hasattr(l_item, 'stories') and hasattr(r_item, 'stories'):
                    self._merge_recursive(l_item.stories, r_item.stories, active_product_name)
            else:
                # New item from GitLab
                r_item.last_synced_at = now_iso
                
                # Recursively set synced_at and product tags for children of new items
                def _set_metadata_recursive(item):
                    item.last_synced_at = now_iso
                    if hasattr(item, 'products'):
                        if active_product_name not in item.products:
                            item.products.append(active_product_name)
                    
                    if hasattr(item, 'features'):
                        for f in item.features: _set_metadata_recursive(f)
                    if hasattr(item, 'stories'):
                        for s in item.stories: _set_metadata_recursive(s)
                
                _set_metadata_recursive(r_item)
                
                local_list.append(r_item)

    def _generate_snapshot(self) -> str:
        """Reliably serializes the current epic hierarchy and metadata into a JSON string."""
        def _serialize_item(item):
            d = asdict(item)
            # Include dynamic properties that asdict misses
            if hasattr(item, 'weight'):
                d['weight'] = item.weight
            if hasattr(item, 'status'):
                d['status'] = item.status
            
            # Recursively handle children
            if hasattr(item, 'features'):
                d['features'] = [_serialize_item(f) for f in item.features]
            elif hasattr(item, 'stories'):
                d['stories'] = [_serialize_item(s) for s in item.stories]
            return d

        data = {
            "active_product_name": self._active_product_name,
            "products": [asdict(p) for p in self._products],
            "epics": [_serialize_item(epic) for epic in self._epics]
        }
        return json.dumps(data, sort_keys=True)

    def mark_as_clean(self) -> None:
        """Stores the current state as the 'clean' reference state."""
        self._clean_snapshot = self._generate_snapshot()

    def clear(self) -> None:
        """Resets the workspace to an empty state."""
        self._epics = []
        self._products = []
        self._active_product_name = None
        self.current_filepath = None

    def has_unsaved_changes(self) -> bool:
        """Returns True if the current state differs from the last clean state."""
        return self._generate_snapshot() != self._clean_snapshot

    def add_epic(self, epic: Epic) -> None:
        """
        Adds a new epic to the workspace root.

        Args:
            epic (Epic): The Epic object to add.
        """
        self._epics.append(epic)
        # Notify the rest of the application that the data has changed
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
            root_items=self._epics,
            products=self._products
        ))

    def update_item_details(self, item_id: str, title: str, description: str, products: List[str] = None, capabilities: List[str] = None) -> None:
        """
        Updates the details of an item within the workspace.

        Args:
            item_id (str): The unique identifier of the item to update.
            title (str): The new title for the item.
            description (str): The new description for the item.
            products (List[str]): The new list of associated product IDs.
            capabilities (List[str]): The new list of associated capability IDs.
        """
        item = self._find_item_by_id(item_id)
        if item:
            item.title = title
            item.description = description
            item.last_synced_at = None
            if hasattr(item, 'products') and products is not None:
                item.products = products
            if hasattr(item, 'capabilities') and capabilities is not None:
                item.capabilities = capabilities
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                root_items=self._epics,
                products=self._products
            ))

    def delete_item(self, item_id: str) -> None:
        """
        Removes an item from the workspace by its ID and notifies listeners.
        Tracks deleted remote items for cleanup during sync.

        Args:
            item_id (str): The unique identifier of the item to delete.
        """
        def _track_deletion(item, item_type):
            if getattr(item, 'gitlab_id', None) or getattr(item, 'gitlab_iid', None):
                # Try to find associated project/group IDs from product tagging
                pid = None
                gid = None
                if hasattr(item, 'products') and item.products:
                    # Safely get the first product if it exists
                    prod_name = item.products[0] if item.products else None
                    if prod_name:
                        product = next((p for p in self._products if p.name == prod_name), None)
                        if product:
                            pid = product.gitlab_project_id
                            gid = product.gitlab_group_id
                
                self.deleted_remote_items.append({
                    'type': item_type,
                    'id': item.gitlab_id,
                    'iid': item.gitlab_iid,
                    'project_id': pid,
                    'group_id': gid
                })

        # Check if it's a top-level epic
        for i, epic in enumerate(self._epics):
            if epic.id == item_id:
                _track_deletion(epic, 'epic')
                # Recursively track children as well if they are remote
                for feature in epic.features:
                    _track_deletion(feature, 'feature')
                    for story in feature.stories:
                        _track_deletion(story, 'story')
                
                self._epics.pop(i)
                self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                    root_items=self._epics,
                    products=self._products
                ))
                return

        # Check sub-items
        for epic in self._epics:
            for j, feature in enumerate(epic.features):
                if feature.id == item_id:
                    _track_deletion(feature, 'feature')
                    for story in feature.stories:
                        _track_deletion(story, 'story')
                        
                    epic.features.pop(j)
                    self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                        root_items=self._epics,
                        products=self._products
                    ))
                    return
                for k, story in enumerate(feature.stories):
                    if story.id == item_id:
                        _track_deletion(story, 'story')
                        feature.stories.pop(k)
                        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                            root_items=self._epics,
                            products=self._products
                        ))
                        return

    def move_feature(self, feature_id: str, new_epic_id: str) -> None:
        """
        Moves a feature to a new parent epic and marks it as dirty.
        """
        feature = self._find_item_by_id(feature_id)
        if not feature or not isinstance(feature, Feature):
            return

        old_epic = self._find_parent(feature_id)
        if not old_epic or not isinstance(old_epic, Epic):
            return

        new_epic = self._find_item_by_id(new_epic_id)
        if not new_epic or not isinstance(new_epic, Epic):
            return

        if old_epic.id == new_epic_id:
            return

        old_epic.features.remove(feature)
        new_epic.features.append(feature)
        feature.last_synced_at = None
        
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
            root_items=self._epics,
            products=self._products
        ))

    def move_story(self, story_id: str, new_feature_id: str) -> None:
        """
        Moves a story to a new parent feature and marks it as dirty.
        """
        story = self._find_item_by_id(story_id)
        if not story or not isinstance(story, Story):
            return

        old_feature = self._find_parent(story_id)
        if not old_feature or not isinstance(old_feature, Feature):
            return

        new_feature = self._find_item_by_id(new_feature_id)
        if not new_feature or not isinstance(new_feature, Feature):
            return

        if old_feature.id == new_feature_id:
            return

        old_feature.stories.remove(story)
        new_feature.stories.append(story)
        story.last_synced_at = None
        
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
            root_items=self._epics,
            products=self._products
        ))

    def split_story(self, story_id: str, orig_new_weight: float, clone_new_weight: float, split_desc: str) -> None:
        """
        Splits a story into two, redistributes weights, and updates titles.
        """
        story = self._find_item_by_id(story_id)
        if not story or not isinstance(story, Story):
            return

        parent_feature = self._find_parent(story_id)
        if not parent_feature or not isinstance(parent_feature, Feature):
            return

        # 1. Clone the story
        clone = copy.deepcopy(story)
        clone.id = str(uuid.uuid4())
        clone.weight = clone_new_weight
        clone.gitlab_id = None
        clone.gitlab_iid = None
        clone.last_synced_at = None
        
        # Update original story
        story.weight = orig_new_weight
        story.last_synced_at = None
        
        # 2. Insert clone after original
        idx = parent_feature.stories.index(story)
        parent_feature.stories.insert(idx + 1, clone)
        
        # 3. Handle naming conventions
        # Regex to strip " (Part \d+ of \d+)"
        base_title = re.sub(r" \(Part \d+ of \d+\)$", "", story.title)
        
        # Find all stories in this feature that match the base title
        matching_stories = [s for s in parent_feature.stories if re.sub(r" \(Part \d+ of \d+\)$", "", s.title) == base_title]
        total = len(matching_stories)
        
        for i, s in enumerate(matching_stories):
            s.title = f"{base_title} (Part {i+1} of {total})"
            s.last_synced_at = None

        # 4. Update descriptions (after titles are finalized)
        today_str = datetime.now().strftime("%m/%d/%Y")
        
        # Coalesce None descriptions to empty strings
        orig_desc = story.description or ""
        clone_desc = clone.description or ""
        
        # New Story Reference Logic (Reference original story title)
        ref_str = f" (#{story.gitlab_iid})" if story.gitlab_iid else ""
        clone.description = clone_desc + f"\n\n[{today_str}] **Split from:** {story.title}{ref_str}\n**Reason:** {split_desc}"
        
        # Original Story Reference Logic (Reference clone story title)
        story.description = orig_desc + f"\n\n[{today_str}] **Split into:** {clone.title}\n**Reason:** {split_desc}"
        
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
            root_items=self._epics,
            products=self._products
        ))

    def _find_parent(self, item_id: str) -> Optional[Any]:
        """Helper to find the parent of an item."""
        for epic in self._epics:
            for feature in epic.features:
                if feature.id == item_id:
                    return epic
                for story in feature.stories:
                    if story.id == item_id:
                        return feature
        return None

    def _find_item_by_id(self, item_id: str) -> Optional[Any]:
        """
        Recursively searches for an item by its ID across all epics,
        features, and stories within the workspace.

        Args:
            item_id (str): The unique identifier of the item to find.

        Returns:
            Optional[Any]: The found item object if found, otherwise None.
        """
        for epic in self._epics:
            if epic.id == item_id:
                return epic
            for feature in epic.features:
                if feature.id == item_id:
                    return feature
                for story in feature.stories:
                    if story.id == item_id:
                        return story
        return None

    def get_epics(self) -> List[Epic]:
        """
        Retrieves all epics currently in the workspace.

        Returns:
            List[Epic]: A list of Epic objects.
        """
        return self._epics

    def get_products(self) -> List[str]:
        """
        Retrieves a unique list of all product names used in the workspace.
        """
        products = set()
        for epic in self._epics:
            products.update(getattr(epic, 'products', []))
            for feature in epic.features:
                products.update(getattr(feature, 'products', []))
                for story in feature.stories:
                    products.update(getattr(story, 'products', []))
        return sorted(list(products))

    def remove_global_tag(self, tag_type: str, tag_value: str) -> None:
        """
        Removes a specific tag from all items in the workspace.

        Args:
            tag_type (str): 'product' or 'capability'.
            tag_value (str): The value of the tag to remove.
        """
        attr_name = 'products' if tag_type == 'product' else 'capabilities'
        
        for epic in self._epics:
            if hasattr(epic, attr_name):
                current_tags = getattr(epic, attr_name)
                if tag_value in current_tags:
                    current_tags.remove(tag_value)
            
            for feature in epic.features:
                if hasattr(feature, attr_name):
                    current_tags = getattr(feature, attr_name)
                    if tag_value in current_tags:
                        current_tags.remove(tag_value)
                
                for story in feature.stories:
                    if hasattr(story, attr_name):
                        current_tags = getattr(story, attr_name)
                        if tag_value in current_tags:
                            current_tags.remove(tag_value)
                            
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=self._epics))
