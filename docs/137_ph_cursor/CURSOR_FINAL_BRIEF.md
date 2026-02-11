# CURSOR FINAL BRIEF — MCC Last Pass

## SCOPE: Fix 2 things only, then stop.

### Task 1: ARCHITECT tab — fix "Error: Load failed"
File: `client/src/components/panels/ArchitectChat.tsx`

The ARCHITECT tab shows "Error: Load failed" when user sends message.
- Debug the LLM call: what endpoint does it POST to?
- Check if the model (Kimi K2.5) is reachable via Polza
- Add error message display (show actual error, not just "Load failed")
- Add loading spinner while waiting for response
- MARKER_137.ARCHITECT_FIX

### Task 2: Delete heartbeat_health.py (duplicate)
File: `src/api/routes/heartbeat_health.py`

Per audit report: this file has routes NOT registered in __init__.py.
All heartbeat functionality already exists in debug_routes.py.
- Delete `heartbeat_health.py`
- Remove any imports referencing it
- Verify no other files import from it
- MARKER_137.HEARTBEAT_CLEANUP

### RULES
- Only touch these 2 things
- Commit via `vetka_git_commit` with task IDs
- Do NOT start new features
- Do NOT refactor other tabs
