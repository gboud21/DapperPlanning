import uuid
import tkinter as tk
from tkinter import messagebox
from src.core.app_context import AppContext
from src.core.events import (
    EventDispatcher, UIItemSelectedEvent, ModelActiveItemChangedEvent, 
    UIAddEpicRequestedEvent, UIAddFeatureRequestedEvent, UIAddStoryRequestedEvent, 
    UIDeleteItemRequestedEvent, ModelHierarchyUpdatedEvent, ModelWorkspaceLoadedEvent,
    UIItemReparentRequestedEvent
)
from src.core.command_bus import CommandBus
from src.core.commands import CloneItemCommand
from src.domain.workspace import Workspace
from src.domain.entities import Epic, Feature, Story, Team

class TreeController:
    def __init__(self, context: AppContext):
        """
        Initializes the TreeController.

        Args:
            context (AppContext): The application context for dependency injection.
        """
        self.context = context
        self.dispatcher: EventDispatcher = context.resolve('event_dispatcher')
        self.command_bus: CommandBus = context.resolve('command_bus')
        self.workspace: Workspace = context.resolve('workspace')
        self.current_selected_id = None
        
        self.context.register('tree_controller', self)
        
        self.epic_count = 0
        self.feature_count = 0
        self.story_count = 0

        # Drag and Drop state
        self._dragged_item_iid = None
        
        self._subscribe_events()
        self._register_commands()
        self._bind_tree_events()

    def _bind_tree_events(self):
        """Binds mouse events for drag and drop to the treeview."""
        # Note: tree_pane registration in MainWindow ensures it's available
        tree_pane = self.context.resolve('tree_pane')
        self.tree = tree_pane.tree
        # Use add="+" to preserve selection behavior
        self.tree.bind("<ButtonPress-1>", self._on_drag_start, add="+")
        self.tree.bind("<ButtonRelease-1>", self._on_drag_release, add="+")

    def _on_drag_start(self, event):
        """Records the IID of the item being dragged."""
        item_id = self.tree.identify_row(event.y)
        if item_id:
            # Check if it's a draggable item (not a product grouping)
            tags = self.tree.item(item_id, "tags")
            if tags and tags[0] in ["Epic", "Feature", "Story"]:
                self._dragged_item_iid = item_id
            else:
                self._dragged_item_iid = None
        else:
            self._dragged_item_iid = None

    def _on_drag_release(self, event):
        """Executes the drop logic and validates reparenting rules."""
        if not self._dragged_item_iid:
            return

        target_iid = self.tree.identify_row(event.y)
        if not target_iid or target_iid == self._dragged_item_iid:
            self._dragged_item_iid = None
            return

        # Extract metadata
        dragged_iid = self._dragged_item_iid
        dragged_tags = self.tree.item(dragged_iid, "tags")
        dragged_type = dragged_tags[0] if dragged_tags else None
        
        target_tags = self.tree.item(target_iid, "tags")
        target_type = target_tags[0] if target_tags else None

        # Rule Enforcement: Stories -> Features, Features -> Epics
        is_valid = False
        if dragged_type == "Story" and target_type == "Feature":
            is_valid = True
        elif dragged_type == "Feature" and target_type == "Epic":
            is_valid = True

        if is_valid:
            dragged_text = self.tree.item(dragged_iid, "text")
            target_text = self.tree.item(target_iid, "text")
            
            if messagebox.askyesno("Confirm Move", f"Are you sure you want to move '{dragged_text}' to '{target_text}'?"):
                # Extract raw IDs (removing product prefixes)
                dragged_id = dragged_iid.split(":", 1)[1] if ":" in dragged_iid else dragged_iid
                target_id = target_iid.split(":", 1)[1] if ":" in target_iid else target_iid
                
                self.dispatcher.dispatch(UIItemReparentRequestedEvent(
                    item_id=dragged_id,
                    new_parent_id=target_id,
                    item_type=dragged_type
                ))
        
        self._dragged_item_iid = None

    def _subscribe_events(self):
        """Subscribes to tree-related notification events."""
        self.dispatcher.subscribe(UIItemSelectedEvent, self.handle_item_selected)
        self.dispatcher.subscribe(UIAddEpicRequestedEvent, self.handle_add_epic)
        self.dispatcher.subscribe(UIAddFeatureRequestedEvent, self.handle_add_feature)
        self.dispatcher.subscribe(UIAddStoryRequestedEvent, self.handle_add_story)
        self.dispatcher.subscribe(UIDeleteItemRequestedEvent, self.handle_delete_item)
        self.dispatcher.subscribe(ModelWorkspaceLoadedEvent, self.handle_workspace_loaded)

    def _register_commands(self):
        """Registers handlers for tree-related commands."""
        self.command_bus.register(CloneItemCommand, self.handle_clone_item)

    def handle_workspace_loaded(self, event: ModelWorkspaceLoadedEvent):
        """Restores active product selection after workspace load."""
        self.workspace = self.context.resolve('workspace')
        if self.workspace.active_product_name:
            # Re-dispatch hierarchy update with select_id for the product
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                root_items=self.workspace.get_epics(),
                products=self.workspace.products,
                select_id=f"PROD:{self.workspace.active_product_name}",
                expand_id=f"PROD:{self.workspace.active_product_name}"
            ))

    def handle_item_selected(self, event: UIItemSelectedEvent):
        """Fetches item data and notifies the view (EditorPane)."""
        self.current_selected_id = event.item_id
        
        # Enable Clone in Menu Bar
        menu_bar = self.context.resolve('app_menu')
        if menu_bar:
            menu_bar.set_clone_state(True)
            menu_bar.set_split_state(event.item_type == "Story")

        # Track Active Product Selection
        if ":" in event.full_iid:
            parts = event.full_iid.split(":", 1)
            # If full_iid is "PROD:Name", product name is parts[1]
            # If full_iid is "Name:ItemID", product name is parts[0]
            product_name = parts[1] if parts[0] == "PROD" else parts[0]
            
            if product_name != "Unassigned":
                self.workspace.active_product_name = product_name

        item = self.workspace._find_item_by_id(event.item_id)
        if item:
            self.dispatcher.dispatch(
                ModelActiveItemChangedEvent(item_type=type(item).__name__, item_data=item)
            )

    def handle_add_epic(self, event: UIAddEpicRequestedEvent):
        self.epic_count += 1
        new_epic = Epic(
            id=str(uuid.uuid4()),
            title=f"Epic {self.epic_count}",
            description="TODO: Add Description"
        )
        self.workspace.add_epic(new_epic)

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
                root_items=self.workspace.get_epics(),
                products=self.workspace.products,
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
                root_items=self.workspace.get_epics(),
                products=self.workspace.products,
                expand_id=event.parent_feature_id
            ))

    def handle_delete_item(self, event: UIDeleteItemRequestedEvent):
        self.workspace.delete_item(event.item_id)
        if self.current_selected_id == event.item_id:
            self.current_selected_id = None
            menu_bar = self.context.resolve('app_menu')
            if menu_bar:
                menu_bar.set_clone_state(False)

    def handle_clone_item(self, command: CloneItemCommand):
        target_id = command.item_id if command.item_id else self.current_selected_id
        if not target_id:
            return

        item = self.workspace._find_item_by_id(target_id)
        if not item:
            return

        # Find parent
        parent = self._find_parent(target_id)
        new_item = item.clone()

        if parent:
            if isinstance(parent, Epic):
                parent.features.append(new_item)
            elif isinstance(parent, Feature):
                parent.stories.append(new_item)
        else:
            # Root epic
            self.workspace.add_epic(new_item)
            return # Workspace.add_epic already dispatches

        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
            root_items=self.workspace.get_epics(),
            products=self.workspace.products,
            select_id=new_item.id,
            expand_id=target_id
        ))

    def _find_parent(self, item_id: str):
        """Helper to find the parent of an item."""
        for epic in self.workspace.get_epics():
            for feature in epic.features:
                if feature.id == item_id:
                    return epic
                for story in feature.stories:
                    if story.id == item_id:
                        return feature
        return None
