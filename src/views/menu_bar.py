import tkinter as tk
import os
from tkinter import ttk, filedialog, messagebox
from src.events import (
    EventDispatcher, UIExportCsvRequestedEvent, UIExportJsonRequestedEvent, 
    UIImportCsvRequestedEvent, UIImportJsonRequestedEvent, UIThemeToggleRequestedEvent, 
    AppThemeChangedEvent
)

class ApplicationMenuBar(tk.Menu):
    def __init__(self, parent: tk.Tk, dispatcher: EventDispatcher):
        """
        Initializes the ApplicationMenuBar.

        Args:
            parent (tk.Tk): The root Tkinter window.
            dispatcher (EventDispatcher): The event dispatcher for communication.
        """
        super().__init__(parent)
        self.root = parent
        self.dispatcher = dispatcher
        self._setup_menu()
        self._bind_events()

    def _setup_menu(self):
        """Sets up the main menu bar cascades."""
        # File menu
        file_menu = tk.Menu(self, tearoff=0)
        file_menu.add_command(label="Import...", command=self._on_import)
        file_menu.add_separator()
        file_menu.add_command(label="Export...", command=self._on_export)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        self.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(self, tearoff=0)
        edit_menu.add_command(label="Copy", command=lambda: None)
        edit_menu.add_command(label="Cut", command=lambda: None)
        edit_menu.add_command(label="Paste", command=lambda: None)
        self.add_cascade(label="Edit", menu=edit_menu)
        
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
        
        # Help menu
        help_menu = tk.Menu(self, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about_dialog)
        self.add_cascade(label="Help", menu=help_menu)

    def _bind_events(self):
        """Binds UI events and subscriptions."""
        self.dispatcher.subscribe(AppThemeChangedEvent, self.handle_theme_change)

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
