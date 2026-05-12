import tkinter as tk
from tkinter import ttk
from src.events import EventDispatcher, UIIntegrationsSaveRequestedEvent, AppThemeChangedEvent

class IntegrationsDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, dispatcher: EventDispatcher, current_settings: dict):
        """
        Initializes the IntegrationsDialog.

        Args:
            parent (tk.Tk): The root Tkinter window.
            dispatcher (EventDispatcher): The application's event dispatcher.
            current_settings (dict): The current integration settings to pre-fill.
        """
        super().__init__(parent)
        self.title("Integration Settings")
        self.geometry("600x500")
        self.dispatcher = dispatcher
        self.current_settings = current_settings
        self.is_dark = False # Will be updated via AppThemeChangedEvent

        self.transient(parent)
        self.grab_set()
        
        self._setup_ui()
        self._bind_events()
        self._load_current_settings()

    def _setup_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._setup_auth_tab()
        self._setup_product_tab()
        self._setup_capabilities_tab()

        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.btn_save = ttk.Button(button_frame, text="Save & Close", command=self._on_save_clicked)
        self.btn_save.pack(side=tk.RIGHT, padx=5)
        
        self.btn_cancel = ttk.Button(button_frame, text="Cancel", command=self.destroy)
        self.btn_cancel.pack(side=tk.RIGHT, padx=5)

    def _setup_auth_tab(self):
        self.auth_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.auth_tab, text="Authentication")

        ttk.Label(self.auth_tab, text="Host URL:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.entry_url = tk.Entry(self.auth_tab)
        self.entry_url.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Label(self.auth_tab, text="PAT (Personal Access Token):").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.entry_pat = tk.Entry(self.auth_tab, show="*")
        self.entry_pat.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Label(self.auth_tab, text="Root Epic Group ID:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.entry_group_id = tk.Entry(self.auth_tab)
        self.entry_group_id.pack(fill=tk.X, padx=10, pady=(0, 10))

    def _setup_product_tab(self):
        self.product_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.product_tab, text="Product Routing")

        # Treeview for product mappings
        self.tree_products = ttk.Treeview(self.product_tab, columns=("Name", "ProjectID"), show="headings", height=10)
        self.tree_products.heading("Name", text="Product Name")
        self.tree_products.heading("ProjectID", text="Target Project ID")
        self.tree_products.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Form to add/update
        form_frame = ttk.Frame(self.product_tab)
        form_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Label(form_frame, text="Name:").pack(side=tk.LEFT)
        self.entry_prod_name = tk.Entry(form_frame, width=15)
        self.entry_prod_name.pack(side=tk.LEFT, padx=5)

        ttk.Label(form_frame, text="Project ID:").pack(side=tk.LEFT)
        self.entry_prod_id = tk.Entry(form_frame, width=15)
        self.entry_prod_id.pack(side=tk.LEFT, padx=5)

        ttk.Button(form_frame, text="Add/Update", command=self._add_update_product).pack(side=tk.LEFT, padx=5)
        ttk.Button(form_frame, text="Remove", command=self._remove_product).pack(side=tk.LEFT, padx=5)

    def _setup_capabilities_tab(self):
        self.caps_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.caps_tab, text="Capabilities")

        self.list_caps = tk.Listbox(self.caps_tab, height=10)
        self.list_caps.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        form_frame = ttk.Frame(self.caps_tab)
        form_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.entry_cap_name = tk.Entry(form_frame)
        self.entry_cap_name.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        ttk.Button(form_frame, text="Add", command=self._add_capability).pack(side=tk.LEFT, padx=5)
        ttk.Button(form_frame, text="Remove", command=self._remove_capability).pack(side=tk.LEFT, padx=5)

    def _bind_events(self):
        self.dispatcher.subscribe(AppThemeChangedEvent, self.handle_theme_change)

    def handle_theme_change(self, event: AppThemeChangedEvent):
        self.is_dark = event.is_dark
        from src.utils.theme_manager import ThemeManager
        palette = ThemeManager.DARK_PALETTE if event.is_dark else ThemeManager.LIGHT_PALETTE
        cursor_color = 'white' if event.is_dark else 'black'

        # Style all tk.Entry widgets
        entries = [
            self.entry_url, self.entry_pat, self.entry_group_id,
            self.entry_prod_name, self.entry_prod_id, self.entry_cap_name
        ]
        for entry in entries:
            entry.configure(
                bg=palette['field_bg'],
                fg=palette['fg'],
                insertbackground=cursor_color,
                highlightthickness=1,
                highlightbackground=palette['bg'],
                highlightcolor=palette['highlight'],
                borderwidth=0
            )
        
        self.list_caps.configure(
            bg=palette['field_bg'],
            fg=palette['fg'],
            selectbackground=palette['highlight'],
            borderwidth=1,
            relief="flat"
        )
        
        # Note: ttk widgets like Notebook and Treeview are styled globally via ThemeManager.apply_ttk_theme

    def _load_current_settings(self):
        self.entry_url.insert(0, self.current_settings.get('auth_url', ''))
        self.entry_pat.insert(0, self.current_settings.get('auth_pat', ''))
        self.entry_group_id.insert(0, self.current_settings.get('epic_group_id', ''))

        mappings = self.current_settings.get('product_mappings', {})
        for name, pid in mappings.items():
            self.tree_products.insert("", tk.END, values=(name, pid))

        capabilities = self.current_settings.get('capabilities', [])
        for cap in capabilities:
            self.list_caps.insert(tk.END, cap)

    def _add_update_product(self):
        name = self.entry_prod_name.get().strip()
        pid = self.entry_prod_id.get().strip()
        if not name or not pid:
            return

        # Check if already exists
        for item in self.tree_products.get_children():
            if self.tree_products.item(item, "values")[0] == name:
                self.tree_products.item(item, values=(name, pid))
                return
        
        self.tree_products.insert("", tk.END, values=(name, pid))
        self.entry_prod_name.delete(0, tk.END)
        self.entry_prod_id.delete(0, tk.END)

    def _remove_product(self):
        selected = self.tree_products.selection()
        for item in selected:
            self.tree_products.delete(item)

    def _add_capability(self):
        cap = self.entry_cap_name.get().strip()
        if cap:
            self.list_caps.insert(tk.END, cap)
            self.entry_cap_name.delete(0, tk.END)

    def _remove_capability(self):
        selected = self.list_caps.curselection()
        if selected:
            self.list_caps.delete(selected)

    def _on_save_clicked(self):
        product_mappings = {}
        for item in self.tree_products.get_children():
            name, pid = self.tree_products.item(item, "values")
            product_mappings[name] = pid

        capabilities = list(self.list_caps.get(0, tk.END))

        self.dispatcher.dispatch(UIIntegrationsSaveRequestedEvent(
            auth_url=self.entry_url.get().strip(),
            auth_pat=self.entry_pat.get().strip(),
            epic_group_id=self.entry_group_id.get().strip(),
            product_mappings=product_mappings,
            capabilities=capabilities
        ))
        self.destroy()
