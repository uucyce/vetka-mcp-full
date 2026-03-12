# Phase 170 CUT Debug Shell Worker-Actions Smoke Recon

## Scope
- Target file: `client/e2e/cut_debug_worker_actions_smoke.spec.cjs`
- Surface: debug shell view on `/cut` with mocked `project-state`
- Goal: prove debug shell toggles correctly, bootstrap endpoint works, and worker actions trigger expected async worker endpoints

## Stable selectors
| Surface | Selector | Expected state |
| --- | --- | --- |
| NLE root | `[data-testid="cut-editor-layout"]` | Visible after `/cut` hydration in NLE mode |
| Debug shell toggle | `[data-testid="cut-view-toggle-button"]` | Toggles between NLE and debug shell views |
| Debug shell container | `[data-testid="cut-debug-shell-container"]` | Visible when debug shell is active |
| Debug shell worker action button | `[data-testid="cut-debug-shell-worker-action-button"]` | Triggers worker actions like 'run', 'stop' |
| Debug shell status indicator | `[data-testid="cut-debug-shell-status"]` | Shows current shell status (ready, running, etc.) |

## Expected interaction states
1. Navigation to `/cut?sandbox_root=...&project_id=...` should hydrate directly into NLE, not legacy shell.
2. Clicking the view toggle button should switch to debug shell view.
3. Debug shell should call `/api/cut/debug-shell/bootstrap` on initialization to get shell_ready status.
4. Worker actions in debug shell (like clicking worker action buttons) should trigger `/api/cut/debug-shell/worker/action` endpoint.
5. Debug shell should be able to query worker jobs via `/api/cut/debug-shell/worker/jobs`.
6. No runtime errors should appear in debug shell mode.
7. Local storage should remain free of vetka_last_runtime_error after debug shell interactions.

## Notes
- The debug shell is intended for development and troubleshooting, not for end-users.
- All worker action endpoints should return success responses for the smoke test to pass.
- The test mocks only the necessary endpoints: project-state, debug-shell/bootstrap, debug-shell/worker/action, and debug-shell/worker/jobs.
- No actual backend workers are touched - all interactions are mocked at the API level.