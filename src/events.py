from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Type
import threading
import tkinter as tk

class Event:
    pass

@dataclass
class UIItemSelectedEvent(Event):
    """Emitted by the View when the user clicks an item in the tree."""
    item_id: str
    item_type: str

@dataclass
class ModelActiveItemChangedEvent(Event):
    """Emitted by the Controller when the active item data is ready for the View to render."""
    item_type: str
    item_data: Any

@dataclass
class UIItemSaveRequestedEvent(Event):
    """Emitted by the View when the user clicks 'Update Current Item'."""
    item_id: str
    new_title: str
    new_description: str
    new_products: List[str] = field(default_factory=list)
    new_capabilities: List[str] = field(default_factory=list)
    weight: float = 0.0

@dataclass
class ModelHierarchyUpdatedEvent(Event):
    """Emitted by the Workspace when the data structure changes, prompting a tree redraw."""
    root_items: List[Any]
    expand_id: str = None

@dataclass
class UISyncRequestedEvent(Event):
    """Emitted by the View when the user clicks 'Sync to GitLab'."""
    pass

@dataclass
class UIExportCsvRequestedEvent(Event):
    """Emitted by the View when the user selects a save location for the CSV export."""
    file_path: str

@dataclass
class UIExportJsonRequestedEvent(Event):
    """Emitted by the View when the user selects a JSON file to import."""
    file_path: str

@dataclass
class UIImportCsvRequestedEvent(Event):
    """Emitted by the View when the user selects a CSV file to import."""
    file_path: str

@dataclass
class UIImportJsonRequestedEvent(Event):
    """Emitted by the View when the user selects a JSON file to import."""
    file_path: str

@dataclass
class UIIntegrationsDialogOpenRequestedEvent(Event):
    """Emitted by the View when the user clicks 'Manage Connections'."""
    pass

@dataclass
class UIIntegrationsSaveRequestedEvent(Event):
    """Emitted by the Integrations Dialog when the user clicks 'Save & Close'."""
    auth_url: str
    auth_pat: str
    epic_group_id: str
    product_mappings: dict[str, str]
    capabilities: list[str]

@dataclass
class UISettingsDialogOpenRequestedEvent(Event):
    """Emitted by the View when the user clicks 'Preferences'."""
    pass

@dataclass
class UISettingsSaveRequestedEvent(Event):
    """Emitted by the Settings Dialog when the user clicks 'Save & Close'."""
    theme: str
    auto_save: bool
    log_level: str
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
class UITemplateConfigExportRequestedEvent(Event):
    """Emitted by the Settings Dialog when the user clicks 'Export Configuration'."""
    payload: dict

@dataclass
class UIErrorNotificationEvent(Event):
    """Emitted by Controllers when an operation fails, prompting the View to show an error dialog."""
    title: str
    message: str

@dataclass
class UIAddEpicRequestedEvent(Event):
    """Emitted by the View when the user clicks 'Add Epic' in the context menu."""
    parent_id: str = None  # None for root level epics

@dataclass
class UIAddFeatureRequestedEvent(Event):
    """Emitted by the View when the user clicks 'Add Feature' in the context menu."""
    parent_epic_id: str

@dataclass
class UIAddStoryRequestedEvent(Event):
    """Emitted by the View when the user clicks 'Add Story' in the context menu."""
    parent_feature_id: str

@dataclass
class UIDeleteItemRequestedEvent(Event):
    """Emitted by the View when the user clicks 'Delete' in the context menu."""
    item_id: str

@dataclass
class UICreateItemRequestedEvent(Event):
    """Emitted by the View when the user clicks 'Create as New Child' to create a new item."""
    parent_id: str
    item_type: str
    title: str
    description: str
    products: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    weight: float = 0.0

@dataclass
class UIThemeToggleRequestedEvent(Event):
    """Emitted by the View when the user toggles the theme."""
    is_dark: bool

@dataclass
class AppThemeChangedEvent(Event):
    """Emitted by the Controller when the application theme has changed."""
    is_dark: bool

class EventDispatcher:
    def __init__(self, root_window: tk.Tk):
        self._listeners: Dict[Type[Event], List[Callable]] = {}
        self._root = root_window
        self._main_thread_id = threading.get_ident()

    def subscribe(self, event_type: Type[Event], listener: Callable[[Event], None]) -> None:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)

    def dispatch(self, event: Event) -> None:
        event_type = type(event)
        if event_type not in self._listeners:
            return

        for listener in self._listeners[event_type]:
            if threading.get_ident() == self._main_thread_id:
                listener(event)
            else:
                self._root.after(0, listener, event)
