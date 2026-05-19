# Controller Guidelines
- Controllers manage the interaction between the View and the Model.
- They must subscribe to `UI` events (from `src.events`) and perform business logic or mutate the `Workspace`.
- Only Controllers should directly call mutation methods on the `Workspace` model.
- Use `UIErrorNotificationEvent` to report errors back to the View.
- Sub-controllers should be instantiated and managed by `MainController`.
