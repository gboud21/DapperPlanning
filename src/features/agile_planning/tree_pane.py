import tkinter as tk
from tkinter import ttk
from src.core.events import (
    EventDispatcher, UIItemSelectedEvent, UIAddEpicRequestedEvent, UIAddFeatureRequestedEvent, 
    UIAddStoryRequestedEvent, UIDeleteItemRequestedEvent, ModelHierarchyUpdatedEvent,
    AppThemeChangedEvent, UICloneItemRequestedEvent
)
from src.utils.theme_manager import ThemeManager

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
        self.tree_scroll = ttk.Scrollbar(self.parent, orient=tk.VERTICAL)
        self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(self.parent, selectmode="browse")
        self.tree.heading("#0", text="Agile Hierarchy", anchor=tk.W)
        
        self.tree.configure(yscrollcommand=self.tree_scroll.set)
        self.tree_scroll.configure(command=self.tree.yview)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Tag Configuration for visual hierarchy
        self.tree.tag_configure('Product', font=("TkDefaultFont", 10, "bold"), foreground="#0078d7")
        self.tree.tag_configure('Epic', font=("TkDefaultFont", 10, "bold"))
        self.tree.tag_configure('Feature_Stub', font=("TkDefaultFont", 10, "italic"), foreground="gray")
        self.tree.tag_configure('Story_Stub', font=("TkDefaultFont", 10, "italic"), foreground="gray")

        # Context Menu for Treeview
        self.tree_context_menu = tk.Menu(self.tree, tearoff=0)
        self.tree_context_menu.add_command(label="Add Epic", command=self._on_add_epic_clicked)
        self.tree_context_menu.add_command(label="Add Feature", command=self._on_add_feature_clicked)
        self.tree_context_menu.add_command(label="Add Story", command=self._on_add_story_clicked)
        self.tree_context_menu.add_separator()
        self.tree_context_menu.add_command(label="Clone", command=self._on_clone_clicked)
        self.tree_context_menu.add_separator()
        self.tree_context_menu.add_command(label="Delete", command=self._on_delete_clicked)

    def _on_clone_clicked(self):
        selected_id = self.tree.focus()
        if selected_id:
            # Extract raw item id if it's prefixed
            raw_id = selected_id
            if ":" in selected_id:
                parts = selected_id.split(":", 1)
                raw_id = parts[1]
            self.dispatcher.dispatch(UICloneItemRequestedEvent(item_id=raw_id))

    def _bind_events(self):
        """Binds UI events and model subscriptions."""
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Button-3>", self._show_tree_context_menu)
        self.dispatcher.subscribe(ModelHierarchyUpdatedEvent, self.render_tree)
        self.dispatcher.subscribe(AppThemeChangedEvent, self.handle_theme_change)

    def handle_theme_change(self, event: AppThemeChangedEvent):
        """Reacts to application-wide theme changes."""
        from src.utils.theme_manager import ThemeManager
        palette = ThemeManager.DARK_PALETTE if event.is_dark else ThemeManager.LIGHT_PALETTE
        
        # Configure context menu
        self.tree_context_menu.configure(
            bg=palette['bg'], 
            fg=palette['fg'], 
            activebackground=palette['highlight'], 
            activeforeground=palette['fg']
        )
        
        # Update tag configurations to match theme
        if event.is_dark:
            self.tree.tag_configure('Feature_Stub', foreground="#808080")
            self.tree.tag_configure('Story_Stub', foreground="#808080")
        else:
            self.tree.tag_configure('Feature_Stub', foreground="gray")
            self.tree.tag_configure('Story_Stub', foreground="gray")

    def _show_tree_context_menu(self, event):
        """Displays the context menu with context-aware command states."""
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            self.tree.focus(item_id)
            
            item_tags = self.tree.item(item_id, "tags")
            item_type = item_tags[0] if item_tags else None
            
            # Context-aware enablement
            self.tree_context_menu.entryconfig("Add Epic", state=tk.DISABLED) # Cannot add Epic under another item in tree
            self.tree_context_menu.entryconfig("Add Feature", state=tk.NORMAL if item_type == "Epic" else tk.DISABLED)
            self.tree_context_menu.entryconfig("Add Story", state=tk.NORMAL if item_type == "Feature" else tk.DISABLED)
            self.tree_context_menu.entryconfig("Clone", state=tk.NORMAL if item_type in ["Epic", "Feature", "Story"] else tk.DISABLED)
            self.tree_context_menu.entryconfig("Delete", state=tk.NORMAL)
        else:
            # Clicked empty space
            self.tree_context_menu.entryconfig("Add Epic", state=tk.NORMAL)
            self.tree_context_menu.entryconfig("Add Feature", state=tk.DISABLED)
            self.tree_context_menu.entryconfig("Add Story", state=tk.DISABLED)
            self.tree_context_menu.entryconfig("Clone", state=tk.DISABLED)
            self.tree_context_menu.entryconfig("Delete", state=tk.DISABLED)
            
        self.tree_context_menu.tk_popup(event.x_root, event.y_root)

    def _on_add_epic_clicked(self):
        self.dispatcher.dispatch(UIAddEpicRequestedEvent())

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
            
            # Extract raw item id if it's prefixed (Product:ItemID or PROD:ProductName)
            raw_id = selected_id
            if ":" in selected_id:
                parts = selected_id.split(":", 1)
                raw_id = parts[1]
                
            self.dispatcher.dispatch(UIItemSelectedEvent(
                item_id=raw_id, 
                item_type=item_type,
                full_iid=selected_id
            ))

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
            
        # Group items by Product
        if event.products:
            for product in event.products:
                prod_iid = f"PROD:{product.name}"
                self.tree.insert("", tk.END, iid=prod_iid, text=product.name, tags=('Product',))
                
                # Filter epics that belong to this product
                relevant_epics = [e for e in event.root_items if product.name in getattr(e, 'products', [])]
                self._populate_nodes(prod_iid, relevant_epics, prod_prefix=product.name)
            
            # Handle Epics with no assigned products
            unassigned_epics = [e for e in event.root_items if not getattr(e, 'products', [])]
            if unassigned_epics:
                self.tree.insert("", tk.END, iid="PROD:Unassigned", text="Unassigned", tags=('Product',))
                self._populate_nodes("PROD:Unassigned", unassigned_epics, prod_prefix="Unassigned")
        else:
            # Legacy/Fallback: No product nodes
            if event.root_items:
                self._populate_nodes("", event.root_items)
            
        for item_id in all_expanded:
            if self.tree.exists(item_id):
                self.tree.item(item_id, open=True)

        if event.select_id and self.tree.exists(event.select_id):
            self.tree.selection_set(event.select_id)
            self.tree.see(event.select_id)
            self.tree.focus(event.select_id)

    def _populate_nodes(self, parent_iid: str, items: list, prod_prefix: str = ""):
        """Recursively populates nodes from Agile objects."""
        show_status = ThemeManager.load_all_settings().get('show_status_in_tree', True)
        for item in items:
            raw_id = getattr(item, 'id', str(id(item)))
            # Ensure unique iid if item appears multiple times under different products
            item_id = f"{prod_prefix}:{raw_id}" if prod_prefix else raw_id
            
            title = getattr(item, 'title', "Untitled")
            weight = getattr(item, 'weight', 0.0)
            status = getattr(item, 'status', 'Backlog')
            item_type = type(item).__name__
            
            if show_status:
                display_text = f"[{weight:.1f}] ({status}) {title}"
            else:
                display_text = f"[{weight:.1f}] {title}"
                
            node_iid = self.tree.insert(parent_iid, tk.END, iid=item_id, text=display_text, tags=(item_type,))
            
            if item_type == "Epic" and hasattr(item, "features"):
                self._populate_nodes(node_iid, item.features, prod_prefix=prod_prefix)
            elif item_type == "Feature" and hasattr(item, "stories"):
                self._populate_nodes(node_iid, item.stories, prod_prefix=prod_prefix)
