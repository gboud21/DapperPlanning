import tkinter as tk
from tkinter import ttk
from src.events import (
    EventDispatcher, UICreateItemRequestedEvent, ModelActiveItemChangedEvent
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
        
        self._setup_ui()
        self._bind_events()

    def _setup_ui(self):
        """Sets up the labels, entries, and save button with a scrollbar."""
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

        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Content widgets
        self.lbl_editor_title = ttk.Label(self.scrollable_frame, text="Select an item to edit", font=("Arial", 14, "bold"))
        self.lbl_editor_title.pack(anchor=tk.W, pady=(0, 10))

        # Item Type Selection
        ttk.Label(self.scrollable_frame, text="Item Type:").pack(anchor=tk.W)
        self.combo_item_type = ttk.Combobox(self.scrollable_frame, state="readonly", 
                                            values=("Product", "Capability", "Epic", "Feature", "Story"))
        self.combo_item_type.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))

        ttk.Label(self.scrollable_frame, text="Title:").pack(anchor=tk.W)
        self.entry_title = ttk.Entry(self.scrollable_frame, width=50)
        self.entry_title.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))

        ttk.Label(self.scrollable_frame, text="Description:").pack(anchor=tk.W)
        self.text_desc = tk.Text(self.scrollable_frame, height=10, width=50)
        self.text_desc.pack(anchor=tk.W, fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.btn_save_item = ttk.Button(self.scrollable_frame, text="Save Item Data", command=self._on_save_clicked)
        self.btn_save_item.pack(anchor=tk.E)

    def _on_canvas_configure(self, event):
        """Adjusts the scrollable frame width to match the canvas width."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _bind_events(self):
        """Subscribes to model updates."""
        self.dispatcher.subscribe(ModelActiveItemChangedEvent, self.populate_editor)

    def _on_save_clicked(self):
        """Dispatches the create request using the current selection as parent."""
        item_type = self.combo_item_type.get()
        title = self.entry_title.get()
        desc = self.text_desc.get("1.0", tk.END).strip()
        
        self.dispatcher.dispatch(UICreateItemRequestedEvent(
            parent_id=self.current_selected_id,
            item_type=item_type,
            title=title,
            description=desc,
            products=[], # UI for this to be added later
            capabilities=[] # UI for this to be added later
        ))

    def populate_editor(self, event: ModelActiveItemChangedEvent):
        """Populates the fields when a model item becomes active."""
        self.current_selected_id = getattr(event.item_data, 'id', None)
        item_type = getattr(event, 'item_type', 'Item')
        self.lbl_editor_title.config(text=f"Editing {item_type}")
        
        self.entry_title.delete(0, tk.END)
        self.entry_title.insert(0, getattr(event.item_data, 'title', ''))
        
        self.text_desc.delete("1.0", tk.END)
        self.text_desc.insert("1.0", getattr(event.item_data, 'description', ''))
        
        # Reset scroll position to top when switching items
        self.canvas.yview_moveto(0)
