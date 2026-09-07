# Workspace Coding Standards & Architectural Guidelines: DapperPlanning

This document defines the mandatory software engineering standards, architectural boundaries, code generation rules, and quality assurance guidelines for the **DapperPlanning** native Rust application workspace.

---

## 1. Architectural Boundaries & Structural Rules (Hard Stops)

### Pattern: Event-Driven MVC with CQRS (Command Bus + Event Dispatcher)

```
       +-------------------------------------------------------------+
       |                         UI LAYER                            |
       |               (dapper_ui View Components)                   |
       +------------------------------+------------------------------+
                                      |
                     dispatches UI    | listens to Model
                        Commands      |    Events
                                      v
       +------------------------------+------------------------------+
       |                     CONTROLLER LAYER                        |
       |                (dapper_workflows Crate)                     |
       +------------------------------+------------------------------+
                                      |
                             executes | 
                            Commands  v
       +------------------------------+------------------------------+
       |                      COMMAND BUS / DISPATCHER               |
       |                (tokio::sync channel router)                 |
       +------------------------------+------------------------------+
                                      |
                               mutates|
                                      v
       +------------------------------+------------------------------+
       |                       DOMAIN MODEL                          |
       |           (dapper_domain Pure Entities & Invariants)        |
       +-------------------------------------------------------------+
```

1. **View Layer Strictness (`dapper_ui`):**
   - **Golden Rule:** Views MUST NEVER import domain entity mutation methods directly or mutate domain models.
   - Views receive state updates strictly by subscribing to **Model Events** emitted over Tokio `broadcast` channels.
   - Views trigger user actions strictly by dispatching **UI Commands** over Tokio `mpsc` channels to the Command Bus.

2. **Controller Layer Strictness (`dapper_workflows`):**
   - Controllers handle incoming UI commands/events, validate business workflows, and dispatch domain commands.
   - Controllers MUST NEVER directly manipulate UI components or invoke private UI layout methods.

3. **Domain Layer Strictness (`dapper_domain`):**
   - Pure business logic. Zero dependencies on UI rendering frameworks (`egui`, `iced`, `slint`), persistence engines, or external API clients.

4. **CQRS Command & Event Routing:**
   - All state mutations MUST be routed through the Command Bus.
   - Cross-component notifications MUST be broadcast via the Event Dispatcher channel architecture.

---

## 2. Tokio Runtime, Concurrency & Locking

1. **Async Reactor Protection via `spawn_blocking`:**
   - Heavy CPU-bound compute operations—specifically custom search/query parsing and the shadow database merge conflict diffing engine—MUST be offloaded using `tokio::task::spawn_blocking`.
   - Never perform synchronous CPU-heavy loops or blocking I/O on async executor worker threads to prevent reactor starvation.

2. **Async-Aware Mutexes & State Locking:**
   - Use `tokio::sync::RwLock` for shared mutable state held across `.await` points to allow concurrent read access and prevent OS thread deadlocks.
   - Standard `std::sync::Mutex` or `std::sync::RwLock` are prohibited across `.await` boundaries.

3. **Channel Architecture:**
   - Point-to-point CQRS Commands: `tokio::sync::mpsc` with bounded channel capacity.
   - Pub-Sub Model Events: `tokio::sync::broadcast`.

---

## 3. Memory Management & Zero-Copy Optimization

1. **Shared Dataset Routing with `Arc<T>`:**
   - Route large domain datasets (such as iteration visibility maps, product team hierarchies, or unpaginated GitLab backlogs) over `tokio::sync::broadcast` channels wrapped in `Arc<T>` (e.g. `Arc<Vec<Story>>` or `Arc<Workspace>`).
   - Deep copying / cloning large domain objects during event broadcasting is strictly forbidden.

2. **Transient String Parsing:**
   - Functions processing transient strings (e.g., query lexers, markdown transformers, or raw string matchers) MUST use `&str` borrowing or `std::borrow::Cow<'a, str>` to eliminate unnecessary `String` heap allocations.

---

## 4. Strict Error Handling & Panic Strategy

1. **Total Ban on `unwrap()` and `expect()` in Production Code:**
   - Production code in library crates (`dapper_domain`, `dapper_core`, `dapper_persistence`, `dapper_gitlab`, `dapper_workflows`, `dapper_ui`, `dapper_desktop`) MUST NOT contain calls to `.unwrap()` or `.expect()`.
   - `.unwrap()` and `.expect()` are permitted **ONLY inside test modules** (`#[test]`).

2. **Error Types & Context Aggregation:**
   - Library crates MUST define explicit domain error enums using `thiserror`.
   - The application binary crate (`dapper_desktop`) MUST use `anyhow::Result` / `anyhow::Context` to aggregate fatal startup, configuration, and top-level execution errors.

3. **UI Graceful Shutdown Policy & Panic Handling:**
   - Cargo release builds MUST specify `panic = "abort"` in `Cargo.toml` to prevent undefined UI state corruption.
   - Integrate a panic hook using `human-panic` in `dapper_desktop` to intercept unexpected panics, log diagnostic tracebacks, and present a friendly graphical error modal instead of silently crashing to the terminal.

---

## 5. Observability & Tracing

1. **Structured Logging:**
   - Use the `tracing` crate for all application telemetry (`tracing::info!`, `tracing::warn!`, `tracing::error!`, `tracing::debug!`). Plain `println!` or `eprintln!` statements are strictly prohibited in production code.

2. **CQRS Command Lifecycle Tracing:**
   - All Command Bus dispatchers and command handler implementations MUST be decorated with `#[tracing::instrument]` annotations to seamlessly track command execution lifecycles, execution latency, and payload metadata across CQRS boundaries.

---

## 6. Trait-Based Dependency Injection (Inversion of Control)

1. **External Boundary Abstraction:**
   - All external infrastructure interfaces—including GitLab REST/GraphQL clients, local JSON workspace persistence repositories, and operating system keyring adapters—MUST be defined strictly as Rust traits in `dapper_core` or `dapper_domain`.

2. **Mockability for TDD:**
   - Components depending on external services MUST accept trait objects (`Arc<dyn WorkspaceRepository>` or `Arc<dyn GitLabClient>`) to allow isolated unit testing with mock implementations without requiring network access or disk I/O.

---

## 7. Cargo Workspace Inheritance & Dependency Management

1. **Centralized Workspace Dependencies (`[workspace.dependencies]`):**
   - ALL third-party library dependencies and version specifications MUST be declared centrally in the root workspace `Cargo.toml` file under the `[workspace.dependencies]` table.
   - Individual workspace crate `Cargo.toml` manifests (`crates/*/Cargo.toml`) MUST NOT define explicit version strings for third-party crates. Instead, they MUST inherit dependencies using Cargo workspace inheritance syntax:
     ```toml
     [dependencies]
     serde = { workspace = true }
     serde_json = { workspace = true }
     tokio = { workspace = true }
     thiserror = { workspace = true }
     tracing = { workspace = true }
     ```

2. **Crate-Level Feature Customization & Variables:**
   - Crate-level `Cargo.toml` files are explicitly permitted to define crate-specific `features`, `optional = true`, or `default-features = false` variables when required by that specific crate, while continuing to inherit the base version from the workspace root:
     ```toml
     [dependencies]
     serde = { workspace = true, features = ["derive"] }
     uuid = { workspace = true, features = ["v4", "serde"] }
     tokio = { workspace = true, features = ["rt-multi-thread", "sync", "macros"], optional = true }
     ```

3. **Single Source of Truth & Compilation Optimization:**
   - Enforces uniform dependency versions across all crates (`dapper_domain`, `dapper_core`, `dapper_persistence`, `dapper_gitlab`, `dapper_workflows`, `dapper_ui`, `dapper_desktop`).
   - Prevents version mismatches, duplicate dependency compilation, and redundant version definitions.

---

## 8. Quality Assurance & Test-Driven Development (TDD)

1. **Strict Red-Green-Refactor Flow:**
   - Unit tests (`#[test]`) and integration tests (`tests/*.rs`) MUST be written or updated **BEFORE** modifying implementation code.

2. **Golden Baseline Schema Compatibility:**
   - Workspace serialization and deserialization implementations in `dapper_persistence` MUST maintain 100% loss-less round-trip compatibility with the golden workspace fixture schema (`tests/fixtures/golden_workspace.json`).

3. **Clippy Compliance:**
   - Code MUST compile cleanly without warnings under `cargo clippy --all-targets -- -D warnings`.

4. **Multi-Platform Target Verification:**
   - All CI/CD build pipelines and code updates MUST pass `cargo test` and `cargo clippy` across Linux (`x86_64-unknown-linux-gnu`), macOS (`x86_64-apple-darwin` / `aarch64-apple-darwin`), and Windows (`x86_64-pc-windows-msvc`) targets to guarantee true cross-platform GUI and file I/O viability.

---

## 9. Pre-Implementation Design Directive

- **Pre-Flight RFC Discussion:** Prior to initiating code implementation for any phase or major component, a detailed architectural design document (`phase_N_design.md`) MUST be written, reviewed, and approved to resolve all design decisions, trait definitions, and clarifying questions.
