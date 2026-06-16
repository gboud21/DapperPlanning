import tkinter as tk
import os
from tkinter import ttk, filedialog, messagebox
from src.core.app_context import AppContext
from src.core.events import (
    EventDispatcher, UIExportCsvRequestedEvent, UIExportJsonRequestedEvent, 
    UIImportCsvRequestedEvent, UIImportJsonRequestedEvent, UIThemeToggleRequestedEvent, 
    AppThemeChangedEvent, UIIntegrationsDialogOpenRequestedEvent, UISettingsDialogOpenRequestedEvent,
    UIOpenWorkspaceRequestedEvent, UISaveWorkspaceRequestedEvent, UISaveAsWorkspaceRequestedEvent,
    UINewWorkspaceRequestedEvent, UISyncMembersRequestedEvent, UISyncLabelsRequestedEvent, 
    UISyncIterationsRequestedEvent, UIStorySplitRequestedEvent
)
from src.core.command_bus import CommandBus
from src.core.commands import SyncWithGitLabCommand, CloneItemCommand

class ApplicationMenuBar(tk.Menu):
    def __init__(self, parent: tk.Tk, context: AppContext):
        """
        Initializes the ApplicationMenuBar.

        Args:
            parent (tk.Tk): The root Tkinter window.
            context (AppContext): The application context for dependency injection.
        """
        super().__init__(parent)
        self.root = parent
        self.context = context
        self.dispatcher: EventDispatcher = context.resolve('event_dispatcher')
        self.command_bus: CommandBus = context.resolve('command_bus')
        self._setup_menu()
        self._bind_events()

    def _setup_menu(self):
        """Sets up the main menu bar cascades."""
        # File menu
        file_menu = tk.Menu(self, tearoff=0)
        file_menu.add_command(label="New Workspace", 
                             command=lambda: self.dispatcher.dispatch(UINewWorkspaceRequestedEvent()),
                             accelerator="Ctrl+N")
        file_menu.add_command(label="Open Workspace...", 
                             command=lambda: self.dispatcher.dispatch(UIOpenWorkspaceRequestedEvent()),
                             accelerator="Ctrl+O")
        file_menu.add_command(label="Save Workspace", 
                             command=lambda: self.dispatcher.dispatch(UISaveWorkspaceRequestedEvent()),
                             accelerator="Ctrl+S")
        file_menu.add_command(label="Save Workspace As...", command=lambda: self.dispatcher.dispatch(UISaveAsWorkspaceRequestedEvent()))
        file_menu.add_separator()
        file_menu.add_command(label="Import...", command=self._on_import)
        file_menu.add_separator()
        file_menu.add_command(label="Export...", command=self._on_export)
        file_menu.add_separator()
        file_menu.add_command(label="Preferences...", command=lambda: self.dispatcher.dispatch(UISettingsDialogOpenRequestedEvent()))
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        self.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        self.edit_menu = tk.Menu(self, tearoff=0)
        self.edit_menu.add_command(label="Clone", 
                                  command=lambda: self.command_bus.execute(CloneItemCommand(item_id=None)),
                                  state="disabled")
        self.edit_menu.add_command(label="Split", 
                                  command=self._on_split_clicked,
                                  state="disabled")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Copy", command=lambda: None)
        self.edit_menu.add_command(label="Cut", command=lambda: None)
        self.edit_menu.add_command(label="Paste", command=lambda: None)
        self.add_cascade(label="Edit", menu=self.edit_menu)

        # View menu
        self.view_menu = tk.Menu(self, tearoff=0)
        self.view_menu.add_command(label="Minimize", command=self._minimize_window)
        self.view_menu.add_command(label="Maximize", command=self._maximize_window)
        self.view_menu.add_command(label="Windowed Mode", command=self._restore_window)
        self.view_menu.add_separator()
        
        # Theme menu cascade
        self.theme_menu = tk.Menu(self.view_menu, tearoff=0)
        self.theme_menu.add_command(label="Light Mode", command=lambda: self.dispatcher.dispatch(UIThemeToggleRequestedEvent(is_dark=False)))
        self.theme_menu.add_command(label="Dark Mode", command=lambda: self.dispatcher.dispatch(UIThemeToggleRequestedEvent(is_dark=True)))
        self.view_menu.add_cascade(label="Theme", menu=self.theme_menu)
        
        self.add_cascade(label="View", menu=self.view_menu)

        # Integrations menu
        integrations_menu = tk.Menu(self, tearoff=0)
        integrations_menu.add_command(label="Pull from GitLab", 
                                     command=lambda: self.command_bus.execute(SyncWithGitLabCommand(sync_type='pull')),
                                     accelerator="Ctrl+Shift+L")
        integrations_menu.add_command(label="Push to GitLab", 
                                     command=lambda: self.command_bus.execute(SyncWithGitLabCommand(sync_type='push')),
                                     accelerator="Ctrl+Shift+P")
        integrations_menu.add_separator()
        integrations_menu.add_command(label="Integrations Settings...", command=lambda: self.dispatcher.dispatch(UIIntegrationsDialogOpenRequestedEvent()))
        integrations_menu.add_separator()
        integrations_menu.add_command(label="Sync GitLab Members", command=lambda: self.dispatcher.dispatch(UISyncMembersRequestedEvent()))
        integrations_menu.add_command(label="Sync GitLab Labels", command=lambda: self.dispatcher.dispatch(UISyncLabelsRequestedEvent()))
        integrations_menu.add_command(label="Sync GitLab Iterations", command=lambda: self.dispatcher.dispatch(UISyncIterationsRequestedEvent()))
        self.add_cascade(label="Integrations", menu=integrations_menu)

        
        # Help menu
        help_menu = tk.Menu(self, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about_dialog)
        self.add_cascade(label="Help", menu=help_menu)

    def set_clone_state(self, enabled: bool):
        """Toggles the 'Clone' menu item state."""
        state = "normal" if enabled else "disabled"
        self.edit_menu.entryconfig("Clone", state=state)

    def set_split_state(self, enabled: bool):
        """Toggles the 'Split' menu item state."""
        state = "normal" if enabled else "disabled"
        self.edit_menu.entryconfig("Split", state=state)

    def _on_split_clicked(self):
        """Dispatches the split request for the currently selected item."""
        # Note: tree_controller tracks the current_selected_id
        tree_controller = self.context.resolve('tree_controller')
        if tree_controller and tree_controller.current_selected_id:
            self.dispatcher.dispatch(UIStorySplitRequestedEvent(story_id=tree_controller.current_selected_id))

    def _bind_events(self):
        """Binds UI events and global keyboard shortcuts."""
        self.dispatcher.subscribe(AppThemeChangedEvent, self.handle_theme_change)
        
        # Global Keyboard Shortcuts - Normalized to lowercase for cross-platform stability
        self.root.bind_all('<Control-n>', self._on_new_shortcut)
        self.root.bind_all('<Command-n>', self._on_new_shortcut)  # macOS
        self.root.bind_all('<Control-o>', self._on_open_shortcut)
        self.root.bind_all('<Command-o>', self._on_open_shortcut)  # macOS
        self.root.bind_all('<Control-s>', self._on_save_shortcut)
        self.root.bind_all('<Command-s>', self._on_save_shortcut)  # macOS
        
        # Sync Shortcuts - Using explicit Shift modifier syntax
        self.root.bind_all('<Control-Shift-l>', self._on_pull_shortcut)
        self.root.bind_all('<Control-Shift-p>', self._on_push_shortcut)

    def _on_new_shortcut(self, event):
        """Handler for the New Workspace shortcut."""
        self.dispatcher.dispatch(UINewWorkspaceRequestedEvent())
        return "break"

    def _on_open_shortcut(self, event):
        """Handler for the Open Workspace shortcut."""
        self.dispatcher.dispatch(UIOpenWorkspaceRequestedEvent())
        return "break"

    def _on_save_shortcut(self, event):
        """Handler for the Save Workspace shortcut."""
        self.dispatcher.dispatch(UISaveWorkspaceRequestedEvent())
        return "break"

    def _on_pull_shortcut(self, event):
        """Handler for the Sync Pull shortcut."""
        self.command_bus.execute(SyncWithGitLabCommand(sync_type='pull'))
        return "break"

    def _on_push_shortcut(self, event):
        """Handler for the Sync Push shortcut."""
        self.command_bus.execute(SyncWithGitLabCommand(sync_type='push'))
        return "break"

    def handle_theme_change(self, event: AppThemeChangedEvent):
        """Reacts to application-wide theme changes to update menu item states."""
        if event.is_dark:
            self.theme_menu.entryconfig("Dark Mode", state="disabled")
            self.theme_menu.entryconfig("Light Mode", state="normal")
        else:
            self.theme_menu.entryconfig("Dark Mode", state="normal")
            self.theme_menu.entryconfig("Light Mode", state="disabled")

    def _on_import(self):
        """Opens a file dialog to select a file to import and dispatches events."""
        file_types = [
            ("CSV Files", "*.csv"),
            ("JSON Files", "*.json"),
            ("All Files", "*.*")
        ]
        
        selected_type = tk.StringVar()
        file_path = filedialog.askopenfilename(filetypes=file_types, typevariable=selected_type)
        if not file_path:
            return

        ext = os.path.splitext(file_path)[1].lower()
        selection = selected_type.get()
        
        format_to_use = None
        if selection == "CSV Files":
            format_to_use = "csv"
        elif selection == "JSON Files":
            format_to_use = "json"
        elif selection == "All Files" or not selection:
            if ext == ".csv":
                format_to_use = "csv"
            elif ext == ".json":
                format_to_use = "json"

        if not ext or ext not in [".csv", ".json"] or not format_to_use:
            messagebox.showerror("Import Error", f"Unsupported or missing file extension: '{ext if ext else 'None'}'.\nPlease select a .csv or .json file.")
            return self._on_import()

        if format_to_use == "csv":
            self.dispatcher.dispatch(UIImportCsvRequestedEvent(file_path=file_path))
        elif format_to_use == "json":
            self.dispatcher.dispatch(UIImportJsonRequestedEvent(file_path=file_path))

    def _on_export(self):
        """Opens a file dialog to select a save location and dispatches events."""
        file_types = [
            ("CSV Files", "*.csv"),
            ("JSON Files", "*.json"),
            ("All Files", "*.*")
        ]
        
        selected_type = tk.StringVar()
        file_path = filedialog.asksaveasfilename(filetypes=file_types, typevariable=selected_type)
        if not file_path:
            return

        ext = os.path.splitext(file_path)[1].lower()
        selection = selected_type.get()
        
        format_to_use = None
        if selection == "CSV Files":
            format_to_use = "csv"
        elif selection == "JSON Files":
            format_to_use = "json"
        elif selection == "All Files" or not selection:
            if ext == ".csv":
                format_to_use = "csv"
            elif ext == ".json":
                format_to_use = "json"

        if not ext or ext not in [".csv", ".json"] or not format_to_use:
            messagebox.showerror("Export Error", f"Unsupported or missing file extension: '{ext if ext else 'None'}'.\nPlease ensure the filename ends with .csv or .json.")
            return self._on_export()

        if format_to_use == "csv":
            self.dispatcher.dispatch(UIExportCsvRequestedEvent(file_path=file_path))
        elif format_to_use == "json":
            self.dispatcher.dispatch(UIExportJsonRequestedEvent(file_path=file_path))

    def _show_about_dialog(self):
        """Displays the about dialog."""
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
