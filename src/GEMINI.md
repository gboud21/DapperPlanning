# Core Architecture
This is an event-driven MVC Tkinter application utilizing Vertical Slicing and a Shared Domain. Components communicate strictly through the `EventDispatcher` in `src/core/events.py`.

## Architectural Rules
- **View**: Dispatches `UI...RequestedEvent`s. Subscribes to `Model...Event`s to update display.
- **Controller**: Subscribes to `UI...RequestedEvent`s. Resolves dependencies via `AppContext`. Mutates the `Workspace` model.
- **Domain**: Contains the core logic and models (`Epic`, `Feature`, `Story`). `Workspace` (in `src/domain/workspace.py`) manages the tree.
- **Infrastructure**: Handles external boundaries (GitLab API, File I/O).

## Key Events
Refer to `src/core/events.py` for full definitions.
- **UI Interaction**: `UIItemSelectedEvent`, `UIItemSaveRequestedEvent`, `UIDeleteItemRequestedEvent`, `UIAdd...RequestedEvent`.
- **Workspace Management**: `UIOpenWorkspaceRequestedEvent`, `UISaveWorkspaceRequestedEvent`, `UISaveAsWorkspaceRequestedEvent`.
- **Model Updates**: `ModelHierarchyUpdatedEvent`, `ModelActiveItemChangedEvent`, `ModelWorkspaceLoadedEvent`.
- **System**: `UIErrorNotificationEvent`, `AppThemeChangedEvent`, `UIWindowStateChangedEvent`.
