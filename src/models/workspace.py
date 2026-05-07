from typing import List, Optional, Any
from src.events import EventDispatcher, ModelHierarchyUpdatedEvent
from .entities import Epic, Feature, Story

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

    def add_epic(self, epic: Epic) -> None:
        """
        Adds a new epic to the workspace root.

        Args:
            epic (Epic): The Epic object to add.
        """
        self._epics.append(epic)
        # Notify the rest of the application that the data has changed
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=self._epics))

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
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=self._epics))

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
                self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=self._epics))
                return

        # Check sub-items
        for epic in self._epics:
            for j, feature in enumerate(epic.features):
                if feature.id == item_id:
                    epic.features.pop(j)
                    self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=self._epics))
                    return
                for k, story in enumerate(feature.stories):
                    if story.id == item_id:
                        feature.stories.pop(k)
                        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=self._epics))
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
