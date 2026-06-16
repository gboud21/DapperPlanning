import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from src.core.app_context import AppContext
from src.core.events import (
    EventDispatcher, ModelHierarchyUpdatedEvent, ModelWorkspaceLoadedEvent,
    AppThemeChangedEvent, UIPiPlannerTreeSelectionChangedEvent
)
from src.core.commands import (
    CreateProductCommand, CreateProductTeamCommand, AddMemberToTeamCommand, RemoveMemberFromTeamCommand
)

class TeamTreePane(ttk.Frame):
    def __init__(self, parent, context: AppContext):
        super().__init__(parent)
        self.context = context
        self.dispatcher: EventDispatcher = context.resolve('event_dispatcher')
        self.workspace = context.resolve('workspace')
        self.command_bus = context.resolve('command_bus')
        
        self._active_drag_data = None
        
        self._setup_ui()
        self._bind_events()
        
    def _setup_ui(self):
        # Vertical splitter partition layout split
        self.paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        # 1. Hierarchy Tree View Container Frame Area
        self.tree_frame = ttk.LabelFrame(self.paned, text="Team Composition Hierarchy")
        self.paned.add(self.tree_frame, weight=3)

        self.tree_scroll = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL)
        self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(
            self.tree_frame, 
            columns=("type", "entity_id"), 
            show="tree",
            yscrollcommand=self.tree_scroll.set
        )
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree_scroll.config(command=self.tree.yview)
        
        # Define Tags for styling
        self.tree.tag_configure('Product', font=("TkDefaultFont", 10, "bold"))
        self.tree.tag_configure('Team', font=("TkDefaultFont", 10))
        self.tree.tag_configure('Member', font=("TkDefaultFont", 9, "italic"))

        # 2. Members Directory Listbox Container Component Frame
        self.list_frame = ttk.LabelFrame(self.paned, text="GitLab Sync Directory")
        self.paned.add(self.list_frame, weight=1)

        self.list_scroll = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL)
        self.list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(
            self.list_frame, 
            selectmode=tk.SINGLE,
            yscrollcommand=self.list_scroll.set
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.list_scroll.config(command=self.listbox.yview)
        
        self._bind_context_menus()
        self._bind_drag_and_drop_hooks()
        self._bind_tree_selection()

    def _bind_context_menus(self):
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Button-2>", self._show_context_menu) # For macOS

    def _show_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        menu = tk.Menu(self, tearoff=0)
        
        if not item_id:
            menu.add_command(label="Add Product", command=self._cmd_add_product)
        else:
            node_type = self.tree.set(item_id, "type")
            entity_id = self.tree.set(item_id, "entity_id")
            
            if node_type == "Product":
                menu.add_command(label="Add Product Team", command=lambda: self._cmd_add_team(entity_id))
            elif node_type == "Team":
                menu.add_command(label="Add Member Here", command=lambda: self._cmd_add_member(entity_id))
            elif node_type == "Member":
                # Find parent team ID for this member node
                parent_iid = self.tree.parent(item_id)
                if parent_iid:
                    team_id = self.tree.set(parent_iid, "entity_id")
                    menu.add_command(label="Remove Member from Team", command=lambda: self._cmd_remove_member(team_id, int(entity_id)))
            
        menu.post(event.x_root, event.y_root)

    def _bind_drag_and_drop_hooks(self):
        self.listbox.bind("<Button-1>", self._on_drag_start)
        self.listbox.bind("<B1-Motion>", self._on_drag_motion)
        self.listbox.bind("<ButtonRelease-1>", self._on_drag_release)

    def _bind_tree_selection(self):
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        
        item_id = selected[0]
        node_type = self.tree.set(item_id, "type")
        entity_id = self.tree.set(item_id, "entity_id")
        
        self.dispatcher.dispatch(UIPiPlannerTreeSelectionChangedEvent(
            selected_type=node_type,
            selected_id=entity_id
        ))

    def _on_drag_start(self, event):
        idx = self.listbox.nearest(event.y)
        if idx >= 0:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)
            self._active_drag_data = self.listbox.get(idx)
            self.config(cursor="hand2")

    def _on_drag_motion(self, event):
        pass

    def _on_drag_release(self, event):
        if not self._active_drag_data:
            return
        
        self.config(cursor="")
        
        # Map raw coordinates relative back into tree widget boundaries
        x, y = event.x_root - self.tree.winfo_rootx(), event.y_root - self.tree.winfo_rooty()
        target_row = self.tree.identify_row(y)
        
        if target_row:
            node_type = self.tree.set(target_row, "type")
            team_id = self.tree.set(target_row, "entity_id")
            
            if node_type == "Team":
                # Parse member ID from string "(ID) Name" or just find by name
                member_str = self._active_drag_data
                if "(" in member_str and ")" in member_str:
                    try:
                        m_id = int(member_str.split("(")[1].split(")")[0])
                        self.command_bus.execute(AddMemberToTeamCommand(team_id=team_id, member_id=m_id))
                    except ValueError:
                        pass
        
        self._active_drag_data = None

    def _cmd_add_product(self):
        name = simpledialog.askstring("Add Product", "Enter Product Name:")
        if name:
            self.command_bus.execute(CreateProductCommand(name=name))

    def _cmd_add_team(self, product_id):
        name = simpledialog.askstring("Add Team", "Enter Team Name:")
        if name:
            self.command_bus.execute(CreateProductTeamCommand(name=name, product_id=product_id))

    def _cmd_add_member(self, team_id):
        # If a member is selected in the listbox, use it
        selection = self.listbox.curselection()
        if selection:
            member_str = self.listbox.get(selection[0])
            if "(" in member_str and ")" in member_str:
                try:
                    m_id = int(member_str.split("(")[1].split(")")[0])
                    self.command_bus.execute(AddMemberToTeamCommand(team_id=team_id, member_id=m_id))
                    return
                except ValueError:
                    pass
        
        # Fallback to manual ID entry if no selection
        m_id = simpledialog.askinteger("Add Member", "Enter GitLab Member ID:")
        if m_id:
            self.command_bus.execute(AddMemberToTeamCommand(team_id=team_id, member_id=m_id))

    def _cmd_remove_member(self, team_id, member_id):
        if messagebox.askyesno("Remove Member", "Are you sure you want to remove this member from the team?"):
            self.command_bus.execute(RemoveMemberFromTeamCommand(team_id=team_id, member_id=member_id))

    def _bind_events(self):
        self.dispatcher.subscribe(ModelHierarchyUpdatedEvent, self.refresh)
        self.dispatcher.subscribe(ModelWorkspaceLoadedEvent, self._on_workspace_loaded)
        self.dispatcher.subscribe(AppThemeChangedEvent, self._handle_theme_change)

    def _on_workspace_loaded(self, event):
        self.workspace = self.context.resolve('workspace')
        self.refresh()

    def refresh(self, event=None):
        """Re-populates the tree and member list."""
        # 1. Update Tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for product in self.workspace.products:
            p_node = self.tree.insert("", tk.END, text=product.name, tags=('Product',))
            self.tree.set(p_node, "type", "Product")
            self.tree.set(p_node, "entity_id", product.name)
            
            teams = [t for t in self.workspace.product_teams if t.product_id == product.name]
            for team in teams:
                t_node = self.tree.insert(p_node, tk.END, text=team.name, tags=('Team',))
                self.tree.set(t_node, "type", "Team")
                self.tree.set(t_node, "entity_id", team.id)
                
                for m_id in team.member_ids:
                    member = self.workspace.members.get(m_id)
                    m_name = member.name if member else f"Unknown ({m_id})"
                    m_node = self.tree.insert(t_node, tk.END, text=m_name, tags=('Member',))
                    self.tree.set(m_node, "type", "Member")
                    self.tree.set(m_node, "entity_id", str(m_id))

        # 2. Update Member List
        self.listbox.delete(0, tk.END)
        for member in sorted(self.workspace.get_members(), key=lambda m: m.name):
            self.listbox.insert(tk.END, f"({member.id}) {member.name}")

    def _handle_theme_change(self, event: AppThemeChangedEvent):
        from src.utils.theme_manager import ThemeManager
        palette = ThemeManager.DARK_PALETTE if event.is_dark else ThemeManager.LIGHT_PALETTE
        
        self.listbox.configure(
            bg=palette['field_bg'],
            fg=palette['fg'],
            selectbackground=palette['highlight']
        )
