import tkinter as tk
import os
from tkinter import ttk, filedialog, messagebox as msgbox, messagebox
from src.events import (
    EventDispatcher, UISyncRequestedEvent, UIExportCsvRequestedEvent,
    UIExportJsonRequestedEvent, UIImportCsvRequestedEvent, UIImportJsonRequestedEvent,
    UIErrorNotificationEvent, UIThemeToggleRequestedEvent, AppThemeChangedEvent
)
from src.utils.theme_manager import ThemeManager
from .tree_pane import TreePane
from .editor_pane import EditorPane
from .menu_bar import ApplicationMenuBar

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
        
        self.setup_ui()
        self._bind_events()

    def setup_ui(self):
        """Sets up the PanedWindow and delegating panes."""
        self.root.overrideredirect(False)
        
        # Instantiate and attach the menu bar
        self.app_menu = ApplicationMenuBar(self.root, self.dispatcher)
        self.root.config(menu=self.app_menu)

        # 1. Bottom Frame: Action Bar (Pack first to prevent being cut off)
        self.bottom_frame = ttk.Frame(self.root)
        self.bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        self.btn_sync = ttk.Button(self.bottom_frame, text="Sync to GitLab", command=self._on_sync_clicked)
        self.btn_sync.pack(side=tk.RIGHT)
        
        self.lbl_status = ttk.Label(self.bottom_frame, text="Ready.")
        self.lbl_status.pack(side=tk.LEFT)

        # 2. Main Paned Window
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 3. Left Pane (Hierarchy)
        self.left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=1)
        self.tree_pane = TreePane(self.left_frame, self.dispatcher)

        # 4. Right Pane (Editor)
        self.right_frame = ttk.Frame(self.paned_window, padding=10)
        self.paned_window.add(self.right_frame, weight=3)
        self.editor_pane = EditorPane(self.right_frame, self.dispatcher)

    def _bind_events(self):
        """Binds overarching UI events."""
        self.dispatcher.subscribe(UIErrorNotificationEvent, self._show_error)
        self.dispatcher.subscribe(AppThemeChangedEvent, self.handle_theme_change)

    def handle_theme_change(self, event: AppThemeChangedEvent):
        """Reacts to application-wide theme changes."""
        ThemeManager.apply_ttk_theme(event.is_dark)
        
        palette = ThemeManager.DARK_PALETTE if event.is_dark else ThemeManager.LIGHT_PALETTE
        self.root.configure(bg=palette['bg'])

    def _show_error(self, event: UIErrorNotificationEvent):
        """Displays an error dialog."""
        msgbox.showerror(title=event.title, message=event.message)

    def _on_sync_clicked(self):
        self.dispatcher.dispatch(UISyncRequestedEvent())
