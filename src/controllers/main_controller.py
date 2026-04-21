from src.events import (
    EventDispatcher, UIItemSelectedEvent, UIItemSaveRequestedEvent, UISyncRequestedEvent,
    ModelActiveItemChangedEvent
)
from src.models.workspace import Workspace
# from src.services.gitlab_client import GitLabClient

class MainController:
    def __init__(self, dispatcher: EventDispatcher, workspace: Workspace):
        """
        Initializes the MainController.

        Args:
            dispatcher (EventDispatcher): The event dispatcher for handling UI and model events.
            workspace (Workspace): The workspace model containing the application data.
        """
        self.dispatcher = dispatcher
        self.workspace = workspace
        
        self.dispatcher.subscribe(UIItemSelectedEvent, self.handle_item_selected)
        self.dispatcher.subscribe(UIItemSaveRequestedEvent, self.handle_item_save)
        self.dispatcher.subscribe(UISyncRequestedEvent, self.handle_sync)

    def handle_item_selected(self, event: UIItemSelectedEvent):
        """
        Handles the event when a UI item is selected.

        Fetches the item data from the workspace and dispatches an event
        to update the view with the active item's details.

        Args:
            event (UIItemSelectedEvent): The event containing the ID of the selected item.
        """
        # Fetch data from the model
        item = self.workspace._find_item_by_id(event.item_id)
        if item:
            # Tell the view exactly what to display
            self.dispatcher.dispatch(
                ModelActiveItemChangedEvent(item_type=type(item).__name__, item_data=item)
            )

    def handle_item_save(self, event: UIItemSaveRequestedEvent):
        """
        Handles the event when a UI item save is requested.

        Updates the item's details in the workspace.

        Args:
            event (UIItemSaveRequestedEvent): The event containing the item ID and new details.
        """
        # Mutate the model (which internally triggers ModelHierarchyUpdatedEvent)
        self.workspace.update_item_details(event.item_id, event.new_title, event.new_description)

    def handle_sync(self, event: UISyncRequestedEvent):
        """
        Handles the event when a synchronization with GitLab is requested.

        This method is intended to trigger the GitLab API interaction,
        potentially in a background thread, using data from the workspace.

        Args:
            event (UISyncRequestedEvent): The event indicating a sync request.
        """
        # Trigger the GitLab API via a background thread, using the Workspace data
        capabilities = self.workspace.get_capabilities()
        # client = GitLabClient(...)
        # client.sync(capabilities)
        pass