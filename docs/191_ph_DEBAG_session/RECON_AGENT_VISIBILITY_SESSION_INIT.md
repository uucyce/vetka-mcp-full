# RECON: Agent Visibility in session_init

**Date:** 2026-03-19
**Phase:** 191 (DEBAG session)
**Source:** Agent field feedback — cross-session recon by Opus

---

## Problem

Agents are informationally blind to each other. `session_init` returns agent_focus (last_completed, hot_files) but NOT:
- What other agents are working on RIGHT NOW (claimed tasks)
- What files changed recently and by whom

This causes file conflicts, duplicate work, and wasted recon cycles.

## Current State

- `action=active_agents` EXISTS on task board but is never called automatically
- `agent_focus` in digest shows `last_completed` per agent — stale, not real-time
- No git-based file change tracking in session_init

## Solution: 2 enrichments to session_init

### 1. Claimed Tasks Overlay

At session_init, auto-query task board for `status=claimed` tasks by OTHER agents.
Inject into response:

```json
"other_agents": [
  {
    "agent": "cursor",
    "task_id": "tb_xxx",
    "title": "CUT-W5.1: Auto-Montage UI",
    "allowed_paths": ["client/src/components/cut/"],
    "claimed_at": "2026-03-19T10:30:00"
  }
]
```

**Implementation:** In `session_tools.py` session_init handler, after agent_type resolved:
1. Call `task_board.list_tasks(filter_status="claimed")`
2. Filter out current agent's own tasks
3. Inject as `other_agents` field

**Cost:** 1 extra task_board query per session_init. Negligible.

### 2. Conflict Radar

At session_init, run `git log --since=2h --name-only --format='%an|%H'` and group by author.
Inject into response:

```json
"conflict_radar": {
  "window": "2h",
  "changes": [
    {
      "agent": "cursor",
      "files": ["client/src/components/cut/TimelineTrackView.tsx", "client/src/store/useCutEditorStore.ts"],
      "commit_count": 3
    }
  ]
}
```

**Implementation:** In `session_tools.py`, after digest loaded:
1. `git log --since=2h --name-only --format='%an'` via subprocess
2. Parse and group by author, excluding current agent
3. Inject as `conflict_radar` field

**Cost:** 1 git subprocess call. ~50ms on this repo.

---

## What This Does NOT Cover (already has tasks)

- project_id consistency → tb_1773881085_8, tb_1773719013_21
- double-close guard → already fixed (4438b1a8c)
- ENGRAM injection into session_init → tb_1773881085_2
- handoff notes → rejected (MGC handles this)
