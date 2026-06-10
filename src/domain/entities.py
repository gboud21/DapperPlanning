from dataclasses import dataclass, field
from typing import List, Optional
import uuid
from src.utils.string_utils import generate_clone_title

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
class Story:
    """
    Represents a user story or a small, deliverable piece of work.
    """
    id: str
    title: str
    description: str
    team: Team
    metadata: GitLabMetadata = field(default_factory=GitLabMetadata)
    interface_boundary: Optional[str] = None
    products: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    weight: float = 0.0
    status: str = 'Backlog'
    assignee_id: Optional[int] = None
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
            interface_boundary=self.interface_boundary,
            products=self.products.copy(),
            capabilities=self.capabilities.copy(),
            weight=self.weight,
            status='Backlog',
            assignee_id=self.assignee_id,
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
            return 'Backlog'
        statuses = [s.status for s in self.stories]
        if all(s == 'Done' for s in statuses):
            return 'Done'
        if all(s == 'Backlog' for s in statuses):
            return 'Backlog'
        return 'In Progress'

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
            return 'Backlog'
        statuses = [f.status for f in self.features]
        if all(s == 'Done' for s in statuses):
            return 'Done'
        if all(s == 'Backlog' for s in statuses):
            return 'Backlog'
        return 'In Progress'
