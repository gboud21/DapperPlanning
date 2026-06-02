import tkinter as tk
from tkinter import ttk
from src.core.events import EventDispatcher, ModelConflictDetectedEvent, UIConflictResolvedEvent

class ConflictResolutionModal(tk.Toplevel):
    def __init__(self, parent: tk.Tk, dispatcher: EventDispatcher, local_item, remote_item):
        super().__init__(parent)
        self.title("Conflict Detected")
        self.geometry("800x600")
        self.dispatcher = dispatcher
        self.local_item = local_item
        self.remote_item = remote_item

        # Modal configuration
        self.transient(parent)
        self.grab_set()

        self._setup_ui()
        
        # Center the window
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        lbl_info = ttk.Label(main_frame, text="A mismatch was found between local and GitLab versions. Please choose which one to keep.", wraplength=750)
        lbl_info.pack(pady=(0, 20))

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Local side
        local_frame = ttk.LabelFrame(content_frame, text="Local Version")
        local_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self._create_item_details(local_frame, self.local_item)

        # Remote side
        remote_frame = ttk.LabelFrame(content_frame, text="GitLab Version")
        remote_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self._create_item_details(remote_frame, self.remote_item)

        # Action buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(20, 0))

        ttk.Button(btn_frame, text="Keep Local", command=self._keep_local).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Keep Remote", command=self._keep_remote).pack(side=tk.LEFT, padx=5)

    def _create_item_details(self, parent, item):
        txt = tk.Text(parent, wrap=tk.WORD, height=20, width=40)
        txt.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        details = f"Title: {item.title}\n\n"
        details += f"Description: {item.description}\n\n"
        details += f"Weight: {getattr(item, 'weight', 'N/A')}\n"
        details += f"Status: {getattr(item, 'status', 'N/A')}\n"
        
        txt.insert(tk.END, details)
        txt.config(state=tk.DISABLED)

    def _keep_local(self):
        self.dispatcher.dispatch(UIConflictResolvedEvent(resolution='local', item_id=self.local_item.id))
        self.destroy()

    def _keep_remote(self):
        self.dispatcher.dispatch(UIConflictResolvedEvent(resolution='remote', item_id=self.local_item.id))
        self.destroy()
