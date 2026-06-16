import tkinter as tk
from tkinter import ttk, messagebox
import re
from src.core.app_context import AppContext
from src.core.events import (
    EventDispatcher, UICreateItemRequestedEvent, ModelActiveItemChangedEvent,
    AppThemeChangedEvent, UIGlobalTagAddRequestedEvent, UIGlobalTagDeleteRequestedEvent,
    ModelWorkspaceLoadedEvent, UILabelUpdateRequestedEvent, ModelHierarchyUpdatedEvent
)
from src.core.command_bus import CommandBus
from src.core.commands import SaveItemCommand
from src.domain.entities import Label
from src.utils.template_generator import TemplateGenerator
from src.utils.ui_utils import enable_scroll_bubbling
from src.utils.debouncer import Debouncer
from src.infrastructure.storage.settings_manager import SettingsManager

class EditorPane:
    def __init__(self, parent_frame: ttk.Frame, context: AppContext):
        """
        Initializes the EditorPane for viewing and editing item details.

        Args:
            parent_frame (ttk.Frame): The frame where the editor widgets will be placed.
            context (AppContext): The application context for dependency injection.
        """
        self.parent = parent_frame
        self.context = context
        self.dispatcher: EventDispatcher = context.resolve('event_dispatcher')
        self.command_bus: CommandBus = context.resolve('command_bus')
        self.workspace = context.resolve('workspace')
        self.settings: SettingsManager = context.resolve('settings_manager')
        
        self.current_selected_id = None
        self._is_populating = False
        
        # Register validation command
        self.vcmd = (self.parent.register(self._validate_weight), '%P')
        
        self._setup_ui()
        self._bind_events()
        self._load_config()

        # Instantiate debouncer for description text
        self.text_debouncer = Debouncer(self.canvas, 750, self._trigger_auto_save)

    def _validate_weight(self, new_value: str) -> bool:
        """Validates that the input is a number with at most one decimal place."""
        if new_value == "":
            return True
        return bool(re.match(r'^\d*\.?\d{0,1}$', new_value))

    def _setup_ui(self):
        """Sets up the labels, entries, and action buttons with a scrollbar."""
        # Create a canvas and scrollbar
        self.scrollbar = ttk.Scrollbar(self.parent, orient="vertical")
        self.scrollbar.pack(side="right", fill="y")
        
        self.canvas = tk.Canvas(self.parent, borderwidth=0, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        
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
        self.scrollbar.configure(command=self.canvas.yview)
        
        # Bind canvas resize to frame width
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Content widgets
        self.lbl_editor_title = ttk.Label(self.scrollable_frame, text="Select an item to edit", font=("Arial", 14, "bold"))
        self.lbl_editor_title.pack(anchor=tk.W, pady=(0, 10))

        # --- Template Parameters Section ---
        params_frame = ttk.LabelFrame(self.scrollable_frame, text="Template Parameters")
        params_frame.pack(fill=tk.X, pady=(0, 10))
        
        params_frame.columnconfigure(1, weight=1)
        params_frame.columnconfigure(3, weight=1)

        ttk.Label(params_frame, text="Tool:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.combo_tool = ttk.Combobox(params_frame, values=["GitLab", "Jira"], state="readonly", style="Preferences.TCombobox")
        self.combo_tool.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        self.combo_tool.bind("<<ComboboxSelected>>", lambda e: self._refresh_description_template())

        ttk.Label(params_frame, text="Methodology:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.combo_methodology = ttk.Combobox(params_frame, values=["Scrum", "Kanban", "SAFe"], state="readonly", style="Preferences.TCombobox")
        self.combo_methodology.grid(row=0, column=3, sticky=tk.EW, padx=5, pady=2)
        self.combo_methodology.bind("<<ComboboxSelected>>", lambda e: self._refresh_description_template())

        ttk.Label(params_frame, text="Type:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.combo_type = ttk.Combobox(params_frame, values=["Heavyweight", "Lightweight"], state="readonly", style="Preferences.TCombobox")
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
                                            values=("Epic", "Feature", "Story"), style="Preferences.TCombobox")
        self.combo_item_type.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))
        self.combo_item_type.bind("<<ComboboxSelected>>", lambda e: self._refresh_description_template())

        ttk.Label(self.scrollable_frame, text="Title:").pack(anchor=tk.W)
        self.entry_title = tk.Entry(self.scrollable_frame, width=50)
        self.entry_title.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))
        self.entry_title.bind("<FocusOut>", self._trigger_auto_save)
        self.entry_title.bind("<Return>", self._trigger_auto_save)

        # Assignee (Hidden by default)
        self.assignee_frame = ttk.Frame(self.scrollable_frame)
        self.assignee_frame.pack(fill=tk.X, pady=(0, 10))
        self.assignee_lbl = ttk.Label(self.assignee_frame, text="Assignee:")
        self.assignee_lbl.grid(row=0, column=0, sticky=tk.W)
        self.assignee_combo = ttk.Combobox(self.assignee_frame, state="normal", style="Preferences.TCombobox")
        self.assignee_combo.grid(row=0, column=1, sticky=tk.EW, padx=5)
        self.assignee_frame.columnconfigure(1, weight=1)
        
        self._master_assignee_list = []
        self.assignee_combo.bind("<<ComboboxSelected>>", self._trigger_auto_save)
        self.assignee_combo.bind("<KeyRelease>", self._on_assignee_key_release)
        self.assignee_combo.bind("<FocusOut>", self._on_assignee_focus_out)
        
        self.assignee_lbl.grid_remove()
        self.assignee_combo.grid_remove()

        # Weight Entry
        ttk.Label(self.scrollable_frame, text="Weight:").pack(anchor=tk.W)
        self.entry_weight = tk.Entry(self.scrollable_frame, validate='key', validatecommand=self.vcmd)
        self.entry_weight.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))
        self.entry_weight.bind("<FocusOut>", self._trigger_auto_save)
        self.entry_weight.bind("<Return>", self._trigger_auto_save)

        # Status Combobox
        ttk.Label(self.scrollable_frame, text="Status:").pack(anchor=tk.W)
        self.combo_status = ttk.Combobox(self.scrollable_frame, values=('Backlog', 'In Progress', 'In Review', 'Done'), state="readonly", style="Preferences.TCombobox")
        self.combo_status.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))
        self.combo_status.bind("<<ComboboxSelected>>", self._trigger_auto_save)

        ttk.Label(self.scrollable_frame, text="Description:").pack(anchor=tk.W)
        self.text_desc = tk.Text(self.scrollable_frame, height=10, width=50)
        self.text_desc.pack(anchor=tk.W, fill=tk.BOTH, expand=True, pady=(0, 10))
        enable_scroll_bubbling(self.text_desc, self.canvas)
        self.text_desc.bind("<KeyRelease>", lambda e: self.text_debouncer.schedule())

        # Dual-Listbox Tag Management
        self.product_ui = self._create_dual_listbox(self.scrollable_frame, "Products", "product")
        self.capability_ui = self._create_dual_listbox(self.scrollable_frame, "Capabilities", "capability")
        self.label_ui = self._create_labels_dual_listbox(self.scrollable_frame)
        
        # Button Frame for CRUD actions
        self.button_frame = ttk.Frame(self.scrollable_frame)
        self.button_frame.pack(fill=tk.X, pady=10)

        self.btn_create = ttk.Button(self.button_frame, text="Create as New Child", command=self._on_save_clicked)
        self.btn_create.pack(side=tk.RIGHT, padx=5)

        # Enable mouse wheel scrolling recursively
        self._bind_mousewheel(self.canvas)

    def _create_labels_dual_listbox(self, parent_frame):
        """Helper to create a dual-listbox specifically for GitLab Labels."""
        frame = ttk.LabelFrame(parent_frame, text="GitLab Labels")
        frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(2, weight=1)
        
        # Left side: Available Labels
        left_container = ttk.Frame(frame)
        left_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ttk.Label(left_container, text="Available").pack(anchor=tk.W)
        list_master = tk.Listbox(left_container, height=6, exportselection=False)
        list_master.pack(fill=tk.BOTH, expand=True)
        enable_scroll_bubbling(list_master, self.canvas)

        # New Label Entry
        entry_new = tk.Entry(left_container)
        entry_new.pack(fill=tk.X, pady=(2, 0))

        btn_add_master = ttk.Button(left_container, text="Create Local Label",
                                    command=lambda: self._add_local_label(list_master, entry_new))
        btn_add_master.pack(fill=tk.X)

        # Middle: Transfer Buttons
        mid_container = ttk.Frame(frame)
        mid_container.grid(row=0, column=1, padx=5)
        
        btn_assign = ttk.Button(mid_container, text=">>", width=5,
                                command=lambda: self._on_label_add(list_master, list_assigned))
        btn_assign.pack(pady=5)
        
        # Right side: Assigned Labels
        right_container = ttk.Frame(frame)
        right_container.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        
        ttk.Label(right_container, text="Assigned").pack(anchor=tk.W)
        list_assigned = tk.Listbox(right_container, height=6, exportselection=False)
        list_assigned.pack(fill=tk.BOTH, expand=True)
        enable_scroll_bubbling(list_assigned, self.canvas)

        btn_delete_assigned = ttk.Button(right_container, text="Remove", 
                                         command=lambda: self._on_label_remove(list_assigned))
        btn_delete_assigned.pack(fill=tk.X)

        return {
            "master": list_master,
            "assigned": list_assigned,
            "entry": entry_new,
            "frame": frame
        }

    def _add_local_label(self, list_master, entry_new):
        """Creates a new label locally in the workspace."""
        val = entry_new.get().strip()
        if not val:
            return

        if val in self.workspace.labels:
            messagebox.showinfo("Label Exists", f"Label '{val}' already exists.")
            return

        # Create local label (defaults to group scope for global availability as per instructions)
        active_product_name = self.workspace.active_product_name
        product = next((p for p in self.workspace.products if p.name == active_product_name), None)
        gid = str(product.gitlab_group_id) if product and product.gitlab_group_id else ""

        new_label = Label(
            id=None,
            name=val,
            color="#666666", # Default gray
            description="Locally created label",
            scope='group',
            scope_name=gid
        )
        self.workspace.labels[val] = new_label

        # Refresh master list
        reserved_labels = {'Epic', 'Feature', 'Story'}
        master_labels_formatted = [
            f"({l.scope_name}) {l.name}" 
            for l in self.workspace.labels.values()
            if l.name not in reserved_labels
        ]
        list_master.delete(0, tk.END)
        for l_str in sorted(master_labels_formatted):
            list_master.insert(tk.END, l_str)

        entry_new.delete(0, tk.END)
        self.dispatcher.dispatch(UISaveWorkspaceRequestedEvent())

    def _on_label_add(self, source, target):
        """Handles adding a label with recursion check and protection."""
        selected_index = source.curselection()
        if not selected_index:
            return

        full_label_str = source.get(selected_index)
        # Extract label name: format is "(Scope: Name) LabelName"
        # Everything after the first ") "
        if ") " in full_label_str:
            label_name = full_label_str.split(") ", 1)[1]
        else:
            label_name = full_label_str
        # Protection Rule
        item_type = self.combo_item_type.get()
        if item_type == 'Feature' and label_name == 'Feature':
            messagebox.showwarning("Reserved Label", "The 'Feature' label is reserved for hierarchy identification and cannot be manually added to Feature items.")
            return

        recursive = messagebox.askyesno("Recursive Update", "Apply this label update recursively to all child items?")
        
        self.dispatcher.dispatch(UILabelUpdateRequestedEvent(
            item_id=self.current_selected_id,
            item_type=item_type,
            label_name=label_name,
            add=True,
            recursive=recursive
        ))

    def _on_label_remove(self, list_assigned):
        """Handles removing a label with recursion check and protection."""
        selected_index = list_assigned.curselection()
        if not selected_index:
            return
            
        full_label_str = list_assigned.get(selected_index)
        # Extract label name: format is "(Scope: Name) LabelName" or "(ScopeName) LabelName"
        # Everything after the first ") "
        if ") " in full_label_str:
            label_name = full_label_str.split(") ", 1)[1]
        else:
            label_name = full_label_str
        
        # Protection Rule
        item_type = self.combo_item_type.get()
        if item_type == 'Feature' and label_name == 'Feature':
            messagebox.showwarning("Reserved Label", "The 'Feature' label is reserved for hierarchy identification and cannot be removed from Feature items.")
            return

        recursive = messagebox.askyesno("Recursive Update", "Remove this label recursively from all child items?")
        
        self.dispatcher.dispatch(UILabelUpdateRequestedEvent(
            item_id=self.current_selected_id,
            item_type=item_type,
            label_name=label_name,
            add=False,
            recursive=recursive
        ))

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
        enable_scroll_bubbling(list_master, self.canvas)
        
        # New Tag Entry
        entry_new = tk.Entry(left_container)
        entry_new.pack(fill=tk.X, pady=(2, 0))
        
        btn_master_frame = ttk.Frame(left_container)
        btn_master_frame.pack(fill=tk.X)
        
        btn_add_master = ttk.Button(btn_master_frame, text="Add", width=5,
                                    command=lambda: self._add_to_master(list_master, entry_new, tag_type))
        btn_add_master.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        btn_delete_master = ttk.Button(btn_master_frame, text="Delete", width=6,
                                       command=lambda: self._delete_from_master_list(list_master, tag_type))
        btn_delete_master.pack(side=tk.LEFT, padx=(2, 0))
        
        # Middle: Transfer Buttons
        mid_container = ttk.Frame(frame)
        mid_container.grid(row=0, column=1, padx=5)
        
        btn_assign = ttk.Button(mid_container, text=">>", width=5,
                                command=lambda: self._transfer_items(list_master, list_assigned))
        btn_assign.pack(pady=5)
        
        # Right side: Assigned Tags
        right_container = ttk.Frame(frame)
        right_container.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        
        ttk.Label(right_container, text="Assigned").pack(anchor=tk.W)
        list_assigned = tk.Listbox(right_container, height=6, exportselection=False)
        list_assigned.pack(fill=tk.BOTH, expand=True)
        enable_scroll_bubbling(list_assigned, self.canvas)

        btn_delete_assigned = ttk.Button(right_container, text="Remove", 
                                         command=lambda: self._remove_assigned_items(list_assigned))
        btn_delete_assigned.pack(fill=tk.X)

        return {
            "master": list_master,
            "assigned": list_assigned,
            "entry": entry_new,
            "frame": frame
        }

    def _transfer_items(self, source, target):
        """Copies selected items from master listbox to assigned listbox without removing from master."""
        selected_indices = source.curselection()
        if not selected_indices:
            return
            
        current_assigned = list(target.get(0, tk.END))
        for i in selected_indices:
            item = source.get(i)
            if item not in current_assigned:
                current_assigned.append(item)
        
        current_assigned.sort()
        target.delete(0, tk.END)
        for item in current_assigned:
            target.insert(tk.END, item)
        self._trigger_auto_save()

    def _remove_assigned_items(self, list_assigned):
        """Removes selected items from the assigned listbox."""
        selected_indices = list_assigned.curselection()
        if not selected_indices:
            return
            
        for i in reversed(selected_indices):
            list_assigned.delete(i)
        self._trigger_auto_save()

    def _delete_from_master_list(self, list_master, tag_type):
        """Deletes a tag from the global master list after confirmation of impact."""
        selected_index = list_master.curselection()
        if not selected_index:
            return
            
        tag_value = list_master.get(selected_index)
        
        # 1. Identify impacted objects in the workspace
        impacted_items = []
        attr_name = 'products' if tag_type == 'product' else 'capabilities'
        
        if not hasattr(self, 'workspace') or not self.workspace:
             if messagebox.askyesno("Confirm Global Delete", f"Are you sure you want to delete '{tag_value}' from the global master list?"):
                self.dispatcher.dispatch(UIGlobalTagDeleteRequestedEvent(tag_type=tag_type, tag_value=tag_value))
                list_master.delete(selected_index)
             return

        for epic in self.workspace.get_epics():
            if tag_value in getattr(epic, attr_name, []):
                impacted_items.append(f"Epic: {epic.title}")
            for feature in epic.features:
                if tag_value in getattr(feature, attr_name, []):
                    impacted_items.append(f"  Feature: {feature.title}")
                for story in feature.stories:
                    if tag_value in getattr(story, attr_name, []):
                        impacted_items.append(f"    Story: {story.title}")
        
        msg = f"Are you sure you want to delete '{tag_value}' globally?\n\n"
        if impacted_items:
            msg += "The following items will be impacted:\n" + "\n".join(impacted_items[:15])
            if len(impacted_items) > 15:
                msg += f"\n...and {len(impacted_items)-15} more."
        else:
            msg += "No items in the current workspace currently use this tag."

        if messagebox.askyesno("Confirm Global Delete", msg):
            self.dispatcher.dispatch(UIGlobalTagDeleteRequestedEvent(tag_type=tag_type, tag_value=tag_value))
            list_master.delete(selected_index)
            # Also remove from current assigned list if present
            ui = self.product_ui if tag_type == 'product' else self.capability_ui
            assigned_items = list(ui['assigned'].get(0, tk.END))
            if tag_value in assigned_items:
                idx = assigned_items.index(tag_value)
                ui['assigned'].delete(idx)

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
        config = self.settings._settings
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
        self._trigger_auto_save()

    def _on_canvas_configure(self, event):
        """Adjusts the scrollable frame width to match the canvas width."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        self.canvas.update_idletasks()
        self.parent.after(20, self._force_redraw)

    def _force_redraw(self):
        """Explicitly triggers updates on the scrollable container and its children."""
        self.scrollable_frame.update()
        self.btn_create.update()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _bind_events(self):
        """Subscribes to model updates."""
        self.dispatcher.subscribe(ModelActiveItemChangedEvent, self.populate_editor)
        self.dispatcher.subscribe(ModelHierarchyUpdatedEvent, self.handle_hierarchy_updated)
        self.dispatcher.subscribe(AppThemeChangedEvent, self.handle_theme_change)
        self.dispatcher.subscribe(ModelWorkspaceLoadedEvent, self.handle_workspace_loaded)

    def handle_hierarchy_updated(self, event: ModelHierarchyUpdatedEvent):
        """Refreshes the current item view if the model was updated."""
        if not self.current_selected_id:
            return
            
        # Re-fetch item from workspace to get updated state
        item = self.workspace._find_item_by_id(self.current_selected_id)
        if item:
            # Determine item type
            item_type = "Epic"
            if hasattr(item, 'features'):
                item_type = "Epic"
            elif hasattr(item, 'stories'):
                item_type = "Feature"
            elif hasattr(item, 'weight'):
                item_type = "Story"
                
            # Simulate an active item change event to trigger re-population
            from src.core.events import ModelActiveItemChangedEvent
            self.populate_editor(ModelActiveItemChangedEvent(item_type=item_type, item_data=item))

    def handle_workspace_loaded(self, event: ModelWorkspaceLoadedEvent):
        """Refreshes the workspace reference."""
        self.workspace = self.context.resolve('workspace')

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
        
        for entry in [self.entry_title, self.entry_weight, self.product_ui['entry'], 
                      self.capability_ui['entry'], self.label_ui['entry']]:
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
                   self.capability_ui['master'], self.capability_ui['assigned'],
                   self.label_ui['master'], self.label_ui['assigned']]:
            lb.configure(
                bg=palette['field_bg'],
                fg=palette['fg'],
                selectbackground=palette['highlight'],
                borderwidth=1,
                relief="flat"
            )

    def _trigger_auto_save(self, *args):
        """Dispatches the update request automatically when data changes."""
        if self._is_populating or not self.current_selected_id:
            return
            
        title = self.entry_title.get()
        desc = self.text_desc.get("1.0", tk.END).strip()
        products = list(self.product_ui['assigned'].get(0, tk.END))
        capabilities = list(self.capability_ui['assigned'].get(0, tk.END))
        
        weight_str = self.entry_weight.get()
        try:
            weight = float(weight_str) if weight_str else 0.0
        except ValueError:
            weight = 0.0
        
        status = self.combo_status.get() or 'Backlog'
        
        # Determine assignee_id from name
        assignee_name = self.assignee_combo.get()
        assignee_id = None
        if assignee_name and assignee_name != "Unassigned":
            member = next((m for m in self.workspace.get_members() if m.name == assignee_name), None)
            if member:
                assignee_id = member.id

        self.command_bus.execute(SaveItemCommand(
            item_id=self.current_selected_id,
            new_title=title,
            new_description=desc,
            new_products=products,
            new_capabilities=capabilities,
            weight=weight,
            status=status,
            assignee_id=assignee_id
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
        
        # Determine assignee_id from name
        assignee_name = self.assignee_combo.get()
        assignee_id = None
        if assignee_name and assignee_name != "Unassigned":
            member = next((m for m in self.workspace.get_members() if m.name == assignee_name), None)
            if member:
                assignee_id = member.id

        self.dispatcher.dispatch(UICreateItemRequestedEvent(
            parent_id=self.current_selected_id,
            item_type=item_type,
            title=title,
            description=desc,
            products=products,
            capabilities=capabilities,
            weight=weight,
            status=status,
            assignee_id=assignee_id
        ))

    def set_assignee_list(self, names):
        """Updates the master assignee list and the combobox values."""
        self._master_assignee_list = names
        self.assignee_combo.config(values=names)

    def _on_assignee_key_release(self, event):
        """Filters the assignee list based on user input and posts the dropdown."""
        # Bypass navigation keys
        if event.keysym in ("Up", "Down", "Left", "Right", "Return", "Escape", "Tab", "Shift_L", "Shift_R"):
            return

        typed_text = self.assignee_combo.get().lower()
        if not typed_text:
            filtered_values = self._master_assignee_list
        else:
            filtered_values = [name for name in self._master_assignee_list if typed_text in name.lower()]

        self.assignee_combo["values"] = filtered_values
        
        # Open the dropdown programmatically
        try:
            self.assignee_combo.tk.call(self.assignee_combo._w, "post")
        except tk.TclError:
            pass # Widget might have been destroyed or not yet mapped

    def _on_assignee_focus_out(self, event):
        """Triggers auto-save when focus leaves the assignee combobox."""
        self._trigger_auto_save()

    def populate_editor(self, event: ModelActiveItemChangedEvent):
        """Populates the fields when a model item becomes active."""
        self._is_populating = True
        try:
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
            desc = getattr(event.item_data, 'description', '')
            self.text_desc.insert("1.0", desc if desc is not None else "")

            # Fetch Global Settings for Tags
            settings = self.settings._settings
            master_products = sorted(settings.get('product_mappings', {}).keys())
            master_capabilities = sorted(settings.get('capabilities', []))
            
            assigned_products = getattr(event.item_data, 'products', [])
            assigned_capabilities = getattr(event.item_data, 'capabilities', [])

            self._populate_dual_listbox(self.product_ui, master_products, assigned_products)
            self._populate_dual_listbox(self.capability_ui, master_capabilities, assigned_capabilities)
            
            # Populate Labels
            assigned_labels = getattr(event.item_data, 'labels', [])
            reserved_labels = {'Epic', 'Feature', 'Story'}
            master_labels_formatted = [
                f"({l.scope_name}) {l.name}" 
                for l in self.workspace.labels.values()
                if l.name not in reserved_labels
            ]
            self.label_ui['master'].delete(0, tk.END)
            for l_str in sorted(master_labels_formatted):
                self.label_ui['master'].insert(tk.END, l_str)
            
            self.label_ui['assigned'].delete(0, tk.END)
            for l_name in sorted(assigned_labels):
                if l_name not in reserved_labels:
                    label_obj = self.workspace.labels.get(l_name)
                    if label_obj:
                        display_name = f"({label_obj.scope_name}) {label_obj.name}"
                    else:
                        display_name = l_name
                    self.label_ui['assigned'].insert(tk.END, display_name)

            # Reset scroll position to top when switching items
            self.canvas.yview_moveto(0)
        finally:
            self._is_populating = False

    def _populate_dual_listbox(self, ui_dict, master_list, assigned_list):
        """Populates the master and assigned listboxes."""
        ui_dict['master'].delete(0, tk.END)
        ui_dict['assigned'].delete(0, tk.END)
        
        for item in sorted(assigned_list):
            ui_dict['assigned'].insert(tk.END, item)
            
        for item in sorted(master_list):
            ui_dict['master'].insert(tk.END, item)
