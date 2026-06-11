import tkinter as tk
from tkinter import ttk
import re

class SplitStoryDialog(tk.Toplevel):
    def __init__(self, parent, story_title, story_weight):
        super().__init__(parent)
        self.title("Split Story")
        self.transient(parent)
        self.grab_set()
        
        self.original_weight = story_weight
        
        # Strip existing " (Part \d+ of \d+)" for preview
        base_title = re.sub(r" \(Part \d+ of \d+\)$", "", story_title)
        
        self._setup_ui(base_title)
        self.result = None
        
    def _setup_ui(self, base_title):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1)
        
        # Row 1: Names
        ttk.Label(main_frame, text="Original:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.orig_name_var = tk.StringVar(value=f"{base_title} (Part X of Y)")
        self.orig_name_entry = ttk.Entry(main_frame, textvariable=self.orig_name_var, state="readonly")
        self.orig_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(main_frame, text="New:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.new_name_var = tk.StringVar(value=f"{base_title} (Part X+1 of Y)")
        self.new_name_entry = ttk.Entry(main_frame, textvariable=self.new_name_var, state="readonly")
        self.new_name_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        
        # Row 2: Weights
        ttk.Label(main_frame, text="Weights:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        weight_frame = ttk.Frame(main_frame)
        weight_frame.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        initial_val = max(1.0, self.original_weight / 2.0)
        self.orig_weight_var = tk.DoubleVar(value=initial_val)
        self.clone_weight_var = tk.DoubleVar(value=self.original_weight - initial_val)
        
        # Ensure sum = original_weight, min = 1.0
        self.orig_weight_spin = ttk.Spinbox(weight_frame, from_=1.0, to=max(1.0, self.original_weight - 1.0), 
                                            textvariable=self.orig_weight_var, width=10)
        self.orig_weight_spin.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(weight_frame, text="+").pack(side=tk.LEFT, padx=2)
        
        self.clone_weight_spin = ttk.Spinbox(weight_frame, from_=1.0, to=max(1.0, self.original_weight - 1.0),
                                             textvariable=self.clone_weight_var, width=10)
        self.clone_weight_spin.pack(side=tk.LEFT, padx=2)
        
        # Trace for dynamic updates
        self.orig_weight_var.trace_add("write", self._on_orig_weight_change)
        self.clone_weight_var.trace_add("write", self._on_clone_weight_change)
        self._updating = False
        
        # Row 3: Description
        ttk.Label(main_frame, text="Reason:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.NW)
        self.desc_text = tk.Text(main_frame, height=4, width=40)
        self.desc_text.grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self._on_cancel).pack(side=tk.LEFT, padx=5)

    def _on_orig_weight_change(self, *args):
        if self._updating: return
        self._updating = True
        try:
            val = self.orig_weight_var.get()
            if val < 1.0: val = 1.0; self.orig_weight_var.set(1.0)
            if val > self.original_weight - 1.0: val = max(1.0, self.original_weight - 1.0); self.orig_weight_var.set(val)
            self.clone_weight_var.set(self.original_weight - val)
        except: pass
        self._updating = False

    def _on_clone_weight_change(self, *args):
        if self._updating: return
        self._updating = True
        try:
            val = self.clone_weight_var.get()
            if val < 1.0: val = 1.0; self.clone_weight_var.set(1.0)
            if val > self.original_weight - 1.0: val = max(1.0, self.original_weight - 1.0); self.clone_weight_var.set(val)
            self.orig_weight_var.set(self.original_weight - val)
        except: pass
        self._updating = False

    def _on_ok(self):
        self.result = {
            "orig_weight": self.orig_weight_var.get(),
            "clone_weight": self.clone_weight_var.get(),
            "reason": self.desc_text.get("1.0", tk.END).strip()
        }
        self.destroy()

    def _on_cancel(self):
        self.destroy()
