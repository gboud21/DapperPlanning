import tkinter as tk
from tkinter import ttk
import webbrowser
from src.utils.theme_manager import ThemeManager

class DryPushSummaryModal(tk.Toplevel):
    def __init__(self, parent: tk.Tk, creations: int, updates: int, conflicts: int, deletions: int, report_path: str):
        """
        Initializes the DryPushSummaryModal.

        Args:
            parent (tk.Tk): The root window.
            creations (int): Count of items to be created on remote.
            updates (int): Count of items to be updated on remote.
            conflicts (int): Count of items in conflict.
            deletions (int): Count of items to be deleted on remote.
            report_path (str): Filepath to the generated markdown report.
        """
        super().__init__(parent)
        self.title("GitLab Dry-Push Summary")
        self.geometry("450x380")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.creations = creations
        self.updates = updates
        self.conflicts = conflicts
        self.deletions = deletions
        self.report_path = report_path
        
        self.is_dark = ThemeManager.load_settings()
        
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Status alert banner
        if self.conflicts > 0:
            status_bg = "#5c0000" if self.is_dark else "#f8d7da"
            status_fg = "#ffffff" if self.is_dark else "#721c24"
            status_title = "⚠ CONFLICTS DETECTED"
            status_desc = "Push will be blocked. Please resolve conflicts."
        else:
            status_bg = "#004d00" if self.is_dark else "#d4edda"
            status_fg = "#ffffff" if self.is_dark else "#155724"
            status_title = "✔ DRY-RUN SUCCESSFUL"
            status_desc = "No conflicts detected. Changes ready to push."

        self.status_frame = tk.Frame(main_frame, bg=status_bg, padx=10, pady=10, borderwidth=1, relief="solid")
        self.status_frame.pack(fill=tk.X, pady=(0, 15))

        self.status_lbl = tk.Label(self.status_frame, text=status_title, font=("TkDefaultFont", 11, "bold"), bg=status_bg, fg=status_fg)
        self.status_lbl.pack(anchor=tk.W)

        self.status_desc_lbl = tk.Label(self.status_frame, text=status_desc, font=("TkDefaultFont", 9), bg=status_bg, fg=status_fg, wraplength=380, justify=tk.LEFT)
        self.status_desc_lbl.pack(anchor=tk.W, pady=(2, 0))

        # Counts Section
        counts_frame = ttk.LabelFrame(main_frame, text="Summary of Changes", padding=10)
        counts_frame.pack(fill=tk.X, pady=(0, 15))

        # Align counts in a grid
        for i, (label_text, val) in enumerate([
            ("Creations:", self.creations),
            ("Updates:", self.updates),
            ("Conflicts:", self.conflicts),
            ("Deletions:", self.deletions)
        ]):
            lbl = ttk.Label(counts_frame, text=label_text, font=("TkDefaultFont", 10, "bold"))
            lbl.grid(row=i, column=0, sticky=tk.W, padx=5, pady=3)
            
            fg_color = ""
            if label_text == "Conflicts:" and self.conflicts > 0:
                fg_color = "#d9534f" if not self.is_dark else "#ff6b6b"
                
            val_lbl = tk.Label(counts_frame, text=str(val), font=("TkDefaultFont", 10), fg=fg_color, bg=counts_frame.cget("background"))
            val_lbl.grid(row=i, column=1, sticky=tk.W, padx=5, pady=3)
            
            if label_text == "Conflicts:":
                self.conflicts_val_lbl = val_lbl
            elif label_text == "Creations:":
                self.creations_val_lbl = val_lbl
            elif label_text == "Updates:":
                self.updates_val_lbl = val_lbl
            elif label_text == "Deletions:":
                self.deletions_val_lbl = val_lbl

        # Report Path section
        report_frame = ttk.Frame(main_frame)
        report_frame.pack(fill=tk.X, pady=(0, 15))

        path_lbl = ttk.Label(report_frame, text="Report Path:", font=("TkDefaultFont", 9, "bold"))
        path_lbl.pack(anchor=tk.W)

        self.path_entry = tk.Entry(report_frame, font=("TkFixedFont", 9))
        self.path_entry.insert(0, self.report_path)
        self.path_entry.config(state="readonly")
        self.path_entry.pack(fill=tk.X, pady=(2, 0))

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.open_btn = ttk.Button(btn_frame, text="Open Report", command=self._open_report)
        self.open_btn.pack(side=tk.LEFT)

        self.close_btn = ttk.Button(btn_frame, text="Close", command=self.destroy)
        self.close_btn.pack(side=tk.RIGHT)

    def _open_report(self):
        webbrowser.open(self.report_path)

    def _apply_theme(self):
        palette = ThemeManager.DARK_PALETTE if self.is_dark else ThemeManager.LIGHT_PALETTE
        bg_color = palette['bg']
        field_bg = palette['field_bg']
        fg_color = palette['fg']
        highlight = palette['highlight']

        self.configure(bg=bg_color)
        
        self.path_entry.configure(
            bg=field_bg,
            fg=fg_color,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=highlight,
            insertbackground='white' if self.is_dark else 'black'
        )
        
        # Update any custom label backgrounds
        for lbl in [self.creations_val_lbl, self.updates_val_lbl, self.conflicts_val_lbl, self.deletions_val_lbl]:
            lbl.configure(bg=bg_color)
            if lbl != self.conflicts_val_lbl or self.conflicts == 0:
                lbl.configure(fg=fg_color)
