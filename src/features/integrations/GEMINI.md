# LOCAL CONTEXT: GITLAB SYNC ENGINE
- **API Boundaries:** Epics are strictly Group-level (`/groups/{id}/epics`). Stories are strictly Project-level (`/projects/{id}/issues`).
- **Update Identity:** `PUT` requests MUST use `gitlab_iid` (Internal ID), NEVER the global `id`.
- **Status Mapping:** Do not pass `state`. Pass `state_event: 'close'` or `'reopen'`.
- **Error Handling:** Do NOT fallback or downgrade types (e.g., Epic to Issue) on 403/404 errors. Raise `GitLabAPIError` immediately and let the SyncWorker fail gracefully.
