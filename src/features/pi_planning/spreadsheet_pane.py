import tkinter as tk
from tkinter import ttk
from src.core.app_context import AppContext
from src.utils.date_utils import calculate_sprint_business_days
from src.core.events import ModelHierarchyUpdatedEvent, AppThemeChangedEvent, ModelWorkspaceLoadedEvent, UIPiPlannerCellSelectedEvent, UIPiPlannerTreeSelectionChangedEvent
from src.core.constants import AgileObjectType, PERCENT_DENOMINATOR, DEFAULT_FACTOR_VALUE

HEADER_FONT = ("Arial", 10, "bold")
DEFAULT_CELL_WIDTH = 10
SELECTION_BG_COLOR = "#1e40af"
OVERLOAD_FG_COLOR = "red"
DEFAULT_FG_COLOR = "black"

PAD_CELL_X = 2
PAD_CELL_Y = 2
PAD_ROW_X = 10

class ScrollableSpreadsheetPane(ttk.Frame):
    def __init__(self, parent, context: AppContext):
        super().__init__(parent)
        self.context = context
        self.workspace = context.resolve('workspace')
        self.dispatcher = context.resolve('event_dispatcher')
        self._selected_cell_coords = None  # Tracks tuple: (row_id, iteration_id)
        
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

    def _on_cell_clicked(self, row_data, iteration_id):
        """Caches coordinates locally and dispatches parameters to update the metrics form."""
        self._selected_cell_coords = (str(row_data['id']), iteration_id)
        self.dispatcher.dispatch(UIPiPlannerCellSelectedEvent(
            selected_type=row_data['type'],
            selected_id=str(row_data['id']),
            team_id=row_data['team_id'],
            iteration_id=iteration_id
        ))
        # Refresh view locally to immediately show the highlight update
        self.dispatcher.dispatch(UIPiPlannerTreeSelectionChangedEvent(
            selected_type=row_data['type'],
            selected_id=str(row_data['id'])
        ))

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

        # Filter iterations down based on workspace exclusion configurations
        visible_iterations = [i for i in iterations if i.id not in self.workspace.hidden_iteration_ids]

        from src.utils.theme_manager import ThemeManager
        is_dark = ThemeManager.load_settings()
        palette = ThemeManager.DARK_PALETTE if is_dark else ThemeManager.LIGHT_PALETTE

        # Header Configuration
        source_title = "Hierarchical Node Source"
        if tree_selection:
            source_title = f"{str(tree_selection['selected_type'])}: {tree_selection['selected_id']}"

        lbl_main_title = tk.Label(self.scroll_inner_frame, text=source_title, font=HEADER_FONT, 
                                  bg=palette['bg'], fg=palette['fg'], relief="ridge")
        lbl_main_title.grid(row=0, column=0, rowspan=2, sticky=tk.NSEW, padx=5, pady=5)
        lbl_main_title.bind("<Button-3>", lambda e: self._show_context_menu(e))

        col_idx = 1
        for iteration in visible_iterations:
            lbl_iter = tk.Label(self.scroll_inner_frame, text=iteration.title, anchor=tk.CENTER, font=HEADER_FONT,
                                bg=palette['field_bg'], fg=palette['fg'], relief="ridge")
            lbl_iter.grid(row=0, column=col_idx, columnspan=2, sticky=tk.EW, padx=PAD_CELL_X, pady=PAD_CELL_Y)
            lbl_iter.bind("<Button-3>", lambda e, it_id=iteration.id: self._show_context_menu(e, it_id))
            
            # Row 1: Target Data Sub-headers
            tk.Label(self.scroll_inner_frame, text="Capacity", width=DEFAULT_CELL_WIDTH, anchor=tk.CENTER,
                     bg=palette['bg'], fg=palette['fg']).grid(row=1, column=col_idx, padx=PAD_CELL_X, pady=PAD_CELL_Y)
            tk.Label(self.scroll_inner_frame, text="Load", width=DEFAULT_CELL_WIDTH, anchor=tk.CENTER,
                     bg=palette['bg'], fg=palette['fg']).grid(row=1, column=col_idx+1, padx=PAD_CELL_X, pady=PAD_CELL_Y)
            col_idx += 2

        # Data Rows
        # Determine what rows to show based on tree selection
        rows_to_render = self._get_rows_to_render(tree_selection)
        
        for r_idx, row_data in enumerate(rows_to_render):
            # Column 0: Name
            lbl_name = tk.Label(self.scroll_inner_frame, text=row_data['display_name'], 
                     bg=palette['bg'], fg=palette['fg'])
            lbl_name.grid(row=r_idx+2, column=0, sticky=tk.W, padx=PAD_ROW_X, pady=PAD_CELL_Y)
            lbl_name.bind("<Button-3>", lambda e: self._show_context_menu(e))
            
            col_idx = 1
            for iteration in visible_iterations:
                capacity = self._calculate_capacity(row_data, iteration)
                load = self._calculate_load(row_data, iteration)
                
                # Establish unique coordinate lookup key
                is_selected = (str(row_data['id']), iteration.id) == self._selected_cell_coords
                
                # Capacity Cell Label Creation
                lbl_cap = tk.Label(
                    self.scroll_inner_frame, 
                    text=f"{capacity:.1f}", 
                    width=DEFAULT_CELL_WIDTH, 
                    relief="groove",
                    bg=SELECTION_BG_COLOR if is_selected else palette['field_bg'],
                    fg=palette['fg']
                )
                lbl_cap.grid(row=r_idx+2, column=col_idx, padx=PAD_CELL_X, pady=PAD_CELL_Y)
                lbl_cap.bind("<Button-1>", lambda e, rd=row_data, it_id=iteration.id: self._on_cell_clicked(rd, it_id))
                lbl_cap.bind("<Button-3>", lambda e, it_id=iteration.id: self._show_context_menu(e, it_id))
                
                # Load Cell Label Creation
                fg_color = OVERLOAD_FG_COLOR if load > capacity and capacity > 0 else palette['fg']
                lbl_load = tk.Label(
                    self.scroll_inner_frame, 
                    text=f"{load:.1f}", 
                    width=DEFAULT_CELL_WIDTH, 
                    relief="groove",
                    fg=fg_color,
                    bg=SELECTION_BG_COLOR if is_selected else palette['field_bg']
                )
                lbl_load.grid(row=r_idx+2, column=col_idx+1, padx=PAD_CELL_X, pady=PAD_CELL_Y)
                lbl_load.bind("<Button-1>", lambda e, rd=row_data, it_id=iteration.id: self._on_cell_clicked(rd, it_id))
                lbl_load.bind("<Button-3>", lambda e, it_id=iteration.id: self._show_context_menu(e, it_id))
                
                col_idx += 2

    def _show_context_menu(self, event, target_iteration_id=None):
        """Generates context menu popups housing column adjustment filters."""
        menu = tk.Menu(self, tearoff=0)
        
        from src.utils.theme_manager import ThemeManager
        is_dark = ThemeManager.load_settings()
        palette = ThemeManager.DARK_PALETTE if is_dark else ThemeManager.LIGHT_PALETTE
        
        menu.configure(
            bg=palette['field_bg'],
            fg=palette['fg'],
            activebackground=palette['highlight'],
            activeforeground=palette['fg']
        )
        
        if target_iteration_id is not None:
            menu.add_command(label="Hide Iteration", command=lambda: self._action_hide_single(target_iteration_id))
            
        menu.add_command(label="Reveal All Iterations", command=self._action_reveal_all)
        menu.add_command(label="Modify Iteration View...", command=self._action_open_modifier_dialog)
        
        # tk_popup handles focus and dismissal automatically
        menu.tk_popup(event.x_root, event.y_root)

    def _action_hide_single(self, iteration_id):
        self.workspace.hidden_iteration_ids.append(iteration_id)
        self._force_grid_refresh()

    def _action_reveal_all(self):
        self.workspace.hidden_iteration_ids = []
        self._force_grid_refresh()

    def _action_open_modifier_dialog(self):
        from src.features.pi_planning.iteration_view_dialog import ModifyIterationViewDialog
        ModifyIterationViewDialog(self.winfo_toplevel(), self.workspace, self._force_grid_refresh)

    def _force_grid_refresh(self):
        # Force spreadsheet redraw pass using current active selection parameters
        view = self.context.resolve('pi_planning_view')
        current_sel = getattr(view, 'current_selection', None)
        self.render_matrix_grid(self.workspace.iterations, tree_selection=current_sel)
        # Fire workspace modification updates to mark clean snapshots as dirty and trigger auto-save
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
            root_items=self.workspace.get_epics(),
            products=self.workspace.products
        ))

    def _get_rows_to_render(self, selection):
        """Returns a list of data dicts for the rows of the spreadsheet."""
        if not selection:
            return []
            
        rows = []
        sel_type = selection['selected_type']
        sel_id = selection['selected_id']
        
        if sel_type == AgileObjectType.PRODUCT:
            # Show all teams for this product
            teams = [t for t in self.workspace.product_teams if t.product_id == sel_id]
            for team in teams:
                rows.append({'type': AgileObjectType.TEAM, 'id': team.id, 'display_name': team.name, 'team_id': team.id})
        elif sel_type == AgileObjectType.TEAM:
            # Show the team itself plus all its members
            team = next((t for t in self.workspace.product_teams if t.id == sel_id), None)
            if team:
                rows.append({'type': AgileObjectType.TEAM, 'id': team.id, 'display_name': f"TEAM: {team.name}", 'team_id': team.id})
                for m_id in team.member_ids:
                    member = self.workspace.members.get(m_id)
                    m_name = member.name if member else f"ID: {m_id}"
                    rows.append({'type': AgileObjectType.MEMBER, 'id': m_id, 'display_name': m_name, 'team_id': team.id})
        elif sel_type == AgileObjectType.MEMBER:
            # Just show this member (but we need to know the team context from the tree selection)
            member = self.workspace.members.get(int(sel_id))
            m_name = member.name if member else f"ID: {sel_id}"
            # Find the team this member is in (simple search)
            for team in self.workspace.product_teams:
                if int(sel_id) in team.member_ids:
                    rows.append({'type': AgileObjectType.MEMBER, 'id': int(sel_id), 'display_name': m_name, 'team_id': team.id})
                    break
        return rows

    def _calculate_capacity(self, row_data, iteration) -> float:
        days = calculate_sprint_business_days(iteration.start_date, iteration.end_date)
        
        if row_data['type'] == AgileObjectType.MEMBER:
            key = f"{row_data['team_id']}_{row_data['id']}_{iteration.id}"
            cap_record = self.workspace.member_capacities.get(key)
            
            pto = cap_record.pto if cap_record else 0
            alloc_pct = cap_record.allocation_pct if cap_record else DEFAULT_FACTOR_VALUE
            alloc = alloc_pct / PERCENT_DENOMINATOR
            
            vel_pct = cap_record.velocity_factor if cap_record else DEFAULT_FACTOR_VALUE
            vel = vel_pct / PERCENT_DENOMINATOR
            
            settings = self.context.resolve('settings_manager')
            util_val = settings._settings.get('utilization_factor', DEFAULT_FACTOR_VALUE)
            util = util_val / PERCENT_DENOMINATOR
            
            return max(0, (days - pto)) * alloc * vel * util
        else:
            # Team capacity is sum of members
            team = next((t for t in self.workspace.product_teams if t.id == row_data['id']), None)
            if not team: return 0.0
            
            total = 0.0
            for m_id in team.member_ids:
                m_row = {'type': AgileObjectType.MEMBER, 'id': m_id, 'team_id': team.id}
                total += self._calculate_capacity(m_row, iteration)
            return total

    def _calculate_load(self, row_data, iteration) -> float:
        if row_data['type'] == AgileObjectType.MEMBER:
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
                m_row = {'type': AgileObjectType.MEMBER, 'id': m_id, 'team_id': team.id}
                total += self._calculate_load(m_row, iteration)
            return total

    def _handle_theme_change(self, event: AppThemeChangedEvent):
        from src.utils.theme_manager import ThemeManager
        palette = ThemeManager.DARK_PALETTE if event.is_dark else ThemeManager.LIGHT_PALETTE
        self.canvas.configure(bg=palette['bg'])
