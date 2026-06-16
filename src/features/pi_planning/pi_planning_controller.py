import uuid
from src.core.app_context import AppContext
from src.core.events import (
    EventDispatcher, ModelHierarchyUpdatedEvent, UISaveWorkspaceRequestedEvent,
    ModelWorkspaceLoadedEvent
)
from src.core.command_bus import CommandBus
from src.core.commands import (
    CreateProductTeamCommand, AddMemberToTeamCommand, UpdateMemberCapacityCommand
)
from src.domain.workspace import Workspace
from src.domain.entities import ProductTeam, TeamMemberCapacity

class PIPlanningController:
    def __init__(self, context: AppContext):
        """
        Initializes the PIPlanningController.

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
        """Subscribes to PI Planning related notifications."""
        self.dispatcher.subscribe(ModelWorkspaceLoadedEvent, self.handle_workspace_loaded)

    def _register_commands(self):
        """Registers handlers for PI Planning related commands."""
        self.command_bus.register(CreateProductTeamCommand, self.handle_create_team)
        self.command_bus.register(AddMemberToTeamCommand, self.handle_add_member_to_team)
        self.command_bus.register(UpdateMemberCapacityCommand, self.handle_update_capacity)

    def handle_workspace_loaded(self, event: ModelWorkspaceLoadedEvent):
        """Refreshes the workspace reference."""
        self.workspace = self.context.resolve('workspace')

    def handle_create_team(self, command: CreateProductTeamCommand):
        """Creates a new team and adds it to the workspace."""
        new_team = ProductTeam(
            id=str(uuid.uuid4()),
            name=command.name,
            product_id=command.product_id
        )
        self.workspace.product_teams.append(new_team)
        
        self._trigger_refresh_and_save()

    def handle_add_member_to_team(self, command: AddMemberToTeamCommand):
        """Adds a member ID to a specific team's member list."""
        team = next((t for t in self.workspace.product_teams if t.id == command.team_id), None)
        if team and command.member_id not in team.member_ids:
            team.member_ids.append(command.member_id)
            self._trigger_refresh_and_save()

    def handle_update_capacity(self, command: UpdateMemberCapacityCommand):
        """Updates or creates a capacity record for a member in an iteration."""
        key = f"{command.team_id}_{command.member_id}_{command.iteration_id}"
        
        capacity = self.workspace.member_capacities.get(key)
        if not capacity:
            capacity = TeamMemberCapacity(
                team_id=command.team_id,
                member_id=command.member_id,
                iteration_id=command.iteration_id
            )
            self.workspace.member_capacities[key] = capacity
            
        capacity.pto = command.pto
        capacity.allocation_pct = command.allocation_pct
        capacity.velocity_factor = command.velocity_factor
        
        self._trigger_refresh_and_save()

    def _trigger_refresh_and_save(self):
        """Broadcasting updates and triggering automated disk save."""
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
            root_items=self.workspace.get_epics(),
            products=self.workspace.products
        ))
        self.dispatcher.dispatch(UISaveWorkspaceRequestedEvent())
