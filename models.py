from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Team:
    name: str
    domain: str = ""

@dataclass
class GitLabMetadata:
    assignee: str = ""
    milestone: str = ""
    weight: int = 0
    labels: List[str] = field(default_factory=list)
    template: str = ""

@dataclass
class Story:
    id: str
    title: str
    description: str
    team: Team
    metadata: GitLabMetadata = field(default_factory=GitLabMetadata)
    # Target system specific: defining decoupling boundaries
    interface_boundary: Optional[str] = None # e.g., "tokio-channel", "trait"

@dataclass
class Feature:
    id: str
    title: str
    description: str
    team: Team
    stories: List[Story] = field(default_factory=list)
    metadata: GitLabMetadata = field(default_factory=GitLabMetadata)

@dataclass
class Epic:
    id: str
    title: str
    description: str
    features: List[Feature] = field(default_factory=list)
    metadata: GitLabMetadata = field(default_factory=GitLabMetadata)

@dataclass
class Capability:
    id: str
    title: str
    epics: List[Epic] = field(default_factory=list)
