import tkinter as tk
from tkinter import ttk, messagebox
from src.core.events import EventDispatcher, UIConflictResolvedEvent, ModelHierarchyUpdatedEvent

class ConflictResolutionModal(tk.Toplevel):
    def __init__(self, parent: tk.Toplevel, dispatcher: EventDispatcher, local_item, remote_item, workspace):
        super().__init__(parent)
        self.title(f"Resolve Conflict: {local_item.title}")
        self.geometry("900x650")
        self.dispatcher = dispatcher
        self.local_item = local_item
        self.remote_item = remote_item
        self.workspace = workspace

        # Selection trackers
        self.chosen_title = tk.StringVar(value="local")
        self.chosen_description = tk.StringVar(value="local")
        self.chosen_weight = tk.StringVar(value="local")
        self.chosen_status = tk.StringVar(value="local")
        self.chosen_assignee = tk.StringVar(value="local")
        self.chosen_iteration = tk.StringVar(value="local")
        self.chosen_labels = tk.StringVar(value="local")
        self.chosen_parent_epic = tk.StringVar(value="local")
        self.chosen_parent_feature = tk.StringVar(value="local")

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
        header_lbl.pack(pady=(0, 10))

        # Categorize changes from baseline
        change_data = self._get_change_analysis()
        
        # 1. Collision Summary (Red)
        if change_data['collisions']:
            lbl_collision = ttk.Label(main_frame, text=f"Direct Collisions (Both Edited): {', '.join(change_data['collisions'])}", 
                                      font=("TkDefaultFont", 9, "bold"), foreground="#991b1b")
            lbl_collision.pack(anchor=tk.W, pady=(5, 0))
        
        # 2. Item-Level Mismatches (Orange/Yellow)
        mismatches = change_data['local_only'] + change_data['remote_only']
        if mismatches:
            mismatch_text = []
            if change_data['local_only']: mismatch_text.append(f"Local-only: {', '.join(change_data['local_only'])}")
            if change_data['remote_only']: mismatch_text.append(f"GitLab-only: {', '.join(change_data['remote_only'])}")
            
            lbl_mismatch = ttk.Label(main_frame, text=f"Item-Level Mismatches (Disjoint Changes): {' | '.join(mismatch_text)}", 
                                     font=("TkDefaultFont", 9, "bold"), foreground="#854d0e") # Dark yellow/orange
            lbl_mismatch.pack(anchor=tk.W, pady=(5, 0))
            
        if not change_data['collisions'] and not mismatches:
             ttk.Label(main_frame, text="Note: Both versions have diverged from baseline, but specific field values appear identical.", 
                      font=("TkDefaultFont", 9, "italic")).pack(anchor=tk.W, pady=(5, 0))

        ttk.Label(main_frame, text="").pack(pady=(0, 15)) # Spacer

        # Grid for side-by-side comparison
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Headers
        ttk.Label(table_frame, text="Attribute", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Label(table_frame, text="Local Version", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(table_frame, text="GitLab Version", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

        # Fields to compare
        all_changes = set(change_data['collisions']) | set(change_data['local_only']) | set(change_data['remote_only'])
        
        self._add_attribute_row(table_frame, 1, "Title", self.local_item.title, self.remote_item.title, self.chosen_title, 
                                is_conflicted="Title" in change_data['collisions'], is_modified="Title" in all_changes)
        
        self._add_attribute_row(table_frame, 2, "Description", self.local_item.description, self.remote_item.description, self.chosen_description, 
                                is_long=True, is_conflicted="Description" in change_data['collisions'], is_modified="Description" in all_changes)
        
        if hasattr(self.local_item, 'weight'):
            self._add_attribute_row(table_frame, 3, "Weight", self.local_item.weight, self.remote_item.weight, self.chosen_weight, 
                                    is_conflicted="Weight" in change_data['collisions'], is_modified="Weight" in all_changes)
        
        self._add_attribute_row(table_frame, 4, "Status", self.local_item.status, self.remote_item.status, self.chosen_status, 
                                is_conflicted="Status" in change_data['collisions'], is_modified="Status" in all_changes)
        
        if hasattr(self.local_item, 'assignee_id'):
            self._add_attribute_row(table_frame, 5, "Assignee ID", self.local_item.assignee_id, self.remote_item.assignee_id, self.chosen_assignee, 
                                    is_conflicted="Assignee ID" in change_data['collisions'], is_modified="Assignee ID" in all_changes)
            
        if hasattr(self.local_item, 'iteration_id'):
            self._add_attribute_row(table_frame, 6, "Iteration ID", self.local_item.iteration_id, self.remote_item.iteration_id, self.chosen_iteration, 
                                    is_conflicted="Iteration ID" in change_data['collisions'], is_modified="Iteration ID" in all_changes)

        self._add_attribute_row(table_frame, 7, "Labels", ", ".join(self.local_item.labels), ", ".join(self.remote_item.labels), self.chosen_labels, 
                                is_conflicted="Labels" in change_data['collisions'], is_modified="Labels" in all_changes)

        if hasattr(self.local_item, 'parent_epic_id') or hasattr(self.remote_item, 'parent_epic_id'):
            l_p = getattr(self.local_item, 'parent_epic_id', None)
            r_p = getattr(self.remote_item, 'parent_epic_id', None)
            if l_p is not None or r_p is not None:
                self._add_attribute_row(table_frame, 8, "Parent Epic ID", l_p, r_p, self.chosen_parent_epic,
                                        is_conflicted="Parent Epic ID" in change_data['collisions'], is_modified="Parent Epic ID" in all_changes)

        if hasattr(self.local_item, 'parent_feature_id') or hasattr(self.remote_item, 'parent_feature_id'):
            l_p = getattr(self.local_item, 'parent_feature_id', None)
            r_p = getattr(self.remote_item, 'parent_feature_id', None)
            if l_p is not None or r_p is not None:
                self._add_attribute_row(table_frame, 9, "Parent Feature ID", l_p, r_p, self.chosen_parent_feature,
                                        is_conflicted="Parent Feature ID" in change_data['collisions'], is_modified="Parent Feature ID" in all_changes)

        # Action buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(20, 0))

        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Resolve Conflict", style="Accent.TButton", command=self._on_ok_clicked).pack(side=tk.RIGHT, padx=5)

    def _get_change_analysis(self):
        """Categorizes all changes from baseline to identify collisions and disjoint mismatches."""
        shadow = self.workspace.shadow_hierarchy.get(self.local_item.id)
        analysis = {'collisions': [], 'local_only': [], 'remote_only': []}
        if not shadow:
            return analysis
            
        fields = {
            'title': 'Title',
            'description': 'Description',
            'weight': 'Weight',
            'status': 'Status',
            'assignee_id': 'Assignee ID',
            'iteration_id': 'Iteration ID',
            'labels': 'Labels',
            'parent_epic_id': 'Parent Epic ID',
            'parent_feature_id': 'Parent Feature ID'
        }
        
        for field, label in fields.items():
            if not hasattr(self.local_item, field) and field not in ('assignee_id', 'iteration_id', 'parent_epic_id', 'parent_feature_id'):
                continue
            
            s_val = shadow.get(field)
            l_val = getattr(self.local_item, field, None)
            r_val = getattr(self.remote_item, field, None)
            
            def has_changed(val, baseline, is_labels=False):
                if is_labels:
                    return sorted(val or []) != sorted(baseline or [])
                return val != baseline

            l_changed = has_changed(l_val, s_val, field == 'labels')
            r_changed = has_changed(r_val, s_val, field == 'labels')
            
            if l_changed and r_changed:
                # Both changed: check if they changed to DIFFERENT values (Collision)
                different = False
                if field == 'labels':
                    different = sorted(l_val or []) != sorted(r_val or [])
                else:
                    different = l_val != r_val
                
                if different:
                    analysis['collisions'].append(label)
            elif l_changed:
                analysis['local_only'].append(label)
            elif r_changed:
                analysis['remote_only'].append(label)
                    
        return analysis

    def _add_attribute_row(self, parent, row, label, local_val, remote_val, var, is_long=False, is_conflicted=False, is_modified=False):
        # Styling based on change type
        fg_color = "#991b1b" if is_conflicted else ("#854d0e" if is_modified else None)
        lbl_style = {"font": ("TkDefaultFont", 9, "bold")}
        if fg_color: lbl_style["foreground"] = fg_color
        
        ttk.Label(parent, text=label, **lbl_style).grid(row=row, column=0, padx=5, pady=5, sticky=tk.NW)
        
        # Local Radio
        l_frame = ttk.Frame(parent)
        l_frame.grid(row=row, column=1, padx=5, pady=5, sticky=tk.NSEW)
        ttk.Radiobutton(l_frame, text="", variable=var, value="local").pack(side=tk.LEFT, anchor=tk.N)
        
        # Highlight background if modified
        bg_color = "#fee2e2" if is_conflicted else ("#fef9c3" if is_modified else None) # Soft red vs Soft yellow
        l_text = tk.Text(l_frame, height=3 if is_long else 1, width=40, wrap=tk.WORD, font=("TkDefaultFont", 9))
        if bg_color: l_text.configure(bg=bg_color)
        l_text.insert(tk.END, str(local_val))
        l_text.config(state=tk.DISABLED)
        l_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Remote Radio
        r_frame = ttk.Frame(parent)
        r_frame.grid(row=row, column=2, padx=5, pady=5, sticky=tk.NSEW)
        ttk.Radiobutton(r_frame, text="", variable=var, value="remote").pack(side=tk.LEFT, anchor=tk.N)
        
        r_text = tk.Text(r_frame, height=3 if is_long else 1, width=40, wrap=tk.WORD, font=("TkDefaultFont", 9))
        if bg_color: r_text.configure(bg=bg_color)
        r_text.insert(tk.END, str(remote_val))
        r_text.config(state=tk.DISABLED)
        r_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _on_ok_clicked(self):
        """Compiles selections and presents a secondary confirmation prompt."""
        summary = "Please confirm your final merged values:\n\n"
        summary += f"Title: {'[Local]' if self.chosen_title.get() == 'local' else '[Remote]'} {self.local_item.title if self.chosen_title.get() == 'local' else self.remote_item.title}\n"
        
        if messagebox.askokcancel("Confirm Merge Resolution", summary + "\nApply these changes and clear conflict status?", parent=self):
            self._apply_merge_resolutions()
            self.local_item.is_conflicted = False
            
            # Count remaining conflicts
            remaining = [i for i in self.workspace.all_items_iterable() if getattr(i, 'is_conflicted', False)]
            count = len(remaining)
            
            if count > 0:
                messagebox.showinfo("Conflicts Remaining", f"Conflict resolved. There are {count} conflicts remaining to be resolved.", parent=self)
                # Refresh tree to update highlighting for this item, but keep filter
                self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                    root_items=self.workspace.get_epics(),
                    products=self.workspace.products
                ))
            else:
                messagebox.showinfo("All Resolved", "All merge conflicts have been successfully resolved. Clearing filter.", parent=self)
                # Clear the conflict isolation filter
                from src.core.events import UITreeFilterAppliedEvent, UISaveWorkspaceRequestedEvent
                self.dispatcher.dispatch(UITreeFilterAppliedEvent(
                    query_string="",
                    show_ancestors=True,
                    show_descendants=False
                ))
                self.workspace.save_shadow_hierarchy(self.workspace.get_epics())
                self.dispatcher.dispatch(UISaveWorkspaceRequestedEvent())
            
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

        if hasattr(self.local_item, 'parent_epic_id') and self.chosen_parent_epic.get() == 'remote':
            remote_p = getattr(self.remote_item, 'parent_epic_id', None)
            if remote_p and remote_p != self.local_item.parent_epic_id:
                if hasattr(self.workspace, 'move_feature'):
                    self.workspace.move_feature(self.local_item.id, remote_p)
            self.local_item.parent_epic_id = remote_p

        if hasattr(self.local_item, 'parent_feature_id') and self.chosen_parent_feature.get() == 'remote':
            remote_p = getattr(self.remote_item, 'parent_feature_id', None)
            if remote_p and remote_p != self.local_item.parent_feature_id:
                if hasattr(self.workspace, 'move_story'):
                    self.workspace.move_story(self.local_item.id, remote_p)
            self.local_item.parent_feature_id = remote_p
            
        # Reset sync timestamp to force push update
        self.local_item.last_synced_at = None

        # Advance the merge baseline snapshot to match the remote server state
        from dataclasses import asdict
        self.workspace.shadow_hierarchy[self.local_item.id] = asdict(self.remote_item)
