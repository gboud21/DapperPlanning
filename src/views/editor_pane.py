import tkinter as tk
from tkinter import ttk
import re
from src.events import (
    EventDispatcher, UICreateItemRequestedEvent, UIItemSaveRequestedEvent, ModelActiveItemChangedEvent,
    AppThemeChangedEvent
)

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

        # Item Type Selection
        ttk.Label(self.scrollable_frame, text="Item Type:").pack(anchor=tk.W)
        self.combo_item_type = ttk.Combobox(self.scrollable_frame, state="readonly", 
                                            values=("Epic", "Feature", "Story"))
        self.combo_item_type.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))

        ttk.Label(self.scrollable_frame, text="Title:").pack(anchor=tk.W)
        self.entry_title = ttk.Entry(self.scrollable_frame, width=50)
        self.entry_title.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))

        # Weight Entry
        ttk.Label(self.scrollable_frame, text="Weight:").pack(anchor=tk.W)
        self.entry_weight = ttk.Entry(self.scrollable_frame, validate='key', validatecommand=self.vcmd)
        self.entry_weight.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))

        ttk.Label(self.scrollable_frame, text="Description:").pack(anchor=tk.W)
        self.text_desc = tk.Text(self.scrollable_frame, height=10, width=50)
        self.text_desc.pack(anchor=tk.W, fill=tk.BOTH, expand=True, pady=(0, 10))

        # Product Tags UI
        ttk.Label(self.scrollable_frame, text="Products:").pack(anchor=tk.W)
        self.list_products = tk.Listbox(self.scrollable_frame, height=3)
        self.list_products.pack(anchor=tk.W, fill=tk.X, pady=(0, 5))
        
        tag_frame_p = ttk.Frame(self.scrollable_frame)
        tag_frame_p.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))
        self.entry_product = ttk.Entry(tag_frame_p)
        self.entry_product.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(tag_frame_p, text="Add", command=self._add_product_tag).pack(side=tk.LEFT, padx=2)
        ttk.Button(tag_frame_p, text="Remove Selected", command=self._remove_product_tag).pack(side=tk.LEFT, padx=2)

        # Capability Tags UI
        ttk.Label(self.scrollable_frame, text="Capabilities:").pack(anchor=tk.W)
        self.list_capabilities = tk.Listbox(self.scrollable_frame, height=3)
        self.list_capabilities.pack(anchor=tk.W, fill=tk.X, pady=(0, 5))
        
        tag_frame_c = ttk.Frame(self.scrollable_frame)
        tag_frame_c.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))
        self.entry_capability = ttk.Entry(tag_frame_c)
        self.entry_capability.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(tag_frame_c, text="Add", command=self._add_capability_tag).pack(side=tk.LEFT, padx=2)
        ttk.Button(tag_frame_c, text="Remove Selected", command=self._remove_capability_tag).pack(side=tk.LEFT, padx=2)
        
        # Button Frame for CRUD actions
        self.button_frame = ttk.Frame(self.scrollable_frame)
        self.button_frame.pack(fill=tk.X, pady=10)

        self.btn_create = ttk.Button(self.button_frame, text="Create as New Child", command=self._on_save_clicked)
        self.btn_create.pack(side=tk.RIGHT, padx=5)

        self.btn_update = ttk.Button(self.button_frame, text="Update Current Item", command=self._on_update_clicked)
        self.btn_update.pack(side=tk.RIGHT, padx=5)

    def _add_product_tag(self):
        val = self.entry_product.get().strip()
        if val:
            self.list_products.insert(tk.END, val)
            self.entry_product.delete(0, tk.END)

    def _remove_product_tag(self):
        sel = self.list_products.curselection()
        if sel:
            self.list_products.delete(sel)

    def _add_capability_tag(self):
        val = self.entry_capability.get().strip()
        if val:
            self.list_capabilities.insert(tk.END, val)
            self.entry_capability.delete(0, tk.END)

    def _remove_capability_tag(self):
        sel = self.list_capabilities.curselection()
        if sel:
            self.list_capabilities.delete(sel)

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
        
        self.canvas.configure(bg=palette['bg'])
        self.text_desc.configure(
            bg=palette['field_bg'],
            fg=palette['fg'],
            insertbackground=palette['fg'],
            borderwidth=1,
            relief="flat"
        )
        for lb in [self.list_products, self.list_capabilities]:
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
        products = list(self.list_products.get(0, tk.END))
        capabilities = list(self.list_capabilities.get(0, tk.END))
        
        weight_str = self.entry_weight.get()
        weight = float(weight_str) if weight_str else 0.0
        
        self.dispatcher.dispatch(UIItemSaveRequestedEvent(
            item_id=self.current_selected_id,
            new_title=title,
            new_description=desc,
            new_products=products,
            new_capabilities=capabilities,
            weight=weight
        ))

    def _on_save_clicked(self):
        """Dispatches the create request using the current selection as parent."""
        item_type = self.combo_item_type.get()
        title = self.entry_title.get()
        desc = self.text_desc.get("1.0", tk.END).strip()
        products = list(self.list_products.get(0, tk.END))
        capabilities = list(self.list_capabilities.get(0, tk.END))

        weight_str = self.entry_weight.get()
        weight = float(weight_str) if weight_str else 0.0
        
        self.dispatcher.dispatch(UICreateItemRequestedEvent(
            parent_id=self.current_selected_id,
            item_type=item_type,
            title=title,
            description=desc,
            products=products,
            capabilities=capabilities,
            weight=weight
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
        
        if item_type in ['Epic', 'Feature']:
            self.entry_weight.config(state='disabled')
        else:
            self.entry_weight.config(state='normal')

        self.text_desc.delete("1.0", tk.END)
        self.text_desc.insert("1.0", getattr(event.item_data, 'description', ''))

        self.list_products.delete(0, tk.END)
        products = getattr(event.item_data, 'products', [])
        for p in products:
            self.list_products.insert(tk.END, p)

        self.list_capabilities.delete(0, tk.END)
        capabilities = getattr(event.item_data, 'capabilities', [])
        for c in capabilities:
            self.list_capabilities.insert(tk.END, c)
        
        # Reset scroll position to top when switching items
        self.canvas.yview_moveto(0)
