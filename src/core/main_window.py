import tkinter as tk
import os
from tkinter import ttk, filedialog, messagebox as msgbox, messagebox
from src.core.app_context import AppContext
from src.core.events import (
    EventDispatcher, UISyncRequestedEvent, UIExportCsvRequestedEvent,
    UIExportJsonRequestedEvent, UIImportCsvRequestedEvent, UIImportJsonRequestedEvent,
    UIErrorNotificationEvent, UIThemeToggleRequestedEvent, AppThemeChangedEvent,
    ModelWorkspaceLoadedEvent, UIWindowStateChangedEvent, UIAppCloseRequestedEvent
)
from src.utils.theme_manager import ThemeManager
from src.features.agile_planning.tree_pane import TreePane
from src.features.agile_planning.editor_pane import EditorPane
from src.core.menu_bar import ApplicationMenuBar

class MainWindow:
    def __init__(self, root: tk.Tk, context: AppContext):
        """
        Initialize the MainWindow.

        Args:
            root (tk.Tk): The root Tkinter window.
            context (AppContext): The application context for dependency injection.
        """
        self.root = root
        self.context = context
        self.dispatcher: EventDispatcher = context.resolve('event_dispatcher')
        self.workspace = context.resolve('workspace')
        self._last_maximized_state = False
        
        self.setup_ui()
        self._bind_events()

    def setup_ui(self):
        """Sets up the PanedWindow and delegating panes."""
        self.root.overrideredirect(False)
        self.root.title("DapperPlanning")
        
        # Instantiate and attach the menu bar
        self.app_menu = ApplicationMenuBar(self.root, self.context)
        self.root.config(menu=self.app_menu)
        self.context.register('app_menu', self.app_menu)

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
        self.tree_pane = TreePane(self.left_frame, self.context)
        self.context.register('tree_pane', self.tree_pane)

        # 4. Right Pane (Editor)
        self.right_frame = ttk.Frame(self.paned_window, padding=10)
        self.paned_window.add(self.right_frame, weight=3)
        self.editor_pane = EditorPane(self.right_frame, self.context)
        self.context.register('editor_pane', self.editor_pane)

    def _bind_events(self):
        """Binds overarching UI events."""
        self.dispatcher.subscribe(UIErrorNotificationEvent, self._show_error)
        self.dispatcher.subscribe(AppThemeChangedEvent, self.handle_theme_change)
        self.dispatcher.subscribe(ModelWorkspaceLoadedEvent, self._handle_workspace_loaded)
        
        # Intercept window close
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.dispatcher.dispatch(UIAppCloseRequestedEvent()))

        # Bind to property changes to detect maximization
        self.root.bind("<Configure>", self._on_configure)

    def _on_configure(self, event):
        """Detects if the window was maximized or restored."""
        # Check if the event is for the root window itself
        if event.widget == self.root:
            is_maximized = self._is_maximized()
            if is_maximized != self._last_maximized_state:
                self._last_maximized_state = is_maximized
                self.dispatcher.dispatch(UIWindowStateChangedEvent(is_maximized=is_maximized))

    def _is_maximized(self) -> bool:
        """Helper to determine if the window is currently maximized."""
        try:
            # Check zoomed state (Windows/macOS)
            if self.root.state() == 'zoomed':
                return True
            # Check zoomed attribute (Linux/X11)
            if self.root.attributes('-zoomed'):
                return True
        except tk.TclError:
            pass
        return False

    def handle_theme_change(self, event: AppThemeChangedEvent):
        """Reacts to application-wide theme changes."""
        ThemeManager.apply_ttk_theme(event.is_dark)
        
        palette = ThemeManager.DARK_PALETTE if event.is_dark else ThemeManager.LIGHT_PALETTE
        self.root.configure(bg=palette['bg'])

    def _handle_workspace_loaded(self, event: ModelWorkspaceLoadedEvent):
        """Updates the window title when a workspace is loaded."""
        if event.filepath:
            self.root.title(f"DapperPlanning - {event.filepath}")
        else:
            self.root.title("DapperPlanning - Untitled")

    def _show_error(self, event: UIErrorNotificationEvent):
        """Displays an error dialog."""
        msgbox.showerror(title=event.title, message=event.message)

    def _on_sync_clicked(self):
        from src.core.commands import SyncWithGitLabCommand
        command_bus = self.context.resolve('command_bus')
        command_bus.execute(SyncWithGitLabCommand(sync_type='pull'))
