# Core Architecture
This is an event-driven MVC Tkinter application. Components communicate strictly through the `EventDispatcher` in `src/events.py`.

## Architectural Rules
- **View**: Dispatches `UI...RequestedEvent`s. Subscribes to `Model...Event`s to update display.
- **Controller**: Subscribes to `UI...RequestedEvent`s. Mutates the `Workspace` model. Dispatches `Model...Event`s if needed (though `Workspace` often does this).
- **Model**: `Workspace` (in `src/models/workspace.py`) manages the tree of `Epic` -> `Feature` -> `Story`.

## Key Events
Refer to `src/events.py` for full definitions.
- **UI Interaction**: `UIItemSelectedEvent`, `UIItemSaveRequestedEvent`, `UIDeleteItemRequestedEvent`, `UIAdd...RequestedEvent`.
- **Workspace Management**: `UIOpenWorkspaceRequestedEvent`, `UISaveWorkspaceRequestedEvent`, `UISaveAsWorkspaceRequestedEvent`.
- **Model Updates**: `ModelHierarchyUpdatedEvent`, `ModelActiveItemChangedEvent`, `ModelWorkspaceLoadedEvent`.
- **System**: `UIErrorNotificationEvent`, `AppThemeChangedEvent`, `UIWindowStateChangedEvent`.
