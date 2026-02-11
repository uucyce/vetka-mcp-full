# Cursor Brief: Phase 131 Wave 2 — Integration & Testing

**Prerequisites:** Wave 1 COMPLETE (C20A-E ✅, 131.1-131.2 ✅)
**Date:** 2026-02-10

## What Changed Since Wave 1

Opus completed:
- **131.1 (MARKER_131.1):** Pipeline → Approval connected. L2 Scout now audits code BEFORE file write.
- **131.2 (MARKER_131.2):** EvalAgent retry enabled (3 attempts with progressive enhancement).
- **130.6:** Verify-before-write, language validation, verifier default=FAIL.

Flow is now: `Coder → Verifier → L2 Scout → Language Check → Write (or stage)`

## Wave 2 Tasks

### C21A: TaskBoard Result Expansion (HIGH, 1h)
**Marker:** MARKER_C21A

**Problem:** TaskBoard saves only 500-char summary. Can't audit what Dragon did.

**File:** `src/orchestration/task_board.py`

Find where results are saved after pipeline dispatch (~line 747). Expand from:
```python
result_summary = str(result.get("results", {}))[:500]
```
To:
```python
pipeline_results = {
    "subtasks_completed": result.get("results", {}).get("subtasks_completed", 0),
    "subtasks_total": result.get("results", {}).get("subtasks_total", 0),
    "files_created": result.get("results", {}).get("files_created", []),
    "stats": result.get("results", {}).get("stats", {}),
    "approval_status": result.get("results", {}).get("approval_status", "unknown"),
}
result_summary = json.dumps(pipeline_results)[:2000]  # 2KB limit
```

---

### C21B: Health Endpoint Enhancement (MEDIUM, 30min)
**Marker:** MARKER_C21B

**Problem:** `/api/health` doesn't show heartbeat daemon status or BMAD status.

**File:** `src/api/routes/debug_routes.py` (or wherever `/api/health` is)

Add to health response:
```json
{
  "heartbeat_daemon": { "running": true, "interval": 60 },
  "bmad": { "approval_mode": "mycelium", "l2_scout": "active" },
  "pipeline_safety": { "verify_before_write": true, "language_validation": true }
}
```

---

### C21C: Frontend Task Board Widget (MEDIUM, 2h)
**Marker:** MARKER_C21C

**Problem:** No UI for task board. Can only use REST API.

**Rule:** NO NEW PANELS. Add to existing DevPanel or Chat sidebar.

**Suggestion:** Add task list to existing DevPanel WebSocket feed.
Show: task_id | title | status | assigned_to | priority

Use `useMyceliumSocket.ts` to get real-time updates from `ws://localhost:8082`.

---

### C21D: End-to-End Dragon Test (HIGH, 1h)
**Marker:** MARKER_C21D

**Problem:** We need to verify the FULL chain works.

**Test plan:**
1. Start server with `VETKA_HEARTBEAT_ENABLED=1`
2. Send message to group chat: `@dragon Create a hello world function in src/vetka_out/hello.py`
3. Verify:
   - Heartbeat picks it up within 60s
   - TaskBoard shows task as "running"
   - Pipeline executes (Scout → Architect → Researcher → Coder → Verifier)
   - L2 Scout audits the output (MARKER_131.1)
   - File written to `src/vetka_out/hello.py` (safe directory)
   - TaskBoard shows "done" with results
4. Check: `data/vetka_staging/` for any rejected/blocked files

Write test results in `docs/131_ph/E2E_TEST_RESULTS.md`

---

## Files Index

| File | Action | Marker |
|------|--------|--------|
| src/orchestration/task_board.py | MODIFY | MARKER_C21A |
| src/api/routes/debug_routes.py | MODIFY | MARKER_C21B |
| client/src/components/DevPanel | MODIFY | MARKER_C21C |
| docs/131_ph/E2E_TEST_RESULTS.md | CREATE | MARKER_C21D |
