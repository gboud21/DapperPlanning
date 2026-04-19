import tkinter as tk
from tkinter import ttk, messagebox
from typing import List
from models import Team, Capability
from gitlab_client import GitLabClient

class PlanningToolApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Standardized Backlog Planning Tool")
        self.geometry("1000x700")
        
        # In-memory data store
        self.teams: List[Team] = []
        self.capabilities: List[Capability] = []
        
        self.setup_ui()

    def setup_ui(self):
        # PanedWindow for resizable left/right sections
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # LEFT PANE: Hierarchy Treeview
        self.left_frame = ttk.Frame(self.paned_window, width=300)
        self.tree = ttk.Treeview(self.left_frame)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.paned_window.add(self.left_frame, weight=1)

        # RIGHT PANE: Contextual Editor Form
        self.right_frame = ttk.Frame(self.paned_window, width=700)
        self.paned_window.add(self.right_frame, weight=3)
        self.setup_editor_form()

        # BOTTOM BAR: Actions
        self.bottom_frame = ttk.Frame(self)
        self.bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        self.btn_sync = ttk.Button(self.bottom_frame, text="Sync to GitLab", command=self.sync_to_gitlab)
        self.btn_sync.pack(side=tk.RIGHT)
        
        self.lbl_status = ttk.Label(self.bottom_frame, text="Ready.")
        self.lbl_status.pack(side=tk.LEFT)

    def setup_editor_form(self):
        """Initializes the dynamically updating input fields on the right pane."""
        self.lbl_editor_title = ttk.Label(self.right_frame, text="Select an item to edit", font=("Arial", 14, "bold"))
        self.lbl_editor_title.pack(anchor=tk.W, pady=(0, 10))

        # Title Field
        ttk.Label(self.right_frame, text="Title:").pack(anchor=tk.W)
        self.entry_title = ttk.Entry(self.right_frame, width=50)
        self.entry_title.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))

        # Description Field
        ttk.Label(self.right_frame, text="Description:").pack(anchor=tk.W)
        self.text_desc = tk.Text(self.right_frame, height=10, width=50)
        self.text_desc.pack(anchor=tk.W, fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Save Button
        self.btn_save_item = ttk.Button(self.right_frame, text="Save Item Data")
        self.btn_save_item.pack(anchor=tk.E)

    def on_tree_select(self, event):
        """Handles populating the right pane based on Treeview selection."""
        pass

    def sync_to_gitlab(self):
        """Iterates through the hierarchy and pushes to GitLab."""
        client = GitLabClient("https://gitlab.com", "YOUR_TOKEN", "GROUP_ID", "PROJECT_ID")
        
        self.lbl_status.config(text="Syncing to GitLab...")
        self.update_idletasks()
        
        try:
            for cap in self.capabilities:
                for epic in cap.epics:
                    epic_iid = client.create_epic(epic, is_feature=False)
                    for feature in epic.features:
                        feature_iid = client.create_epic(feature, is_feature=True, parent_id=epic_iid)
                        for story in feature.stories:
                            client.create_story(story, epic_iid=feature_iid)
            
            self.lbl_status.config(text="Sync Complete!")
            messagebox.showinfo("Success", "Successfully pushed backlog to GitLab.")
        except Exception as e:
            self.lbl_status.config(text="Sync Failed.")
            messagebox.showerror("Error", f"Failed to sync to GitLab: {e}")

if __name__ == "__main__":
    app = PlanningToolApp()
    app.mainloop()
