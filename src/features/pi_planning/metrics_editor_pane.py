import tkinter as tk
from tkinter import ttk, messagebox
from src.core.app_context import AppContext
from src.core.events import (
    UIUpdateCapacityMetricsRequestedEvent, UIPiPlannerTreeSelectionChangedEvent, 
    AppThemeChangedEvent, ModelWorkspaceLoadedEvent
)

class MetricsEditorPane(ttk.LabelFrame):
    def __init__(self, parent, context: AppContext):
        super().__init__(parent, text="Capacity Metrics Editor", padding=10)
        self.context = context
        self.dispatcher = context.resolve('event_dispatcher')
        self.workspace = context.resolve('workspace')
        
        self.current_selection = None
        self.active_iteration_id = None
        
        self._setup_form()
        self._bind_events()

    def _setup_form(self):
        # Grid layout for inputs
        # Row 0: PTO and Allocation
        ttk.Label(self, text="PTO Days:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.entry_pto = tk.Entry(self, width=10)
        self.entry_pto.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.entry_pto.bind("<FocusOut>", self._on_field_changed)
        
        ttk.Label(self, text="Allocation %:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.entry_alloc = tk.Entry(self, width=10)
        self.entry_alloc.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        self.entry_alloc.bind("<FocusOut>", self._on_field_changed)

        # Row 1: Velocity and Utilization
        ttk.Label(self, text="Velocity Factor %:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.entry_vel = tk.Entry(self, width=10)
        self.entry_vel.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.entry_vel.bind("<FocusOut>", self._on_field_changed)
        
        ttk.Label(self, text="Utilization Factor %:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.entry_util = tk.Entry(self, width=10)
        self.entry_util.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        self.entry_util.bind("<FocusOut>", self._on_util_changed)

        # Load global utilization
        settings = self.context.resolve('settings_manager')
        self.entry_util.insert(0, str(settings.get('utilization_factor', 100)))

        # Initially disable inputs
        self._set_inputs_state("disabled")

    def _set_inputs_state(self, state):
        for entry in [self.entry_pto, self.entry_alloc, self.entry_vel]:
            entry.config(state=state)
        # Utilization is always editable
        self.entry_util.config(state="normal")

    def _bind_events(self):
        self.dispatcher.subscribe(UIPiPlannerTreeSelectionChangedEvent, self._handle_selection_changed)
        self.dispatcher.subscribe(AppThemeChangedEvent, self._handle_theme_change)
        self.dispatcher.subscribe(ModelWorkspaceLoadedEvent, self._handle_workspace_loaded)

    def _handle_workspace_loaded(self, event: ModelWorkspaceLoadedEvent):
        """Refreshes the workspace reference."""
        self.workspace = self.context.resolve('workspace')
        self._load_metrics()

    def _handle_selection_changed(self, event: UIPiPlannerTreeSelectionChangedEvent):
        self.current_selection = {'type': event.selected_type, 'id': event.selected_id}
        
        if event.selected_type == "Member":
            self._set_inputs_state("normal")
            # Populate fields if we have iteration data
            if self.workspace.iterations:
                # For Phase 4, we default to the first iteration if none selected
                if not self.active_iteration_id:
                    self.active_iteration_id = self.workspace.iterations[0].id
                self._load_metrics()
        else:
            self._set_inputs_state("disabled")
            self._clear_fields()
            # If it's a product or team, we might still want to trigger a refresh of the spreadsheet 
            # if anything changed, but tree selection event already triggers that in PIPlanningView.

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
        self.entry_alloc.insert(0, str(cap.allocation_pct if cap else 100))
        
        self.entry_vel.delete(0, tk.END)
        self.entry_vel.insert(0, str(cap.velocity_factor if cap else 100))

    def _clear_fields(self):
        for entry in [self.entry_pto, self.entry_alloc, self.entry_vel]:
            entry.delete(0, tk.END)

    def _on_field_changed(self, event):
        if not self.current_selection or self.current_selection['type'] != "Member":
            return
            
        try:
            # 1. Validation
            pto = int(self.entry_pto.get() or 0)
            alloc = int(self.entry_alloc.get().replace('%', '') or 100)
            vel = int(self.entry_vel.get().replace('%', '') or 100)
            
            # Clamp bounds
            alloc = max(0, min(100, alloc))
            vel = max(0, min(100, vel))
            
            # PTO bounds check (requires iteration context)
            if self.active_iteration_id:
                it = next((i for i in self.workspace.iterations if i.id == self.active_iteration_id), None)
                if it:
                    from src.utils.date_utils import calculate_sprint_business_days
                    max_days = calculate_sprint_business_days(it.start_date, it.end_date)
                    pto = max(0, min(max_days, pto))

            # 2. Update UI with cleaned values
            self.entry_pto.delete(0, tk.END); self.entry_pto.insert(0, str(pto))
            self.entry_alloc.delete(0, tk.END); self.entry_alloc.insert(0, f"{alloc}")
            self.entry_vel.delete(0, tk.END); self.entry_vel.insert(0, f"{vel}")

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
            util = int(self.entry_util.get().replace('%', '') or 100)
            util = max(0, min(100, util))
            self.entry_util.delete(0, tk.END); self.entry_util.insert(0, f"{util}")
            
            # Save to settings
            settings = self.context.resolve('settings_manager')
            settings.set('utilization_factor', util)
            
            # Trigger full refresh
            self.dispatcher.dispatch(UIPiPlannerTreeSelectionChangedEvent(
                selected_type=self.current_selection['type'] if self.current_selection else "Product",
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
