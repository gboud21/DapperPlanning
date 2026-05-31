# External Services

## Responsibility
External infrastructure clients and third-party API adapters.

## Available Services
- **GitLabClient (`gitlab_client.py`)**: Handles communication with the GitLab API for creating Epics and Stories. 

## Design Patterns
- Services use standard `urllib.request` to remain lightweight.
- They map local entities (`Epic`, `Story`) to GitLab-specific JSON structures.
- All network operations must be considered potentially blocking; use the `EventDispatcher` to handle completion or errors in a thread-safe manner.
