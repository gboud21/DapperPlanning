import tkinter as tk
from tkinter import ttk
from src.core.app_context import AppContext
from src.core.events import (
    EventDispatcher, UIItemSelectedEvent, UIAddEpicRequestedEvent, UIAddFeatureRequestedEvent, 
    UIAddStoryRequestedEvent, UIDeleteItemRequestedEvent, ModelHierarchyUpdatedEvent,
    AppThemeChangedEvent, UIStorySplitRequestedEvent
)
from src.core.command_bus import CommandBus
from src.core.commands import CloneItemCommand
from src.utils.theme_manager import ThemeManager

class TreePane:
    def __init__(self, parent_frame: ttk.Frame, context: AppContext):
        """
        Initializes the TreePane with a treeview and its controls.

        Args:
            parent_frame (ttk.Frame): The frame where the treeview will be placed.
            context (AppContext): The application context for dependency injection.
        """
        self.parent = parent_frame
        self.context = context
        self.dispatcher: EventDispatcher = context.resolve('event_dispatcher')
        self.command_bus: CommandBus = context.resolve('command_bus')
        
        self._setup_ui()
        self._bind_events()

    def _setup_ui(self):
        """Sets up the Treeview and its context menu."""
        # Filter Button (Packed first at bottom to ensure it stays below)
        self.btn_filter = ttk.Button(self.parent, text="Filter Hierarchy...", command=self._on_filter_clicked)
        self.btn_filter.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

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

        # Conflict Highlight Tags
        self.tree.tag_configure("conflict_leaf", background="#fee2e2", foreground="#991b1b")   # Soft red
        self.tree.tag_configure("conflict_parent", background="#fef08a", foreground="#854d0e") # Soft yellow

        # Context Menu for Treeview
        self.tree_context_menu = tk.Menu(self.tree, tearoff=0)
        self.tree_context_menu.add_command(label="Resolve Merge Conflict", command=self._on_resolve_clicked)
        self.tree_context_menu.add_separator()
        self.tree_context_menu.add_command(label="Add Epic", command=self._on_add_epic_clicked)
        self.tree_context_menu.add_command(label="Add Feature", command=self._on_add_feature_clicked)
        self.tree_context_menu.add_command(label="Add Story", command=self._on_add_story_clicked)
        self.tree_context_menu.add_separator()
        self.tree_context_menu.add_command(label="Split Story", command=self._on_split_clicked)
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
            self.command_bus.execute(CloneItemCommand(item_id=raw_id))

    def _on_split_clicked(self):
        selected_id = self.tree.focus()
        if selected_id:
            raw_id = selected_id
            if ":" in selected_id:
                parts = selected_id.split(":", 1)
                raw_id = parts[1]
            self.dispatcher.dispatch(UIStorySplitRequestedEvent(story_id=raw_id))

    def _bind_events(self):
        """Binds UI events and model subscriptions."""
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Button-3>", self._show_tree_context_menu)
        
        # Keyboard Shortcuts - Normalized to lowercase for cross-platform stability
        self.tree.bind("<Delete>", lambda e: self._on_delete_clicked())
        self.tree.bind("<Control-d>", lambda e: self._on_delete_clicked())
        self.tree.bind("<Control-Shift-n>", self._on_shortcut_add_child)

        self.dispatcher.subscribe(ModelHierarchyUpdatedEvent, self.render_tree)
        self.dispatcher.subscribe(AppThemeChangedEvent, self.handle_theme_change)

    def _on_shortcut_add_child(self, event):
        """Context-aware shortcut handler for adding child items."""
        selected_id = self.tree.focus()
        if not selected_id:
            # If nothing selected, add Epic at root
            self._on_add_epic_clicked()
            return "break"
            
        item_tags = self.tree.item(selected_id, "tags")
        item_type = item_tags[0] if item_tags else None
        
        if item_type == "Epic":
            self._on_add_feature_clicked()
        elif item_type == "Feature":
            self._on_add_story_clicked()
        
        return "break"

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
            
            # Extract raw item id
            raw_id = item_id.split(":", 1)[1] if ":" in item_id else item_id
            workspace = self.context.resolve('workspace')
            item = workspace._find_item_by_id(raw_id)
            
            item_tags = self.tree.item(item_id, "tags")
            item_type = item_tags[0] if item_tags else None
            
            # Conflict Logic
            is_conflicted = getattr(item, 'is_conflicted', False)
            self.tree_context_menu.entryconfig("Resolve Merge Conflict", state=tk.NORMAL if is_conflicted else tk.DISABLED)
            
            # Context-aware enablement
            self.tree_context_menu.entryconfig("Add Epic", state=tk.DISABLED) # Cannot add Epic under another item in tree
            self.tree_context_menu.entryconfig("Add Feature", state=tk.NORMAL if item_type == "Epic" else tk.DISABLED)
            self.tree_context_menu.entryconfig("Add Story", state=tk.NORMAL if item_type == "Feature" else tk.DISABLED)
            self.tree_context_menu.entryconfig("Split Story", state=tk.NORMAL if item_type == "Story" else tk.DISABLED)
            self.tree_context_menu.entryconfig("Clone", state=tk.NORMAL if item_type in ["Epic", "Feature", "Story"] else tk.DISABLED)
            self.tree_context_menu.entryconfig("Delete", state=tk.NORMAL)
        else:
            # Clicked empty space
            self.tree_context_menu.entryconfig("Resolve Merge Conflict", state=tk.DISABLED)
            self.tree_context_menu.entryconfig("Add Epic", state=tk.NORMAL)
            self.tree_context_menu.entryconfig("Add Feature", state=tk.DISABLED)
            self.tree_context_menu.entryconfig("Add Story", state=tk.DISABLED)
            self.tree_context_menu.entryconfig("Split Story", state=tk.DISABLED)
            self.tree_context_menu.entryconfig("Clone", state=tk.DISABLED)
            self.tree_context_menu.entryconfig("Delete", state=tk.DISABLED)
            
        self.tree_context_menu.tk_popup(event.x_root, event.y_root)

    def _on_resolve_clicked(self):
        """Dispatches the resolve request for the currently selected item."""
        selected_id = self.tree.focus()
        if selected_id:
            raw_id = selected_id.split(":", 1)[1] if ":" in selected_id else selected_id
            workspace = self.context.resolve('workspace')
            item = workspace._find_item_by_id(raw_id)
            if item and getattr(item, 'is_conflicted', False):
                 # Find remote item from sync_worker or latest fetch cache
                 # For now we'll assume we need to dispatch an event to the Integrations Controller
                 from src.features.integrations.conflict_resolution_modal import ConflictResolutionModal
                 # We need the remote copy which was identified during pre-push
                 # I'll need to make sure this is available in the workspace or sync_worker
                 integrations_controller = self.context.resolve('integrations_controller')
                 remote_item = integrations_controller.get_latest_remote_copy(item.gitlab_id)
                 if remote_item:
                     modal = ConflictResolutionModal(self.parent.winfo_toplevel(), self.dispatcher, item, remote_item)

    def _on_filter_clicked(self):
        """Opens the tree filter dialog."""
        from src.features.agile_planning.tree_filter_dialog import TreeFilterDialog
        tree_controller = self.context.resolve('tree_controller')
        dialog = TreeFilterDialog(self.parent.winfo_toplevel(), self.context, active_filter=tree_controller.active_filter_context)
        dialog.grab_set()

    def _on_add_epic_clicked(self):
        self.dispatcher.dispatch(UIAddEpicRequestedEvent())

    def _on_add_feature_clicked(self):
        selected_id = self.tree.focus()
        if selected_id:
            raw_id = selected_id.split(":", 1)[1] if ":" in selected_id else selected_id
            self.dispatcher.dispatch(UIAddFeatureRequestedEvent(parent_epic_id=raw_id))

    def _on_add_story_clicked(self):
        selected_id = self.tree.focus()
        if selected_id:
            raw_id = selected_id.split(":", 1)[1] if ":" in selected_id else selected_id
            self.dispatcher.dispatch(UIAddStoryRequestedEvent(parent_feature_id=raw_id))

    def _on_delete_clicked(self):
        selected_id = self.tree.focus()
        if selected_id:
            raw_id = selected_id.split(":", 1)[1] if ":" in selected_id else selected_id
            self.dispatcher.dispatch(UIDeleteItemRequestedEvent(item_id=raw_id))

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
        """Renders the tree view while preserving expanded state and applying filters."""
        tree_controller = self.context.resolve('tree_controller')
        filter_context = tree_controller.active_filter_context
        
        # Calculate whitelist if filtering is active
        whitelist = None
        if filter_context and filter_context.query_string.strip():
            from src.utils.query_parser import parse_query_to_ast
            try:
                ast = parse_query_to_ast(filter_context.query_string)
                workspace = self.context.resolve('workspace')
                whitelist = self._calculate_filter_whitelist(event.root_items, filter_context, ast, workspace)
            except ValueError:
                # Fallback to no filtering if syntax is bad
                whitelist = None

        def get_all_expanded(parent=""):
            expanded = []
            for item in self.tree.get_children(parent):
                if self.tree.item(item, "open"):
                    expanded.append(item)
                expanded.extend(get_all_expanded(item))
            return expanded
        
        all_expanded = get_all_expanded()
        
        # Helper to find any iid matching a raw_id (prefixed or not)
        def find_iids_for_raw(raw_id):
            matches = []
            # Check existing items before clearing (though they will be re-inserted)
            # Actually, since we re-insert with the same strategy, we can predict iids
            if event.products:
                for prod in event.products:
                    matches.append(f"{prod.name}:{raw_id}")
                matches.append(f"Unassigned:{raw_id}")
            else:
                matches.append(raw_id)
            return matches

        if event.expand_id:
            all_expanded.extend(find_iids_for_raw(event.expand_id))

        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Group items by Product
        if event.products:
            for product in event.products:
                relevant_epics = [e for e in event.root_items if product.name in getattr(e, 'products', [])]
                
                # If filtering, skip entire product node if no epics visible
                if whitelist is not None:
                    relevant_epics = [e for e in relevant_epics if e.id in whitelist]
                    if not relevant_epics:
                        continue

                prod_iid = f"PROD:{product.name}"
                self.tree.insert("", tk.END, iid=prod_iid, text=product.name, tags=('Product',))
                self._populate_nodes(prod_iid, relevant_epics, prod_prefix=product.name, whitelist=whitelist)
            
            # Handle Epics with no assigned products
            unassigned_epics = [e for e in event.root_items if not getattr(e, 'products', [])]
            if unassigned_epics:
                if whitelist is not None:
                    unassigned_epics = [e for e in unassigned_epics if e.id in whitelist]
                
                if unassigned_epics:
                    self.tree.insert("", tk.END, iid="PROD:Unassigned", text="Unassigned", tags=('Product',))
                    self._populate_nodes("PROD:Unassigned", unassigned_epics, prod_prefix="Unassigned", whitelist=whitelist)
        else:
            # Legacy/Fallback: No product nodes
            root_items = event.root_items
            if whitelist is not None:
                root_items = [e for e in root_items if e.id in whitelist]
            
            if root_items:
                self._populate_nodes("", root_items, whitelist=whitelist)
            
        # Restore expansion
        for iid in all_expanded:
            if self.tree.exists(iid):
                self.tree.item(iid, open=True)

        # Restore selection (checking all potential prefixed iids)
        if event.select_id:
            for potential_iid in find_iids_for_raw(event.select_id):
                if self.tree.exists(potential_iid):
                    self.tree.selection_set(potential_iid)
                    self.tree.see(potential_iid)
                    self.tree.focus(potential_iid)
                    break

    def _has_conflicted_descendant(self, item) -> bool:
        """Recursively checks if any child of the item is conflicted."""
        if getattr(item, 'is_conflicted', False):
            return True
        if hasattr(item, 'features'):
            return any(self._has_conflicted_descendant(f) for f in item.features)
        if hasattr(item, 'stories'):
            return any(getattr(s, 'is_conflicted', False) for s in item.stories)
        return False

    def _determine_node_tags(self, item) -> tuple:
        """Returns the appropriate layout fill tags depending on conflict presence."""
        item_type = type(item).__name__
        tags = [item_type]
        
        if getattr(item, 'is_conflicted', False):
            tags.append("conflict_leaf")
        elif self._has_conflicted_descendant(item):
            tags.append("conflict_parent")
            
        return tuple(tags)

    def _populate_nodes(self, parent_iid: str, items: list, prod_prefix: str = "", whitelist=None):
        """Recursively populates nodes from Agile objects, respecting whitelist."""
        show_status = ThemeManager.load_all_settings().get('show_status_in_tree', True)
        for item in items:
            if whitelist is not None and item.id not in whitelist:
                continue

            raw_id = getattr(item, 'id', str(id(item)))
            # Ensure unique iid if item appears multiple times under different products
            item_id = f"{prod_prefix}:{raw_id}" if prod_prefix else raw_id
            
            title = getattr(item, 'title', "Untitled")
            weight = getattr(item, 'weight', 0.0)
            status = str(getattr(item, 'status', 'Backlog'))
            item_type = type(item).__name__
            
            if show_status:
                display_text = f"[{weight:.1f}] ({status}) {title}"
            else:
                display_text = f"[{weight:.1f}] {title}"
                
            tags = self._determine_node_tags(item)
            node_iid = self.tree.insert(parent_iid, tk.END, iid=item_id, text=display_text, tags=tags)
            
            if item_type == "Epic" and hasattr(item, "features"):
                self._populate_nodes(node_iid, item.features, prod_prefix=prod_prefix, whitelist=whitelist)
            elif item_type == "Feature" and hasattr(item, "stories"):
                self._populate_nodes(node_iid, item.stories, prod_prefix=prod_prefix, whitelist=whitelist)

    def _calculate_filter_whitelist(self, root_items, filter_context, ast, workspace):
        """Calculates a set of item IDs that should be visible based on query AST."""
        matches = set()
        
        # 1. First pass: Find direct matches
        all_items = []
        def collect(items):
            for i in items:
                all_items.append(i)
                if hasattr(i, 'features'): collect(i.features)
                if hasattr(i, 'stories'): collect(i.stories)
        collect(root_items)
        
        for item in all_items:
            if ast.evaluate(item, workspace):
                matches.add(item.id)
                
        if not matches:
            return set()
            
        # 2. Second pass: Expand hierarchy based on modifiers
        whitelist = set(matches)
        
        if filter_context.show_ancestors:
            # We need parent mapping to trace up
            parent_map = {}
            def map_parents(items, parent_id=None):
                for i in items:
                    if parent_id: parent_map[i.id] = parent_id
                    if hasattr(i, 'features'): map_parents(i.features, i.id)
                    if hasattr(i, 'stories'): map_parents(i.stories, i.id)
            map_parents(root_items)
            
            for matched_id in matches:
                curr = matched_id
                while curr in parent_map:
                    curr = parent_map[curr]
                    whitelist.add(curr)
                    
        if filter_context.show_descendants:
            def add_descendants(item_id):
                item = next((i for i in all_items if i.id == item_id), None)
                if not item: return
                if hasattr(item, 'features'):
                    for f in item.features:
                        whitelist.add(f.id)
                        add_descendants(f.id)
                if hasattr(item, 'stories'):
                    for s in item.stories:
                        whitelist.add(s.id)
            
            for matched_id in matches:
                add_descendants(matched_id)
                
        return whitelist
