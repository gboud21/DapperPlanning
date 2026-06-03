from abc import ABC, abstractmethod
from src.core.app_context import AppContext

class FeatureModule(ABC):
    """
    Abstract Base Class for all feature slices in DapperPlanning.
    Every feature (e.g., agile_planning, integrations, settings) must implement this
    interface to ensure deterministic initialization and dependency injection.
    """
    
    def __init__(self, context: AppContext):
        """
        Initializes the feature module with the shared application context.
        
        Args:
            context (AppContext): The central dependency injection container.
        """
        self.context = context
        self.dispatcher = context.resolve('event_dispatcher')
        self.workspace = context.resolve('workspace')
        self.setup_controllers()
        self.setup_ui_components()

    @abstractmethod
    def setup_controllers(self):
        """
        Instantiate and wire up the feature's controllers.
        Controllers should subscribe to UI events here.
        """
        pass

    @abstractmethod
    def setup_ui_components(self):
        """
        Instantiate the feature's UI Panes or Windows.
        Views should subscribe to Model events here.
        """
        pass
