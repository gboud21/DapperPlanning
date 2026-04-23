from dataclasses import dataclass, field
from typing import List, Optional

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
class Story:
    """
    Represents a user story or a small, deliverable piece of work.

    Attributes:
        id (str): A unique identifier for the story.
        title (str): The title or brief description of the story.
        description (str): A detailed description of the story.
        team (Team): The team responsible for the story.
        metadata (GitLabMetadata): GitLab-specific metadata for the story.
        interface_boundary (Optional[str]): Describes any external interfaces or boundaries
                                            this story interacts with.
    """
    id: str
    title: str
    description: str
    team: Team
    metadata: GitLabMetadata = field(default_factory=GitLabMetadata)
    interface_boundary: Optional[str] = None

@dataclass
class Feature:
    """
    Represents a distinct feature, composed of multiple stories.

    Attributes:
        id (str): A unique identifier for the feature.
        title (str): The title or brief description of the feature.
        description (str): A detailed description of the feature.
        team (Team): The team responsible for the feature.
        stories (List[Story]): A list of stories that make up this feature.
        metadata (GitLabMetadata): GitLab-specific metadata for the feature.
    """
    id: str
    title: str
    description: str
    team: Team
    stories: List[Story] = field(default_factory=list)
    metadata: GitLabMetadata = field(default_factory=GitLabMetadata)

@dataclass
class Epic:
    """
    Represents a large body of work, composed of multiple features.

    Attributes:
        id (str): A unique identifier for the epic.
        title (str): The title or brief description of the epic.
        description (str): A detailed description of the epic.
        features (List[Feature]): A list of features that belong to this epic.
        metadata (GitLabMetadata): GitLab-specific metadata for the epic.
    """
    id: str
    title: str
    description: str
    features: List[Feature] = field(default_factory=list)
    metadata: GitLabMetadata = field(default_factory=GitLabMetadata)

@dataclass
class Product:
    """
    Represents a top-level product, composed of multiple capabilities.

    Attributes:
        id (str): A unique identifier for the product.
        title (str): The title of the product.
        description (str): A detailed description of the product.
        capabilities (List[Capability]): A list of capabilities that belong to this product.
    """
    id: str
    title: str
    description: str = ""
    capabilities: List[Capability] = field(default_factory=list)

@dataclass
class Capability:
    """
    Represents a high-level capability or business function, composed of multiple epics.

    Attributes:
        id (str): A unique identifier for the capability.
        title (str): The title or brief description of the capability.
        description (str): A detailed description of the capability.
        epics (List[Epic]): A list of epics that contribute to this capability.
    """
    id: str
    title: str
    description: str = ""
    epics: List[Epic] = field(default_factory=list)
