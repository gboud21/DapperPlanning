# Feature Domain: Agile Planning

## Responsibility
Manages the core Agile lifecycle, including the hierarchical structure of work items and their detailed editing.

## Business Hierarchy
The model follows a strict parent-child relationship:
- **Epic**: Root containers. Can contain multiple Features.
- **Feature**: Mid-level containers. Can contain multiple Stories. Weight and Status are dynamically calculated from child Stories.
- **Story**: Leaf nodes where actual work and weights are defined.

**Capabilities and Products** are handled as list of string tags across all entities.

## UI Interactions
- **TreePane**: Visualizes the hierarchy. Dispatches `UIItemSelectedEvent` when an item is clicked.
- **EditorPane**: Provides form-based editing. Uses **Auto-Save** logic (debounced for text area, immediate for others) to dispatch `UIItemSaveRequestedEvent`.
- **TreeController / EditorController**: Handle model mutations and ensure `Workspace` is updated correctly.

## Workspace Model
`src.features.agile_planning.workspace.Workspace` manages the state of the current project, including "Unsaved Changes" tracking via JSON snapshots.

## Domain Rules
- All status/weight roll-ups for Epics and Features must be implemented as properties in `entities.py`.
- No direct manipulation of the `_epics` list outside of the `Workspace` class.
