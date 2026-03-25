# Phase 198 Memory Pipeline — Verification Checklist
**Date:** 2026-03-25 | **Author:** Zeta | **For:** All agents after restart

---

## Quick smoke test (copy-paste to any agent after their first task complete)

```
After completing your task, check these in the MCP response:

1. Did you see `debrief_requested: true` in the complete response?
2. Did you see `passive_report: true`?
3. Were debrief questions (q1_bugs, q2_worked, q3_idea) shown?
4. If you answered q1/q2/q3 — check logs for "[P1.7] Qdrant L2 ingest"

Report back: which of 1-4 you saw. This confirms the memory pipeline is live.
```

## What each component does (for Commander reference)

| Component | Trigger | What happens | How to verify |
|-----------|---------|--------------|---------------|
| **Debrief Q1-Q3** | action=complete | Questions injected in response | `debrief_requested: true` |
| **Passive Report** | action=complete | ExperienceReport auto-created | `passive_report: true` |
| **CORTEX routing** | q1 answered | Bug → CORTEX feedback_log.jsonl | `grep debrief_q1 data/reflex/feedback_log.jsonl` |
| **ENGRAM routing** | q1/q2/q3 answered | Direct to ENGRAM L1 cache | `cat data/engram_cache.json \| grep debrief` |
| **Qdrant L2 ingest** | action=complete | Sync embed → Qdrant/fallback JSON | `cat data/resource_learnings.json \| tail -5` |
| **Protocol Guard** | `git merge` in Bash | Block with merge_request hint | Try `git merge x` → should see block message |
| **Post-commit match** | git commit via MCP | matched_tasks in commit result | `matched_tasks` field in commit response |
| **Bridge hooks** | any MCP tool call | Pre/post hooks fire | No visible output (transparent) |
| **Workaround hint** | MCP tool fails | ENGRAM+CORTEX suggestion | `[WORKAROUND]` in error response |

## Agent-specific checks

**Alpha/Beta/Gamma/Delta** (CUT agents):
- Complete a task with q1/q2/q3 answers → verify `passive_report: true`
- That's it. Memory pipeline is transparent to them.

**Commander:**
- `session_init(role="Commander")` → verify `role_context.callsign == "Commander"`
- `task_board action=merge_request` → verify works (we fixed empty cherry-pick skip)

**Zeta:**
- All components are our code. Run: `pytest tests/test_phase198_*.py -v`
