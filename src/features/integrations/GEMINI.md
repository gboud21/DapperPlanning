# Feature Domain: External Integrations

## Responsibility
Manages authentication credentials and project mapping configurations for external services (e.g., GitLab).

## Key Components
- **IntegrationsDialog**: UI for managing Host URL, PAT, and Product/Capability mappings.
- **IntegrationsController**: Persists integration-specific secrets and settings via `ThemeManager`.

## Data Mapping
The `integrations` slice is responsible for maintaining the master lists of `Products` and `Capabilities` that populate the listboxes in the `Agile Planning` editor.

## Security
- PATs (Personal Access Tokens) must be handled as sensitive.
- Never log or display plain-text tokens in the UI after initial entry.
