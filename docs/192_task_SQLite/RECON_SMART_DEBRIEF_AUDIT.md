# RECON: Smart Debrief Pipeline — Audit
**Task:** `tb_1774232470_8`
**Date:** 2026-03-23
**Author:** Opus (Zeta)
**Status:** RECON COMPLETE

---

## Verdict: Pipeline is DEAD at the entrance

Gamma confirmed: 17 tasks closed via `action=complete`, zero `debrief_requested` in response. Zero experience reports in `data/experience_reports/`.

---

## Chain Analysis: Link by Link

```
DESIGNED CHAIN:
  complete → debrief_requested → agent answers → submit_experience_report
  → process_smart_debrief → auto-tasks + memory routing

ACTUAL STATE:
  complete → [3 bypass paths] → debrief never injected → chain dead
```

### Link 1: `action=complete` → debrief injection
**File:** `task_board_tools.py:577-604`
**Status:** CODE EXISTS but has 3 BYPASS PATHS

The debrief injection code (MARKER_ZETA.F1) sits at line 577 — but only runs on ONE of FOUR return paths:

| Path | Lines | Hits debrief? | When |
|------|-------|---------------|------|
| Case A: commit_hash provided | 504-505 | **NO — early return** | Agent passed commit_hash |
| Verifier merge | 524-528 | **NO — early return** | Pipeline run_id exists |
| Auto-closed by commit pipeline | 553-560 | **NO — early return** | GitCommitTool auto-closed |
| Legacy close (nothing to commit) | 573-606 | **YES** | Only path that reaches F1 |

**Root cause:** Agents almost always pass `commit_hash` (Case A) or get auto-closed by commit pipeline. The debrief code is only reached on the rarest path.

### Link 2: `session_tracker.tasks_completed > 0`
**File:** `session_tracker.py:139`
**Status:** WORKS — but depends on `record_action()` being called first

`record_action()` IS called at line 282-290 for every task_board action. The counter increments. BUT:
- Session ID is hardcoded `"mcp_default"` — all agents share one counter
- The check at line 583 uses `arguments.get("session_id", "default")` — a DIFFERENT key!
- `"mcp_default"` ≠ `"default"` → **`get_session("default")` returns a fresh session with tasks_completed=0**

**This alone kills the pipeline.** Even if debrief code ran, `tasks_completed > 0` would be False.

### Link 3: Agent sees `debrief_requested` in MCP response
**Status:** NEVER TESTED — chain dies before this

Even if injected, MCP tool responses are JSON dicts returned to Claude. Claude Code shows them in its tool output. The agent SHOULD see it... but we've never verified because Link 1+2 prevent injection.

### Link 4: Agent calls `submit_experience_report`
**Status:** NEVER HAPPENS

No debrief questions → no prompt → no report. Zero files in `data/experience_reports/`.

### Link 5: `process_smart_debrief()` → auto-tasks
**File:** `smart_debrief.py:156-195`
**Status:** CODE WORKS (tested) — but never called in production

Called from `ExperienceReportStore.submit()` → but submit() is never called.

### Link 6: `_route_to_memory()` → subsystem writes
**File:** `smart_debrief.py:120-153`
**Status:** LOGS ONLY — F4 wiring not implemented

Handoff written (`HANDOFF_ZETA_F4_MEMORY_WIRING.md`) but code still only returns trigger dict + logs. No real writes to REFLEX/AURA/MGC/ENGRAM.

---

## Summary Table

| # | Link | Status | Blocker |
|---|------|--------|---------|
| 1 | Debrief injection in complete | **BYPASSED** | 3 of 4 return paths skip it |
| 2 | session_tracker check | **BROKEN** | Session ID mismatch: "mcp_default" ≠ "default" |
| 3 | Agent sees questions | **UNTESTED** | Blocked by 1+2 |
| 4 | Agent submits report | **NEVER** | No trigger |
| 5 | process_smart_debrief | **WORKS** (code) | Never called |
| 6 | _route_to_memory | **LOGS ONLY** | F4 not implemented |

---

## Fix Plan

### Phase 1: Make debrief fire (fix Links 1+2)

**Fix 1a:** Move debrief injection BEFORE all return paths — inject into `result` dict before ANY return in the complete handler. Or: extract to a function and call it on every success path.

**Fix 1b:** Fix session ID mismatch — use the SAME session_id in `record_action()` and `get_session()`. Either both `"mcp_default"` or both from `arguments.get("session_id", "default")`.

### Phase 2: Implement F4 memory wiring (fix Link 6)

Handoff ready: `HANDOFF_ZETA_F4_MEMORY_WIRING.md` has exact API signatures, ready code, test strategy.

### Phase 3: Verify end-to-end

Test with one real agent: complete → see questions → submit report → verify auto-tasks created.

---

*"A pipeline that never fires is worse than no pipeline — it creates false confidence."*
