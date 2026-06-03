import tkinter as tk
from tkinter import ttk
from src.utils.theme_manager import ThemeManager

class SyncErrorModal(tk.Toplevel):
    def __init__(self, parent: tk.Tk, title: str, error_message: str, suggested_solution: str, is_dark: bool = False):
        """
        Initializes the SyncErrorModal.

        Args:
            parent (tk.Tk): The root window.
            title (str): The error title.
            error_message (str): The technical error message.
            suggested_solution (str): A human-readable solution.
            is_dark (bool): Whether to use dark theme colors.
        """
        super().__init__(parent)
        self.title(title)
        self.geometry("500x400")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.error_message = error_message
        self.suggested_solution = suggested_solution
        self.is_dark = is_dark

        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """Sets up the UI components."""
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header with bold error title
        header_lbl = ttk.Label(main_frame, text="⚠ Sync Operation Failed", font=("TkDefaultFont", 12, "bold"))
        header_lbl.pack(anchor=tk.W, pady=(0, 10))

        # Technical Error Message
        error_lbl = ttk.Label(main_frame, text="Technical Error:", font=("TkDefaultFont", 10, "bold"))
        error_lbl.pack(anchor=tk.W)
        
        self.msg_text = tk.Text(main_frame, height=3, wrap=tk.WORD, font=("TkDefaultFont", 10))
        self.msg_text.insert("1.0", self.error_message)
        self.msg_text.config(state=tk.DISABLED)
        self.msg_text.pack(fill=tk.X, pady=(0, 15))

        # Suggested Solution Frame
        self.solution_frame = tk.LabelFrame(main_frame, text="How to fix this:", font=("TkDefaultFont", 10, "bold"), padx=10, pady=10)
        self.solution_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        solution_lbl = ttk.Label(self.solution_frame, text=self.suggested_solution, wraplength=440, font=("TkDefaultFont", 10))
        solution_lbl.pack(fill=tk.BOTH, expand=True)

        # Close Button
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        
        close_btn = ttk.Button(btn_frame, text="Close", command=self.destroy)
        close_btn.pack(side=tk.RIGHT)

    def _apply_theme(self):
        """Applies theme-specific styling."""
        palette = ThemeManager.DARK_PALETTE if self.is_dark else ThemeManager.LIGHT_PALETTE
        bg_color = palette['bg']
        field_bg = palette['field_bg']
        fg_color = palette['fg']
        highlight = palette['highlight']

        self.configure(bg=bg_color)
        
        # Style the Text widget
        self.msg_text.configure(bg=field_bg, fg=fg_color, borderwidth=0, highlightthickness=1, highlightbackground=highlight)
        
        # Style the LabelFrame
        self.solution_frame.configure(bg=bg_color, fg=fg_color, borderwidth=1, relief="solid")
        # Note: ttk labels and frames are styled globally via ThemeManager.apply_ttk_theme
