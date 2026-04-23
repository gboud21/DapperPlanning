from typing import List, Optional, Any
from src.events import EventDispatcher, ModelHierarchyUpdatedEvent
from .entities import Product, Capability, Epic, Feature, Story

class Workspace:
    def __init__(self, dispatcher: EventDispatcher):
        """
        Initializes the Workspace.

        Args:
            dispatcher (EventDispatcher): The event dispatcher for notifying
                                          the application about model changes.
        """
        self.dispatcher = dispatcher
        self._products: List[Product] = []

    def add_product(self, product: Product) -> None:
        """
        Adds a new product to the workspace.

        Args:
            product (Product): The Product object to add.
        """
        self._products.append(product)
        # Notify the rest of the application that the data has changed
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=self._products))

    def update_item_details(self, item_id: str, title: str, description: str) -> None:
        """
        Updates the title and description of an item within the workspace.

        Args:
            item_id (str): The unique identifier of the item to update.
            title (str): The new title for the item.
            description (str): The new description for the item.
        """
        item = self._find_item_by_id(item_id)
        if item:
            item.title = title
            item.description = description
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=self._products))

    def _find_item_by_id(self, item_id: str) -> Optional[Any]:
        """
        Recursively searches for an item by its ID across all products,
        capabilities, epics, features, and stories within the workspace.

        Args:
            item_id (str): The unique identifier of the item to find.

        Returns:
            Optional[Any]: The found item object if found, otherwise None.
        """
        for product in self._products:
            if product.id == item_id:
                return product
            for capability in product.capabilities:
                if capability.id == item_id:
                    return capability
                for epic in capability.epics:
                    if epic.id == item_id:
                        return epic
                    for feature in epic.features:
                        if feature.id == item_id:
                            return feature
                        for story in feature.stories:
                            if story.id == item_id:
                                return story
        return None

    def get_products(self) -> List[Product]:
        """
        Retrieves all products currently in the workspace.

        Returns:
            List[Product]: A list of Product objects.
        """
        return self._products