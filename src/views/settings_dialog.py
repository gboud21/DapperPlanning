import tkinter as tk
from tkinter import ttk
from src.events import (
    EventDispatcher, UISettingsSaveRequestedEvent, AppThemeChangedEvent, 
    UITemplateConfigExportRequestedEvent
)
from src.utils.template_generator import TemplateGenerator

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
        self.geometry("600x650") # Increased height for new controls
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
        self.combo_theme = ttk.Combobox(self.general_tab, values=["Light", "Dark"], state="readonly", style="Preferences.TCombobox")
        self.combo_theme.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Auto-Save
        self.var_auto_save = tk.BooleanVar()
        self.check_auto_save = ttk.Checkbutton(self.general_tab, text="Enable Auto-Save", variable=self.var_auto_save)
        self.check_auto_save.pack(anchor=tk.W, padx=10, pady=10)

        # Log Level
        ttk.Label(self.general_tab, text="Logging Level:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.combo_log_level = ttk.Combobox(self.general_tab, values=["DEBUG", "INFO", "WARNING", "ERROR"], state="readonly", style="Preferences.TCombobox")
        self.combo_log_level.pack(fill=tk.X, padx=10, pady=(0, 10))

    def _setup_templates_tab(self):
        self.templates_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.templates_tab, text="Editor Templates")

        # Template Parameters LabelFrame
        params_frame = ttk.LabelFrame(self.templates_tab, text="Template Parameters")
        params_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Grid layout for parameters
        params_frame.columnconfigure(1, weight=1)
        params_frame.columnconfigure(3, weight=1)

        # 1. Target Tool
        ttk.Label(params_frame, text="Target Tool:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.combo_tool = ttk.Combobox(params_frame, values=["GitLab", "Jira"], state="readonly", style="Preferences.TCombobox")
        self.combo_tool.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        self.combo_tool.bind("<<ComboboxSelected>>", lambda e: self._refresh_template_preview())

        # 2. Methodology
        ttk.Label(params_frame, text="Methodology:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.combo_methodology = ttk.Combobox(params_frame, values=["Scrum", "Kanban", "SAFe"], state="readonly", style="Preferences.TCombobox")
        self.combo_methodology.grid(row=0, column=3, sticky=tk.EW, padx=5, pady=2)
        self.combo_methodology.bind("<<ComboboxSelected>>", lambda e: self._refresh_template_preview())

        # 3. Hierarchy
        ttk.Label(params_frame, text="Hierarchy:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.combo_hierarchy = ttk.Combobox(params_frame, values=["Epic -> Feature -> Story", "Epic -> Story"], state="readonly", style="Preferences.TCombobox")
        self.combo_hierarchy.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        self.combo_hierarchy.bind("<<ComboboxSelected>>", lambda e: self._refresh_template_preview())

        # 4. Description Type
        ttk.Label(params_frame, text="Description Type:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.combo_type = ttk.Combobox(params_frame, values=["Heavyweight", "Lightweight"], state="readonly", style="Preferences.TCombobox")
        self.combo_type.grid(row=1, column=3, sticky=tk.EW, padx=5, pady=2)
        self.combo_type.bind("<<ComboboxSelected>>", lambda e: self._refresh_template_preview())

        # 5. Include Out of Scope
        self.var_out_of_scope = tk.BooleanVar()
        self.check_out_of_scope = ttk.Checkbutton(params_frame, text="Include Out of Scope", variable=self.var_out_of_scope, command=self._refresh_template_preview)
        self.check_out_of_scope.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)

        # 6. Include Compliance & Security
        self.var_compliance = tk.BooleanVar()
        self.check_compliance = ttk.Checkbutton(params_frame, text="Include Compliance & Security", variable=self.var_compliance, command=self._refresh_template_preview)
        self.check_compliance.grid(row=2, column=2, columnspan=2, sticky=tk.W, padx=5, pady=2)

        # Existing Template Controls (Below Parameters)
        
        # Item Type Selection
        ttk.Label(self.templates_tab, text="Item Type:").pack(anchor=tk.W, padx=10, pady=(5, 0))
        self.combo_item_type = ttk.Combobox(self.templates_tab, values=["Epic", "Feature", "Story"], state="readonly", style="Preferences.TCombobox")
        self.combo_item_type.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.combo_item_type.bind("<<ComboboxSelected>>", self._on_item_type_changed)

        # Template Name Selection
        ttk.Label(self.templates_tab, text="Template Name:").pack(anchor=tk.W, padx=10, pady=(5, 0))
        self.combo_template_name = ttk.Combobox(self.templates_tab, state="readonly", style="Preferences.TCombobox")
        self.combo_template_name.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.combo_template_name.bind("<<ComboboxSelected>>", self._on_template_name_changed)

        # Template Editor
        ttk.Label(self.templates_tab, text="Content:").pack(anchor=tk.W, padx=10, pady=(5, 0))
        self.text_template = tk.Text(self.templates_tab, height=8) # Reduced height slightly to fit
        self.text_template.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Actions
        btn_frame = ttk.Frame(self.templates_tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        ttk.Button(btn_frame, text="Save as New", command=self._save_new_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Update", command=self._update_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Revert to Default", command=self._revert_template).pack(side=tk.LEFT, padx=2)

        # Export Button
        export_frame = ttk.Frame(self.templates_tab)
        export_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(export_frame, text="Export Configuration", command=self._on_export_config_clicked).pack(fill=tk.X)

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
        
        # Load Template Parameters
        self.combo_tool.set(self.current_settings.get('target_tool', 'GitLab'))
        self.combo_methodology.set(self.current_settings.get('methodology', 'Scrum'))
        self.combo_hierarchy.set(self.current_settings.get('hierarchy', 'Epic -> Feature -> Story'))
        self.combo_type.set(self.current_settings.get('description_type', 'Heavyweight'))
        self.var_out_of_scope.set(self.current_settings.get('include_out_of_scope', False))
        self.var_compliance.set(self.current_settings.get('include_compliance', False))
        
        self.combo_item_type.set("Epic")
        self._on_item_type_changed(None)

    def _refresh_template_preview(self):
        """Generates a preview based on current parameters and updates the text area."""
        content = TemplateGenerator.generate(
            item_type=self.combo_item_type.get(),
            tool=self.combo_tool.get(),
            desc_type=self.combo_type.get(),
            out_of_scope=self.var_out_of_scope.get(),
            compliance=self.var_compliance.get()
        )
        self.text_template.delete("1.0", tk.END)
        self.text_template.insert("1.0", content)

    def _on_item_type_changed(self, event):
        item_type = self.combo_item_type.get()
        names = list(self.templates.get(item_type, {}).keys())
        self.combo_template_name.config(values=names)
        if names:
            self.combo_template_name.set(names[0])
            self._on_template_name_changed(None)
        else:
            self._refresh_template_preview()

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
        self._refresh_template_preview()

    def _on_export_config_clicked(self):
        payload = {
            "tool": self.combo_tool.get(),
            "methodology": self.combo_methodology.get(),
            "hierarchy": self.combo_hierarchy.get(),
            "out_of_scope_checked": self.var_out_of_scope.get(),
            "compliance_checked": self.var_compliance.get(),
            "type": self.combo_type.get(),
            "template_text": self.text_template.get("1.0", tk.END).strip()
        }
        self.dispatcher.dispatch(UITemplateConfigExportRequestedEvent(payload=payload))

    def _on_save_clicked(self):
        self.dispatcher.dispatch(UISettingsSaveRequestedEvent(
            theme=self.combo_theme.get().lower(),
            auto_save=self.var_auto_save.get(),
            log_level=self.combo_log_level.get(),
            templates=self.templates,
            target_tool=self.combo_tool.get(),
            methodology=self.combo_methodology.get(),
            hierarchy=self.combo_hierarchy.get(),
            description_type=self.combo_type.get(),
            include_out_of_scope=self.var_out_of_scope.get(),
            include_compliance=self.var_compliance.get()
        ))
        self.destroy()
