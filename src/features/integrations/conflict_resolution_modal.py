import tkinter as tk
from tkinter import ttk, messagebox
from src.core.events import EventDispatcher, UIConflictResolvedEvent, ModelHierarchyUpdatedEvent

class ConflictResolutionModal(tk.Toplevel):
    def __init__(self, parent: tk.Toplevel, dispatcher: EventDispatcher, local_item, remote_item):
        super().__init__(parent)
        self.title(f"Resolve Conflict: {local_item.title}")
        self.geometry("900x650")
        self.dispatcher = dispatcher
        self.local_item = local_item
        self.remote_item = remote_item

        # Selection trackers
        self.chosen_title = tk.StringVar(value="local")
        self.chosen_description = tk.StringVar(value="local")
        self.chosen_weight = tk.StringVar(value="local")
        self.chosen_status = tk.StringVar(value="local")
        self.chosen_assignee = tk.StringVar(value="local")
        self.chosen_iteration = tk.StringVar(value="local")
        self.chosen_labels = tk.StringVar(value="local")

        # Modal configuration
        self.transient(parent)
        self.grab_set()

        self._setup_ui()
        
        # Center the window
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        header_lbl = ttk.Label(main_frame, text="A conflict was detected. Select which attributes to keep from each version.", 
                               font=("TkDefaultFont", 10, "bold"), wraplength=850)
        header_lbl.pack(pady=(0, 20))

        # Grid for side-by-side comparison
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Headers
        ttk.Label(table_frame, text="Attribute", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Label(table_frame, text="Local Version", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(table_frame, text="GitLab Version", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

        # Fields to compare
        self._add_attribute_row(table_frame, 1, "Title", self.local_item.title, self.remote_item.title, self.chosen_title)
        self._add_attribute_row(table_frame, 2, "Description", self.local_item.description, self.remote_item.description, self.chosen_description, is_long=True)
        
        if hasattr(self.local_item, 'weight'):
            self._add_attribute_row(table_frame, 3, "Weight", self.local_item.weight, self.remote_item.weight, self.chosen_weight)
        
        self._add_attribute_row(table_frame, 4, "Status", self.local_item.status, self.remote_item.status, self.chosen_status)
        
        if hasattr(self.local_item, 'assignee_id'):
            self._add_attribute_row(table_frame, 5, "Assignee ID", self.local_item.assignee_id, self.remote_item.assignee_id, self.chosen_assignee)
            
        if hasattr(self.local_item, 'iteration_id'):
            self._add_attribute_row(table_frame, 6, "Iteration ID", self.local_item.iteration_id, self.remote_item.iteration_id, self.chosen_iteration)

        self._add_attribute_row(table_frame, 7, "Labels", ", ".join(self.local_item.labels), ", ".join(self.remote_item.labels), self.chosen_labels)

        # Action buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(20, 0))

        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Resolve Conflict", style="Accent.TButton", command=self._on_ok_clicked).pack(side=tk.RIGHT, padx=5)

    def _add_attribute_row(self, parent, row, label, local_val, remote_val, var, is_long=False):
        ttk.Label(parent, text=label).grid(row=row, column=0, padx=5, pady=5, sticky=tk.NW)
        
        # Local Radio
        l_frame = ttk.Frame(parent)
        l_frame.grid(row=row, column=1, padx=5, pady=5, sticky=tk.NSEW)
        ttk.Radiobutton(l_frame, text="", variable=var, value="local").pack(side=tk.LEFT, anchor=tk.N)
        
        l_text = tk.Text(l_frame, height=3 if is_long else 1, width=40, wrap=tk.WORD, font=("TkDefaultFont", 9))
        l_text.insert(tk.END, str(local_val))
        l_text.config(state=tk.DISABLED)
        l_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Remote Radio
        r_frame = ttk.Frame(parent)
        r_frame.grid(row=row, column=2, padx=5, pady=5, sticky=tk.NSEW)
        ttk.Radiobutton(r_frame, text="", variable=var, value="remote").pack(side=tk.LEFT, anchor=tk.N)
        
        r_text = tk.Text(r_frame, height=3 if is_long else 1, width=40, wrap=tk.WORD, font=("TkDefaultFont", 9))
        r_text.insert(tk.END, str(remote_val))
        r_text.config(state=tk.DISABLED)
        r_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _on_ok_clicked(self):
        """Compiles selections and presents a secondary confirmation prompt."""
        summary = "Please confirm your final merged values:\n\n"
        summary += f"Title: {'[Local]' if self.chosen_title.get() == 'local' else '[Remote]'} {self.local_item.title if self.chosen_title.get() == 'local' else self.remote_item.title}\n"
        
        if messagebox.askokcancel("Confirm Merge Resolution", summary + "\nApply these changes and clear conflict status?"):
            self._apply_merge_resolutions()
            self.local_item.is_conflicted = False
            # Trigger UI refresh to clear highlights
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=[])) # Partial trigger is enough for refresh
            self.destroy()

    def _apply_merge_resolutions(self):
        """Applies chosen attributes to the local item."""
        if self.chosen_title.get() == 'remote':
            self.local_item.title = self.remote_item.title
        
        if self.chosen_description.get() == 'remote':
            self.local_item.description = self.remote_item.description
            
        if hasattr(self.local_item, 'weight') and self.chosen_weight.get() == 'remote':
            self.local_item.weight = self.remote_item.weight
            
        if self.chosen_status.get() == 'remote':
            self.local_item.status = self.remote_item.status
            
        if hasattr(self.local_item, 'assignee_id') and self.chosen_assignee.get() == 'remote':
            self.local_item.assignee_id = self.remote_item.assignee_id
            
        if hasattr(self.local_item, 'iteration_id') and self.chosen_iteration.get() == 'remote':
            self.local_item.iteration_id = self.remote_item.iteration_id
            
        if self.chosen_labels.get() == 'remote':
            self.local_item.labels = self.remote_item.labels.copy()
            
        # Reset sync timestamp to force push update
        self.local_item.last_synced_at = None
