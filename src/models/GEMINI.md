# Model Guidelines
- Entities (`Team`, `Epic`, `Feature`, `Story`) are strictly defined as `dataclasses`.
- `Epic`, `Feature`, and `Story` each contain `products` and `capabilities` as lists of string tags.
- The `Workspace` class manages state. State mutations must trigger a `ModelHierarchyUpdatedEvent` via the dispatcher.
- Do not import `tkinter` or `services` here.
