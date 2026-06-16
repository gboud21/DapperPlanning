from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Command:
    """Base class for all intent-to-act commands."""
    pass

@dataclass
class SaveItemCommand(Command):
    """Command to save updates to an existing item."""
    item_id: str
    new_title: str
    new_description: str
    new_products: List[str] = field(default_factory=list)
    new_capabilities: List[str] = field(default_factory=list)
    new_labels: List[str] = field(default_factory=list)
    weight: float = 0.0
    status: str = 'Backlog'
    assignee_id: Optional[int] = None
    iteration_id: Optional[int] = None

@dataclass
class SyncWithGitLabCommand(Command):
    """Command to trigger a synchronization with GitLab."""
    sync_type: str  # 'pull' or 'push'

@dataclass
class CloneItemCommand(Command):
    """Command to clone an existing item."""
    item_id: Optional[str] = None

@dataclass
class CreateProductTeamCommand(Command):
    """Command to create a new product team."""
    name: str
    product_id: str

@dataclass
class AddMemberToTeamCommand(Command):
    """Command to add a member to a team."""
    team_id: str
    member_id: int

@dataclass
class UpdateMemberCapacityCommand(Command):
    """Command to update member capacity metrics."""
    team_id: str
    member_id: int
    iteration_id: int
    pto: int
    allocation_pct: int
    velocity_factor: int
