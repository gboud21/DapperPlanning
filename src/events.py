from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Type
import threading
import tkinter as tk

class Event:
    pass

@dataclass
class UIItemSelectedEvent(Event):
    """Emitted by the View when the user clicks an item in the tree."""
    item_id: str

@dataclass
class ModelActiveItemChangedEvent(Event):
    """Emitted by the Controller when the active item data is ready for the View to render."""
    item_type: str
    item_data: Any

@dataclass
class UIItemSaveRequestedEvent(Event):
    """Emitted by the View when the user clicks 'Save Item Data'."""
    item_id: str
    new_title: str
    new_description: str

@dataclass
class ModelHierarchyUpdatedEvent(Event):
    """Emitted by the Workspace when the data structure changes, prompting a tree redraw."""
    pass

@dataclass
class UISyncRequestedEvent(Event):
    """Emitted by the View when the user clicks 'Sync to GitLab'."""
    pass

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