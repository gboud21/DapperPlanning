import tkinter as tk
from tkinter import ttk
import webbrowser
from src.utils.theme_manager import ThemeManager

class _ThemedText(tk.Text):
    """Custom tk.Text supporting disabledbackground and disabledforeground options without TclError."""
    def __init__(self, *args, **kwargs):
        self._custom_opts = {}
        super().__init__(*args, **kwargs)

    def configure(self, cnf=None, **kw):
        if cnf and isinstance(cnf, dict):
            cnf = dict(cnf)
            for k in ('disabledbackground', 'disabledforeground'):
                if k in cnf:
                    self._custom_opts[k] = cnf.pop(k)
        for k in ('disabledbackground', 'disabledforeground'):
            if k in kw:
                self._custom_opts[k] = kw.pop(k)
        return super().configure(cnf, **kw)

    config = configure

    def cget(self, key):
        if key in self._custom_opts:
            return self._custom_opts[key]
        return super().cget(key)

    def __getitem__(self, key):
        return self.cget(key)


class DryPushSummaryModal(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Tk,
        creations: int,
        updates: int,
        conflicts: int,
        deletions: int,
        report_path: str,
        creations_list: list = None,
        updates_list: list = None,
        conflicts_list: list = None,
        deletions_list: list = None
    ):
        """
        Initializes the DryPushSummaryModal.

        Args:
            parent (tk.Tk): The root window.
            creations (int): Count of items to be created on remote.
            updates (int): Count of items to be updated on remote.
            conflicts (int): Count of items in conflict.
            deletions (int): Count of items to be deleted on remote.
            report_path (str): Filepath to the generated markdown report.
            creations_list (list): List of created items.
            updates_list (list): List of updated items.
            conflicts_list (list): List of conflicted items.
            deletions_list (list): List of deleted items.
        """
        super().__init__(parent)
        self.title("GitLab Dry-Push Summary")
        self.geometry("600x720")
        self.minsize(550, 650)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.creations = creations
        self.updates = updates
        self.conflicts = conflicts
        self.deletions = deletions
        self.report_path = report_path

        self.creations_list = creations_list if creations_list is not None else []
        self.updates_list = updates_list if updates_list is not None else []
        self.conflicts_list = conflicts_list if conflicts_list is not None else []
        self.deletions_list = deletions_list if deletions_list is not None else []
        
        self.is_dark = ThemeManager.load_settings()
        
        self._setup_ui()
        self._apply_theme()

    def geometry(self, newGeometry=None):
        if newGeometry is not None:
            self._requested_geometry = newGeometry
            return super().geometry(newGeometry)
        return getattr(self, '_requested_geometry', super().geometry())

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Buttons (packed at bottom FIRST to stay visible when content expands)
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.open_btn = ttk.Button(btn_frame, text="Open Report", command=self._open_report)
        self.open_btn.pack(side=tk.LEFT)

        self.close_btn = ttk.Button(btn_frame, text="Close", command=self.destroy)
        self.close_btn.pack(side=tk.RIGHT)

        # Report Path section (packed at bottom SECOND, above buttons)
        report_frame = ttk.Frame(main_frame)
        report_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 15))

        path_lbl = ttk.Label(report_frame, text="Report Path:", font=("TkDefaultFont", 9, "bold"))
        path_lbl.pack(anchor=tk.W)

        self.path_entry = tk.Entry(report_frame, font=("TkFixedFont", 9))
        self.path_entry.insert(0, self.report_path)
        self.path_entry.config(state="readonly")
        self.path_entry.pack(fill=tk.X, pady=(2, 0))

        # Status alert banner (packed at top)
        if self.conflicts > 0:
            status_bg = "#5c0000" if self.is_dark else "#f8d7da"
            status_fg = "#ffffff" if self.is_dark else "#721c24"
            status_title = "⚠ CONFLICTS DETECTED"
            status_desc = "Push will be blocked. Please resolve conflicts."
        else:
            status_bg = "#004d00" if self.is_dark else "#d4edda"
            status_fg = "#ffffff" if self.is_dark else "#155724"
            status_title = "✔ DRY-RUN SUCCESSFUL"
            status_desc = "No conflicts detected. Changes ready to push."

        self.status_frame = tk.Frame(main_frame, bg=status_bg, padx=10, pady=10, borderwidth=1, relief="solid")
        self.status_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 15))

        self.status_lbl = tk.Label(self.status_frame, text=status_title, font=("TkDefaultFont", 11, "bold"), bg=status_bg, fg=status_fg)
        self.status_lbl.pack(anchor=tk.W)

        self.status_desc_lbl = tk.Label(self.status_frame, text=status_desc, font=("TkDefaultFont", 9), bg=status_bg, fg=status_fg, wraplength=480, justify=tk.LEFT)
        self.status_desc_lbl.pack(anchor=tk.W, pady=(2, 0))

        # Counts Section (packed at top)
        counts_frame = ttk.LabelFrame(main_frame, text="Summary of Changes", padding=10)
        counts_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 15))

        # Align counts in a grid
        for i, (label_text, val) in enumerate([
            ("Creations:", self.creations),
            ("Updates:", self.updates),
            ("Conflicts:", self.conflicts),
            ("Deletions:", self.deletions)
        ]):
            lbl = ttk.Label(counts_frame, text=label_text, font=("TkDefaultFont", 10, "bold"))
            lbl.grid(row=i, column=0, sticky=tk.W, padx=5, pady=3)
            
            fg_color = ""
            if label_text == "Conflicts:" and self.conflicts > 0:
                fg_color = "#d9534f" if not self.is_dark else "#ff6b6b"
                
            kwargs = {}
            if fg_color:
                kwargs["fg"] = fg_color
            val_lbl = tk.Label(counts_frame, text=str(val), font=("TkDefaultFont", 10), **kwargs)
            val_lbl.grid(row=i, column=1, sticky=tk.W, padx=5, pady=3)
            
            if label_text == "Conflicts:":
                self.conflicts_val_lbl = val_lbl
            elif label_text == "Creations:":
                self.creations_val_lbl = val_lbl
            elif label_text == "Updates:":
                self.updates_val_lbl = val_lbl
            elif label_text == "Deletions:":
                self.deletions_val_lbl = val_lbl

        # Details Pane (expands cleanly in the middle)
        details_frame = ttk.LabelFrame(main_frame, text="Object Details", padding=10)
        details_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 15))

        self.details_text = _ThemedText(details_frame, height=6, wrap=tk.WORD, font=("TkFixedFont", 9))
        details_scroll = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=details_scroll.set)

        details_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        lines = []
        
        lines.append(f"=== Creations ({len(self.creations_list)}) ===")
        if self.creations_list:
            for item in self.creations_list:
                lines.append(self._format_item(item))
        else:
            lines.append("  (None)")
        lines.append("")

        lines.append(f"=== Updates ({len(self.updates_list)}) ===")
        if self.updates_list:
            for item in self.updates_list:
                lines.append(self._format_item(item))
        else:
            lines.append("  (None)")
        lines.append("")

        lines.append(f"=== Conflicts ({len(self.conflicts_list)}) ===")
        if self.conflicts_list:
            for item in self.conflicts_list:
                lines.append(self._format_item(item))
        else:
            lines.append("  (None)")
        lines.append("")

        lines.append(f"=== Deletions ({len(self.deletions_list)}) ===")
        if self.deletions_list:
            for item in self.deletions_list:
                lines.append(self._format_item(item))
        else:
            lines.append("  (None)")

        self.details_text.insert("1.0", "\n".join(lines))
        self.details_text.config(state=tk.DISABLED)

    def _format_item(self, item) -> str:
        if isinstance(item, dict):
            item_type = item.get('type', 'Item').capitalize()
            iid = item.get('iid', 'N/A')
            gid = item.get('id', 'N/A')
            return f"  - {item_type}: (GitLab IID: {iid}, GitLab ID: {gid})"
        else:
            cls_name = item.__class__.__name__
            title = getattr(item, 'title', str(item))
            item_id = getattr(item, 'id', 'N/A')
            return f"  - {cls_name}: {title} (ID: {item_id})"

    def _open_report(self):
        webbrowser.open(self.report_path)

    def _apply_theme(self):
        palette = ThemeManager.DARK_PALETTE if self.is_dark else ThemeManager.LIGHT_PALETTE
        bg_color = palette['bg']
        field_bg = palette['field_bg']
        fg_color = palette['fg']
        highlight = palette['highlight']

        self.configure(bg=bg_color)
        
        self.path_entry.configure(
            bg=field_bg,
            fg=fg_color,
            disabledbackground=field_bg,
            disabledforeground=fg_color,
            readonlybackground=field_bg,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=highlight,
            insertbackground='white' if self.is_dark else 'black'
        )

        if hasattr(self, 'details_text'):
            self.details_text.configure(
                bg=field_bg,
                fg=fg_color,
                disabledbackground=field_bg,
                disabledforeground=fg_color,
                borderwidth=0,
                highlightthickness=1,
                highlightbackground=highlight,
                insertbackground='white' if self.is_dark else 'black'
            )
        
        # Update any custom label backgrounds
        for lbl in [self.creations_val_lbl, self.updates_val_lbl, self.conflicts_val_lbl, self.deletions_val_lbl]:
            lbl.configure(bg=bg_color)
            if lbl != self.conflicts_val_lbl or self.conflicts == 0:
                lbl.configure(fg=fg_color)
