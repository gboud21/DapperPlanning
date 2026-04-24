import tkinter as tk
from tkinter import ttk
from src.events import (
    EventDispatcher, UIItemSelectedEvent, UIAddProductRequestedEvent, 
    UIAddCapabilityRequestedEvent, UIAddEpicRequestedEvent, UIAddFeatureRequestedEvent, 
    UIAddStoryRequestedEvent, UIDeleteItemRequestedEvent, ModelHierarchyUpdatedEvent
)

class TreePane:
    def __init__(self, parent_frame: ttk.Frame, dispatcher: EventDispatcher):
        """
        Initializes the TreePane with a treeview and its controls.

        Args:
            parent_frame (ttk.Frame): The frame where the treeview will be placed.
            dispatcher (EventDispatcher): The application's event dispatcher.
        """
        self.parent = parent_frame
        self.dispatcher = dispatcher
        
        self._setup_ui()
        self._bind_events()

    def _setup_ui(self):
        """Sets up the Treeview and its context menu."""
        self.tree = ttk.Treeview(self.parent, selectmode="browse")
        self.tree.heading("#0", text="Agile Hierarchy", anchor=tk.W)
        
        self.tree_scroll = ttk.Scrollbar(self.parent, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scroll.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Tag Configuration for visual hierarchy
        self.tree.tag_configure('Product', font=("TkDefaultFont", 10, "bold"), background="#e6f2ff")
        self.tree.tag_configure('Capability', font=("TkDefaultFont", 10, "bold"))
        self.tree.tag_configure('Epic')
        self.tree.tag_configure('Feature_Stub', font=("TkDefaultFont", 10, "italic"), foreground="gray")
        self.tree.tag_configure('Story_Stub', font=("TkDefaultFont", 10, "italic"), foreground="gray")

        # Context Menu for Treeview
        self.tree_context_menu = tk.Menu(self.tree, tearoff=0)
        self.tree_context_menu.add_command(label="Add Product", command=self._on_add_product_clicked)
        self.tree_context_menu.add_command(label="Add Capability", command=self._on_add_capability_clicked)
        self.tree_context_menu.add_command(label="Add Epic", command=self._on_add_epic_clicked)
        self.tree_context_menu.add_command(label="Add Feature", command=self._on_add_feature_clicked)
        self.tree_context_menu.add_command(label="Add Story", command=self._on_add_story_clicked)
        self.tree_context_menu.add_command(label="Delete", command=self._on_delete_clicked)

    def _bind_events(self):
        """Binds UI events and model subscriptions."""
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Button-3>", self._show_tree_context_menu)
        self.dispatcher.subscribe(ModelHierarchyUpdatedEvent, self.render_tree)

    def _show_tree_context_menu(self, event):
        """Displays the context menu with context-aware command states."""
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            self.tree.focus(item_id)
            
            item_tags = self.tree.item(item_id, "tags")
            item_type = item_tags[0] if item_tags else None
            
            # Context-aware enablement
            self.tree_context_menu.entryconfig("Add Capability", state=tk.NORMAL if item_type == "Product" else tk.DISABLED)
            self.tree_context_menu.entryconfig("Add Epic", state=tk.NORMAL if item_type == "Capability" else tk.DISABLED)
            self.tree_context_menu.entryconfig("Add Feature", state=tk.NORMAL if item_type == "Epic" else tk.DISABLED)
            self.tree_context_menu.entryconfig("Add Story", state=tk.NORMAL if item_type == "Feature" else tk.DISABLED)
            self.tree_context_menu.entryconfig("Delete", state=tk.NORMAL)
        else:
            for label in ["Add Capability", "Add Epic", "Add Feature", "Add Story", "Delete"]:
                self.tree_context_menu.entryconfig(label, state=tk.DISABLED)
            
        self.tree_context_menu.tk_popup(event.x_root, event.y_root)

    def _on_add_product_clicked(self):
        self.dispatcher.dispatch(UIAddProductRequestedEvent())

    def _on_add_capability_clicked(self):
        selected_id = self.tree.focus()
        if selected_id:
            self.dispatcher.dispatch(UIAddCapabilityRequestedEvent(parent_product_id=selected_id))

    def _on_add_epic_clicked(self):
        selected_id = self.tree.focus()
        if selected_id:
            self.dispatcher.dispatch(UIAddEpicRequestedEvent(parent_capability_id=selected_id))

    def _on_add_feature_clicked(self):
        selected_id = self.tree.focus()
        if selected_id:
            self.dispatcher.dispatch(UIAddFeatureRequestedEvent(parent_epic_id=selected_id))

    def _on_add_story_clicked(self):
        selected_id = self.tree.focus()
        if selected_id:
            self.dispatcher.dispatch(UIAddStoryRequestedEvent(parent_feature_id=selected_id))

    def _on_delete_clicked(self):
        selected_id = self.tree.focus()
        if selected_id:
            self.dispatcher.dispatch(UIDeleteItemRequestedEvent(item_id=selected_id))

    def _on_tree_select(self, event):
        selected_id = self.tree.focus()
        if selected_id:
            tags = self.tree.item(selected_id, "tags")
            item_type = tags[0] if tags else "Unknown"
            self.dispatcher.dispatch(UIItemSelectedEvent(item_id=selected_id, item_type=item_type))

    def render_tree(self, event: ModelHierarchyUpdatedEvent):
        """Renders the tree view while preserving expanded state."""
        def get_all_expanded(parent=""):
            expanded = []
            for item in self.tree.get_children(parent):
                if self.tree.item(item, "open"):
                    expanded.append(item)
                expanded.extend(get_all_expanded(item))
            return expanded
        
        all_expanded = get_all_expanded()
        if event.expand_id and event.expand_id not in all_expanded:
            all_expanded.append(event.expand_id)

        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if event.root_items:
            self._populate_nodes("", event.root_items)
            
        for item_id in all_expanded:
            if self.tree.exists(item_id):
                self.tree.item(item_id, open=True)

    def _populate_nodes(self, parent_iid: str, items: list):
        """Recursively populates nodes from Agile objects."""
        for item in items:
            item_id = getattr(item, 'id', str(id(item)))
            title = getattr(item, 'title', "Untitled")
            item_type = type(item).__name__
            
            node_iid = self.tree.insert(parent_iid, tk.END, iid=item_id, text=title, tags=(item_type,))
            
            if item_type == "Product" and hasattr(item, "capabilities"):
                self._populate_nodes(node_iid, item.capabilities)
            elif item_type == "Capability" and hasattr(item, "epics"):
                self._populate_nodes(node_iid, item.epics)
            elif item_type == "Epic" and hasattr(item, "features"):
                self._populate_nodes(node_iid, item.features)
            elif item_type == "Feature" and hasattr(item, "stories"):
                self._populate_nodes(node_iid, item.stories)
