import uuid
from src.core.app_context import AppContext
from src.core.events import (
    EventDispatcher, UICreateItemRequestedEvent,
    ModelHierarchyUpdatedEvent, ModelWorkspaceLoadedEvent, ModelActiveItemChangedEvent
)
from src.core.command_bus import CommandBus
from src.core.commands import SaveItemCommand
from src.domain.workspace import Workspace
from src.domain.entities import Epic, Feature, Story, Team

class EditorController:
    def __init__(self, context: AppContext):
        """
        Initializes the EditorController.

        Args:
            context (AppContext): The application context for dependency injection.
        """
        self.context = context
        self.dispatcher: EventDispatcher = context.resolve('event_dispatcher')
        self.command_bus: CommandBus = context.resolve('command_bus')
        self.workspace: Workspace = context.resolve('workspace')
        
        self._subscribe_events()
        self._register_commands()

    def _subscribe_events(self):
        """Subscribes to editor-related notifications."""
        self.dispatcher.subscribe(UICreateItemRequestedEvent, self.handle_create_item)
        self.dispatcher.subscribe(ModelWorkspaceLoadedEvent, self.handle_workspace_loaded)
        self.dispatcher.subscribe(ModelActiveItemChangedEvent, self.handle_active_item_changed)

    def _register_commands(self):
        """Registers handlers for editor-related commands."""
        self.command_bus.register(SaveItemCommand, self.handle_save_item)

    def handle_workspace_loaded(self, event: ModelWorkspaceLoadedEvent):
        """Refreshes the workspace reference."""
        self.workspace = self.context.resolve('workspace')

    def handle_save_item(self, command: SaveItemCommand):
        """Updates an existing item's details via command execution."""
        item = self.workspace._find_item_by_id(command.item_id)
        if isinstance(item, Story):
             item.weight = command.weight
             item.status = command.status
             item.assignee_id = command.assignee_id

        self.workspace.update_item_details(
            command.item_id, 
            command.new_title, 
            command.new_description, 
            products=command.new_products, 
            capabilities=command.new_capabilities,
            labels=command.new_labels
        )
        # State mutation is done, ModelHierarchyUpdatedEvent is dispatched by workspace.update_item_details

    def handle_active_item_changed(self, event: ModelActiveItemChangedEvent):
        """Manages contextual UI visibility and population (e.g. Assignee for Stories)."""
        try:
            editor_pane = self.context.resolve('editor_pane')
        except KeyError:
            return

        if event.item_type == 'Story':
            # Unhide Assignee UI
            editor_pane.assignee_lbl.grid()
            editor_pane.assignee_combo.grid()
            
            # Populate members
            members = self.workspace.get_members()
            member_names = ["Unassigned"] + [m.name for m in members]
            editor_pane.set_assignee_list(member_names)
            
            # Set current assignee
            assignee_id = getattr(event.item_data, 'assignee_id', None)
            if assignee_id:
                member = self.workspace.members.get(assignee_id)
                if member:
                    editor_pane.assignee_combo.set(member.name)
                else:
                    editor_pane.assignee_combo.set("Unassigned")
            else:
                editor_pane.assignee_combo.set("Unassigned")
        else:
            # Hide Assignee UI for Epics/Features
            editor_pane.assignee_lbl.grid_remove()
            editor_pane.assignee_combo.grid_remove()

    def handle_create_item(self, event: UICreateItemRequestedEvent):
        """Creates a new item and attaches it to the parent in the model."""
        new_id = str(uuid.uuid4())
        item = None
        
        if event.item_type == "Epic" and not event.parent_id:
            item = Epic(
                id=new_id, 
                title=event.title, 
                description=event.description,
                products=event.products,
                capabilities=event.capabilities
            )
            self.workspace.add_epic(item)
            return

        parent = self.workspace._find_item_by_id(event.parent_id)
        if not parent:
            return

        if event.item_type == "Feature" and isinstance(parent, Epic):
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
                capabilities=event.capabilities,
                weight=event.weight,
                status=event.status,
                assignee_id=event.assignee_id
            )
            parent.stories.append(item)

        if item:
            # Trigger refresh and expand the parent
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                root_items=self.workspace.get_epics(),
                expand_id=event.parent_id
            ))
