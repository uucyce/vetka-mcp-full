# ARCHITECTURE: SYNAPSE-207 — Auto-Notification Routing
**Date:** 2026-04-05 | **Author:** Zeta (Harness) | **Status:** IMPLEMENTED
**Task:** tb_1775346715_19775_4 | **Marker:** MARKER_207

---

## Overview

Auto-notification routing makes the fleet self-coordinating. When agents change
task status, the TaskBoard automatically notifies the right participants without
manual `action=notify` calls.

## Notification Routing Table

| Trigger Event | Source | Target | ntype | Wake? | Purpose |
|---------------|--------|--------|-------|-------|---------|
| Task claimed | Any agent | Commander | `task_claimed` | Inform | Commander tracks who's working on what |
| Task completed (done_worktree) | Any agent | Commander | `task_completed` | Inform | Commander knows work is done |
| Task completed (done_worktree) | Any agent | Delta | `task_done_worktree` | Wake | QA gate — Delta starts verification |
| Task verified (pass) | Delta/Epsilon | Owner + Commander | `task_verified` | Inform | Ready for merge |
| Task verified (fail) | Delta/Epsilon | Owner | `task_needs_fix` | Wake | Agent must fix and resubmit |

### Wake vs Inform

- **Wake** = file signal + UDS event + tmux send-keys `/inbox`. Used when the
  target agent needs to act immediately (e.g., Delta must verify, agent must fix).
- **Inform** = file signal only. Agent reads on next tool call via PostToolUse
  hook. Used for awareness (e.g., Commander tracking claims).

Currently both paths use the same `notify()` mechanism (file signal + EventBus).
The UDS daemon handles wake escalation: if target agent's tmux session exists
but is idle, it sends `/inbox` via send-keys.

## Implementation Points

### 1. TaskBoard (`src/orchestration/task_board.py`)

New constants:
```python
NOTIF_TASK_CLAIMED = "task_claimed"          # MARKER_207.NOTIFY_CLAIM
NOTIF_TASK_DONE_WORKTREE = "task_done_worktree"  # MARKER_207.NOTIFY_QA
```

Hook points:
- `claim_task()` → `_auto_notify(task, NOTIF_TASK_CLAIMED)` — informs Commander
- `complete_task()` → `_auto_notify(task, NOTIF_TASK_DONE_WORKTREE)` — wakes Delta
  (only when `final_status == "done_worktree"`)
- `complete_task()` → `_auto_notify(task, NOTIF_TASK_COMPLETED)` — informs Commander
  (pre-existing)
- `verify_task()` → `_auto_notify(task, NOTIF_TASK_VERIFIED)` — informs owner + Commander
  (pre-existing)
- `verify_task()` → `_auto_notify(task, NOTIF_TASK_NEEDS_FIX)` — wakes owner
  (pre-existing)

### 2. CLAUDE.md Template (`data/templates/claude_md_template.j2`)

Synapse section varies by domain:
- **architect**: Full spawn/write/wake/kill commands + fleet check
- **harness**: spawn/write/wake + fleet status (infra maintainers)
- **engine/media/ux/qa**: Passive auto-notification summary + wake info

### 3. REFLEX Tool Catalog (`data/reflex/tool_catalog.json`)

Three new entries registered:
- `synapse_spawn` — spawn agent in new Terminal window
- `synapse_write` — inject prompt into running agent's tmux session
- `synapse_wake` — wake sleeping agent via `/inbox` send-keys

All three restricted to roles: Commander, Zeta, Eta.

## Notification Flow Diagram

```
Agent claims task
  └─→ TaskBoard.claim_task()
       └─→ _auto_notify(NOTIF_TASK_CLAIMED)
            └─→ notify("Commander", "Task claimed by Alpha: ...")
                 ├─→ SQLite notifications table
                 ├─→ ~/.claude/signals/Commander.json (file signal)
                 └─→ EventBus → UDS daemon (if running)

Agent completes task (worktree branch)
  └─→ TaskBoard.complete_task()
       ├─→ _auto_notify(NOTIF_TASK_COMPLETED)
       │    └─→ notify("Commander", "Task completed by Alpha: ...")
       └─→ _auto_notify(NOTIF_TASK_DONE_WORKTREE)
            └─→ notify("Delta", "Ready for QA: ...")
                 ├─→ ~/.claude/signals/Delta.json
                 └─→ UDS daemon → spawn_synapse.sh Delta (if offline)

Delta verifies task (pass)
  └─→ TaskBoard.verify_task()
       └─→ _auto_notify(NOTIF_TASK_VERIFIED)
            ├─→ notify(owner, "Task verified: ...")
            └─→ notify("Commander", "Task verified, ready to merge: ...")
```

## Design Decisions

1. **Delta as primary QA target**: All done_worktree tasks route to Delta.
   If Delta is overloaded, Commander can re-route to Epsilon manually.

2. **No claim→owner notification**: When an agent claims their own task,
   notifying themselves would be noise. Only Commander is notified.

3. **Idempotent notifications**: `_auto_notify` may fire multiple times
   (e.g., on retry). Each creates a new notification — agents must handle
   deduplication via `ack_notifications`.

4. **Never block on notification failure**: All notify calls are wrapped
   in try/except. Task status changes succeed even if notification fails.
