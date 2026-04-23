import uuid
from src.events import (
    EventDispatcher, UIItemSelectedEvent, UIItemSaveRequestedEvent, UISyncRequestedEvent,
    ModelActiveItemChangedEvent, UIAddProductRequestedEvent, UICreateItemRequestedEvent,
    ModelHierarchyUpdatedEvent
)
from src.models.workspace import Workspace
from src.models.entities import Product, Capability, Epic, Feature, Story, Team

class MainController:
    def __init__(self, dispatcher: EventDispatcher, workspace: Workspace):
        """
        Initializes the MainController.

        Args:
            dispatcher (EventDispatcher): The event dispatcher for handling UI and model events.
            workspace (Workspace): The workspace model containing the application data.
        """
        self.dispatcher = dispatcher
        self.workspace = workspace
        self.product_count = 0
        
        self.dispatcher.subscribe(UIItemSelectedEvent, self.handle_item_selected)
        self.dispatcher.subscribe(UIItemSaveRequestedEvent, self.handle_item_save)
        self.dispatcher.subscribe(UISyncRequestedEvent, self.handle_sync)
        self.dispatcher.subscribe(UIAddProductRequestedEvent, self.handle_add_product)
        self.dispatcher.subscribe(UICreateItemRequestedEvent, self.handle_create_item)

    def handle_item_selected(self, event: UIItemSelectedEvent):
        """
        Handles the event when a UI item is selected.

        Fetches the item data from the workspace and dispatches an event
        to update the view with the active item's details.

        Args:
            event (UIItemSelectedEvent): The event containing the ID of the selected item.
        """
        item = self.workspace._find_item_by_id(event.item_id)
        if item:
            self.dispatcher.dispatch(
                ModelActiveItemChangedEvent(item_type=type(item).__name__, item_data=item)
            )

    def handle_item_save(self, event: UIItemSaveRequestedEvent):
        """
        Handles the event when a UI item save is requested.

        Updates the item's details in the workspace.

        Args:
            event (UIItemSaveRequestedEvent): The event containing the item ID and new details.
        """
        self.workspace.update_item_details(event.item_id, event.new_title, event.new_description)

    def handle_add_product(self, event: UIAddProductRequestedEvent):
        """
        Handles the request to add a new top-level Product.
        """
        self.product_count += 1
        new_product = Product(
            id=str(uuid.uuid4()), 
            title=f"Product {self.product_count}",
            description="TODO: Add Description"
        )
        self.workspace.add_product(new_product)

    def handle_create_item(self, event: UICreateItemRequestedEvent):
        """
        Handles the request to create a new item within the hierarchy.
        """
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
            item = Epic(id=new_id, title=event.title, description=event.description)
            parent.epics.append(item)
        elif event.item_type == "Feature" and isinstance(parent, Epic):
            item = Feature(id=new_id, title=event.title, description=event.description, team=Team(name="Unassigned"))
            parent.features.append(item)
        elif event.item_type == "Story" and isinstance(parent, Feature):
            item = Story(id=new_id, title=event.title, description=event.description, team=Team(name="Unassigned"))
            parent.stories.append(item)

        if item:
            # Trigger refresh
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=self.workspace.get_products()))

    def handle_sync(self, event: UISyncRequestedEvent):
        """
        Handles the event when a synchronization with GitLab is requested.
        """
        pass