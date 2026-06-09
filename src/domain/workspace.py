from typing import List, Optional, Any
import json
from dataclasses import asdict
from src.core.events import EventDispatcher, ModelHierarchyUpdatedEvent
from src.domain.entities import Epic, Feature, Story, Product

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
        self._active_product_name: Optional[str] = None
        self.current_filepath: Optional[str] = None
        self._clean_snapshot: Optional[str] = None

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
                if isinstance(l_item, Story) and hasattr(r_item, 'weight'):
                    l_item.weight = r_item.weight
                
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

        Args:
            item_id (str): The unique identifier of the item to delete.
        """
        # Check if it's a top-level epic
        for i, epic in enumerate(self._epics):
            if epic.id == item_id:
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
                    epic.features.pop(j)
                    self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                        root_items=self._epics,
                        products=self._products
                    ))
                    return
                for k, story in enumerate(feature.stories):
                    if story.id == item_id:
                        feature.stories.pop(k)
                        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                            root_items=self._epics,
                            products=self._products
                        ))
                        return

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
