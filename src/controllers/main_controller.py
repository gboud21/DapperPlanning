from src.events import (
    EventDispatcher, UIItemSelectedEvent, UIItemSaveRequestedEvent, UISyncRequestedEvent,
    ModelActiveItemChangedEvent
)
from src.models.workspace import Workspace
# from src.services.gitlab_client import GitLabClient

class MainController:
    def __init__(self, dispatcher: EventDispatcher, workspace: Workspace):
        self.dispatcher = dispatcher
        self.workspace = workspace
        
        self.dispatcher.subscribe(UIItemSelectedEvent, self.handle_item_selected)
        self.dispatcher.subscribe(UIItemSaveRequestedEvent, self.handle_item_save)
        self.dispatcher.subscribe(UISyncRequestedEvent, self.handle_sync)

    def handle_item_selected(self, event: UIItemSelectedEvent):
        # Fetch data from the model
        item = self.workspace._find_item_by_id(event.item_id)
        if item:
            # Tell the view exactly what to display
            self.dispatcher.dispatch(
                ModelActiveItemChangedEvent(item_type=type(item).__name__, item_data=item)
            )

    def handle_item_save(self, event: UIItemSaveRequestedEvent):
        # Mutate the model (which internally triggers ModelHierarchyUpdatedEvent)
        self.workspace.update_item_details(event.item_id, event.new_title, event.new_description)

    def handle_sync(self, event: UISyncRequestedEvent):
        # Trigger the GitLab API via a background thread, using the Workspace data
        capabilities = self.workspace.get_capabilities()
        # client = GitLabClient(...)
        # client.sync(capabilities)
        pass