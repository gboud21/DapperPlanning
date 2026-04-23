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
        
        self.setup_menu()
        self.setup_ui()
        self._bind_events()

    def setup_menu(self):
        """
        Set up the main menu bar.
        """
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Copy", command=lambda: None)
        edit_menu.add_command(label="Cut", command=lambda: None)
        edit_menu.add_command(label="Paste", command=lambda: None)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Minimize", command=self._minimize_window)
        view_menu.add_command(label="Maximize", command=self._maximize_window)
        view_menu.add_command(label="Windowed Mode", command=self._restore_window)
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about_dialog)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)

    def _show_about_dialog(self):
        """
        Show the About dialog with a close button.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("About")
        dialog.geometry("200x100")
        dialog.transient(self.root)
        dialog.grab_set()
        
        close_btn = ttk.Button(dialog, text="Close", command=dialog.destroy)
        close_btn.pack(expand=True)

    def _minimize_window(self):
        """Minimize the main window."""
        self.root.iconify()

    def _maximize_window(self):
        """Maximize the main window."""
        try:
            self.root.state("zoomed")
        except tk.TclError:
            # Fallback for X11 environments
            try:
                self.root.attributes("-zoomed", True)
            except tk.TclError:
                pass

    def _restore_window(self):
        """Restore the window to normal (windowed) mode."""
        try:
            self.root.state("normal")
        except tk.TclError:
            pass
        
        try:
            self.root.attributes("-zoomed", False)
        except tk.TclError:
            pass

    def setup_ui(self):
        """
        Set up the user interface components including the treeview, 
        editor pane, and action buttons.
        """
        # Ensure native title bar is enabled
        self.root.overrideredirect(False)

        # 1. Main Paned Window
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 2. Left Frame: Treeview
        self.tree_container = ttk.Frame(self.paned_window)
        self.paned_window.add(self.tree_container, weight=1)

        self.tree = ttk.Treeview(self.tree_container, selectmode="browse")
        self.tree.heading("#0", text="Agile Hierarchy", anchor=tk.W)
        
        self.tree_scroll = ttk.Scrollbar(self.tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scroll.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Tag Configuration for visual hierarchy
        self.tree.tag_configure('Product', font=("TkDefaultFont", 10, "bold"), background="#e6f2ff")
        self.tree.tag_configure('Capability', font=("TkDefaultFont", 10, "bold"))
        self.tree.tag_configure('Epic')
        self.tree.tag_configure('Feature_Stub', font=("TkDefaultFont", 10, "italic"), foreground="gray")
        self.tree.tag_configure('Story_Stub', font=("TkDefaultFont", 10, "italic"), foreground="gray")

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
            # Retrieve the item's tags to determine the item type
            tags = self.tree.item(selected_id, "tags")
            item_type = tags[0] if tags else "Unknown"
            self.dispatcher.dispatch(UIItemSelectedEvent(item_id=selected_id, item_type=item_type))

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