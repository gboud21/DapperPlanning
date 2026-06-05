from abc import ABC, abstractmethod
from src.domain.workspace import Workspace

class WorkspaceRepository(ABC):
    @abstractmethod
    def load(self) -> Workspace:
        """Loads a Workspace from persistence."""
        pass

    @abstractmethod
    def save(self, workspace: Workspace) -> None:
        """Saves a Workspace to persistence."""
        pass
