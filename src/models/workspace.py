from typing import List, Optional
from src.events import EventDispatcher, ModelHierarchyUpdatedEvent
from .entities import Capability, Epic, Feature, Story

class Workspace:
    def __init__(self, dispatcher: EventDispatcher):
        """
        Initializes the Workspace.

        Args:
            dispatcher (EventDispatcher): The event dispatcher for notifying
                                          the application about model changes.
        """
        self.dispatcher = dispatcher
        self._capabilities: List[Capability] = []

    def add_capability(self, capability: Capability) -> None:
        """
        Adds a new capability to the workspace.

        Args:
            capability (Capability): The Capability object to add.
        """
        self._capabilities.append(capability)
        # Notify the rest of the application that the data has changed
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent())

    def update_item_details(self, item_id: str, title: str, description: str) -> None:
        """
        Updates the title and description of an item within the workspace.

        Args:
            item_id (str): The unique identifier of the item to update.
            title (str): The new title for the item.
            description (str): The new description for the item.
        """
        # Recursive search to find the item by ID and update it (stubbed for brevity)
        item = self._find_item_by_id(item_id)
        if item:
            item.title = title
            item.description = description
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent())

    def _find_item_by_id(self, item_id: str) -> Optional[Any]:
        """
        Recursively searches for an item by its ID across all capabilities,
        epics, features, and stories within the workspace.

        Args:
            item_id (str): The unique identifier of the item to find.

        Returns:
            Optional[Any]: The found item object (Capability, Epic, Feature, or Story)
                           if found, otherwise None.
        """
        # Implementation of search logic across capabilities > epics > features > stories
        pass

    def get_capabilities(self) -> List[Capability]:
        """
        Retrieves all capabilities currently in the workspace.

        Returns:
            List[Capability]: A list of Capability objects.
        """
        return self._capabilities