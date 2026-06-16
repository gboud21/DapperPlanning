import tkinter as tk
from tkinter import ttk
from typing import List, Optional
from src.core.app_context import AppContext
from src.core.events import EventDispatcher, UITreeFilterAppliedEvent, AppThemeChangedEvent
from src.utils.query_parser import parse_query_to_ast, tokenize

class TreeFilterDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, context: AppContext, active_filter=None):
        super().__init__(parent)
        self.context = context
        self.dispatcher: EventDispatcher = context.resolve('event_dispatcher')
        self.workspace = context.resolve('workspace')
        
        self.title("Filter Hierarchy")
        self.geometry("600x450")
        self.minsize(500, 350)
        
        self.active_filter = active_filter
        self.autocomplete_popup = None
        
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

        ttk.Label(self.main_frame, text="Enter Query Console Expression:", font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W, pady=(0,5))
        
        # Query Console Input Box
        self.txt_query = tk.Text(self.main_frame, height=5, font=("Courier New", 11), wrap=tk.WORD, undo=True)
        self.txt_query.pack(fill=tk.BOTH, expand=True, pady=(0,2))
        self.txt_query.bind("<KeyRelease>", self._on_query_text_mutated)
        self.txt_query.bind("<Tab>", self._on_tab_pressed)
        self.txt_query.bind("<Return>", self._on_enter_pressed)
        self.txt_query.bind("<FocusOut>", lambda e: self._close_autocomplete())
        
        # Validation status message string label
        self.lbl_status = ttk.Label(self.main_frame, text="Status: Ready", foreground="green")
        self.lbl_status.pack(anchor=tk.W, pady=(0, 10))

        # Hierarchy Modifiers Box Frame
        modifiers_frame = ttk.LabelFrame(self.main_frame, text="Hierarchy Options", padding=5)
        modifiers_frame.pack(fill=tk.X, pady=(0, 10))

        self.var_show_ancestors = tk.BooleanVar(value=True)
        self.check_ancestors = ttk.Checkbutton(modifiers_frame, text="Show All Ancestors", variable=self.var_show_ancestors, state="disabled")
        self.check_ancestors.pack(side=tk.LEFT, padx=5)

        self.var_show_descendants = tk.BooleanVar(value=False)
        self.check_descendants = ttk.Checkbutton(modifiers_frame, text="Show All Descendants", variable=self.var_show_descendants)
        self.check_descendants.pack(side=tk.LEFT, padx=5)

        # Example label
        example_text = 'Example: type == "Story" AND status != "Done"'
        ttk.Label(self.main_frame, text=example_text, font=("TkDefaultFont", 8, "italic")).pack(anchor=tk.W, pady=(0, 10))

        # Command buttons action bar layout split row
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X)
        
        self.btn_apply = ttk.Button(button_frame, text="Apply Filter", command=self._on_apply_clicked, style="Accent.TButton")
        self.btn_apply.pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _on_query_text_mutated(self, event):
        if event.keysym in ("Tab", "Return", "Up", "Down", "Escape"):
             return

        query_text = self.txt_query.get("1.0", tk.END).strip()
        
        # 1. Real-time grammar verification check
        try:
            parse_query_to_ast(query_text)
            self.lbl_status.config(text="Status: Valid Expression Syntax Structure", foreground="green")
            self.btn_apply.config(state="normal")
        except ValueError as err:
            self.lbl_status.config(text=f"Syntax Error: {str(err)}", foreground="red")
            self.btn_apply.config(state="disabled")

        # 2. Autocomplete logic
        self._trigger_autocomplete()

    def _trigger_autocomplete(self):
        # Get word before cursor
        cursor_pos = self.txt_query.index(tk.INSERT)
        line, col = map(int, cursor_pos.split('.'))
        current_line = self.txt_query.get(f"{line}.0", cursor_pos)
        
        # Simple word extraction
        match = re.search(r'([a-zA-Z0-9_]+)$', current_line)
        if not match:
            self._close_autocomplete()
            return
            
        prefix = match.group(1)
        
        # Context-aware suggestions
        suggestions = []
        
        # keywords
        keywords = ["type", "status", "assignee", "label", "title", "description", 
                    "AND", "OR", "NOT", "contains", "not contains", "==" , "!="]
        
        # Values from workspace
        types = ["Epic", "Feature", "Story"]
        statuses = ["Backlog", "In Progress", "In Review", "Done", "Closed"]
        members = [m.name for m in self.workspace.get_members()]
        labels = list(self.workspace.labels.keys())
        
        all_options = keywords + types + statuses + members + labels
        suggestions = [opt for opt in all_options if opt.lower().startswith(prefix.lower())]
        
        if suggestions:
            self._show_autocomplete(suggestions, prefix)
        else:
            self._close_autocomplete()

    def _show_autocomplete(self, suggestions, prefix):
        if not self.autocomplete_popup:
            self.autocomplete_popup = tk.Toplevel(self)
            self.autocomplete_popup.overrideredirect(True)
            self.autocomplete_listbox = tk.Listbox(self.autocomplete_popup, font=("Courier New", 10))
            self.autocomplete_listbox.pack(fill=tk.BOTH, expand=True)
            self.autocomplete_listbox.bind("<ButtonRelease-1>", lambda e: self._apply_autocomplete())
            
        self.autocomplete_listbox.delete(0, tk.END)
        for s in suggestions:
            self.autocomplete_listbox.insert(tk.END, s)
            
        self.autocomplete_listbox.selection_set(0)
        
        # Position popup
        bbox = self.txt_query.bbox(tk.INSERT)
        if bbox:
            x = self.txt_query.winfo_rootx() + bbox[0]
            y = self.txt_query.winfo_rooty() + bbox[1] + bbox[3]
            self.autocomplete_popup.geometry(f"200x150+{x}+{y}")
            self.autocomplete_popup.deiconify()
            self.autocomplete_popup.lift()

    def _close_autocomplete(self):
        if self.autocomplete_popup:
            self.autocomplete_popup.withdraw()

    def _apply_autocomplete(self):
        if not self.autocomplete_popup or not self.autocomplete_listbox.curselection():
            return
            
        selected = self.autocomplete_listbox.get(self.autocomplete_listbox.curselection())
        
        # Replace prefix with selection
        cursor_pos = self.txt_query.index(tk.INSERT)
        line, col = map(int, cursor_pos.split('.'))
        current_line = self.txt_query.get(f"{line}.0", cursor_pos)
        match = re.search(r'([a-zA-Z0-9_]+)$', current_line)
        
        if match:
            start_col = match.start()
            self.txt_query.delete(f"{line}.{start_col}", cursor_pos)
            
            # Wrap in quotes if it's a value with spaces
            if " " in selected and selected not in ("not contains", "In Progress", "In Review"):
                 selected = f'"{selected}"'
                 
            self.txt_query.insert(f"{line}.{start_col}", selected)
            
        self._close_autocomplete()
        self._on_query_text_mutated(None)

    def _on_tab_pressed(self, event):
        if self.autocomplete_popup and self.autocomplete_popup.winfo_viewable():
            self._apply_autocomplete()
            return "break"

    def _on_enter_pressed(self, event):
        if self.autocomplete_popup and self.autocomplete_popup.winfo_viewable():
            self._apply_autocomplete()
            return "break"

    def _load_active_filter(self):
        if self.active_filter:
            self.var_show_ancestors.set(True) # Force True as requested
            self.var_show_descendants.set(self.active_filter.show_descendants)
            self.txt_query.insert("1.0", self.active_filter.query_string)
            self._on_query_text_mutated(None)

    def _on_apply_clicked(self):
        query_text = self.txt_query.get("1.0", tk.END).strip()
        self.dispatcher.dispatch(UITreeFilterAppliedEvent(
            query_string=query_text,
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
        
        cursor_color = 'white' if event.is_dark else 'black'
        self.txt_query.configure(
            bg=palette['field_bg'],
            fg=palette['fg'],
            insertbackground=cursor_color,
            highlightthickness=1,
            highlightbackground=palette['bg'],
            highlightcolor=palette['highlight'],
            borderwidth=0
        )
        
        if self.autocomplete_popup:
             self.autocomplete_listbox.configure(
                bg=palette['field_bg'],
                fg=palette['fg'],
                selectbackground=palette['highlight']
            )
            
import re
