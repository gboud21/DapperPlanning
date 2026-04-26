import uuid
from src.events import (
    EventDispatcher, UIItemSaveRequestedEvent, UICreateItemRequestedEvent,
    ModelHierarchyUpdatedEvent
)
from src.models.workspace import Workspace
from src.models.entities import Product, Capability, Epic, Feature, Story, Team

class EditorController:
    def __init__(self, dispatcher: EventDispatcher, workspace: Workspace):
        """
        Initializes the EditorController.

        Args:
            dispatcher (EventDispatcher): The application's event dispatcher.
            workspace (Workspace): The model representing the agile workspace.
        """
        self.dispatcher = dispatcher
        self.workspace = workspace
        
        self._subscribe_events()

    def _subscribe_events(self):
        """Subscribes to editor-related UI events."""
        self.dispatcher.subscribe(UIItemSaveRequestedEvent, self.handle_item_save)
        self.dispatcher.subscribe(UICreateItemRequestedEvent, self.handle_create_item)

    def handle_item_save(self, event: UIItemSaveRequestedEvent):
        """Updates an existing item's details."""
        self.workspace.update_item_details(
            event.item_id, 
            event.new_title, 
            event.new_description, 
            products=event.new_products, 
            capabilities=event.new_capabilities
        )

    def handle_create_item(self, event: UICreateItemRequestedEvent):
        """Creates a new item and attaches it to the parent in the model."""
        new_id = str(uuid.uuid4())
        item = None
        
        if event.item_type == "Product":
            item = Product(id=new_id, title=event.title, description=event.description)
            self.workspace.add_product(item)
            return

        parent = self.workspace._find_item_by_id(event.parent_id)
        if not parent:
            return

        if event.item_type == "Capability" and isinstance(parent, Product):
            item = Capability(id=new_id, title=event.title, description=event.description)
            parent.capabilities.append(item)
        elif event.item_type == "Epic" and isinstance(parent, Capability):
            item = Epic(
                id=new_id, 
                title=event.title, 
                description=event.description,
                products=event.products,
                capabilities=event.capabilities
            )
            parent.epics.append(item)
        elif event.item_type == "Feature" and isinstance(parent, Epic):
            item = Feature(
                id=new_id, 
                title=event.title, 
                description=event.description, 
                team=Team(name="Unassigned"),
                products=event.products,
                capabilities=event.capabilities
            )
            parent.features.append(item)
        elif event.item_type == "Story" and isinstance(parent, Feature):
            item = Story(
                id=new_id, 
                title=event.title, 
                description=event.description, 
                team=Team(name="Unassigned"),
                products=event.products,
                capabilities=event.capabilities
            )
            parent.stories.append(item)

        if item:
            # Trigger refresh and expand the parent
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                root_items=self.workspace.get_products(),
                expand_id=event.parent_id
            ))
