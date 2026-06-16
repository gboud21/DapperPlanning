import tkinter as tk
from tkinter import ttk
from src.core.app_context import AppContext
from src.features.pi_planning.team_tree_pane import TeamTreePane

class PIPlanningView(ttk.Frame):
    def __init__(self, parent, context: AppContext):
        super().__init__(parent)
        self.context = context
        
        # Main horizontal paned window to split sidebar and main area
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # 1. Left Side: Team Composition Tree (implemented in Phase 3)
        self.left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=1)
        
        self.team_tree = TeamTreePane(self.left_frame, self.context)
        self.team_tree.pack(fill=tk.BOTH, expand=True)
        self.context.register('team_tree_pane', self.team_tree)

        # 2. Right Side: Planning Spreadsheet (Placeholder for Phase 4)
        self.right_frame = ttk.Frame(self.paned_window, padding=10)
        self.paned_window.add(self.right_frame, weight=4)
        
        self.lbl_placeholder = ttk.Label(
            self.right_frame, 
            text="Planning Matrix & Capacity Editor\n(Implementation in Phase 4)", 
            font=("Arial", 14, "italic"),
            justify=tk.CENTER
        )
        self.lbl_placeholder.pack(expand=True)
