import tkinter as tk
from tkinter import ttk
from src.events import (
    EventDispatcher, UIItemSelectedEvent, UIItemSaveRequestedEvent, UISyncRequestedEvent,
    ModelHierarchyUpdatedEvent, ModelActiveItemChangedEvent
)

class MainWindow:
    def __init__(self, root: tk.Tk, dispatcher: EventDispatcher):
        self.root = root
        self.dispatcher = dispatcher
        
        self.setup_ui()
        self._bind_events()

    def setup_ui(self):
        # UI Initialization (PanedWindow, Treeview, Editor pane)
        # Assuming layout code from previous implementation goes here
        pass

    def _bind_events(self):
        # 1. UI triggers (Tkinter to Dispatcher)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.btn_save_item.config(command=self._on_save_clicked)
        self.btn_sync.config(command=self._on_sync_clicked)

        # 2. Model subscriptions (Dispatcher to Tkinter)
        self.dispatcher.subscribe(ModelHierarchyUpdatedEvent, self.render_tree)
        self.dispatcher.subscribe(ModelActiveItemChangedEvent, self.populate_editor)

    # --- UI Action Handlers ---
    def _on_tree_select(self, event):
        selected_id = self.tree.focus()
        if selected_id:
            self.dispatcher.dispatch(UIItemSelectedEvent(item_id=selected_id))

    def _on_save_clicked(self):
        selected_id = self.tree.focus()
        if selected_id:
            title = self.entry_title.get()
            desc = self.text_desc.get("1.0", tk.END).strip()
            self.dispatcher.dispatch(UIItemSaveRequestedEvent(selected_id, title, desc))

    def _on_sync_clicked(self):
        self.dispatcher.dispatch(UISyncRequestedEvent())

    # --- View Updaters ---
    def render_tree(self, event: ModelHierarchyUpdatedEvent):
        # Clears and rebuilds the Tkinter Treeview based on the latest Workspace state
        pass

    def populate_editor(self, event: ModelActiveItemChangedEvent):
        # Fills out the contextual editor text fields with event.item_data
        pass