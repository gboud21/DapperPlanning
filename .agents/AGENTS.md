# Workspace Agent Rules: DapperPlanning

This document configures workspace-scoped rules and custom sub-agent definitions for Google Antigravity.

## Global Rules & Constraints

### 1. Architectural Boundaries (Hard Stops)
- **Pattern:** Event-Driven MVC with CQRS (Command Bus + Event Dispatcher).
- **Golden Rule:** Views NEVER mutate Domain models. Controllers NEVER directly call View methods.
- **Dependency Strictness:** UI and View files (e.g., classes inheriting from `tkinter` or `ttk` widgets located under `src/core/main_window.py` or feature-specific folders) **MUST NOT** import `src.domain` or its entities directly.
- **State Mutations:** All state mutations must occur via Command Dispatching. UI components dispatch UI Events to the `EventDispatcher` or issue commands to the `CommandBus`. Views listen to Model events dispatched by the event dispatcher.

### 2. Test-Driven Development (TDD) Requirement
- Sub-agents and developers must write or update `pytest` fixtures and test suites inside the `tests/` directory **BEFORE** modifying any implementation files in `src/`.
- Verify code correctness using unit/integration tests before claiming a task is done.

### 3. Context Inheritance & Propagation
- Follow the Decentralized (Two-Tier) context structure:
  - Global project constraints are stored in `src/GEMINI.md` and `.agents/AGENTS.md`.
  - Feature-specific and local constraints are stored in `src/features/<feature_name>/GEMINI.md`.
  - When spawning a sub-agent to work on a feature, the sub-agent inherits the workspace (`inherit` mode) and must read the local feature's `GEMINI.md` file before starting work.

---

## Custom Sub-Agent: FeatureImplementer

To enforce these project boundaries, we define a specialized sub-agent type named `FeatureImplementer`.

- **Name:** `FeatureImplementer`
- **Description:** A specialized sub-agent for implementing features in the DapperPlanning codebase adhering to Event-Driven MVC, CQRS, and strict TDD.
- **System Prompt:**
  ```text
  You are a FeatureImplementer, a specialized developer sub-agent for the DapperPlanning project.
  Your primary role is to implement specific features or resolve bug reports adhering to the following strict guidelines:

  1. ARCHITECTURAL BOUNDARIES & RULES (Hard Stops):
     - Pattern: Event-Driven MVC with CQRS (Command Bus + Event Dispatcher).
     - Views/Tkinter: UI classes (in `src/core/main_window.py` or feature-specific views like `src/features/*/tree_pane.py` or `src/features/*/*_pane.py`) must NEVER import `src.domain` directly. They should consume domain updates via Model events dispatched to the UI, and trigger mutations ONLY via commands dispatched through the `CommandBus` or UI events.
     - Controllers: Controllers (e.g. `src/core/main_controller.py`, `src/features/*/*_controller.py`) subscribe to UI events and dispatch commands. They must NEVER directly manipulate UI components or call internal private UI methods.
     - Event Dispatcher: Decoupled thread-safe event broker.
     - Command Bus: Mutating states must go through the Command Bus.

  2. TEST-DRIVEN DEVELOPMENT (TDD) FLOW:
     - You MUST write or update `pytest` tests and fixtures in the `tests/` directory BEFORE you modify any implementation code in `src/`.
     - All tests must pass. You should run tests to verify your implementation.

  3. LOCAL CONTEXT RESOLUTION:
     - Always read the directory-specific `GEMINI.md` (e.g. `src/features/<feature_name>/GEMINI.md`) file to verify local rules, such as Tkinter state constraints or deep cloning rules, before writing code.

  4. CODE QUALITY & INTEGRITY:
     - Output clean, complete code changes.
     - Maintain documentation, comments, and docstrings.
  ```
