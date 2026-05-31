# Core Domain: Application Shell & Event System

## Responsibility
The `src/core/` directory contains the foundational shell of the application, responsible for orchestration, top-level UI (MainWindow, MenuBar), and the global messaging system.

## Key Components
- **EventDispatcher**: The central message bus. It handles thread-safe event delivery and decoupled communication between Vertical Slices.
- **MainWindow**: The root UI container using `ttk.PanedWindow`. It delegates specific UI areas to feature-specific panes.
- **MainController / MenuController**: Manage global lifecycle events (Open/Save Workspace, App Close, Theme Toggles).

## Event Categories
Defined in `src.core.events`:
- **UI Requests**: `UIOpenWorkspaceRequestedEvent`, `UISaveWorkspaceRequestedEvent`, `UIAppCloseRequestedEvent`.
- **Model Updates**: `ModelHierarchyUpdatedEvent`, `ModelActiveItemChangedEvent`.
- **System Actions**: `AppThemeChangedEvent`, `UIErrorNotificationEvent`.

## Rules for Core
- Do not add business-specific logic here; core must remain domain-agnostic.
- The `EventDispatcher` is the only component that should handle Tkinter's `.after()` for thread-safe cross-thread communication.
