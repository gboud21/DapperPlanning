# LOCAL CONTEXT: GITLAB SYNC ENGINE

## Responsibility
Manages network synchronization with the GitLab API, conflict resolution dialogs, and dry-push simulations.

## Key Rules
- **API Boundaries:** Epics are strictly Group-level (`/groups/{id}/epics`). Stories are strictly Project-level (`/projects/{id}/issues`).
- **Update Identity:** `PUT` requests MUST use `gitlab_iid` (Internal ID), NEVER the global `id`.
- **Status Mapping:** Do not pass `state`. Pass `state_event: 'close'` or `'reopen'`.
- **Bidirectional Conflict Detection:** Both Push and Pull operations scan against `shadow_hierarchy` baseline evaluating core attributes and structural hierarchy reparenting. Conflicted items trigger `ModelConflictDetectedEvent` for user selection.
- **Dry Push Simulation:** `_execute_dry_push()` logs item details to `logger.info`, generates markdown audit reports, dispatches `ModelDryPushCompletedEvent`, and renders interactive GUI modals without mutating server state.
- **Error Handling:** Do NOT fallback or downgrade types (e.g., Epic to Issue) on 403/404 errors. Raise `GitLabAPIError` immediately and let the SyncWorker fail gracefully.

## Sub-Agent Instructions & Testing
- **Local Hard Stops**:
  - UI Dialogs (`integrations_dialog.py`, `conflict_resolution_modal.py`, `dry_push_summary_modal.py`) must never import or mutate domain classes directly.
  - Run all network processes asynchronously.
- **Testing Targets**:
  - Update or write tests under `tests/ui/test_integrations_controller.py` and `tests/integration/features/test_conflict_detection.py` BEFORE modifying sync or resolution logic.
