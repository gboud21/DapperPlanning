# GLOBAL ARCHITECTURE: DAPPER PLANNING

- **Pattern:** Event-Driven MVC with CQRS (Command Bus + Event Dispatcher) and dependency injection via `AppContext`.
- **Golden Rule:** Views NEVER mutate Domain models directly. Controllers NEVER directly call View methods.
- **Dependency Strictness:** View/UI elements (e.g. Tkinter classes in `src/core/main_window.py` or feature panes) MUST NOT import or instantiate `src.domain` objects directly. All state mutations occur via command execution through the `CommandBus`.

## Architectural Context

1. **App Context (`src/core/app_context.py`):** Dependency Injection container housing global services (`event_dispatcher`, `command_bus`, `workspace`, `workspace_repository`, `settings_manager`, `gitlab_client`).
2. **Command Bus (`src/core/command_bus.py`):** Routes state-mutating actions (`SyncWithGitLabCommand`, `SaveWorkspaceCommand`, etc.) to registered handlers.
3. **Event Dispatcher (`src/core/events.py`):** Manages decoupled event communication:
   - Views subscribe to Model events (`ModelHierarchyUpdatedEvent`, `ModelConflictDetectedEvent`).
   - Controllers subscribe to UI events (`UISyncMembersRequestedEvent`, `UISaveWorkspaceRequestedEvent`) and dispatch commands.
4. **Git-like Merge & Shadow Baseline (`src/domain/workspace.py`):** `shadow_hierarchy` maintains an ancestor snapshot to detect bidirectional push/pull merge conflicts across core attributes and structural hierarchy reparenting.

---

## ARCHITECT-TO-WORKER DELEGATION PROTOCOL (Antigravity CLI)

When the Architect needs to implement a feature or bug fix, they MUST spawn a specialized `FeatureImplementer` sub-agent in `inherit` mode (allowing shared real-time changes).

### Handoff Template

When invoking `FeatureImplementer`, the Architect must structure the `Prompt` using this standardized template:

```text
[SUB-AGENT EXECUTION TEMPLATE]
1. Context: You are implementing feature/bug-fix: [Feature Name].
2. Workspace Mode: 'inherit' (working in the active workspace).
3. Read Local Context: Read `src/features/[feature_name]/GEMINI.md` before starting code changes.
4. TDD Requirement:
   - Identify or create test files in the `tests/` directory (e.g., `tests/unit/` or `tests/ui/`).
   - Write or update tests BEFORE making any changes to the corresponding logic in `src/`.
5. Architectural Boundaries (Hard Stops):
   - NEVER import `src.domain` directly inside View/UI classes.
   - All state modifications MUST go through command dispatch via the Command Bus (`command_bus.execute(command)`).
   - Controllers must not call UI components' internal methods directly.
6. Execution Plan & Tasks:
   [Step-by-step description of tasks mapped out by the Architect]
7. Verification:
   - Run `pytest` (or `cargo test` during Rust phase) to ensure all tests pass.
```

---

## UPCOMING PHASE: RUST MIGRATION GUIDELINES

The next development phase involves migrating the application core and UI from Python to **Rust**:

1. **Domain & CQRS Port:** Port pure domain entities (`Product`, `Capability`, `Epic`, `Feature`, `Story`) and CQRS Command/Event Bus patterns to idiomatic Rust (using `serde` for serialization and strongly typed channels/event buses).
2. **TDD Continuity:** Maintain strict TDD by writing Rust unit/integration tests (`#[test]`) before implementing domain methods, repository persistence, and API clients.
3. **Architectural Parity:** Preserve strict separation between UI view components, Controllers, Command Bus handlers, and Infrastructure clients.