import tkinter as tk
from tkinter import ttk
from src.events import EventDispatcher, UISettingsSaveRequestedEvent, AppThemeChangedEvent

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, dispatcher: EventDispatcher, current_settings: dict):
        """
        Initializes the SettingsDialog.

        Args:
            parent (tk.Tk): The root Tkinter window.
            dispatcher (EventDispatcher): The application's event dispatcher.
            current_settings (dict): The current general settings and templates.
        """
        super().__init__(parent)
        self.title("General Settings")
        self.geometry("600x500")
        self.dispatcher = dispatcher
        self.current_settings = current_settings
        
        # Internal state for templates
        self.templates = {k: v.copy() for k, v in current_settings.get('templates', {}).items()}

        self.transient(parent)
        self.grab_set()
        
        self._setup_ui()
        self._bind_events()
        self._load_current_settings()

    def _setup_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._setup_general_tab()
        self._setup_templates_tab()

        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.btn_save = ttk.Button(button_frame, text="Save & Close", command=self._on_save_clicked)
        self.btn_save.pack(side=tk.RIGHT, padx=5)
        
        self.btn_cancel = ttk.Button(button_frame, text="Cancel", command=self.destroy)
        self.btn_cancel.pack(side=tk.RIGHT, padx=5)

    def _setup_general_tab(self):
        self.general_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.general_tab, text="General")

        # Theme
        ttk.Label(self.general_tab, text="Theme:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.combo_theme = ttk.Combobox(self.general_tab, values=["Light", "Dark"], state="readonly")
        self.combo_theme.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Auto-Save
        self.var_auto_save = tk.BooleanVar()
        self.check_auto_save = ttk.Checkbutton(self.general_tab, text="Enable Auto-Save", variable=self.var_auto_save)
        self.check_auto_save.pack(anchor=tk.W, padx=10, pady=10)

        # Log Level
        ttk.Label(self.general_tab, text="Logging Level:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.combo_log_level = ttk.Combobox(self.general_tab, values=["DEBUG", "INFO", "WARNING", "ERROR"], state="readonly")
        self.combo_log_level.pack(fill=tk.X, padx=10, pady=(0, 10))

    def _setup_templates_tab(self):
        self.templates_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.templates_tab, text="Editor Templates")

        # Item Type Selection
        ttk.Label(self.templates_tab, text="Item Type:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.combo_item_type = ttk.Combobox(self.templates_tab, values=["Epic", "Feature", "Story"], state="readonly")
        self.combo_item_type.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.combo_item_type.bind("<<ComboboxSelected>>", self._on_item_type_changed)

        # Template Name Selection
        ttk.Label(self.templates_tab, text="Template Name:").pack(anchor=tk.W, padx=10, pady=(5, 0))
        self.combo_template_name = ttk.Combobox(self.templates_tab, state="readonly")
        self.combo_template_name.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.combo_template_name.bind("<<ComboboxSelected>>", self._on_template_name_changed)

        # Template Editor
        ttk.Label(self.templates_tab, text="Content:").pack(anchor=tk.W, padx=10, pady=(5, 0))
        self.text_template = tk.Text(self.templates_tab, height=10)
        self.text_template.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Actions
        btn_frame = ttk.Frame(self.templates_tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(btn_frame, text="Save as New", command=self._save_new_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Update", command=self._update_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Revert to Default", command=self._revert_template).pack(side=tk.LEFT, padx=2)

    def _bind_events(self):
        self.dispatcher.subscribe(AppThemeChangedEvent, self.handle_theme_change)

    def handle_theme_change(self, event: AppThemeChangedEvent):
        from src.utils.theme_manager import ThemeManager
        palette = ThemeManager.DARK_PALETTE if event.is_dark else ThemeManager.LIGHT_PALETTE
        cursor_color = 'white' if event.is_dark else 'black'
        
        self.text_template.configure(
            bg=palette['field_bg'],
            fg=palette['fg'],
            insertbackground=cursor_color,
            borderwidth=1,
            relief="flat"
        )

    def _load_current_settings(self):
        self.combo_theme.set(self.current_settings.get('theme', 'Dark').capitalize())
        self.var_auto_save.set(self.current_settings.get('auto_save', False))
        self.combo_log_level.set(self.current_settings.get('log_level', 'INFO'))
        
        self.combo_item_type.set("Epic")
        self._on_item_type_changed(None)

    def _on_item_type_changed(self, event):
        item_type = self.combo_item_type.get()
        names = list(self.templates.get(item_type, {}).keys())
        self.combo_template_name.config(values=names)
        if names:
            self.combo_template_name.set(names[0])
            self._on_template_name_changed(None)

    def _on_template_name_changed(self, event):
        item_type = self.combo_item_type.get()
        name = self.combo_template_name.get()
        content = self.templates.get(item_type, {}).get(name, "")
        self.text_template.delete("1.0", tk.END)
        self.text_template.insert("1.0", content)

    def _save_new_template(self):
        item_type = self.combo_item_type.get()
        content = self.text_template.get("1.0", tk.END).strip()
        
        # Simple popup for name
        name_dialog = tk.Toplevel(self)
        name_dialog.title("New Template Name")
        ttk.Label(name_dialog, text="Enter Name:").pack(padx=10, pady=5)
        entry_name = tk.Entry(name_dialog)
        entry_name.pack(padx=10, pady=5)
        
        def confirm():
            name = entry_name.get().strip()
            if name:
                if item_type not in self.templates: self.templates[item_type] = {}
                self.templates[item_type][name] = content
                self._on_item_type_changed(None)
                self.combo_template_name.set(name)
                name_dialog.destroy()

        ttk.Button(name_dialog, text="OK", command=confirm).pack(pady=10)

    def _update_template(self):
        item_type = self.combo_item_type.get()
        name = self.combo_template_name.get()
        content = self.text_template.get("1.0", tk.END).strip()
        if item_type and name:
            self.templates[item_type][name] = content

    def _revert_template(self):
        # Implementation could fetch original defaults if stored, 
        # here we just clear it or revert to an empty string for simplicity in scaffold
        self.text_template.delete("1.0", tk.END)

    def _on_save_clicked(self):
        self.dispatcher.dispatch(UISettingsSaveRequestedEvent(
            theme=self.combo_theme.get().lower(),
            auto_save=self.var_auto_save.get(),
            log_level=self.combo_log_level.get(),
            templates=self.templates
        ))
        self.destroy()
