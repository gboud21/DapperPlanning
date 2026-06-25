# LOCAL CONTEXT: TKINTER AGILE UI

## Responsibility
Manages the desktop UI elements, tree view lists, and interactive story editor components for Agile/Backlog planning.

## Key Rules
- **Library:** Strict `tkinter` and `ttk`. No external UI libraries.
- **Tree IDs:** The TreeView uses generated UUIDs as `iid` strings to prevent duplication crashes. You must map these back to Domain objects via the Workspace.
- **Dynamic State:** UI elements (like Edit/Clone menu items) must be dynamically disabled via Controller state tracking if `current_selected_id` is None.
- **Deep Cloning:** Domain clones must strip `gitlab_id` and `gitlab_iid` completely so the integration engine treats them as POST creations, not PUT updates.

## Sub-Agent Instructions & Testing
- **Local Hard Stops**:
  - Panes and UI elements (like `editor_pane.py` or `tree_pane.py`) MUST NOT import or instantiate `src.domain` entities directly.
  - All state mutations must be dispatched via commands.
- **Testing Targets**:
  - Update or write tests under `tests/ui/` or `tests/unit/features/` BEFORE modifying implementation logic in this directory.
