import tkinter as tk
from tkinter import ttk
from src.core.events import EventDispatcher, UIIntegrationsSaveRequestedEvent, AppThemeChangedEvent

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
        self._pending_product_updates = {} # Maps product_name -> project_id (int or None)
        self._pending_group_updates = {} # Maps product_name -> group_id (int or None)
        
        # Register integer validation
        self.vcmd_int = (self.register(self._validate_integer), '%P')

        self.transient(parent)
        self.grab_set()
        
        self._setup_ui()
        self._bind_events()
        self._load_current_settings()

    def _validate_integer(self, P_value: str) -> bool:
        """Returns True if P_value is empty or is a digit."""
        if P_value == "":
            return True
        return P_value.isdigit()

    def _setup_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._setup_auth_tab()
        self._setup_product_tab()
        self._setup_capabilities_tab()
        self._setup_sync_labels_tab()

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
        self.entry_url.pack(fill=tk.X, padx=10, pady=(0, 2))
        ttk.Label(self.auth_tab, text="Example: https://gitlab.com", font=("TkDefaultFont", 8, "italic")).pack(anchor=tk.W, padx=10, pady=(0, 10))

        ttk.Label(self.auth_tab, text="PAT (Personal Access Token):").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.entry_pat = tk.Entry(self.auth_tab, show="*")
        self.entry_pat.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Label(self.auth_tab, text="Root Epic Group ID:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.entry_group_id = tk.Entry(self.auth_tab)
        self.entry_group_id.pack(fill=tk.X, padx=10, pady=(0, 10))

    def _setup_product_tab(self):
        self.product_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.product_tab, text="Product Routing")

        # 1. Active Product Selection
        active_frame = ttk.LabelFrame(self.product_tab, text="Sync Context", padding=10)
        active_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        
        ttk.Label(active_frame, text="Active Product for Sync:").pack(side=tk.LEFT, padx=(0, 10))
        self.combo_active_prod = ttk.Combobox(active_frame, state="readonly")
        self.combo_active_prod.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 2. Treeview for product mappings
        self.tree_products = ttk.Treeview(self.product_tab, columns=("Name", "ProjectID", "GroupID"), show="headings", height=8)
        self.tree_products.heading("Name", text="Product Name")
        self.tree_products.heading("ProjectID", text="GitLab Project ID")
        self.tree_products.heading("GroupID", text="GitLab Group ID")
        self.tree_products.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.tree_products.bind("<<TreeviewSelect>>", self._on_product_selected)

        # 3. Form to add/update
        form_frame = ttk.Frame(self.product_tab)
        form_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Label(form_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.entry_prod_name = tk.Entry(form_frame, width=15)
        self.entry_prod_name.grid(row=0, column=1, padx=2)

        ttk.Label(form_frame, text="Project ID:").grid(row=0, column=2, sticky=tk.W, padx=2)
        self.entry_prod_id = tk.Entry(form_frame, width=10, validate='key', validatecommand=self.vcmd_int)
        self.entry_prod_id.grid(row=0, column=3, padx=2)
        self.entry_prod_id.bind("<KeyRelease>", self._on_prod_id_keyup)

        ttk.Label(form_frame, text="Group ID:").grid(row=0, column=4, sticky=tk.W, padx=2)
        self.entry_prod_group_id = tk.Entry(form_frame, width=10, validate='key', validatecommand=self.vcmd_int)
        self.entry_prod_group_id.grid(row=0, column=5, padx=2)
        self.entry_prod_group_id.bind("<KeyRelease>", self._on_prod_group_id_keyup)

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=0, column=6, padx=5)
        ttk.Button(btn_frame, text="Add/Update", command=self._add_update_product).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove", command=self._remove_product).pack(side=tk.LEFT, padx=2)

    def _refresh_active_product_options(self):
        """Updates the Combobox with current product names."""
        product_names = sorted(list(self._pending_product_updates.keys()))
        self.combo_active_prod['values'] = product_names
        
        # Preserve selection if still valid
        current = self.combo_active_prod.get()
        if current not in product_names:
            if product_names:
                # Default to first one if nothing selected or previous selection gone
                self.combo_active_prod.set(product_names[0])
            else:
                self.combo_active_prod.set("")

    def _on_product_selected(self, event):
        selected = self.tree_products.selection()
        if not selected:
            return
        
        name, pid, gid = self.tree_products.item(selected[0], "values")
        self.entry_prod_name.delete(0, tk.END)
        self.entry_prod_name.insert(0, name)
        
        self.entry_prod_id.delete(0, tk.END)
        # Check pending first, then current display
        val_pid = self._pending_product_updates.get(name, pid)
        if val_pid is not None and val_pid != "":
            self.entry_prod_id.insert(0, str(val_pid))

        self.entry_prod_group_id.delete(0, tk.END)
        val_gid = self._pending_group_updates.get(name, gid)
        if val_gid is not None and val_gid != "":
            self.entry_prod_group_id.insert(0, str(val_gid))

    def _on_prod_id_keyup(self, event):
        name = self.entry_prod_name.get().strip()
        if not name:
            return
        
        val = self.entry_prod_id.get().strip()
        self._pending_product_updates[name] = int(val) if val else None
        self._refresh_active_product_options()

    def _on_prod_group_id_keyup(self, event):
        name = self.entry_prod_name.get().strip()
        if not name:
            return
        
        val = self.entry_prod_group_id.get().strip()
        self._pending_group_updates[name] = int(val) if val else None
        self._refresh_active_product_options()

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

    def _setup_sync_labels_tab(self):
        self.sync_labels_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.sync_labels_tab, text="Sync Labels")

        ttk.Label(self.sync_labels_tab, text="Epic Sync Label Name:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.entry_epic_sync_label = tk.Entry(self.sync_labels_tab)
        self.entry_epic_sync_label.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Label(self.sync_labels_tab, text="Feature Sync Label Name:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.entry_feature_sync_label = tk.Entry(self.sync_labels_tab)
        self.entry_feature_sync_label.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Create a LabelFrame for Legacy Status Configuration
        legacy_frame = ttk.LabelFrame(self.sync_labels_tab, text="Legacy Status Label Mappings", padding=10)
        legacy_frame.pack(fill=tk.X, padx=10, pady=10)

        self.var_legacy_status = tk.BooleanVar()
        self.check_legacy_status = ttk.Checkbutton(
            legacy_frame, text="Enable Legacy Status Indication (Label-based)", 
            variable=self.var_legacy_status, command=self._toggle_legacy_status_widgets
        )
        self.check_legacy_status.pack(anchor=tk.W, pady=(0, 10))

        # Status Fields Layout Grid
        grid_frame = ttk.Frame(legacy_frame)
        grid_frame.pack(fill=tk.X)

        self.legacy_entries = {}
        statuses = ["Backlog", "In Progress", "In Review", "Done", "Closed"]
        for idx, status in enumerate(statuses):
            ttk.Label(grid_frame, text=f"{status} Label:").grid(row=idx, column=0, sticky=tk.W, pady=2, padx=5)
            entry = tk.Entry(grid_frame)
            entry.grid(row=idx, column=1, sticky=tk.EW, pady=2, padx=5)
            self.legacy_entries[status] = entry

        grid_frame.columnconfigure(1, weight=1)

    def _toggle_legacy_status_widgets(self):
        target_state = "normal" if self.var_legacy_status.get() else "disabled"
        for entry in self.legacy_entries.values():
            entry.config(state=target_state)

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
            self.entry_prod_name, self.entry_prod_id, self.entry_prod_group_id, self.entry_cap_name,
            self.entry_epic_sync_label, self.entry_feature_sync_label
        ] + list(self.legacy_entries.values())
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
        
        # Style Combobox for high contrast in settings
        self.combo_active_prod.configure(style='Preferences.TCombobox')

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
        self.entry_epic_sync_label.insert(0, self.current_settings.get('epic_sync_label', 'Epic'))
        self.entry_feature_sync_label.insert(0, self.current_settings.get('feature_sync_label', 'Feature'))

        # Load Legacy Status Settings
        self.var_legacy_status.set(self.current_settings.get('legacy_status_enabled', False))
        mappings = self.current_settings.get('status_label_mappings', {})
        for status, entry in self.legacy_entries.items():
            entry.insert(0, mappings.get(status, status))
        self._toggle_legacy_status_widgets()

        mappings = self.current_settings.get('product_mappings', {})
        project_ids = self.current_settings.get('product_project_ids', {})
        group_ids = self.current_settings.get('product_group_ids', {})
        for name, _ in mappings.items():
            proj_id = project_ids.get(name, "")
            grp_id = group_ids.get(name, "")
            self.tree_products.insert("", tk.END, values=(name, proj_id, grp_id))
            # Sync pending map for initial load
            self._pending_product_updates[name] = project_ids.get(name)
            self._pending_group_updates[name] = group_ids.get(name)

        capabilities = self.current_settings.get('capabilities', [])
        for cap in capabilities:
            self.list_caps.insert(tk.END, cap)
            
        self._refresh_active_product_options()
        
        # Set current active product from settings or workspace
        active_prod = self.current_settings.get('active_product_name')
        if active_prod:
            self.combo_active_prod.set(active_prod)

    def _add_update_product(self):
        name = self.entry_prod_name.get().strip()
        pid = self.entry_prod_id.get().strip()
        gid = self.entry_prod_group_id.get().strip()
        if not name:
            return

        # pid/gid can be empty (None)
        proj_id = int(pid) if pid else None
        grp_id = int(gid) if gid else None

        # Check if already exists
        found = False
        for item in self.tree_products.get_children():
            if self.tree_products.item(item, "values")[0] == name:
                self.tree_products.item(item, values=(name, pid if pid else "", gid if gid else ""))
                self._pending_product_updates[name] = proj_id
                self._pending_group_updates[name] = grp_id
                found = True
                break
        
        if not found:
            self.tree_products.insert("", tk.END, values=(name, pid if pid else "", gid if gid else ""))
            self._pending_product_updates[name] = proj_id
            self._pending_group_updates[name] = grp_id
            
        self._refresh_active_product_options()
        self.entry_prod_name.delete(0, tk.END)
        self.entry_prod_id.delete(0, tk.END)
        self.entry_prod_group_id.delete(0, tk.END)

    def _remove_product(self):
        selected = self.tree_products.selection()
        for item in selected:
            name = self.tree_products.item(item, "values")[0]
            if name in self._pending_product_updates:
                del self._pending_product_updates[name]
            if name in self._pending_group_updates:
                del self._pending_group_updates[name]
            self.tree_products.delete(item)
        self._refresh_active_product_options()

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
        product_mappings = {} # We keep this for backward compat or other routing
        for item in self.tree_products.get_children():
            name, pid, gid = self.tree_products.item(item, "values")
            product_mappings[name] = name # routing to self name for now

        capabilities = list(self.list_caps.get(0, tk.END))
        
        status_label_mappings = {status: entry.get().strip() for status, entry in self.legacy_entries.items()}

        self.dispatcher.dispatch(UIIntegrationsSaveRequestedEvent(
            auth_url=self.entry_url.get().strip(),
            auth_pat=self.entry_pat.get().strip(),
            epic_group_id=self.entry_group_id.get().strip(),
            product_mappings=product_mappings,
            capabilities=capabilities,
            product_project_ids=self._pending_product_updates,
            product_group_ids=self._pending_group_updates,
            active_product_name=self.combo_active_prod.get(),
            epic_sync_label=self.entry_epic_sync_label.get().strip() or "Epic",
            feature_sync_label=self.entry_feature_sync_label.get().strip() or "Feature",
            legacy_status_enabled=self.var_legacy_status.get(),
            status_label_mappings=status_label_mappings
        ))
        self.destroy()
