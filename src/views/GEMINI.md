# View Guidelines
- Use `ttk` for all Tkinter widgets.
- Views MUST NOT import or mutate Models directly.
- To request data changes or actions, dispatch events (e.g., `UIItemSaveRequestedEvent`, `UISyncRequestedEvent`).
- Subscribe to `ModelHierarchyUpdatedEvent` and `ModelActiveItemChangedEvent` for UI updates.