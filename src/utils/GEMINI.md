# Utility Guidelines
- **Adapters** (`src/utils/adapters.py`): Handle physical I/O (CSV, JSON). Use `DataAdapterFactory` to retrieve the correct adapter.
- **Transformers** (`src/utils/transformers.py`): Handle logic for converting between flat and nested data structures. 
- **ThemeManager** (`src/utils/theme_manager.py`): Manages application settings and visual styles. Do not add business logic here.
