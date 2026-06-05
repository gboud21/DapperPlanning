# LOCAL CONTEXT: TKINTER AGILE UI
- **Library:** Strict `tkinter` and `ttk`. No external UI libraries.
- **Tree IDs:** The TreeView uses generated UUIDs as `iid` strings to prevent duplication crashes. You must map these back to Domain objects via the Workspace.
- **Dynamic State:** UI elements (like Edit/Clone menu items) must be dynamically disabled via Controller state tracking if `current_selected_id` is None.
- **Deep Cloning:** Domain clones must strip `gitlab_id` and `gitlab_iid` completely so the integration engine treats them as POST creations, not PUT updates.
