from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Type, Optional
import threading
import tkinter as tk

class Event:
    """Base class for all application events."""
    pass

# --- 1. UI ACTION EVENTS (Requests for mutation or navigation) ---

@dataclass
class UIItemSelectedEvent(Event):
    """Emitted by the View when the user clicks an item in the tree."""
    item_id: str
    item_type: str
    full_iid: str = ""

@dataclass
class UIItemSaveRequestedEvent(Event):
    """Emitted by the View when the user clicks 'Update Current Item'."""
    item_id: str
    new_title: str
    new_description: str
    new_products: List[str] = field(default_factory=list)
    new_capabilities: List[str] = field(default_factory=list)
    weight: float = 0.0
    status: str = 'Backlog'

@dataclass
class UICloneItemRequestedEvent(Event):
    """Emitted by the View when the user requests to clone an item."""
    item_id: Optional[str] = None

@dataclass
class UISyncRequestedEvent(Event):
    pass

@dataclass
class UIGitLabPullRequestedEvent(Event):
    pass

@dataclass
class UIGitLabPushRequestedEvent(Event):
    pass

@dataclass
class UIConflictResolvedEvent(Event):
    resolution: str  # 'local' or 'remote'
    item_id: str

@dataclass
class UISyncMembersRequestedEvent(Event):
    pass

@dataclass
class UIOpenWorkspaceRequestedEvent(Event):
    pass

@dataclass
class UINewWorkspaceRequestedEvent(Event):
    pass

@dataclass
class UISaveWorkspaceRequestedEvent(Event):
    pass

@dataclass
class UISaveAsWorkspaceRequestedEvent(Event):
    pass

@dataclass
class UIAppCloseRequestedEvent(Event):
    pass

@dataclass
class UIExportCsvRequestedEvent(Event):
    file_path: str

@dataclass
class UIExportJsonRequestedEvent(Event):
    file_path: str

@dataclass
class UIImportCsvRequestedEvent(Event):
    file_path: str

@dataclass
class UIImportJsonRequestedEvent(Event):
    file_path: str

@dataclass
class UIIntegrationsDialogOpenRequestedEvent(Event):
    pass

@dataclass
class UIIntegrationsSaveRequestedEvent(Event):
    auth_url: str
    auth_pat: str
    epic_group_id: str
    product_mappings: dict[str, str]
    capabilities: list[str]
    product_project_ids: Dict[str, Optional[int]] = field(default_factory=dict)
    product_group_ids: Dict[str, Optional[int]] = field(default_factory=dict)
    active_product_name: Optional[str] = None

@dataclass
class UISettingsDialogOpenRequestedEvent(Event):
    pass

@dataclass
class UISettingsSaveRequestedEvent(Event):
    theme: str
    auto_save: bool
    log_level: str
    show_status_in_tree: bool
    templates: dict
    target_tool: str
    methodology: str
    hierarchy: str
    description_type: str
    include_out_of_scope: bool
    include_compliance: bool
    last_selected_item_type: str
    selected_templates: dict

@dataclass
class UILogLevelChangedEvent(Event):
    """Emitted when the user changes the logging level in settings."""
    log_level: str

@dataclass
class UITemplateConfigExportRequestedEvent(Event):
    payload: dict

@dataclass
class UIAddEpicRequestedEvent(Event):
    parent_id: str = None

@dataclass
class UIAddFeatureRequestedEvent(Event):
    parent_epic_id: str

@dataclass
class UIAddStoryRequestedEvent(Event):
    parent_feature_id: str

@dataclass
class UIDeleteItemRequestedEvent(Event):
    item_id: str

@dataclass
class UICreateItemRequestedEvent(Event):
    parent_id: str
    item_type: str
    title: str
    description: str
    products: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    weight: float = 0.0
    status: str = 'Backlog'
    assignee_id: Optional[int] = None

@dataclass
class UIItemReparentRequestedEvent(Event):
    """Emitted when the user drags and drops an item to a new parent."""
    item_id: str
    new_parent_id: str
    item_type: str

@dataclass
class UIStorySplitRequestedEvent(Event):
    """Emitted when the user requests to split a story."""
    story_id: str

@dataclass
class UIThemeToggleRequestedEvent(Event):
    is_dark: bool

@dataclass
class UIWindowStateChangedEvent(Event):
    is_maximized: bool

@dataclass
class UIGlobalTagAddRequestedEvent(Event):
    tag_type: str
    tag_value: str

@dataclass
class UIGlobalTagDeleteRequestedEvent(Event):
    tag_type: str
    tag_value: str


# --- 2. MODEL NOTIFICATION EVENTS (State change broadcasts) ---

@dataclass
class ModelActiveItemChangedEvent(Event):
    item_type: str
    item_data: Any

@dataclass
class ModelHierarchyUpdatedEvent(Event):
    root_items: List[Any]
    products: List[Any] = field(default_factory=list)
    expand_id: str = None
    select_id: str = None

@dataclass
class ModelWorkspaceLoadedEvent(Event):
    filepath: Optional[str] = None

@dataclass
class ModelSyncProgressEvent(Event):
    message: str
    percent: float

@dataclass
class ModelSyncErrorEvent(Event):
    """Emitted when the SyncWorker encounters an error."""
    title: str
    error_message: str
    suggested_solution: str
    debug_info: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ModelConflictDetectedEvent(Event):
    local_item: Any
    remote_item: Any


# --- 3. SYSTEM INTERRUPT EVENTS (App-wide lifecycle & errors) ---

@dataclass
class AppThemeChangedEvent(Event):
    is_dark: bool

@dataclass
class UIErrorNotificationEvent(Event):
    title: str
    message: str


# --- NAMESPACE GROUPINGS (For Type Safety & Discovery) ---

class Actions:
    """Namespace for all UI-driven Requests and Actions."""
    ITEM_SELECTED = UIItemSelectedEvent
    ITEM_SAVE = UIItemSaveRequestedEvent
    CLONE_ITEM = UICloneItemRequestedEvent
    SYNC = UISyncRequestedEvent
    GITLAB_PULL = UIGitLabPullRequestedEvent
    GITLAB_PUSH = UIGitLabPushRequestedEvent
    CONFLICT_RESOLVED = UIConflictResolvedEvent
    WORKSPACE_OPEN = UIOpenWorkspaceRequestedEvent
    WORKSPACE_NEW = UINewWorkspaceRequestedEvent
    WORKSPACE_SAVE = UISaveWorkspaceRequestedEvent
    WORKSPACE_SAVE_AS = UISaveAsWorkspaceRequestedEvent
    APP_CLOSE = UIAppCloseRequestedEvent
    EXPORT_CSV = UIExportCsvRequestedEvent
    EXPORT_JSON = UIExportJsonRequestedEvent
    IMPORT_CSV = UIImportCsvRequestedEvent
    IMPORT_JSON = UIImportJsonRequestedEvent
    INTEGRATIONS_OPEN = UIIntegrationsDialogOpenRequestedEvent
    INTEGRATIONS_SAVE = UIIntegrationsSaveRequestedEvent
    SETTINGS_OPEN = UISettingsDialogOpenRequestedEvent
    SETTINGS_SAVE = UISettingsSaveRequestedEvent
    SYNC_MEMBERS = UISyncMembersRequestedEvent
    LOG_LEVEL_CHANGED = UILogLevelChangedEvent
    TEMPLATE_EXPORT = UITemplateConfigExportRequestedEvent
    ADD_EPIC = UIAddEpicRequestedEvent
    ADD_FEATURE = UIAddFeatureRequestedEvent
    ADD_STORY = UIAddStoryRequestedEvent
    DELETE_ITEM = UIDeleteItemRequestedEvent
    CREATE_ITEM = UICreateItemRequestedEvent
    THEME_TOGGLE = UIThemeToggleRequestedEvent
    WINDOW_STATE = UIWindowStateChangedEvent
    TAG_ADD = UIGlobalTagAddRequestedEvent
    TAG_DELETE = UIGlobalTagDeleteRequestedEvent
    ITEM_REPARENT = UIItemReparentRequestedEvent
    ITEM_SPLIT = UIStorySplitRequestedEvent

class Notifications:
    """Namespace for all State Update and Sync Notifications."""
    ACTIVE_ITEM_CHANGED = ModelActiveItemChangedEvent
    HIERARCHY_UPDATED = ModelHierarchyUpdatedEvent
    WORKSPACE_LOADED = ModelWorkspaceLoadedEvent
    SYNC_PROGRESS = ModelSyncProgressEvent
    SYNC_ERROR = ModelSyncErrorEvent
    CONFLICT_DETECTED = ModelConflictDetectedEvent

class System:
    """Namespace for Application-wide Interrupts and Core Events."""
    THEME_CHANGED = AppThemeChangedEvent
    ERROR = UIErrorNotificationEvent


# --- DISPATCHER ---

class EventDispatcher:
    def __init__(self, root_window: tk.Tk):
        self._listeners: Dict[Type[Event], List[Callable]] = {}
        self._root = root_window
        self._main_thread_id = threading.get_ident()

    def subscribe(self, event_type: Type[Event], listener: Callable[[Event], None]) -> None:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)

    def unsubscribe(self, event_type: Type[Event], listener: Callable[[Event], None]) -> None:
        """Removes a listener from an event type."""
        if event_type in self._listeners:
            if listener in self._listeners[event_type]:
                self._listeners[event_type].remove(listener)

    def dispatch(self, event: Event) -> None:
        """
        Dispatches an event to all registered listeners.
        Includes runtime telemetry for thread-safety validation.
        """
        event_type = type(event)
        event_name = event_type.__name__
        thread_id = threading.get_ident()
        is_main_thread = thread_id == self._main_thread_id
        
        # Runtime Telemetry
        origin = "MAIN" if is_main_thread else f"BG:{threading.current_thread().name}"
        delivery = "DIRECT" if is_main_thread else "QUEUED"
        print(f"[EVENT_TRACE] [{origin}] {event_name} ({delivery})")

        if event_type not in self._listeners:
            return

        for listener in self._listeners[event_type]:
            if is_main_thread:
                listener(event)
            else:
                # Thread-safe dispatch using Tkinter's .after()
                self._root.after(0, listener, event)

__all__ = [
    'Event', 'EventDispatcher', 'Actions', 'Notifications', 'System',
    # Keeping individual events for backward compatibility
    'UIItemSelectedEvent', 'UIItemSaveRequestedEvent', 'UICloneItemRequestedEvent', 'UISyncRequestedEvent',
    'UIGitLabPullRequestedEvent', 'UIGitLabPushRequestedEvent', 'UIConflictResolvedEvent',
    'UIOpenWorkspaceRequestedEvent', 'UINewWorkspaceRequestedEvent', 'UISaveWorkspaceRequestedEvent',
    'UISaveAsWorkspaceRequestedEvent', 'UIAppCloseRequestedEvent', 'UIExportCsvRequestedEvent',
    'UIExportJsonRequestedEvent', 'UIImportCsvRequestedEvent', 'UIImportJsonRequestedEvent',
    'UIIntegrationsDialogOpenRequestedEvent', 'UIIntegrationsSaveRequestedEvent',
    'UISettingsDialogOpenRequestedEvent', 'UISettingsSaveRequestedEvent', 'UILogLevelChangedEvent',
    'UITemplateConfigExportRequestedEvent', 'UIAddEpicRequestedEvent',
    'UIAddFeatureRequestedEvent', 'UIAddStoryRequestedEvent', 'UIDeleteItemRequestedEvent',
    'UICreateItemRequestedEvent', 'UIThemeToggleRequestedEvent', 'UIWindowStateChangedEvent',
    'UIGlobalTagAddRequestedEvent', 'UIGlobalTagDeleteRequestedEvent',
    'ModelActiveItemChangedEvent', 'ModelHierarchyUpdatedEvent', 'ModelWorkspaceLoadedEvent',
    'ModelSyncProgressEvent', 'ModelSyncErrorEvent', 'ModelConflictDetectedEvent', 'AppThemeChangedEvent',
    'UIErrorNotificationEvent'
]
