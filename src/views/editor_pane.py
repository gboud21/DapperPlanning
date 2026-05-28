import tkinter as tk
from tkinter import ttk
import re
from src.events import (
    EventDispatcher, UICreateItemRequestedEvent, UIItemSaveRequestedEvent, ModelActiveItemChangedEvent,
    AppThemeChangedEvent, UIGlobalTagAddRequestedEvent
)
from src.utils.template_generator import TemplateGenerator
from src.utils.theme_manager import ThemeManager

class EditorPane:
    def __init__(self, parent_frame: ttk.Frame, dispatcher: EventDispatcher):
        """
        Initializes the EditorPane for viewing and editing item details.

        Args:
            parent_frame (ttk.Frame): The frame where the editor widgets will be placed.
            dispatcher (EventDispatcher): The application's event dispatcher.
        """
        self.parent = parent_frame
        self.dispatcher = dispatcher
        self.current_selected_id = None
        
        # Register validation command
        self.vcmd = (self.parent.register(self._validate_weight), '%P')
        
        self._setup_ui()
        self._bind_events()
        self._load_config()

    def _validate_weight(self, new_value: str) -> bool:
        """Validates that the input is a number with at most one decimal place."""
        if new_value == "":
            return True
        return bool(re.match(r'^\d*\.?\d{0,1}$', new_value))

    def _setup_ui(self):
        """Sets up the labels, entries, and action buttons with a scrollbar."""
        # Create a canvas and scrollbar
        self.canvas = tk.Canvas(self.parent, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.parent, orient="vertical", command=self.canvas.yview)
        
        # Create a frame to hold the content
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure canvas
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Bind canvas resize to frame width
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Pack scrollbar first, then canvas
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Content widgets
        self.lbl_editor_title = ttk.Label(self.scrollable_frame, text="Select an item to edit", font=("Arial", 14, "bold"))
        self.lbl_editor_title.pack(anchor=tk.W, pady=(0, 10))

        # --- Template Parameters Section ---
        params_frame = ttk.LabelFrame(self.scrollable_frame, text="Template Parameters")
        params_frame.pack(fill=tk.X, pady=(0, 10))
        
        params_frame.columnconfigure(1, weight=1)
        params_frame.columnconfigure(3, weight=1)

        ttk.Label(params_frame, text="Tool:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.combo_tool = ttk.Combobox(params_frame, values=["GitLab", "Jira"], state="readonly")
        self.combo_tool.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        self.combo_tool.bind("<<ComboboxSelected>>", lambda e: self._refresh_description_template())

        ttk.Label(params_frame, text="Methodology:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.combo_methodology = ttk.Combobox(params_frame, values=["Scrum", "Kanban", "SAFe"], state="readonly")
        self.combo_methodology.grid(row=0, column=3, sticky=tk.EW, padx=5, pady=2)
        self.combo_methodology.bind("<<ComboboxSelected>>", lambda e: self._refresh_description_template())

        ttk.Label(params_frame, text="Type:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.combo_type = ttk.Combobox(params_frame, values=["Heavyweight", "Lightweight"], state="readonly")
        self.combo_type.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        self.combo_type.bind("<<ComboboxSelected>>", lambda e: self._refresh_description_template())

        self.var_out_of_scope = tk.BooleanVar()
        self.check_out_of_scope = ttk.Checkbutton(params_frame, text="Include Out of Scope", variable=self.var_out_of_scope, command=self._refresh_description_template)
        self.check_out_of_scope.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)

        self.var_compliance = tk.BooleanVar()
        self.check_compliance = ttk.Checkbutton(params_frame, text="Include Compliance & Security", variable=self.var_compliance, command=self._refresh_description_template)
        self.check_compliance.grid(row=2, column=2, columnspan=2, sticky=tk.W, padx=5, pady=2)
        # -----------------------------------

        # Item Type Selection
        ttk.Label(self.scrollable_frame, text="Item Type:").pack(anchor=tk.W)
        self.combo_item_type = ttk.Combobox(self.scrollable_frame, state="readonly", 
                                            values=("Epic", "Feature", "Story"))
        self.combo_item_type.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))
        self.combo_item_type.bind("<<ComboboxSelected>>", lambda e: self._refresh_description_template())

        ttk.Label(self.scrollable_frame, text="Title:").pack(anchor=tk.W)
        self.entry_title = tk.Entry(self.scrollable_frame, width=50)
        self.entry_title.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))

        # Weight Entry
        ttk.Label(self.scrollable_frame, text="Weight:").pack(anchor=tk.W)
        self.entry_weight = tk.Entry(self.scrollable_frame, validate='key', validatecommand=self.vcmd)
        self.entry_weight.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))

        # Status Combobox
        ttk.Label(self.scrollable_frame, text="Status:").pack(anchor=tk.W)
        self.combo_status = ttk.Combobox(self.scrollable_frame, values=('Backlog', 'In Progress', 'In Review', 'Done'), state="readonly")
        self.combo_status.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))

        ttk.Label(self.scrollable_frame, text="Description:").pack(anchor=tk.W)
        self.text_desc = tk.Text(self.scrollable_frame, height=10, width=50)
        self.text_desc.pack(anchor=tk.W, fill=tk.BOTH, expand=True, pady=(0, 10))

        # Dual-Listbox Tag Management
        self.product_ui = self._create_dual_listbox(self.scrollable_frame, "Products", "product")
        self.capability_ui = self._create_dual_listbox(self.scrollable_frame, "Capabilities", "capability")
        
        # Button Frame for CRUD actions
        self.button_frame = ttk.Frame(self.scrollable_frame)
        self.button_frame.pack(fill=tk.X, pady=10)

        self.btn_create = ttk.Button(self.button_frame, text="Create as New Child", command=self._on_save_clicked)
        self.btn_create.pack(side=tk.RIGHT, padx=5)

        self.btn_update = ttk.Button(self.button_frame, text="Update Current Item", command=self._on_update_clicked)
        self.btn_update.pack(side=tk.RIGHT, padx=5)

        # Enable mouse wheel scrolling recursively
        self._bind_mousewheel(self.canvas)

    def _create_dual_listbox(self, parent_frame, title, tag_type):
        """Helper to create a dual-listbox tag management component."""
        frame = ttk.LabelFrame(parent_frame, text=title)
        frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(2, weight=1)
        
        # Left side: Master Pool
        left_container = ttk.Frame(frame)
        left_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        ttk.Label(left_container, text="Available").pack(anchor=tk.W)
        list_master = tk.Listbox(left_container, height=6, exportselection=False)
        list_master.pack(fill=tk.BOTH, expand=True)
        
        # New Tag Entry
        entry_new = tk.Entry(left_container)
        entry_new.pack(fill=tk.X, pady=(2, 0))
        btn_add_master = ttk.Button(left_container, text="Add to Master List", 
                                    command=lambda: self._add_to_master(list_master, entry_new, tag_type))
        btn_add_master.pack(fill=tk.X)
        
        # Middle: Transfer Buttons
        mid_container = ttk.Frame(frame)
        mid_container.grid(row=0, column=1, padx=5)
        
        btn_assign = ttk.Button(mid_container, text=">>", width=5,
                                command=lambda: self._transfer_items(list_master, list_assigned))
        btn_assign.pack(pady=5)
        
        btn_remove = ttk.Button(mid_container, text="<<", width=5,
                                command=lambda: self._transfer_items(list_assigned, list_master))
        btn_remove.pack(pady=5)
        
        # Right side: Assigned Tags
        right_container = ttk.Frame(frame)
        right_container.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        
        ttk.Label(right_container, text="Assigned").pack(anchor=tk.W)
        list_assigned = tk.Listbox(right_container, height=6, exportselection=False)
        list_assigned.pack(fill=tk.BOTH, expand=True)

        return {
            "master": list_master,
            "assigned": list_assigned,
            "entry": entry_new,
            "frame": frame
        }

    def _transfer_items(self, source, target):
        """Moves selected items from source listbox to target listbox."""
        selected_indices = source.curselection()
        if not selected_indices:
            return
            
        items_to_move = [source.get(i) for i in selected_indices]
        
        # Remove from source
        for i in reversed(selected_indices):
            source.delete(i)
            
        # Add to target and sort
        all_target_items = list(target.get(0, tk.END)) + items_to_move
        all_target_items.sort()
        
        target.delete(0, tk.END)
        for item in all_target_items:
            target.insert(tk.END, item)

    def _add_to_master(self, list_master, entry_new, tag_type):
        """Adds a new tag to the local master listbox and dispatches global event."""
        val = entry_new.get().strip()
        if not val:
            return
            
        all_master = list(list_master.get(0, tk.END))
        if val not in all_master:
            all_master.append(val)
            all_master.sort()
            
            list_master.delete(0, tk.END)
            for item in all_master:
                list_master.insert(tk.END, item)
                
            self.dispatcher.dispatch(UIGlobalTagAddRequestedEvent(tag_type=tag_type, tag_value=val))
            
        entry_new.delete(0, tk.END)

    def _on_mousewheel(self, event):
        """Handles mouse wheel scrolling for the canvas."""
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        elif event.delta: # Windows/macOS
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _bind_mousewheel(self, widget):
        """Recursively binds mouse wheel events to a widget and its children."""
        # Widgets that handle their own vertical scrolling should be excluded
        if isinstance(widget, (tk.Text, tk.Listbox, ttk.Scrollbar)):
            return

        widget.bind("<Button-4>", self._on_mousewheel, add="+")
        widget.bind("<Button-5>", self._on_mousewheel, add="+")
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        
        for child in widget.winfo_children():
            self._bind_mousewheel(child)

    def _load_config(self):
        """Loads user configuration for template defaults."""
        config = ThemeManager.get_general_settings()
        self.combo_tool.set(config.get('target_tool', 'GitLab'))
        self.combo_methodology.set(config.get('methodology', 'Scrum'))
        self.combo_type.set(config.get('description_type', 'Heavyweight'))
        self.var_out_of_scope.set(config.get('include_out_of_scope', False))
        self.var_compliance.set(config.get('include_compliance', False))

    def _refresh_description_template(self):
        """Generates and updates the description text based on current parameters."""
        content = TemplateGenerator.generate(
            item_type=self.combo_item_type.get(),
            tool=self.combo_tool.get(),
            desc_type=self.combo_type.get(),
            out_of_scope=self.var_out_of_scope.get(),
            compliance=self.var_compliance.get()
        )
        self.text_desc.delete("1.0", tk.END)
        self.text_desc.insert("1.0", content)

    def _on_canvas_configure(self, event):
        """Adjusts the scrollable frame width to match the canvas width."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        self.canvas.update_idletasks()
        self.parent.after(20, self._force_redraw)

    def _force_redraw(self):
        """Explicitly triggers updates on the scrollable container and its children."""
        self.scrollable_frame.update()
        self.btn_update.update()
        self.btn_create.update()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _bind_events(self):
        """Subscribes to model updates."""
        self.dispatcher.subscribe(ModelActiveItemChangedEvent, self.populate_editor)
        self.dispatcher.subscribe(AppThemeChangedEvent, self.handle_theme_change)

    def handle_theme_change(self, event: AppThemeChangedEvent):
        """Reacts to application-wide theme changes."""
        from src.utils.theme_manager import ThemeManager
        palette = ThemeManager.DARK_PALETTE if event.is_dark else ThemeManager.LIGHT_PALETTE
        cursor_color = 'white' if event.is_dark else 'black'
        
        self.canvas.configure(bg=palette['bg'])
        self.text_desc.configure(
            bg=palette['field_bg'],
            fg=palette['fg'],
            insertbackground=cursor_color,
            borderwidth=1,
            relief="flat"
        )
        
        for entry in [self.entry_title, self.entry_weight, self.product_ui['entry'], self.capability_ui['entry']]:
            entry.configure(
                bg=palette['field_bg'],
                fg=palette['fg'],
                insertbackground=cursor_color,
                highlightthickness=1,
                highlightbackground=palette['bg'],
                highlightcolor=palette['highlight'],
                borderwidth=0
            )

        for lb in [self.product_ui['master'], self.product_ui['assigned'], 
                   self.capability_ui['master'], self.capability_ui['assigned']]:
            lb.configure(
                bg=palette['field_bg'],
                fg=palette['fg'],
                selectbackground=palette['highlight'],
                borderwidth=1,
                relief="flat"
            )

    def _on_update_clicked(self):
        """Dispatches the update request for the currently selected item."""
        if not self.current_selected_id:
            return
            
        title = self.entry_title.get()
        desc = self.text_desc.get("1.0", tk.END).strip()
        products = list(self.product_ui['assigned'].get(0, tk.END))
        capabilities = list(self.capability_ui['assigned'].get(0, tk.END))
        
        weight_str = self.entry_weight.get()
        weight = float(weight_str) if weight_str else 0.0
        
        status = self.combo_status.get() or 'Backlog'
        
        self.dispatcher.dispatch(UIItemSaveRequestedEvent(
            item_id=self.current_selected_id,
            new_title=title,
            new_description=desc,
            new_products=products,
            new_capabilities=capabilities,
            weight=weight,
            status=status
        ))

    def _on_save_clicked(self):
        """Dispatches the create request using the current selection as parent."""
        item_type = self.combo_item_type.get()
        title = self.entry_title.get()
        desc = self.text_desc.get("1.0", tk.END).strip()
        products = list(self.product_ui['assigned'].get(0, tk.END))
        capabilities = list(self.capability_ui['assigned'].get(0, tk.END))

        weight_str = self.entry_weight.get()
        weight = float(weight_str) if weight_str else 0.0
        
        status = self.combo_status.get() or 'Backlog'
        
        self.dispatcher.dispatch(UICreateItemRequestedEvent(
            parent_id=self.current_selected_id,
            item_type=item_type,
            title=title,
            description=desc,
            products=products,
            capabilities=capabilities,
            weight=weight,
            status=status
        ))

    def populate_editor(self, event: ModelActiveItemChangedEvent):
        """Populates the fields when a model item becomes active."""
        self.current_selected_id = getattr(event.item_data, 'id', None)
        item_type = getattr(event, 'item_type', 'Item')
        self.lbl_editor_title.config(text=f"Editing {item_type}")
        
        self.combo_item_type.set(item_type)
        
        self.entry_title.delete(0, tk.END)
        self.entry_title.insert(0, getattr(event.item_data, 'title', ''))
        
        # Populate weight and set state
        self.entry_weight.config(state='normal')
        self.entry_weight.delete(0, tk.END)
        weight = getattr(event.item_data, 'weight', 0.0)
        self.entry_weight.insert(0, f"{weight:.1f}")
        
        # Populate status and set state
        self.combo_status.set(getattr(event.item_data, 'status', 'Backlog'))
        
        if item_type in ['Epic', 'Feature']:
            self.entry_weight.config(state='disabled')
            self.combo_status.config(state='disabled')
        else:
            self.entry_weight.config(state='normal')
            self.combo_status.config(state='readonly')

        self.text_desc.delete("1.0", tk.END)
        self.text_desc.insert("1.0", getattr(event.item_data, 'description', ''))

        # Fetch Global Settings for Tags
        settings = ThemeManager.get_integration_settings()
        master_products = sorted(settings.get('product_mappings', {}).keys())
        master_capabilities = sorted(settings.get('capabilities', []))
        
        assigned_products = getattr(event.item_data, 'products', [])
        assigned_capabilities = getattr(event.item_data, 'capabilities', [])

        self._populate_dual_listbox(self.product_ui, master_products, assigned_products)
        self._populate_dual_listbox(self.capability_ui, master_capabilities, assigned_capabilities)
        
        # Reset scroll position to top when switching items
        self.canvas.yview_moveto(0)

    def _populate_dual_listbox(self, ui_dict, master_list, assigned_list):
        """Populates the master and assigned listboxes based on diff logic."""
        ui_dict['master'].delete(0, tk.END)
        ui_dict['assigned'].delete(0, tk.END)
        
        assigned_set = set(assigned_list)
        
        for item in sorted(assigned_list):
            ui_dict['assigned'].insert(tk.END, item)
            
        for item in sorted(master_list):
            if item not in assigned_set:
                ui_dict['master'].insert(tk.END, item)

