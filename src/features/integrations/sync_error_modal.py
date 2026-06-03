import tkinter as tk
from tkinter import ttk
from src.utils.theme_manager import ThemeManager

class SyncErrorModal(tk.Toplevel):
    def __init__(self, parent: tk.Tk, title: str, error_message: str, suggested_solution: str, debug_info: dict = None, is_dark: bool = False):
        """
        Initializes the SyncErrorModal.

        Args:
            parent (tk.Tk): The root window.
            title (str): The error title.
            error_message (str): The technical error message.
            suggested_solution (str): A human-readable solution.
            debug_info (dict): Detailed model/settings data for debugging.
            is_dark (bool): Whether to use dark theme colors.
        """
        super().__init__(parent)
        self.title(title)
        self.geometry("550x500")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.error_message = error_message
        self.suggested_solution = suggested_solution
        self.debug_info = debug_info or {}
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
        self.solution_frame.pack(fill=tk.X, pady=(0, 15))

        solution_lbl = ttk.Label(self.solution_frame, text=self.suggested_solution, wraplength=480, font=("TkDefaultFont", 10))
        solution_lbl.pack(fill=tk.BOTH, expand=True)

        # Debug Information Section
        debug_lbl = ttk.Label(main_frame, text="Debug Information:", font=("TkDefaultFont", 10, "bold"))
        debug_lbl.pack(anchor=tk.W)

        # Extract token for specialized widget and mask it in the general log
        self._raw_token = self.debug_info.pop("Token", "N/A")
        
        self.debug_text = tk.Text(main_frame, height=6, wrap=tk.NONE, font=("TkFixedFont", 9))
        debug_content = "\n".join([f"{k}: {v}" for k, v in self.debug_info.items()])
        debug_content += f"\nToken: {'*' * 8} (Use button below to reveal)"
        
        self.debug_text.insert("1.0", debug_content)
        self.debug_text.config(state=tk.DISABLED)
        
        # Add scrollbars for debug info
        debug_scroll_y = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.debug_text.yview)
        debug_scroll_x = ttk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=self.debug_text.xview)
        self.debug_text.configure(yscrollcommand=debug_scroll_y.set, xscrollcommand=debug_scroll_x.set)
        
        self.debug_text.pack(fill=tk.BOTH, expand=True)
        
        # Token Reveal Widget
        token_frame = ttk.Frame(main_frame)
        token_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.token_entry = tk.Entry(token_frame, font=("TkFixedFont", 9), show="*")
        self.token_entry.insert(0, self._raw_token)
        self.token_entry.config(state='readonly')
        self.token_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.reveal_btn = ttk.Button(token_frame, text="Reveal PAT", command=self._toggle_token_visibility)
        self.reveal_btn.pack(side=tk.RIGHT)
        
        # Close Button
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        
        close_btn = ttk.Button(btn_frame, text="Close", command=self.destroy)
        close_btn.pack(side=tk.RIGHT)

    def _toggle_token_visibility(self):
        """Toggles the visibility of the PAT in the entry widget."""
        if self.token_entry.cget('show') == '*':
            self.token_entry.config(show='')
            self.reveal_btn.config(text="Hide PAT")
        else:
            self.token_entry.config(show='*')
            self.reveal_btn.config(text="Reveal PAT")

    def _apply_theme(self):
        """Applies theme-specific styling."""
        palette = ThemeManager.DARK_PALETTE if self.is_dark else ThemeManager.LIGHT_PALETTE
        bg_color = palette['bg']
        field_bg = palette['field_bg']
        fg_color = palette['fg']
        highlight = palette['highlight']
        cursor_color = 'white' if self.is_dark else 'black'

        self.configure(bg=bg_color)
        
        # Style the multi-line Text widgets
        for widget in [self.msg_text, self.debug_text]:
            widget.configure(
                bg=field_bg, 
                fg=fg_color, 
                borderwidth=0, 
                highlightthickness=1, 
                highlightbackground=highlight,
                insertbackground=cursor_color
            )
        
        # Style the token reveal entry (High Contrast: Black on White)
        self.token_entry.configure(
            bg='white',
            fg='black',
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=highlight,
            insertbackground='black'
        )
        
        # Style the LabelFrame
        self.solution_frame.configure(bg=bg_color, fg=fg_color, borderwidth=1, relief="solid")
