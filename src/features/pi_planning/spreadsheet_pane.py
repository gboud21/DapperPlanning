import tkinter as tk
from tkinter import ttk
from src.core.app_context import AppContext
from src.utils.date_utils import calculate_sprint_business_days
from src.core.events import ModelHierarchyUpdatedEvent, AppThemeChangedEvent, ModelWorkspaceLoadedEvent

class ScrollableSpreadsheetPane(ttk.Frame):
    def __init__(self, parent, context: AppContext):
        super().__init__(parent)
        self.context = context
        self.workspace = context.resolve('workspace')
        self.dispatcher = context.resolve('event_dispatcher')
        
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scrollbar_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar_x = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.scroll_inner_frame = ttk.Frame(self.canvas)
        
        self.canvas.configure(xscrollcommand=self.scrollbar_x.set, yscrollcommand=self.scrollbar_y.set)
        
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas_window = self.canvas.create_window((0,0), window=self.scroll_inner_frame, anchor=tk.NW)
        
        self.scroll_inner_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        self.dispatcher.subscribe(AppThemeChangedEvent, self._handle_theme_change)
        self.dispatcher.subscribe(ModelWorkspaceLoadedEvent, self._handle_workspace_loaded)

    def _handle_workspace_loaded(self, event: ModelWorkspaceLoadedEvent):
        """Refreshes the workspace reference."""
        self.workspace = self.context.resolve('workspace')

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # Optional: could force width if needed, but matrix is usually wider than canvas
        pass

    def render_matrix_grid(self, iterations: list, tree_selection: dict = None):
        """Generates dynamic multi-level spanned layout configurations."""
        # Clean out old widget grid objects before painting updates
        for widget in self.scroll_inner_frame.winfo_children():
            widget.destroy()
            
        if not iterations:
            ttk.Label(self.scroll_inner_frame, text="No iterations found. Sync iterations first.").pack(padx=20, pady=20)
            return

        # Header Configuration
        # Row 0: Spanned Parent Headers (Iteration Titles)
        # Row 1: Sub-headers (Capacity, Load)
        
        source_title = "Hierarchical Node Source"
        if tree_selection:
            source_title = f"{tree_selection['selected_type']}: {tree_selection['selected_id']}"

        lbl_main_title = ttk.Label(self.scroll_inner_frame, text=source_title, font=("Arial", 10, "bold"), padding=10)
        lbl_main_title.grid(row=0, column=0, rowspan=2, sticky=tk.NSEW, padx=5, pady=5)
        
        col_idx = 1
        for iteration in iterations:
            lbl_iter = ttk.Label(self.scroll_inner_frame, text=iteration.title, anchor=tk.CENTER, font=("Arial", 10, "bold"))
            lbl_iter.grid(row=0, column=col_idx, columnspan=2, sticky=tk.EW, padx=2, pady=2)
            
            # Row 1: Target Data Sub-headers
            ttk.Label(self.scroll_inner_frame, text="Capacity", width=10, anchor=tk.CENTER).grid(row=1, column=col_idx, padx=2, pady=2)
            ttk.Label(self.scroll_inner_frame, text="Load", width=10, anchor=tk.CENTER).grid(row=1, column=col_idx+1, padx=2, pady=2)
            col_idx += 2

        # Data Rows
        # Determine what rows to show based on tree selection
        rows_to_render = self._get_rows_to_render(tree_selection)
        
        for r_idx, row_data in enumerate(rows_to_render):
            # Column 0: Name
            ttk.Label(self.scroll_inner_frame, text=row_data['display_name']).grid(row=r_idx+2, column=0, sticky=tk.W, padx=10, pady=2)
            
            col_idx = 1
            for iteration in iterations:
                capacity = self._calculate_capacity(row_data, iteration)
                load = self._calculate_load(row_data, iteration)
                
                # Capacity Cell
                lbl_cap = ttk.Label(self.scroll_inner_frame, text=f"{capacity:.1f}", width=10, anchor=tk.CENTER)
                lbl_cap.grid(row=r_idx+2, column=col_idx, padx=2, pady=2)
                
                # Load Cell
                # Color code load based on capacity
                fg_color = ""
                if load > capacity and capacity > 0:
                    fg_color = "red"
                
                lbl_load = ttk.Label(self.scroll_inner_frame, text=f"{load:.1f}", width=10, anchor=tk.CENTER, foreground=fg_color)
                lbl_load.grid(row=r_idx+2, column=col_idx+1, padx=2, pady=2)
                
                col_idx += 2

    def _get_rows_to_render(self, selection):
        """Returns a list of data dicts for the rows of the spreadsheet."""
        if not selection:
            return []
            
        rows = []
        sel_type = selection['selected_type']
        sel_id = selection['selected_id']
        
        if sel_type == "Product":
            # Show all teams for this product
            teams = [t for t in self.workspace.product_teams if t.product_id == sel_id]
            for team in teams:
                rows.append({'type': 'Team', 'id': team.id, 'display_name': team.name, 'team_id': team.id})
        elif sel_type == "Team":
            # Show the team itself plus all its members
            team = next((t for t in self.workspace.product_teams if t.id == sel_id), None)
            if team:
                rows.append({'type': 'Team', 'id': team.id, 'display_name': f"TEAM: {team.name}", 'team_id': team.id})
                for m_id in team.member_ids:
                    member = self.workspace.members.get(m_id)
                    m_name = member.name if member else f"ID: {m_id}"
                    rows.append({'type': 'Member', 'id': m_id, 'display_name': m_name, 'team_id': team.id})
        elif sel_type == "Member":
            # Just show this member (but we need to know the team context from the tree selection)
            # Tree selection doesn't currently provide parent ID, we might need to find it
            member = self.workspace.members.get(int(sel_id))
            m_name = member.name if member else f"ID: {sel_id}"
            # Find the team this member is in (simple search)
            for team in self.workspace.product_teams:
                if int(sel_id) in team.member_ids:
                    rows.append({'type': 'Member', 'id': int(sel_id), 'display_name': m_name, 'team_id': team.id})
                    break
        return rows

    def _calculate_capacity(self, row_data, iteration) -> float:
        days = calculate_sprint_business_days(iteration.start_date, iteration.end_date)
        
        if row_data['type'] == 'Member':
            key = f"{row_data['team_id']}_{row_data['id']}_{iteration.id}"
            cap_record = self.workspace.member_capacities.get(key)
            
            pto = cap_record.pto if cap_record else 0
            alloc = (cap_record.allocation_pct if cap_record else 100) / 100.0
            vel = (cap_record.velocity_factor if cap_record else 100) / 100.0
            
            settings = self.context.resolve('settings_manager')
            util_val = settings._settings.get('utilization_factor', 100)
            util = util_val / 100.0
            
            return max(0, (days - pto)) * alloc * vel * util
        else:
            # Team capacity is sum of members
            team = next((t for t in self.workspace.product_teams if t.id == row_data['id']), None)
            if not team: return 0.0
            
            total = 0.0
            for m_id in team.member_ids:
                m_row = {'type': 'Member', 'id': m_id, 'team_id': team.id}
                total += self._calculate_capacity(m_row, iteration)
            return total

    def _calculate_load(self, row_data, iteration) -> float:
        if row_data['type'] == 'Member':
            # Sum weight of stories assigned to this member in this iteration
            total_load = 0.0
            for epic in self.workspace.get_epics():
                for feature in epic.features:
                    for story in feature.stories:
                        if story.assignee_id == int(row_data['id']) and story.iteration_id == iteration.id:
                            total_load += story.weight
            return total_load
        else:
            # Team load is sum of members' load
            team = next((t for t in self.workspace.product_teams if t.id == row_data['id']), None)
            if not team: return 0.0
            
            total = 0.0
            for m_id in team.member_ids:
                m_row = {'type': 'Member', 'id': m_id, 'team_id': team.id}
                total += self._calculate_load(m_row, iteration)
            return total

    def _handle_theme_change(self, event: AppThemeChangedEvent):
        from src.utils.theme_manager import ThemeManager
        palette = ThemeManager.DARK_PALETTE if event.is_dark else ThemeManager.LIGHT_PALETTE
        self.canvas.configure(bg=palette['bg'])
        # Re-render to apply theme to labels if needed, or rely on ttk styles
