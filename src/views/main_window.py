import tkinter as tk
from tkinter import ttk
from src.events import (
    EventDispatcher, UISyncRequestedEvent
)
from .tree_pane import TreePane
from .editor_pane import EditorPane

class MainWindow:
    def __init__(self, root: tk.Tk, dispatcher: EventDispatcher):
        """
        Initialize the MainWindow.

        Args:
            root (tk.Tk): The root Tkinter window.
            dispatcher (EventDispatcher): The event dispatcher for UI and model communication.
        """
        self.root = root
        self.dispatcher = dispatcher
        
        self.setup_menu()
        self.setup_ui()
        self._bind_events()

    def setup_menu(self):
        """Sets up the main menu bar."""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Copy", command=lambda: None)
        edit_menu.add_command(label="Cut", command=lambda: None)
        edit_menu.add_command(label="Paste", command=lambda: None)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Minimize", command=self._minimize_window)
        view_menu.add_command(label="Maximize", command=self._maximize_window)
        view_menu.add_command(label="Windowed Mode", command=self._restore_window)
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about_dialog)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)

    def _show_about_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("About")
        dialog.geometry("200x100")
        dialog.transient(self.root)
        dialog.grab_set()
        
        close_btn = ttk.Button(dialog, text="Close", command=dialog.destroy)
        close_btn.pack(expand=True)

    def _minimize_window(self):
        self.root.iconify()

    def _maximize_window(self):
        try:
            self.root.state("zoomed")
        except tk.TclError:
            try:
                self.root.attributes("-zoomed", True)
            except tk.TclError:
                pass

    def _restore_window(self):
        try:
            self.root.state("normal")
        except tk.TclError:
            pass
        try:
            self.root.attributes("-zoomed", False)
        except tk.TclError:
            pass

    def setup_ui(self):
        """Sets up the PanedWindow and delegating panes."""
        self.root.overrideredirect(False)

        # 1. Main Paned Window
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 2. Left Pane (Hierarchy)
        self.left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=1)
        self.tree_pane = TreePane(self.left_frame, self.dispatcher)

        # 3. Right Pane (Editor)
        self.right_frame = ttk.Frame(self.paned_window, padding=10)
        self.paned_window.add(self.right_frame, weight=3)
        self.editor_pane = EditorPane(self.right_frame, self.dispatcher)

        # 4. Bottom Frame: Action Bar
        self.bottom_frame = ttk.Frame(self.root)
        self.bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        self.btn_sync = ttk.Button(self.bottom_frame, text="Sync to GitLab", command=self._on_sync_clicked)
        self.btn_sync.pack(side=tk.RIGHT)
        
        self.lbl_status = ttk.Label(self.bottom_frame, text="Ready.")
        self.lbl_status.pack(side=tk.LEFT)

    def _bind_events(self):
        """Binds overarching UI events."""
        pass

    def _on_sync_clicked(self):
        self.dispatcher.dispatch(UISyncRequestedEvent())
