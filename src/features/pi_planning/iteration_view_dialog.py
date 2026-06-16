import tkinter as tk
from tkinter import ttk
from src.core.events import AppThemeChangedEvent

class ModifyIterationViewDialog(tk.Toplevel):
    def __init__(self, parent, workspace, callback):
        super().__init__(parent)
        self.workspace = workspace
        self.callback = callback
        self.title("Modify Iteration View")
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()

        # Local scratchpad models for listbox populations
        self.displayed_items = [i for i in self.workspace.iterations if i.id not in self.workspace.hidden_iteration_ids]
        self.hidden_items = [i for i in self.workspace.iterations if i.id in self.workspace.hidden_iteration_ids]

        self._setup_ui()
        self._populate_lists()
        
        # Apply initial theme
        from src.utils.theme_manager import ThemeManager
        self._apply_theme(ThemeManager.load_settings())

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left Column - Displayed
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(left_frame, text="Displayed Iterations").pack(anchor=tk.W)
        self.list_displayed = tk.Listbox(left_frame, exportselection=False)
        self.list_displayed.pack(fill=tk.BOTH, expand=True)
        self.list_displayed.bind("<Double-Button-1>", lambda e: self._move_to_hidden())

        # Middle Buttons Column
        mid_frame = ttk.Frame(main_frame, padding=10)
        mid_frame.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Button(mid_frame, text="->", width=4, command=self._move_to_hidden).pack(expand=True, anchor=tk.S, pady=5)
        ttk.Button(mid_frame, text="<-", width=4, command=self._move_to_displayed).pack(expand=True, anchor=tk.N, pady=5)

        # Right Column - Hidden
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(right_frame, text="Hidden Iterations").pack(anchor=tk.W)
        self.list_hidden = tk.Listbox(right_frame, exportselection=False)
        self.list_hidden.pack(fill=tk.BOTH, expand=True)
        self.list_hidden.bind("<Double-Button-1>", lambda e: self._move_to_displayed())

        # Bottom Actions Bar
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(btn_frame, text="Apply", style="Accent.TButton", command=self._on_apply).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _populate_lists(self):
        # Sort items by title for alphabetical order
        self.displayed_items.sort(key=lambda x: x.title)
        self.hidden_items.sort(key=lambda x: x.title)
        
        self.list_displayed.delete(0, tk.END)
        self.list_hidden.delete(0, tk.END)
        for item in self.displayed_items: self.list_displayed.insert(tk.END, item.title)
        for item in self.hidden_items: self.list_hidden.insert(tk.END, item.title)

    def _move_to_hidden(self):
        idx = self.list_displayed.curselection()
        if idx:
            item = self.displayed_items.pop(idx[0])
            self.hidden_items.append(item)
            self._populate_lists()

    def _move_to_displayed(self):
        idx = self.list_hidden.curselection()
        if idx:
            item = self.hidden_items.pop(idx[0])
            self.displayed_items.append(item)
            self._populate_lists()

    def _on_apply(self):
        # Update backing array structures only on Apply selection
        self.workspace.hidden_iteration_ids = [i.id for i in self.hidden_items]
        self.callback()
        self.destroy()

    def _apply_theme(self, is_dark):
        from src.utils.theme_manager import ThemeManager
        palette = ThemeManager.DARK_PALETTE if is_dark else ThemeManager.LIGHT_PALETTE
        self.configure(bg=palette['bg'])
        self.list_displayed.configure(bg=palette['field_bg'], fg=palette['fg'], selectbackground=palette['highlight'])
        self.list_hidden.configure(bg=palette['field_bg'], fg=palette['fg'], selectbackground=palette['highlight'])
