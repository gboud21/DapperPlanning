# Core Architecture
This is an event-driven MVC Tkinter application utilizing Vertical Slicing and a Shared Domain. Components communicate strictly through the `EventDispatcher` in `src/core/events.py`.

## Implementation Blueprint Patterns

### 1. Standard Event (src/core/events.py)
```python
@dataclass
class UIFeatureActionRequestedEvent(Event):
    """Description of the event trigger."""
    item_id: str
    payload: Dict[str, Any]
```

### 2. Thread-Safe View Dispatching (src/features/...)
```python
class FeaturePane:
    def __init__(self, parent, dispatcher):
        self.dispatcher = dispatcher
        self.btn = ttk.Button(parent, text="Do Action", command=self._on_click)
        self.btn.pack()

    def _on_click(self):
        # UI logic only, never mutate state here
        self.dispatcher.dispatch(UIFeatureActionRequestedEvent(item_id="123", payload={}))

    def update_view(self, event: ModelUpdateEvent):
        # Update UI components safely
        self.btn.config(state='normal')
```

### 3. Decoupled Controller Subscription (src/features/...)
```python
class FeatureController:
    def __init__(self, context: AppContext):
        self.dispatcher = context.resolve('event_dispatcher')
        self.workspace = context.resolve('workspace')
        self.dispatcher.subscribe(UIFeatureActionRequestedEvent, self.handle_action)

    def handle_action(self, event: UIFeatureActionRequestedEvent):
        # Business logic and model mutation
        self.workspace.mutate_something(event.item_id)
        # Always notify system of changes
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(...))
```

## Architectural Rules
- **View**: Dispatches `UI...RequestedEvent`s. Subscribes to `Model...Event`s to update display.
- **Controller**: Subscribes to `UI...RequestedEvent`s. Resolves dependencies via `AppContext`. Mutates the `Workspace` model.
- **Domain**: Contains the core logic and models (`Epic`, `Feature`, `Story`). `Workspace` (in `src/domain/workspace.py`) manages the tree.
- **Infrastructure**: Handles external boundaries (GitLab API, File I/O).

## Global UI Rules
- **Widget States**: Control access and interaction via `widget.config(state='disabled'|'normal')`. Avoid `pack_forget()` or `destroy()` for permanent UI elements unless clearing a dynamic list.
- **Thread Bridges**: Background workers must use `self.dispatcher.dispatch(Event)` to communicate back to the UI. The `EventDispatcher` ensures execution on the main thread via `.after()`.
- **Validation**: Perform basic input validation in the View (regex, type checks) before dispatching the request.

## Key Events
Refer to `src/core/events.py` for full definitions.
- **UI Interaction**: `UIItemSelectedEvent`, `UIItemSaveRequestedEvent`, `UIDeleteItemRequestedEvent`, `UIAdd...RequestedEvent`.
- **Workspace Management**: `UIOpenWorkspaceRequestedEvent`, `UISaveWorkspaceRequestedEvent`, `UISaveAsWorkspaceRequestedEvent`.
- **Model Updates**: `ModelHierarchyUpdatedEvent`, `ModelActiveItemChangedEvent`, `ModelWorkspaceLoadedEvent`.
- **System**: `UIErrorNotificationEvent`, `AppThemeChangedEvent`, `UIWindowStateChangedEvent`.
