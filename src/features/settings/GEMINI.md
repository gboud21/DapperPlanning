# Feature Domain: Application Settings

## Responsibility
Manages application-wide preferences, visual themes, and editor templates.

## Key Components
- **SettingsDialog**: The UI for managing theme, logging, and templates.
- **SettingsController**: Orchestrates saving settings and dispatching `AppThemeChangedEvent`.
- **ThemeManager (Util)**: The underlying engine that persists settings to `settings.json` and applies `ttk.Style` configurations.

## Persistence
Settings are stored in the user data directory. The `SettingsController` ensures that any changes to critical parameters (like `target_tool` or `methodology`) are immediately available to the `TemplateGenerator` in other slices via `ThemeManager.get_general_settings()`.

## Rules
- When adding new settings, update `ThemeManager.get_default_settings()`.
- UI styles for high-contrast elements must use the `Preferences.TCombobox` style for black-text readability.

## Sub-Agent Instructions & Testing
- **Local Hard Stops**:
  - Keep configuration logic isolated from domain data. Do not import `src.domain` in settings UI or controller files.
- **Testing Targets**:
  - Update or write tests in `tests/ui/test_settings_controller.py` BEFORE changing settings dialog or controller code.
