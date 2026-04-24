from src.events import (
    EventDispatcher, UISyncRequestedEvent
)
from src.models.workspace import Workspace
from .tree_controller import TreeController
from .editor_controller import EditorController

class MainController:
    def __init__(self, dispatcher: EventDispatcher, workspace: Workspace):
        """
        Initializes the MainController and its sub-controllers.

        Args:
            dispatcher (EventDispatcher): The application's event dispatcher.
            workspace (Workspace): The model representing the agile workspace.
        """
        self.dispatcher = dispatcher
        self.workspace = workspace
        
        # Instantiate sub-controllers
        self.tree_controller = TreeController(dispatcher, workspace)
        self.editor_controller = EditorController(dispatcher, workspace)
        
        self._subscribe_events()

    def _subscribe_events(self):
        """Subscribes to overarching application events."""
        self.dispatcher.subscribe(UISyncRequestedEvent, self.handle_sync)

    def handle_sync(self, event: UISyncRequestedEvent):
        """Handles synchronization with external services (GitLab)."""
        # Overarching logic for syncing would remain here or be delegated to a service
        pass
