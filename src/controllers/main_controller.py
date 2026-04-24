import uuid
from src.events import (
    EventDispatcher, UIItemSelectedEvent, UIItemSaveRequestedEvent, UISyncRequestedEvent,
    ModelActiveItemChangedEvent, UIAddProductRequestedEvent, UICreateItemRequestedEvent,
    ModelHierarchyUpdatedEvent, UIDeleteItemRequestedEvent, UIAddCapabilityRequestedEvent,
    UIAddEpicRequestedEvent, UIAddFeatureRequestedEvent, UIAddStoryRequestedEvent
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
        self.capability_count = 0
        self.epic_count = 0
        self.feature_count = 0
        self.story_count = 0
        
        self.dispatcher.subscribe(UIItemSelectedEvent, self.handle_item_selected)
        self.dispatcher.subscribe(UIItemSaveRequestedEvent, self.handle_item_save)
        self.dispatcher.subscribe(UISyncRequestedEvent, self.handle_sync)
        self.dispatcher.subscribe(UIAddProductRequestedEvent, self.handle_add_product)
        self.dispatcher.subscribe(UIAddCapabilityRequestedEvent, self.handle_add_capability)
        self.dispatcher.subscribe(UIAddEpicRequestedEvent, self.handle_add_epic)
        self.dispatcher.subscribe(UIAddFeatureRequestedEvent, self.handle_add_feature)
        self.dispatcher.subscribe(UIAddStoryRequestedEvent, self.handle_add_story)
        self.dispatcher.subscribe(UICreateItemRequestedEvent, self.handle_create_item)
        self.dispatcher.subscribe(UIDeleteItemRequestedEvent, self.handle_delete_item)

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

    def handle_delete_item(self, event: UIDeleteItemRequestedEvent):
        """
        Handles the event when a UI item deletion is requested.

        Args:
            event (UIDeleteItemRequestedEvent): The event containing the ID of the item to delete.
        """
        self.workspace.delete_item(event.item_id)

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

    def handle_add_capability(self, event: UIAddCapabilityRequestedEvent):
        """
        Handles the request to add a new Capability to a Product.
        """
        parent = self.workspace._find_item_by_id(event.parent_product_id)
        if parent and isinstance(parent, Product):
            self.capability_count += 1
            new_capability = Capability(
                id=str(uuid.uuid4()),
                title=f"Capability {self.capability_count}",
                description="TODO: Add Description"
            )
            parent.capabilities.append(new_capability)
            # Trigger refresh
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                root_items=self.workspace.get_products(),
                expand_id=event.parent_product_id
            ))

    def handle_add_epic(self, event: UIAddEpicRequestedEvent):
        """
        Handles the request to add a new Epic to a Capability.
        """
        parent = self.workspace._find_item_by_id(event.parent_capability_id)
        if parent and isinstance(parent, Capability):
            self.epic_count += 1
            new_epic = Epic(
                id=str(uuid.uuid4()),
                title=f"Epic {self.epic_count}",
                description="TODO: Add Description"
            )
            parent.epics.append(new_epic)
            # Trigger refresh
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                root_items=self.workspace.get_products(),
                expand_id=event.parent_capability_id
            ))

    def handle_add_feature(self, event: UIAddFeatureRequestedEvent):
        """
        Handles the request to add a new Feature to an Epic.
        """
        parent = self.workspace._find_item_by_id(event.parent_epic_id)
        if parent and isinstance(parent, Epic):
            self.feature_count += 1
            new_feature = Feature(
                id=str(uuid.uuid4()),
                title=f"Feature {self.feature_count}",
                description="TODO: Add Description",
                team=Team(name="Unassigned")
            )
            parent.features.append(new_feature)
            # Trigger refresh
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                root_items=self.workspace.get_products(),
                expand_id=event.parent_epic_id
            ))

    def handle_add_story(self, event: UIAddStoryRequestedEvent):
        """
        Handles the request to add a new Story to a Feature.
        """
        parent = self.workspace._find_item_by_id(event.parent_feature_id)
        if parent and isinstance(parent, Feature):
            self.story_count += 1
            new_story = Story(
                id=str(uuid.uuid4()),
                title=f"Story {self.story_count}",
                description="TODO: Add Description",
                team=Team(name="Unassigned")
            )
            parent.stories.append(new_story)
            # Trigger refresh
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                root_items=self.workspace.get_products(),
                expand_id=event.parent_feature_id
            ))

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
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                root_items=self.workspace.get_products(),
                expand_id=event.parent_id
            ))

    def handle_sync(self, event: UISyncRequestedEvent):
        """
        Handles the event when a synchronization with GitLab is requested.
        """
        pass