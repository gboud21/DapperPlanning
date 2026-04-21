import tkinter as tk
from tkinter import ttk
from src.events import (
    EventDispatcher, UIItemSelectedEvent, UIItemSaveRequestedEvent, UISyncRequestedEvent,
    ModelHierarchyUpdatedEvent, ModelActiveItemChangedEvent
)

class MainWindow:
    def __init__(self, root: tk.Tk, dispatcher: EventDispatcher):
        """
        Initialize the MainWindow.

        Args:
            root (tk.Tk): The root Tkinter window.
            dispatcher (EventDispatcher): The event dispatcher for UI and model communication.
        """
        self.root = root
        self.dispatcher = dispatcher
        
        self.setup_ui()
        self._bind_events()

    def setup_ui(self):
        """
        Set up the user interface components including the treeview, 
        editor pane, and action buttons.
        """
        # 1. Main Paned Window
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 2. Left Frame: Treeview
        self.left_frame = ttk.Frame(self.paned_window, width=300)
        self.tree = ttk.Treeview(self.left_frame)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.paned_window.add(self.left_frame, weight=1)

        # 3. Right Frame: Editor
        self.right_frame = ttk.Frame(self.paned_window, width=700)
        self.paned_window.add(self.right_frame, weight=3)
        
        self.lbl_editor_title = ttk.Label(self.right_frame, text="Select an item to edit", font=("Arial", 14, "bold"))
        self.lbl_editor_title.pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(self.right_frame, text="Title:").pack(anchor=tk.W)
        self.entry_title = ttk.Entry(self.right_frame, width=50)
        self.entry_title.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))

        ttk.Label(self.right_frame, text="Description:").pack(anchor=tk.W)
        self.text_desc = tk.Text(self.right_frame, height=10, width=50)
        self.text_desc.pack(anchor=tk.W, fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.btn_save_item = ttk.Button(self.right_frame, text="Save Item Data")
        self.btn_save_item.pack(anchor=tk.E)

        # 4. Bottom Frame: Action Bar
        self.bottom_frame = ttk.Frame(self.root)
        self.bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        self.btn_sync = ttk.Button(self.bottom_frame, text="Sync to GitLab")
        self.btn_sync.pack(side=tk.RIGHT)
        
        self.lbl_status = ttk.Label(self.bottom_frame, text="Ready.")
        self.lbl_status.pack(side=tk.LEFT)

    def _bind_events(self):
        """
        Bind UI components to event handlers and subscribe to model events.
        """
        # 1. UI triggers (Tkinter to Dispatcher)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.btn_save_item.config(command=self._on_save_clicked)
        self.btn_sync.config(command=self._on_sync_clicked)

        # 2. Model subscriptions (Dispatcher to Tkinter)
        self.dispatcher.subscribe(ModelHierarchyUpdatedEvent, self.render_tree)
        self.dispatcher.subscribe(ModelActiveItemChangedEvent, self.populate_editor)

    # --- UI Action Handlers ---
    def _on_tree_select(self, event):
        """
        Handle the treeview item selection event.
        
        Args:
            event: The Tkinter event object triggered on tree selection.
        """
        selected_id = self.tree.focus()
        if selected_id:
            self.dispatcher.dispatch(UIItemSelectedEvent(item_id=selected_id))

    def _on_save_clicked(self):
        """
        Handle the save button click event to dispatch the updated 
        item details to the model.
        """
        selected_id = self.tree.focus()
        if selected_id:
            title = self.entry_title.get()
            desc = self.text_desc.get("1.0", tk.END).strip()
            self.dispatcher.dispatch(UIItemSaveRequestedEvent(selected_id, title, desc))

    def _on_sync_clicked(self):
        """
        Handle the sync button click event to trigger a synchronization process.
        """
        self.dispatcher.dispatch(UISyncRequestedEvent())

    # --- View Updaters ---
    def render_tree(self, event: ModelHierarchyUpdatedEvent):
        """
        Render the tree view based on updates to the model hierarchy.
        
        Args:
            event (ModelHierarchyUpdatedEvent): The event containing hierarchy update details.
        """
        # Future implementation: clear and rebuild the Tkinter Treeview based on Workspace state
        pass

    def populate_editor(self, event: ModelActiveItemChangedEvent):
        """
        Populate the editor pane fields based on the selected active item in the model.
        
        Args:
            event (ModelActiveItemChangedEvent): The event containing the active item details.
        """
        # Dynamically updates the form when the Model alerts the View that an item was selected
        self.lbl_editor_title.config(text=f"Editing {event.item_type}")
        self.entry_title.delete(0, tk.END)
        self.entry_title.insert(0, getattr(event.item_data, 'title', ''))
        self.text_desc.delete("1.0", tk.END)
        self.text_desc.insert("1.0", getattr(event.item_data, 'description', ''))