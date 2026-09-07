# GLOBAL ARCHITECTURE & STANDARDS: DAPPER PLANNING

- **Coding Standards:** All code generation MUST strictly abide by [CODING_STANDARDS.md](file:///home/gboud21/code/DapperPlanning/CODING_STANDARDS.md).
- **Pattern:** Event-Driven MVC with CQRS (Command Bus + Event Dispatcher) and dependency injection via `AppContext`.
- **Golden Rule:** Views NEVER mutate Domain models. Controllers NEVER directly call View methods.
- **Dependency Strictness:** View/UI elements (e.g. Tkinter classes in `src/core/main_window.py` or feature panes in Python, `dapper_ui` components in Rust) MUST NOT import or instantiate domain objects directly. All mutations occur via command execution.

## Architectural Context for the Architect

1. **App Context (`src/core/app_context.py`):** Acts as the Dependency Injection (DI) container. Houses references to global services like `event_dispatcher`, `command_bus`, `workspace`, and `workspace_repository`.
2. **Command Bus (`src/core/command_bus.py`):** Routes state-mutating actions (defined in `src/core/commands.py`) to their respective handlers. All domain changes MUST flow through the Command Bus.
3. **Event Dispatcher (`src/core/events.py`):** Manages UI events (triggered by users) and Model events (triggered on state change). Views subscribe to Model events, while Controllers subscribe to UI events and issue Commands.

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
   - Write or update `pytest` tests/fixtures BEFORE making any changes to the corresponding logic in `src/`.
5. Architectural Boundaries (Hard Stops):
   - NEVER import `src.domain` directly inside View/Tkinter classes.
   - All state modifications MUST go through command dispatch via the Command Bus (`command_bus.execute(command)`).
   - Controllers must not call UI components' internal methods directly.
6. Execution Plan & Tasks:
   [Step-by-step description of tasks mapped out by the Architect]
7. Verification:
   - Run `pytest` to ensure all tests pass.
   - Provide clean Python diffs of the test files followed by source files in your response.
```

---

## Workspace Sub-Agent Invocation Command Example

For the Architect (main agent), the invocation is performed using the `invoke_subagent` tool:

```json
{
  "Subagents": [
    {
      "TypeName": "FeatureImplementer",
      "Role": "Feature Developer for [Feature Name]",
      "Prompt": "[Filled-in SUB-AGENT EXECUTION TEMPLATE]",
      "Workspace": "inherit"
    }
  ]
}
```