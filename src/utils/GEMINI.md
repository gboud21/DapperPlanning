# Global Utilities

## Responsibility
Cross-cutting concerns and helper utilities available to all layers.

## Available Modules
- **Debouncer (`debouncer.py`)**: Handles delayed execution of callbacks (e.g., auto-save for text areas).
- **Scroll Bubbler (`ui_utils.py`)**: Forwards mouse wheel events from greedy widgets (Text, Listbox) to parent containers.
- **ThemeManager (`theme_manager.py`)**: Central authority for settings persistence and `ttk.Style` application.
- **TemplateGenerator (`template_generator.py`)**: Business logic for generating initial item descriptions based on settings.

## Rules
- Utilities must remain stateless or manage state strictly through `ThemeManager`.
- Do not add business logic for specific features or domain models here.
