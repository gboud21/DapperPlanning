import tkinter as tk
from tkinter import ttk, messagebox
from src.core.app_context import AppContext
from src.core.events import (
    UIUpdateCapacityMetricsRequestedEvent, UIPiPlannerTreeSelectionChangedEvent, 
    AppThemeChangedEvent, ModelWorkspaceLoadedEvent, UIPiPlannerCellSelectedEvent
)
from src.core.constants import AgileObjectType, DEFAULT_FACTOR_VALUE
from src.utils.debouncer import Debouncer

ENTRY_WIDGET_WIDTH = 10
GRID_PADDING_X = 5
GRID_PADDING_Y = 5

class MetricsEditorPane(ttk.LabelFrame):
    def __init__(self, parent, context: AppContext):
        super().__init__(parent, text="Capacity Metrics Editor", padding=10)
        self.context = context
        self.dispatcher = context.resolve('event_dispatcher')
        self.workspace = context.resolve('workspace')
        
        self.current_selection = None
        self.active_iteration_id = None
        
        # Initialize debouncer for real-time updates
        self.metrics_debouncer = Debouncer(self, 500, self._on_debounce_trigger)
        
        self._setup_form()
        self._bind_events()

    def _on_debounce_trigger(self):
        """Callback for debouncer to dispatch the update event."""
        self._on_field_changed(None)
        self._on_util_changed(None)

    def _setup_form(self):
        # Grid layout for inputs
        # Row 0: PTO and Allocation
        ttk.Label(self, text="PTO Days:").grid(row=0, column=0, sticky=tk.W, padx=GRID_PADDING_X, pady=GRID_PADDING_Y)
        self.entry_pto = tk.Entry(self, width=ENTRY_WIDGET_WIDTH)
        self.entry_pto.grid(row=0, column=1, sticky=tk.W, padx=GRID_PADDING_X, pady=GRID_PADDING_Y)
        self.entry_pto.bind("<KeyRelease>", lambda e: self.metrics_debouncer.schedule())
        self.entry_pto.bind("<FocusOut>", self._on_field_changed)
        
        ttk.Label(self, text="Allocation %:").grid(row=0, column=2, sticky=tk.W, padx=GRID_PADDING_X, pady=GRID_PADDING_Y)
        self.entry_alloc = tk.Entry(self, width=ENTRY_WIDGET_WIDTH)
        self.entry_alloc.grid(row=0, column=3, sticky=tk.W, padx=GRID_PADDING_X, pady=GRID_PADDING_Y)
        self.entry_alloc.bind("<KeyRelease>", lambda e: self.metrics_debouncer.schedule())
        self.entry_alloc.bind("<FocusOut>", self._on_field_changed)

        # Row 1: Velocity and Utilization
        ttk.Label(self, text="Velocity Factor %:").grid(row=1, column=0, sticky=tk.W, padx=GRID_PADDING_X, pady=GRID_PADDING_Y)
        self.entry_vel = tk.Entry(self, width=ENTRY_WIDGET_WIDTH)
        self.entry_vel.grid(row=1, column=1, sticky=tk.W, padx=GRID_PADDING_X, pady=GRID_PADDING_Y)
        self.entry_vel.bind("<KeyRelease>", lambda e: self.metrics_debouncer.schedule())
        self.entry_vel.bind("<FocusOut>", self._on_field_changed)
        
        ttk.Label(self, text="Utilization Factor %:").grid(row=1, column=2, sticky=tk.W, padx=GRID_PADDING_X, pady=GRID_PADDING_Y)
        self.entry_util = tk.Entry(self, width=ENTRY_WIDGET_WIDTH)
        self.entry_util.grid(row=1, column=3, sticky=tk.W, padx=GRID_PADDING_X, pady=GRID_PADDING_Y)
        self.entry_util.bind("<KeyRelease>", lambda e: self.metrics_debouncer.schedule())
        self.entry_util.bind("<FocusOut>", self._on_util_changed)

        # Load global utilization
        settings = self.context.resolve('settings_manager')
        self.entry_util.insert(0, str(settings.get('utilization_factor', DEFAULT_FACTOR_VALUE)))

        # Initially disable inputs
        self._set_inputs_state("disabled")

    def _set_inputs_state(self, state):
        for entry in [self.entry_pto, self.entry_alloc, self.entry_vel]:
            entry.config(state=state)
        # Utilization is always editable
        self.entry_util.config(state="normal")

    def _bind_events(self):
        self.dispatcher.subscribe(UIPiPlannerTreeSelectionChangedEvent, self._handle_selection_changed)
        self.dispatcher.subscribe(UIPiPlannerCellSelectedEvent, self._handle_cell_selected)
        self.dispatcher.subscribe(AppThemeChangedEvent, self._handle_theme_change)
        self.dispatcher.subscribe(ModelWorkspaceLoadedEvent, self._handle_workspace_loaded)

    def _handle_cell_selected(self, event: UIPiPlannerCellSelectedEvent):
        """Intercepts matrix grid selections to contextually unlock input entries."""
        self.current_selection = {'type': event.selected_type, 'id': event.selected_id}
        self.active_iteration_id = event.iteration_id
        
        # Update title to show context
        it = next((i for i in self.workspace.iterations if i.id == self.active_iteration_id), None)
        it_name = it.title if it else "Unknown"
        self.config(text=f"Capacity Metrics Editor - {it_name}")

        if event.selected_type == AgileObjectType.MEMBER:
            self._set_inputs_state("normal")
            self._load_metrics()
        else:
            self._set_inputs_state("disabled")
            self._clear_fields()

    def _handle_workspace_loaded(self, event: ModelWorkspaceLoadedEvent):
        """Refreshes the workspace reference."""
        self.workspace = self.context.resolve('workspace')
        self._load_metrics()

    def _handle_selection_changed(self, event: UIPiPlannerTreeSelectionChangedEvent):
        self.current_selection = {'type': event.selected_type, 'id': event.selected_id}
        
        if event.selected_type == AgileObjectType.MEMBER:
            self._set_inputs_state("normal")
            # Populate fields if we have iteration data
            if self.workspace.iterations:
                # Default to first iteration if no cell has been clicked yet
                if self.active_iteration_id is None:
                    self.active_iteration_id = self.workspace.iterations[0].id
                
                it = next((i for i in self.workspace.iterations if i.id == self.active_iteration_id), None)
                it_name = it.title if it else "Unknown"
                self.config(text=f"Capacity Metrics Editor - {it_name}")
                self._load_metrics()
        else:
            self._set_inputs_state("disabled")
            self._clear_fields()
            self.config(text="Capacity Metrics Editor")

    def _load_metrics(self):
        if not self.current_selection or not self.active_iteration_id:
            return
            
        # Find team ID for the member
        team_id = None
        m_id = int(self.current_selection['id'])
        for team in self.workspace.product_teams:
            if m_id in team.member_ids:
                team_id = team.id
                break
        
        if not team_id: return
        
        key = f"{team_id}_{m_id}_{self.active_iteration_id}"
        cap = self.workspace.member_capacities.get(key)
        
        self.entry_pto.delete(0, tk.END)
        self.entry_pto.insert(0, str(cap.pto if cap else 0))
        
        self.entry_alloc.delete(0, tk.END)
        self.entry_alloc.insert(0, f"{cap.allocation_pct if cap else DEFAULT_FACTOR_VALUE}%")
        
        self.entry_vel.delete(0, tk.END)
        self.entry_vel.insert(0, f"{cap.velocity_factor if cap else DEFAULT_FACTOR_VALUE}%")

    def _clear_fields(self):
        for entry in [self.entry_pto, self.entry_alloc, self.entry_vel]:
            entry.delete(0, tk.END)

    def _on_field_changed(self, event):
        if not self.current_selection or self.current_selection['type'] != AgileObjectType.MEMBER:
            return
            
        try:
            MIN_PERCENT_BOUND = 0
            MAX_PERCENT_BOUND = 100

            # 1. Validation
            pto_str = self.entry_pto.get()
            pto = int(pto_str) if pto_str else 0
            
            alloc_str = self.entry_alloc.get().replace('%', '')
            alloc = int(alloc_str) if alloc_str else DEFAULT_FACTOR_VALUE
            
            vel_str = self.entry_vel.get().replace('%', '')
            vel = int(vel_str) if vel_str else DEFAULT_FACTOR_VALUE
            
            # Clamp bounds
            alloc = max(MIN_PERCENT_BOUND, min(MAX_PERCENT_BOUND, alloc))
            vel = max(MIN_PERCENT_BOUND, min(MAX_PERCENT_BOUND, vel))
            
            # PTO bounds check (requires iteration context)
            if self.active_iteration_id:
                it = next((i for i in self.workspace.iterations if i.id == self.active_iteration_id), None)
                if it:
                    from src.utils.date_utils import calculate_sprint_business_days
                    max_days = calculate_sprint_business_days(it.start_date, it.end_date)
                    pto = max(0, min(max_days, pto))

            # 2. Update UI with cleaned and formatted values
            self.entry_pto.delete(0, tk.END); self.entry_pto.insert(0, str(pto))
            self.entry_alloc.delete(0, tk.END); self.entry_alloc.insert(0, f"{alloc}%")
            self.entry_vel.delete(0, tk.END); self.entry_vel.insert(0, f"{vel}%")

            # 3. Dispatch Update
            team_id = self._find_team_for_member(int(self.current_selection['id']))
            if team_id and self.active_iteration_id:
                self.dispatcher.dispatch(UIUpdateCapacityMetricsRequestedEvent(
                    team_id=team_id,
                    member_id=int(self.current_selection['id']),
                    iteration_id=self.active_iteration_id,
                    pto=pto,
                    allocation_pct=alloc,
                    velocity_factor=vel
                ))
        except ValueError:
            self._load_metrics() # Reset to last valid state

    def _on_util_changed(self, event):
        try:
            MIN_PERCENT_BOUND = 0
            MAX_PERCENT_BOUND = 100

            util_str = self.entry_util.get().replace('%', '')
            util = int(util_str) if util_str else DEFAULT_FACTOR_VALUE
            util = max(MIN_PERCENT_BOUND, min(MAX_PERCENT_BOUND, util))
            self.entry_util.delete(0, tk.END); self.entry_util.insert(0, f"{util}%")
            
            # Save to settings
            settings = self.context.resolve('settings_manager')
            settings.set('utilization_factor', util)
            settings.save()
            
            # Trigger full refresh via cell selection event if available, else standard selection
            if self.current_selection and self.active_iteration_id:
                 self.dispatcher.dispatch(UIPiPlannerCellSelectedEvent(
                    selected_type=self.current_selection['type'],
                    selected_id=str(self.current_selection['id']),
                    team_id=self._find_team_for_member(int(self.current_selection['id'])),
                    iteration_id=self.active_iteration_id
                ))
            else:
                self.dispatcher.dispatch(UIPiPlannerTreeSelectionChangedEvent(
                    selected_type=self.current_selection['type'] if self.current_selection else AgileObjectType.PRODUCT,
                    selected_id=self.current_selection['id'] if self.current_selection else ""
                ))
        except:
            pass

    def _find_team_for_member(self, member_id):
        for team in self.workspace.product_teams:
            if member_id in team.member_ids:
                return team.id
        return None

    def _handle_theme_change(self, event: AppThemeChangedEvent):
        from src.utils.theme_manager import ThemeManager
        palette = ThemeManager.DARK_PALETTE if event.is_dark else ThemeManager.LIGHT_PALETTE
        cursor_color = 'white' if event.is_dark else 'black'
        
        for entry in [self.entry_pto, self.entry_alloc, self.entry_vel, self.entry_util]:
            entry.configure(
                bg=palette['field_bg'],
                fg=palette['fg'],
                insertbackground=cursor_color,
                highlightthickness=1,
                highlightbackground=palette['bg'],
                highlightcolor=palette['highlight'],
                borderwidth=0
            )
