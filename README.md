# DapperPlanning

> **Note:** This project is developed to standardize the software planning process for software engineers by software engineers, eliminating clunky tools designed for program managers (such as Jira) and providing direct, native bidirectional integration with GitLab.

---

## Problem & Solution

- **Problem:** Existing planning tools (e.g., Jira) are clunky, tedious, and designed primarily for Program Managers rather than Software Engineers.
- **Solution:** A native desktop planning application built for Product Owners, Product Managers, Scrum Masters, and Engineers to manage backlogs, calculate PI capacities, execute dry-push simulations, and synchronize bidirectionally with GitLab.

---

## Features & Capabilities

- **Agile Hierarchy:** Strict data modeling from **Products** $\rightarrow$ **Capabilities** $\rightarrow$ **Epics** $\rightarrow$ **Features** $\rightarrow$ **Stories**.
- **Role-Based Filtered Views:** Toggle view perspectives for Product Managers, Product Owners, Scrum Masters, Engineers, or All.
- **PI Planning & Capacity Engine:** Calculate team and individual member capacities based on PTO, velocity factors, allocation percentages, and sprint business days.
- **Bidirectional GitLab Sync Engine:**
  - Pull and push Epics (Group-level) and Stories/Issues (Project-level).
  - Pre-fetch diff scanning against local `shadow_hierarchy` baseline.
  - Interactive merge conflict resolution modal supporting core agile fields and structural reparenting diffs.
- **Dry-Push Simulation:** Simulates push operations without mutating server state, logging item details, rendering interactive GUI breakdown modals, and outputting markdown audit reports.
- **Fallback Export:** Export in-memory workspaces to standard CSV files.

---

## Architecture & Technology

- **Pattern:** Event-Driven MVC with CQRS (Command Bus + Event Dispatcher) and Dependency Injection via `AppContext`.
- **Current Stack:** Python 3 (`tkinter`, `ttk`), `pandas`, `pytest` (61 passing unit/integration/UI tests).
- **Persistence:** Local JSON workspace storage with `shadow_hierarchy` baseline tracking for git-like merge resolution.

---

## Roadmap: Rust Migration Phase

The upcoming development phase transitions the DapperPlanning codebase from **Python 3 / Tkinter** to **Rust**, porting:
1. Pure domain entities and invariant validation.
2. The CQRS Command Bus and thread-safe Event Dispatcher architecture.
3. Bidirectional GitLab API integration and JSON repository serialization.
4. Native desktop GUI implementation.
