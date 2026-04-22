# Service Guidelines
- Services (like `GitLabClient`) handle external HTTP requests.
- Parse JSON payloads directly into the dataclasses defined in `src/models/entities.py`.