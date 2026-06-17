import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
from src.utils.ai_utils import convert_hours_to_fibonacci_weight

class AIEstimationDialog(tk.Toplevel):
    def __init__(self, parent, context, item_id, initial_history: list):
        super().__init__(parent)
        self.context = context
        self.item_id = item_id
        self.llm_client = context.resolve('generic_llm_client')
        self.history = initial_history # Caches the multi-turn conversational history tokens array
        
        self.title("AI Effort Estimation Assistant")
        self.geometry("650x550")
        self.transient(parent)
        self.grab_set()
        
        self.estimated_hours = 0.0
        self.suggested_points = 0
        
        self._setup_ui()
        self._apply_theme()
        self._request_ai_estimation()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Reasoning Area Text Area Row Block
        ttk.Label(main_frame, text="AI Qualitative Analysis & Reasoning:", font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W)
        self.txt_reasoning = tk.Text(main_frame, height=15, wrap=tk.WORD, font=("Courier New", 10))
        self.txt_reasoning.pack(fill=tk.BOTH, expand=True, pady=(5, 15))
        
        # 2. Iterative Feedback Input Box Frame Lane
        ttk.Label(main_frame, text="Provide Additional Context Feedback:", font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W)
        self.entry_feedback = ttk.Entry(main_frame)
        self.entry_feedback.pack(fill=tk.X, pady=5)
        self.entry_feedback.bind("<Return>", lambda e: self._on_resubmit())
        
        # 3. Action Buttons Row Control Layout Bar Split
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="Resubmit Context", command=self._on_resubmit).pack(side=tk.LEFT)
        
        self.btn_accept = ttk.Button(btn_frame, text="Accept Estimate (points)", style="Accent.TButton", command=self._on_accept)
        self.btn_accept.pack(side=tk.RIGHT, padx=5)
        self.btn_accept.config(state="disabled")
        
        ttk.Button(btn_frame, text="Reject", command=self.destroy).pack(side=tk.RIGHT)

    def _apply_theme(self):
        from src.utils.theme_manager import ThemeManager
        is_dark = ThemeManager.load_settings()
        palette = ThemeManager.DARK_PALETTE if is_dark else ThemeManager.LIGHT_PALETTE
        self.configure(bg=palette['bg'])
        
        cursor_color = 'white' if is_dark else 'black'
        self.txt_reasoning.configure(
            bg=palette['field_bg'],
            fg=palette['fg'],
            insertbackground=cursor_color,
            padx=10,
            pady=10,
            borderwidth=0
        )

    def _request_ai_estimation(self):
        """Passes history arrays down to the REST client and updates the UI."""
        self.txt_reasoning.config(state="normal")
        self.txt_reasoning.delete("1.0", tk.END)
        self.txt_reasoning.insert(tk.END, "Consulting the Oracle... please wait.")
        self.txt_reasoning.config(state="disabled")
        self.update()
        
        # Call LLM client
        response = self.llm_client.send_chat_turn(self.history)
        
        # Update history with model response for multi-turn
        self.history.append({"role": "model", "parts": [{"text": json.dumps(response)}]})
        
        # Update UI
        self.txt_reasoning.config(state="normal")
        self.txt_reasoning.delete("1.0", tk.END)
        self.txt_reasoning.insert(tk.END, response.get('reasoning', 'No reasoning provided.'))
        self.txt_reasoning.config(state="disabled")
        
        self.estimated_hours = float(response.get('estimated_hours', 0.0))
        self.suggested_points = convert_hours_to_fibonacci_weight(self.estimated_hours)
        
        self.btn_accept.config(text=f"Accept Estimate ({self.suggested_points} points)", state="normal")

    def _on_resubmit(self):
        feedback = self.entry_feedback.get().strip()
        if not feedback:
            return
            
        self.history.append({"role": "user", "parts": [{"text": feedback}]})
        self.entry_feedback.delete(0, tk.END)
        self._request_ai_estimation()

    def _on_accept(self):
        """Applies the calculated weight directly to the active story field."""
        # Find the EditorPane and update its weight entry
        # Alternatively, dispatch an event or use the Resolve mechanism
        # For simplicity in this vertical slice, we'll try to find the editor pane or use the command bus
        
        # Actually, let's use the command bus to save the item directly
        workspace = self.context.resolve('workspace')
        item = workspace._find_item_by_id(self.item_id)
        
        if item:
            from src.core.commands import SaveItemCommand
            command_bus = self.context.resolve('command_bus')
            
            # Keep existing attributes, only change weight
            command_bus.execute(SaveItemCommand(
                item_id=self.item_id,
                new_title=item.title,
                new_description=item.description,
                new_products=getattr(item, 'products', []),
                new_capabilities=getattr(item, 'capabilities', []),
                new_labels=getattr(item, 'labels', []),
                weight=float(self.suggested_points),
                status=getattr(item, 'status', 'Backlog'),
                assignee_id=getattr(item, 'assignee_id', None),
                iteration_id=getattr(item, 'iteration_id', None)
            ))
            
            # Also need to manually update the UI entry if it's currently showing
            # We can dispatch an event to trigger a refresh
            from src.core.events import ModelActiveItemChangedEvent
            item_type = type(item).__name__
            self.context.resolve('event_dispatcher').dispatch(
                ModelActiveItemChangedEvent(item_type=item_type, item_data=item)
            )

        self.destroy()
