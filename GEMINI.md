# DapperPlanning - System Architecture

## Architectural Pattern: Vertical Slice (Package by Feature)
This application follows a strict Vertical Slice Architecture. All components related to a specific business domain (Models, Views, Controllers) are consolidated within the same feature directory in `src/features/`.

## Code Generation Dependency Order
When extending the application or adding new features, follow this sequential order to ensure architectural integrity:
1. **Domain Models**: Define or update entities in `src/domain/entities.py` and workspace logic in `src/domain/workspace.py`.
2. **Core Events**: Define new `UI...RequestedEvent` or `Model...Event` classes in `src/core/events.py`.
3. **Infrastructure**: Implement required API clients, adapters, or storage transformers in `src/infrastructure/`.
4. **Feature Slice**: Create the feature directory in `src/features/` containing the `View/Pane` and `Controller`.
5. **App Injection**: Register the new controller and wire the UI components in `src/core/main_window.py` and `src/main.py`.

## Absolute Guardrails
- **Feature Isolation**: Features MUST NEVER directly import views or controllers from other features. Communication is strictly via the `EventDispatcher`.
- **Non-Blocking UI**: NEVER run synchronous blocking calls (I/O, API, heavy computation) directly inside Tkinter event handlers. Use worker threads and dispatch updates back to the UI thread.
- **Unidirectional Data Flow**: UI Views/Panes MUST NEVER mutate domain entities or the `Workspace` directly. They only dispatch `UI...RequestedEvent`s.
- **State Management**: Use `widget.config(state='disabled')` for Role-Based Access Control or state-dependent UI instead of destroying and recreating elements.

## Core Mandates
1. **MVC Separation**:
   - **View**: Only dispatches UI events and subscribes to model update events. 
   - **Controller**: Subscribes to UI events, resolves dependencies via `AppContext`, and performs business logic or model mutations.
   - **Model**: Represents the domain state (Entities and Workspace).
2. **Thread Safety**: Any background operations that require UI updates must use `dispatcher.dispatch()`, which is bridged to the main thread via `root.after()`.
3. **Data Integrity**: State mutations must always trigger a `ModelHierarchyUpdatedEvent` to ensure the UI remains synchronized with the model.
