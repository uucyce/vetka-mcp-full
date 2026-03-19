# RECON: Agent Feedback — TaskBoard UX & Memory Integration

**Date:** 2026-03-19
**Phase:** 191 (DEBAG session)
**Source:** Multi-agent field report (Opus, Cursor, Codex sessions)

---

## What Works Well

1. **Task Board MCP as single gateway** — claim -> work -> complete with auto-commit eliminates git ceremony. `[task:tb_xxxx]` gives full traceability.
2. **session_init fat context** — phase, pending tasks, hot files, recent commits in one call. Without it: 5-6 separate calls.
3. **Unified protocol for all agents** — Opus, Cursor, Codex on one task board. Ownership via claim prevents conflicts.

## Problems Found

### P1: `complete` = commit + close is a rigid coupling
- When pre-commit hook fails (digest update, etc.) — task stays open, error not obvious
- Stale/already-implemented tasks (187.5, 187.9) had to be closed via `update status=done`, bypassing closure pipeline (no commit_hash, no closed_at)
- **Fix:** Add `action=close` (no git) and `action=bulk_close`

| Action | Git commit? | Closes task? | Use case |
|--------|-------------|--------------|----------|
| `complete` | yes | yes | Normal work |
| `close` | no | yes | Stale, already_implemented, research |
| `bulk_close` | no | yes (N tasks) | Cleanup after review |

`close` accepts `reason` field: already_implemented, duplicate, obsolete, research_done.

### P2: Anti-spam task reminder noise
- System reminders "task tools haven't been used recently" fire even when agent actively uses MCP task board
- MCP tool calls don't register in internal task tracking
- **Fix:** Suppress or make reminder MCP-aware

### P3: AURA user_id mismatch (fixed in 191.5)
- session_init returned `has_preferences: false` due to user_id mismatch
- All pre-191.5 sessions ran without AURA personalization
- **Fix applied:** MARKER_191.5. Add cold-start warning when `aura.entries < 3`.

### P4: No task completion progress tracking
- Task 187.6 had checklist in description, but after partial work by other agents — unclear what's done
- **Fix:** Add `subtasks: [{title, done}]` field + `action=subtask_done` + progress in `action=get`

### P5: Bulk complete missing
- 187.10 + 187.11 closed in one commit, but `complete` accepts single task_id
- Had to close second via `update` (bypasses closure pipeline)
- **Fix:** `action=complete task_ids=[...]` — one commit, multiple tasks closed

## Ideas — Prioritized

### Idea 1: ENGRAM L1 -> session_init injection (Priority 1)
At session_init: take hot_files -> L1 lookup -> inject top-3 lessons into `context_hints`.
Minimal overhead (L1 = O(1)), maximum impact. Agent gets "don't forget: scorer.py and feedback.py always change together".

### Idea 2: Failure feedback -> task enrichment (Priority 2)
When pipeline fails, `failure_history` exists but not shown in `action=get`.
Add `failure_hints` field in get response, auto-populated from failure_history.

### Idea 3: Memory health dashboard in session_init (Priority 2)
```yaml
memory_health:
  aura: {entries: 2, status: ok}
  engram_l1: {entries: 5, hit_rate: 0.73}
  reflex: {success_rate: 0.007}  # RED FLAG — currently broken
```
reflex success_rate 0.007 needs separate investigation.

### Idea 4: Task lineage (Priority 3)
`parent_task_id` and `dependencies` exist in schema but unused.
Auto-suggest: if title contains "187.9" and "187.8" exists -> propose link.

### Idea 5: Bulk complete (Priority 3)
`action=complete task_ids=["tb_xxx", "tb_yyy"]` — one commit, multiple tasks closed.

---

## Implementation Plan

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 1 | `action=close` + `action=bulk_close` | 1h | Unblocks most frequent pain |
| 2 | ENGRAM L1 -> session_init injection | 2h | Max ROI for agent context |
| 3 | Memory health in session_init | 30min | Diagnostics |
| 4 | Bulk complete | 1h | QoL |
| 5 | Task subtask progress | 2h | Multi-agent visibility |
| 6 | Failure hints in action=get | 1h | Pipeline reliability |
| 7 | Task lineage auto-suggest | 2h | When time permits |
