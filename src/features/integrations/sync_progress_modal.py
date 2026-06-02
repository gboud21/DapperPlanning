import tkinter as tk
from tkinter import ttk
from src.core.events import EventDispatcher, ModelSyncProgressEvent

class SyncProgressModal(tk.Toplevel):
    def __init__(self, parent: tk.Tk, dispatcher: EventDispatcher):
        super().__init__(parent)
        self.title("GitLab Synchronization")
        self.geometry("400x150")
        self.resizable(False, False)
        self.dispatcher = dispatcher

        # Modal configuration
        self.transient(parent)
        self.grab_set()

        self._setup_ui()
        self.dispatcher.subscribe(ModelSyncProgressEvent, self._on_progress)
        
        # Center the window
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.lbl_status = ttk.Label(main_frame, text="Starting synchronization...", wraplength=350)
        self.lbl_status.pack(pady=(0, 10))

        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.progress.pack(pady=10)

    def _on_progress(self, event: ModelSyncProgressEvent):
        self.lbl_status.config(text=event.message)
        self.progress['value'] = event.percent
        if event.percent >= 100:
            self.after(500, self.destroy)
