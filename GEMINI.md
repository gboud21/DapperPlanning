# DapperPlanning - System Architecture

## Architectural Pattern: Vertical Slice (Package by Feature)
This application follows a strict Vertical Slice Architecture. All components related to a specific business domain (Models, Views, Controllers) are consolidated within the same feature directory in `src/features/`.

## Core Mandates
1. **Feature Isolation**: Features must never directly import components from other features. Communication between features must occur exclusively through the global `EventDispatcher` in `src.core.events`.
2. **MVC Separation**:
   - **View**: Only dispatches UI events and subscribes to model update events. Never mutates the Workspace or Entities directly.
   - **Controller**: Subscribes to UI events and performs business logic or model mutations.
   - **Model**: Represents the domain state (Entities and Workspace).
3. **Thread Safety**: Any background operations (e.g., API calls) that require UI updates must use the Tkinter-safe `dispatcher.dispatch()` method, which ensures execution on the main thread via `.after()`.
4. **Data Integrity**: State mutations must always trigger a `ModelHierarchyUpdatedEvent` via the dispatcher to ensure the UI remains synchronized with the model.
