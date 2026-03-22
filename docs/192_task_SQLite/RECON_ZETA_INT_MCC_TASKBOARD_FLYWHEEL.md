# RECON: MCC↔TaskBoard Activity + Flywheel Integration
**Task:** tb_1774153652_5 (ZETA-INT-RECON)
**Date:** 2026-03-22
**Author:** Opus (Zeta)

---

## Q1: Does `action=active_agents` Already Work?

**YES — fully implemented.**

- **MCP handler:** `task_board_tools.py:567-570`
- **Core method:** `task_board.py:1753-1788` (`get_active_agents()`)

Returns list of agents with `claimed` or `running` tasks:
```json
{
  "agents": [{
    "agent_name": "opus",
    "agent_type": "claude_code",
    "task_id": "tb_xxx",
    "task_title": "...",
    "status": "running",
    "elapsed_seconds": 1234
  }],
  "count": 1
}
```

**Missing:** No `role`, `domain`, `branch` in the response. Could be enriched
from Agent Registry for a full "who's working where" view.

---

## Q2: How Does MCC Pipeline Update Task Status in Real-Time?

**3-step chain:**

1. **Pipeline → TaskBoard:** `agent_pipeline.py:2734-2747` calls `board.update_task()`
   with `pipeline_task_id`, `assigned_tier`, `result_summary`

2. **TaskBoard → HTTP:** `task_board.py:865-902` (`_notify_board_update()`)
   sends fire-and-forget POST to `http://localhost:5001/api/debug/task-board/notify`

3. **HTTP → SocketIO:** `debug_routes.py:2444-2498` broadcasts
   `sio.emit("task_board_updated", {...})`

**SocketIO events emitted:**

| Action | When |
|--------|------|
| `task_board_updated` (action="added") | Task created |
| `task_board_updated` (action="task_claimed") | Agent claims |
| `task_board_updated` (action="task_completed") | Task done |
| `task_board_updated` (action="updated") | Any update |
| `task_board_updated` (action="auto_dispatched") | Dragon auto-dispatch |

**Conclusion:** MCC↔TaskBoard real-time sync already works. Frontend (if running)
sees all changes via SocketIO. No additional wiring needed.

---

## Q3: Flywheel Merge Gate Debrief — Integration Points

**Status: Architecture complete (189 doc), code ZERO.**

No matches for `debrief`, `merge_gate`, `experience_processor` in src/.

### Minimal Hook Points for SC-C (Sigma)

**Primary hook — task completion response:**
`task_board_tools.py:563-565` (after `board.complete_task()` returns, before final return)

```python
# After: result = board.complete_task(...)
# Insert: debrief trigger check
if result.get("success") and should_trigger_debrief(task, session_stats):
    result["debrief_requested"] = True
    result["debrief_context"] = build_debrief_context(task_id)
```

**Secondary hook — promote_to_main:**
`task_board.py:1594-1606` (before return in `promote_to_main()`)

This is the ideal trigger point because:
- Only fires on verified main merges (not worktree completions)
- Work is already verified (tests passed, no conflicts)
- Natural checkpoint for reflection

### Required Implementation (F-steps from 189 arch doc)

| Step | What | Where | Status |
|------|------|-------|--------|
| F5 | `should_trigger_debrief()` | task_board.py | NOT DONE |
| F6 | Inject debrief in MCP response | task_board_tools.py:563 | NOT DONE |
| F7 | `action=debrief` handler | task_board_tools.py | NOT DONE |
| F8 | `action=phase_close` | task_board_tools.py | NOT DONE |
| F9 | `experience_digest` in session_init | session_tools.py | NOT DONE |

**F1-F4** (passive signal collection) are prerequisites but lower priority.

### Connection to Zeta D2

SC-C should use `ExperienceReportStore.submit(report)` as storage backend:
```python
from src.services.experience_report import ExperienceReport, get_experience_store

report = ExperienceReport(
    session_id=session_id,
    agent_callsign=callsign,
    domain=domain,
    branch=branch,
    timestamp=now_iso,
    lessons_learned=[debrief["best_discovery"]],
    recommendations=[debrief["improvement"]],
    # ... auto-populated from passive signals
)
get_experience_store().submit(report)
```

Then call `session_tracker.record_action(sid, "vetka_submit_experience_report", {...})`
so Protocol Guard knows the report was submitted.

---

## Q4: Stale Task Cleanup — DONE

29 test artifact tasks deleted (source=api, titles: Test task/Lane task etc.).
2 done tasks (195.1, 195.2) status updated to done_main.

---

## Summary for Sigma

Everything SC-C needs is mapped:
- **Storage:** `ExperienceReportStore` (Zeta D2) — ready
- **Guard:** Protocol Guard `experience_report_after_task` rule — ready
- **Hook:** `task_board_tools.py:563` + `task_board.py:1594` — identified
- **SocketIO:** Already broadcasts task events — no extra work
- **active_agents:** Already works — can enrich with registry data later
