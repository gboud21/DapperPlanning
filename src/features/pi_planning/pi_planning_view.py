import tkinter as tk
from tkinter import ttk
from src.core.app_context import AppContext
from src.features.pi_planning.team_tree_pane import TeamTreePane
from src.features.pi_planning.spreadsheet_pane import ScrollableSpreadsheetPane
from src.features.pi_planning.metrics_editor_pane import MetricsEditorPane
from src.core.events import (
    UIPiPlannerTreeSelectionChangedEvent, ModelHierarchyUpdatedEvent, 
    ModelWorkspaceLoadedEvent, UIPiPlannerCellSelectedEvent
)

class PIPlanningView(ttk.Frame):
    def __init__(self, parent, context: AppContext):
        super().__init__(parent)
        self.context = context
        self.dispatcher = context.resolve('event_dispatcher')
        self.workspace = context.resolve('workspace')
        
        self.context.register('pi_planning_view', self)
        
        self.current_selection = None
        
        # Main horizontal paned window to split sidebar and main area
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # 1. Left Side: Team Composition Tree
        self.left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=1)
        
        self.team_tree = TeamTreePane(self.left_frame, self.context)
        self.team_tree.pack(fill=tk.BOTH, expand=True)
        self.context.register('team_tree_pane', self.team_tree)

        # 2. Right Side: Planning Spreadsheet & Metrics
        self.right_frame = ttk.Frame(self.paned_window, padding=10)
        self.paned_window.add(self.right_frame, weight=4)
        
        self.spreadsheet = ScrollableSpreadsheetPane(self.right_frame, self.context)
        self.spreadsheet.pack(fill=tk.BOTH, expand=True)
        self.context.register('pi_spreadsheet', self.spreadsheet)

        self.metrics_editor = MetricsEditorPane(self.right_frame, self.context)
        self.metrics_editor.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        self.context.register('pi_metrics_editor', self.metrics_editor)

        self._bind_events()

    def _bind_events(self):
        self.dispatcher.subscribe(UIPiPlannerTreeSelectionChangedEvent, self._handle_selection_changed)
        self.dispatcher.subscribe(UIPiPlannerCellSelectedEvent, self._handle_cell_selected)
        self.dispatcher.subscribe(ModelHierarchyUpdatedEvent, self._handle_model_updated)
        self.dispatcher.subscribe(ModelWorkspaceLoadedEvent, self._handle_workspace_loaded)

    def _handle_workspace_loaded(self, event: ModelWorkspaceLoadedEvent):
        """Refreshes the workspace reference."""
        self.workspace = self.context.resolve('workspace')
        self.refresh_spreadsheet()

    def _handle_selection_changed(self, event: UIPiPlannerTreeSelectionChangedEvent):
        self.current_selection = {'selected_type': event.selected_type, 'selected_id': event.selected_id}
        self.refresh_spreadsheet()

    def _handle_cell_selected(self, event: UIPiPlannerCellSelectedEvent):
        """Triggers immediate redraw to show highlight."""
        # Note: self.current_selection doesn't necessarily need updating here 
        # because the spreadsheet already knows its selected coords.
        # But we refresh to force the repaint.
        self.refresh_spreadsheet()

    def _handle_model_updated(self, event: ModelHierarchyUpdatedEvent):
        self.refresh_spreadsheet()

    def refresh_spreadsheet(self):
        self.spreadsheet.render_matrix_grid(
            iterations=self.workspace.iterations,
            tree_selection=self.current_selection
        )
