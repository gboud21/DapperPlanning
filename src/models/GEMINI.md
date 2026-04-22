# Model Guidelines
- Entities (`Team`, `Capability`, `Epic`, `Feature`, `Story`) are strictly defined as `dataclasses`.
- The `Workspace` class manages state. State mutations must trigger a `ModelHierarchyUpdatedEvent` via the dispatcher.
- Do not import `tkinter` or `services` here.