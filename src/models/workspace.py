from typing import List, Optional
from src.events import EventDispatcher, ModelHierarchyUpdatedEvent
from .entities import Capability, Epic, Feature, Story

class Workspace:
    def __init__(self, dispatcher: EventDispatcher):
        self.dispatcher = dispatcher
        self._capabilities: List[Capability] = []

    def add_capability(self, capability: Capability) -> None:
        self._capabilities.append(capability)
        # Notify the rest of the application that the data has changed
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent())

    def update_item_details(self, item_id: str, title: str, description: str) -> None:
        # Recursive search to find the item by ID and update it (stubbed for brevity)
        item = self._find_item_by_id(item_id)
        if item:
            item.title = title
            item.description = description
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent())
            
    def _find_item_by_id(self, item_id: str) -> Optional[Any]:
        # Implementation of search logic across capabilities > epics > features > stories
        pass
        
    def get_capabilities(self) -> List[Capability]:
        return self._capabilities