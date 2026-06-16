import tkinter as tk
from tkinter import ttk
from typing import List
from src.core.app_context import AppContext
from src.core.events import EventDispatcher, TreeFilterRule, UITreeFilterAppliedEvent, AppThemeChangedEvent

class TreeFilterDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, context: AppContext, active_filter=None):
        super().__init__(parent)
        self.context = context
        self.dispatcher: EventDispatcher = context.resolve('event_dispatcher')
        self.workspace = context.resolve('workspace')
        
        self.title("Filter Hierarchy")
        self.geometry("600x400")
        self.minsize(500, 300)
        
        self.rules_rows = []
        self.active_filter = active_filter
        
        self._setup_ui()
        self._load_active_filter()
        self._bind_events()
        
        # Apply initial theme
        from src.utils.theme_manager import ThemeManager
        self.handle_theme_change(AppThemeChangedEvent(is_dark=ThemeManager.load_settings()))

    def _setup_ui(self):
        # Main container with padding
        self.main_frame = ttk.Frame(self, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Rules container with scrollbar
        self.scroll_container = ttk.Frame(self.main_frame)
        self.scroll_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.canvas = tk.Canvas(self.scroll_container, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.scroll_container, orient="vertical", command=self.canvas.yview)
        self.rules_inner_frame = ttk.Frame(self.canvas)

        self.rules_inner_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.rules_inner_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Hierarchy Modifiers
        modifiers_frame = ttk.LabelFrame(self.main_frame, text="Hierarchy Options", padding=5)
        modifiers_frame.pack(fill=tk.X, pady=(0, 10))

        self.var_show_ancestors = tk.BooleanVar(value=True)
        self.check_ancestors = ttk.Checkbutton(modifiers_frame, text="Show All Ancestors", variable=self.var_show_ancestors, state="disabled")
        self.check_ancestors.pack(side=tk.LEFT, padx=5)

        self.var_show_descendants = tk.BooleanVar(value=False)
        self.check_descendants = ttk.Checkbutton(modifiers_frame, text="Show All Descendants", variable=self.var_show_descendants)
        self.check_descendants.pack(side=tk.LEFT, padx=5)

        # Buttons
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Add Rule", command=self._add_rule_row).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear All", command=self._clear_all).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Apply Filter", command=self._on_apply_clicked, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _add_rule_row(self, conjunction="AND", field_type="Type", target_value="Story", case_sensitive=False):
        row_idx = len(self.rules_rows)
        row_frame = ttk.Frame(self.rules_inner_frame, padding=(0, 2))
        row_frame.pack(fill=tk.X)

        # Conjunction (hidden for first row)
        var_conjunction = tk.StringVar(value=conjunction)
        combo_conj = ttk.Combobox(row_frame, values=["AND", "OR"], textvariable=var_conjunction, state="readonly", width=5, style="Preferences.TCombobox")
        if row_idx > 0:
            combo_conj.grid(row=0, column=0, padx=(0, 5))
        else:
            # Placeholder for alignment
            ttk.Label(row_frame, width=7).grid(row=0, column=0)

        # Field Type
        var_field = tk.StringVar(value=field_type)
        combo_field = ttk.Combobox(row_frame, values=["Type", "Label", "Assignee", "Status", "Title", "Description"], textvariable=var_field, state="readonly", width=12, style="Preferences.TCombobox")
        combo_field.grid(row=0, column=1, padx=5)
        combo_field.bind("<<ComboboxSelected>>", lambda e, idx=row_idx: self._update_value_options(idx))

        # Target Value (Container for switching between combo and entry)
        value_container = ttk.Frame(row_frame)
        value_container.grid(row=0, column=2, padx=5)
        
        var_value = tk.StringVar(value=target_value)
        combo_value = ttk.Combobox(value_container, textvariable=var_value, state="readonly", width=20, style="Preferences.TCombobox")
        entry_value = tk.Entry(value_container, textvariable=var_value, width=22)
        
        # Case Sensitive Checkbox
        var_case = tk.BooleanVar(value=case_sensitive)
        check_case = ttk.Checkbutton(row_frame, text="Aa", variable=var_case, width=3)
        check_case.grid(row=0, column=3, padx=2)

        # Delete Button
        btn_del = ttk.Button(row_frame, text="X", width=3, command=lambda idx=row_idx: self._remove_rule_row(idx))
        btn_del.grid(row=0, column=4, padx=5)

        self.rules_rows.append({
            "frame": row_frame,
            "var_conjunction": var_conjunction,
            "var_field": var_field,
            "var_value": var_value,
            "combo_value": combo_value,
            "entry_value": entry_value,
            "var_case": var_case,
            "check_case": check_case
        })
        
        self._update_value_options(row_idx)
        # Scroll to bottom
        self.canvas.yview_moveto(1.0)

    def _update_value_options(self, row_idx):
        row = self.rules_rows[row_idx]
        field = row["var_field"].get()
        combo = row["combo_value"]
        entry = row["entry_value"]
        check = row["check_case"]
        
        # Determine widget visibility
        if field in ["Title", "Description"]:
            combo.grid_remove()
            entry.grid(row=0, column=0)
            check.grid() # Show case checkbox
            
            # Apply entry theme manually as it's not a ttk widget
            from src.utils.theme_manager import ThemeManager
            palette = ThemeManager.DARK_PALETTE if ThemeManager.load_settings() else ThemeManager.LIGHT_PALETTE
            cursor_color = 'white' if ThemeManager.load_settings() else 'black'
            entry.configure(
                bg=palette['field_bg'],
                fg=palette['fg'],
                insertbackground=cursor_color,
                highlightthickness=1,
                highlightbackground=palette['bg'],
                highlightcolor=palette['highlight'],
                borderwidth=0
            )
        else:
            entry.grid_remove()
            combo.grid(row=0, column=0)
            check.grid_remove() # Hide case checkbox
            
            values = []
            if field == "Type":
                values = ["Epic", "Feature", "Story"]
            elif field == "Status":
                values = ["Backlog", "In Progress", "In Review", "Done", "Closed"]
            elif field == "Assignee":
                values = ["Unassigned"] + [m.name for m in self.workspace.get_members()]
            elif field == "Label":
                values = sorted(list(self.workspace.labels.keys()))
                
            combo.config(values=values)
            if combo.get() not in values:
                combo.set(values[0] if values else "")

    def _remove_rule_row(self, row_idx):
        if 0 <= row_idx < len(self.rules_rows):
            row = self.rules_rows.pop(row_idx)
            row["frame"].destroy()

    def _clear_all(self):
        for row in self.rules_rows:
            row["frame"].destroy()
        self.rules_rows = []
        self._add_rule_row()

    def _load_active_filter(self):
        if self.active_filter:
            self.var_show_ancestors.set(self.active_filter.show_ancestors)
            self.var_show_descendants.set(self.active_filter.show_descendants)
            if self.active_filter.rules:
                for rule in self.active_filter.rules:
                    self._add_rule_row(rule.conjunction, rule.field_type, rule.target_value, rule.case_sensitive)
            else:
                self._add_rule_row()
        else:
            self._add_rule_row()

    def _on_apply_clicked(self):
        compiled_rules = []
        for row in self.rules_rows:
            compiled_rules.append(TreeFilterRule(
                conjunction=row["var_conjunction"].get(),
                field_type=row["var_field"].get(),
                target_value=row["var_value"].get(),
                case_sensitive=row["var_case"].get()
            ))
            
        self.dispatcher.dispatch(UITreeFilterAppliedEvent(
            rules=compiled_rules,
            show_ancestors=self.var_show_ancestors.get(),
            show_descendants=self.var_show_descendants.get()
        ))
        self.destroy()

    def _bind_events(self):
        self.dispatcher.subscribe(AppThemeChangedEvent, self.handle_theme_change)

    def handle_theme_change(self, event: AppThemeChangedEvent):
        from src.utils.theme_manager import ThemeManager
        palette = ThemeManager.DARK_PALETTE if event.is_dark else ThemeManager.LIGHT_PALETTE
        self.configure(bg=palette['bg'])
        self.canvas.configure(bg=palette['bg'])
