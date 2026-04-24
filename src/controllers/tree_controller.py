import uuid
from src.events import (
    EventDispatcher, UIItemSelectedEvent, ModelActiveItemChangedEvent, 
    UIAddProductRequestedEvent, UIAddCapabilityRequestedEvent, UIAddEpicRequestedEvent, 
    UIAddFeatureRequestedEvent, UIAddStoryRequestedEvent, UIDeleteItemRequestedEvent, 
    ModelHierarchyUpdatedEvent
)
from src.models.workspace import Workspace
from src.models.entities import Product, Capability, Epic, Feature, Story, Team

class TreeController:
    def __init__(self, dispatcher: EventDispatcher, workspace: Workspace):
        """
        Initializes the TreeController.

        Args:
            dispatcher (EventDispatcher): The application's event dispatcher.
            workspace (Workspace): The model representing the agile workspace.
        """
        self.dispatcher = dispatcher
        self.workspace = workspace
        
        self.product_count = 0
        self.capability_count = 0
        self.epic_count = 0
        self.feature_count = 0
        self.story_count = 0
        
        self._subscribe_events()

    def _subscribe_events(self):
        """Subscribes to tree-related UI events."""
        self.dispatcher.subscribe(UIItemSelectedEvent, self.handle_item_selected)
        self.dispatcher.subscribe(UIAddProductRequestedEvent, self.handle_add_product)
        self.dispatcher.subscribe(UIAddCapabilityRequestedEvent, self.handle_add_capability)
        self.dispatcher.subscribe(UIAddEpicRequestedEvent, self.handle_add_epic)
        self.dispatcher.subscribe(UIAddFeatureRequestedEvent, self.handle_add_feature)
        self.dispatcher.subscribe(UIAddStoryRequestedEvent, self.handle_add_story)
        self.dispatcher.subscribe(UIDeleteItemRequestedEvent, self.handle_delete_item)

    def handle_item_selected(self, event: UIItemSelectedEvent):
        """Fetches item data and notifies the view (EditorPane)."""
        item = self.workspace._find_item_by_id(event.item_id)
        if item:
            self.dispatcher.dispatch(
                ModelActiveItemChangedEvent(item_type=type(item).__name__, item_data=item)
            )

    def handle_add_product(self, event: UIAddProductRequestedEvent):
        self.product_count += 1
        new_product = Product(
            id=str(uuid.uuid4()), 
            title=f"Product {self.product_count}",
            description="TODO: Add Description"
        )
        self.workspace.add_product(new_product)

    def handle_add_capability(self, event: UIAddCapabilityRequestedEvent):
        parent = self.workspace._find_item_by_id(event.parent_product_id)
        if parent and isinstance(parent, Product):
            self.capability_count += 1
            new_capability = Capability(
                id=str(uuid.uuid4()),
                title=f"Capability {self.capability_count}",
                description="TODO: Add Description"
            )
            parent.capabilities.append(new_capability)
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                root_items=self.workspace.get_products(),
                expand_id=event.parent_product_id
            ))

    def handle_add_epic(self, event: UIAddEpicRequestedEvent):
        parent = self.workspace._find_item_by_id(event.parent_capability_id)
        if parent and isinstance(parent, Capability):
            self.epic_count += 1
            new_epic = Epic(
                id=str(uuid.uuid4()),
                title=f"Epic {self.epic_count}",
                description="TODO: Add Description"
            )
            parent.epics.append(new_epic)
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                root_items=self.workspace.get_products(),
                expand_id=event.parent_capability_id
            ))

    def handle_add_feature(self, event: UIAddFeatureRequestedEvent):
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
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                root_items=self.workspace.get_products(),
                expand_id=event.parent_epic_id
            ))

    def handle_add_story(self, event: UIAddStoryRequestedEvent):
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
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                root_items=self.workspace.get_products(),
                expand_id=event.parent_feature_id
            ))

    def handle_delete_item(self, event: UIDeleteItemRequestedEvent):
        self.workspace.delete_item(event.item_id)
