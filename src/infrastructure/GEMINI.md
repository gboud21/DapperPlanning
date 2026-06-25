# Infrastructure Layer

## Responsibility
External infrastructure clients, API adapters, and physical data storage persistence.

## Components
### API (`src/infrastructure/api/`)
- **GitLabClient (`gitlab_client.py`)**: Handles communication with the GitLab API for creating Epics and Stories.

### Storage (`src/infrastructure/storage/`)
- **Adapters (`adapters.py`)**: Handles physical file I/O for JSON and CSV.
- **Transformers (`transformers.py`)**: Logic for converting between nested object hierarchies and flat dictionary structures.

## Design Patterns
- Infrastructure services remain decoupled from the Core and Feature layers.
- They map local Domain entities (`Epic`, `Story`) to external JSON structures or flat storage formats.
- All network operations must be considered potentially blocking; use the `EventDispatcher` to handle completion or errors in a thread-safe manner.

## Sub-Agent Instructions & Testing
- **Local Hard Stops**:
  - Infrastructure modules must never import Tkinter/UI files or trigger direct UI methods.
  - Do not introduce UI-dependencies inside API clients or file adapters.
- **Testing Targets**:
  - Update or write unit/integration tests under `tests/unit/infrastructure/` BEFORE modifying file reading, transforming, or API client code.
