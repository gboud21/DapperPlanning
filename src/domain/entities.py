from dataclasses import dataclass, field
from typing import List, Optional
import uuid
from src.utils.string_utils import generate_clone_title
from src.core.constants import AgileStatus, DEFAULT_FACTOR_VALUE

@dataclass
class Product:
    """
    Represents a product that work items can be assigned to.
    """
    name: str
    gitlab_project_id: Optional[int] = None
    gitlab_group_id: Optional[int] = None

@dataclass
class Team:
    """
    Represents a development team.

    Attributes:
        name (str): The name of the team.
        domain (str): The domain or area of responsibility for the team (optional).
    """
    name: str
    domain: str = ""

@dataclass
class GitLabMetadata:
    """
    Stores metadata relevant to GitLab issues or merge requests.

    Attributes:
        assignee (str): The GitLab username of the assignee.
        milestone (str): The GitLab milestone associated with the item.
        weight (int): The weight assigned to the item in GitLab.
        labels (List[str]): A list of GitLab labels.
        template (str): The GitLab issue or merge request template to use.
    """
    assignee: str = ""
    milestone: str = ""
    weight: int = 0
    labels: List[str] = field(default_factory=list)
    template: str = ""

@dataclass
class Member:
    """
    Represents a project or group member from GitLab.
    """
    id: int  # GitLab User ID
    name: str
    username: str
    group_ids: List[int] = field(default_factory=list)
    project_ids: List[int] = field(default_factory=list)

@dataclass
class Label:
    """
    Represents a GitLab label.
    """
    id: Optional[int]
    name: str
    color: str
    description: str
    scope: str  # 'group' or 'project'
    scope_name: str  # the name of the group or project

@dataclass
class Iteration:
    id: int
    iid: int
    title: str
    start_date: str  # ISO format string from API
    end_date: str    # ISO format string from API
    state: str       # "opened", "closed", etc.

    @property
    def display_name(self) -> str:
        from datetime import datetime
        try:
            s_dt = datetime.fromisoformat(self.start_date).strftime("%m/%d/%Y")
            e_dt = datetime.fromisoformat(self.end_date).strftime("%m/%d/%Y")
            return f"{self.title} ({s_dt} - {e_dt})"
        except:
            return self.title or f"Iteration {self.iid}"

@dataclass
class ProductTeam:
    id: str
    name: str
    product_id: str
    member_ids: List[int] = field(default_factory=list)

@dataclass
class TeamMemberCapacity:
    team_id: str
    member_id: int
    iteration_id: int
    pto: int = 0
    allocation_pct: int = DEFAULT_FACTOR_VALUE
    velocity_factor: int = DEFAULT_FACTOR_VALUE

@dataclass
class Story:
    """
    Represents a user story or a small, deliverable piece of work.
    """
    id: str
    title: str
    description: str
    team: Team
    metadata: GitLabMetadata = field(default_factory=GitLabMetadata)
    labels: List[str] = field(default_factory=list)
    interface_boundary: Optional[str] = None
    products: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    weight: float = 0.0
    status: str = AgileStatus.BACKLOG.value
    assignee_id: Optional[int] = None
    iteration_id: Optional[int] = None
    # Sync Metadata
    gitlab_id: Optional[int] = None
    gitlab_iid: Optional[int] = None
    last_synced_at: Optional[str] = None

    def clone(self) -> 'Story':
        return Story(
            id=str(uuid.uuid4()),
            title=generate_clone_title(self.title),
            description=self.description,
            team=self.team,
            metadata=self.metadata,
            labels=self.labels.copy(),
            interface_boundary=self.interface_boundary,
            products=self.products.copy(),
            capabilities=self.capabilities.copy(),
            weight=self.weight,
            status=AgileStatus.BACKLOG.value,
            assignee_id=self.assignee_id,
            iteration_id=None,
            gitlab_id=None,
            gitlab_iid=None,
            last_synced_at=None
        )

@dataclass
class Feature:
    """
    Represents a distinct feature, composed of multiple stories.
    """
    id: str
    title: str
    description: str
    team: Team
    stories: List[Story] = field(default_factory=list)
    metadata: GitLabMetadata = field(default_factory=GitLabMetadata)
    labels: List[str] = field(default_factory=list)
    products: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    # Sync Metadata
    gitlab_id: Optional[int] = None
    gitlab_iid: Optional[int] = None
    last_synced_at: Optional[str] = None

    def clone(self) -> 'Feature':
        return Feature(
            id=str(uuid.uuid4()),
            title=generate_clone_title(self.title),
            description=self.description,
            team=self.team,
            stories=[s.clone() for s in self.stories],
            metadata=self.metadata,
            labels=self.labels.copy(),
            products=self.products.copy(),
            capabilities=self.capabilities.copy(),
            gitlab_id=None,
            gitlab_iid=None,
            last_synced_at=None
        )

    @property
    def weight(self) -> float:
        """Returns the sum of the weights of all items in its stories list."""
        return sum(s.weight for s in self.stories)

    @property
    def status(self) -> str:
        """Dynamically calculates status based on children."""
        if not self.stories:
            return AgileStatus.BACKLOG.value
        statuses = [s.status for s in self.stories]
        if all(s == AgileStatus.CLOSED.value for s in statuses):
            return AgileStatus.CLOSED.value
        if all(s in (AgileStatus.DONE.value, AgileStatus.CLOSED.value) for s in statuses):
            return AgileStatus.DONE.value
        if all(s == AgileStatus.BACKLOG.value for s in statuses):
            return AgileStatus.BACKLOG.value
        return AgileStatus.IN_PROGRESS.value

@dataclass
class Epic:
    """
    Represents a large body of work, composed of multiple features.
    """
    id: str
    title: str
    description: str
    features: List[Feature] = field(default_factory=list)
    metadata: GitLabMetadata = field(default_factory=GitLabMetadata)
    labels: List[str] = field(default_factory=list)
    products: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    # Sync Metadata
    gitlab_id: Optional[int] = None
    gitlab_iid: Optional[int] = None
    last_synced_at: Optional[str] = None

    def clone(self) -> 'Epic':
        return Epic(
            id=str(uuid.uuid4()),
            title=generate_clone_title(self.title),
            description=self.description,
            features=[f.clone() for f in self.features],
            metadata=self.metadata,
            labels=self.labels.copy(),
            products=self.products.copy(),
            capabilities=self.capabilities.copy(),
            gitlab_id=None,
            gitlab_iid=None,
            last_synced_at=None
        )

    @property
    def weight(self) -> float:
        """Returns the sum of the weights of all items in its features list."""
        return sum(f.weight for f in self.features)

    @property
    def status(self) -> str:
        """Dynamically calculates status based on children."""
        if not self.features:
            return AgileStatus.BACKLOG.value
        statuses = [f.status for f in self.features]
        if all(s == AgileStatus.CLOSED.value for s in statuses):
            return AgileStatus.CLOSED.value
        if all(s in (AgileStatus.DONE.value, AgileStatus.CLOSED.value) for s in statuses):
            return AgileStatus.DONE.value
        if all(s == AgileStatus.BACKLOG.value for s in statuses):
            return AgileStatus.BACKLOG.value
        return AgileStatus.IN_PROGRESS.value
