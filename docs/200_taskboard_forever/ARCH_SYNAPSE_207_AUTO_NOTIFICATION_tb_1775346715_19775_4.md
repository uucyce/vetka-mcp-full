# ARCHITECTURE: SYNAPSE-207 — Auto-Notification Routing (Expanded)
**Date:** 2026-04-05 | **Author:** Zeta (Harness) | **Status:** IMPLEMENTED
**Task:** tb_1775346715_19775_4 | **Marker:** MARKER_207

---

## Overview

SYNAPSE-207 is the capstone infrastructure task that makes the fleet self-coordinating.
Seven subsystems work together: auto-notification chain, per-role CLAUDE.md, heartbeat
monitor, compacting detection, dilemma escalation, Scout pre-merge manifests, and
REFLEX tool registration.

## 1. Notification Routing Table

| Trigger Event | Source | Target | ntype | Wake? | Purpose |
|---------------|--------|--------|-------|-------|---------|
| Task claimed | Any agent | Commander | `task_claimed` | Inform | Commander tracks who's working |
| Task completed (done_worktree) | Any agent | Commander | `task_completed` | Inform | Commander knows work is done |
| Task completed (done_worktree) | Any agent | Delta | `task_done_worktree` | Wake | QA gate — Delta starts verification |
| Task verified (pass) | Delta/Epsilon | Owner + Commander | `task_verified` | Inform | Ready for merge |
| Task verified (fail) | Delta/Epsilon | Owner | `task_needs_fix` | Wake | Agent must fix and resubmit |
| Task merged (done_main) | Commander | Next queued agent | `task_done_main` | Wake | Slot open, next agent can start |
| Agent compacting | Any agent | Commander | `agent_compacting` | Wake | Prepare replacement agent |
| Dilemma escalation | Any agent | Commander | `dilemma_escalation` | Wake | Agent stuck, needs Commander decision |

### Wake vs Inform

- **Wake** = file signal + UDS event + tmux send-keys `/inbox`. Target must act now.
- **Inform** = file signal only. Agent reads on next tool call via PostToolUse hook.

## 2. Heartbeat Monitor

**Method:** `TaskBoard.synapse_heartbeat_check()`

- Reads `data/synapse_sessions.json` for per-agent `last_activity` timestamps
- If agent silent > 3 min with claimed task → `synapse_write.sh ROLE "status report"`
- If agent reports `compacting: true` → notify Commander to prepare replacement
- Designed to be called by cron/loop or Commander manually

**Session Registry:** `data/synapse_sessions.json`
```json
{
  "Alpha": {
    "tmux_session": "vetka-Alpha",
    "worktree": "cut-engine",
    "agent_type": "claude_code",
    "backend": "iterm2",
    "spawned_at": 1775347000,
    "last_activity": 1775347180,
    "compacting": false
  }
}
```

## 3. Compacting Detection

**Method:** `TaskBoard.report_compacting(role)`

When an agent detects its context window is being compressed:
1. Agent calls `action=notify ntype=agent_compacting` (or future `action=report_compacting`)
2. TaskBoard finds agent's claimed task
3. Notifies Commander: "COMPACTING: agent X lost context on task Y. Prepare replacement."
4. Commander spawns fresh agent via `spawn_synapse.sh` to pick up the task

## 4. Dilemma Escalation

Agents stuck on protocol decisions (conflicting rules, ambiguous scope) can escalate:
```
vetka_task_board action=notify source_role=Alpha target_role=Commander
    ntype=dilemma_escalation message="Conflicting ownership on shared_zone file X"
```

Routing: `_auto_notify` sends to Commander with DILEMMA prefix + extra_msg context.
Commander wakes, approves/rejects via reply notification, agent continues.

## 5. Scout Pre-Merge Manifest

**Method:** `TaskBoard._scout_pre_merge_manifest(task, branch)`

Called automatically in `merge_request()` before executing cherry-pick/merge:
- Runs `git diff --stat main...branch` + `git diff --name-only`
- Checks changed files against `allowed_paths` of other active tasks
- Produces overlap risk report included in merge_request result

```json
{
  "branch": "claude/cut-engine",
  "changed_files": ["client/src/store/useTimelineInstanceStore.ts", ...],
  "file_count": 5,
  "overlap_risks": [
    {"file": "client/src/store/useCutEditorStore.ts",
     "conflicting_task": "tb_xxx", "conflicting_role": "Gamma"}
  ]
}
```

## 6. spawn_synapse.sh v2

Enhanced with:
- **INIT_PROMPT** parameter (4th arg, default: "vetka session init")
- **Session registry** writes to `data/synapse_sessions.json` on spawn
- **Auto-init** sends INIT_PROMPT to tmux session after 8s boot delay
- All 4 agent types supported: `claude_code`, `opencode`, `vibe`, `generic_cli`

## 7. REFLEX Tool Catalog

Three tools registered in `data/reflex/tool_catalog.json`:
- `synapse_spawn` — spawn agent in new Terminal window
- `synapse_write` — inject prompt into running agent's tmux session
- `synapse_wake` — wake sleeping agent via `/inbox` send-keys

Restricted to roles: Commander, Zeta, Eta.

## 8. CLAUDE.md Per Role

Template at `data/templates/claude_md_template.j2` generates role-specific Synapse sections:
- **architect** (Commander): Full spawn/write/wake/kill + fleet management
- **harness** (Zeta/Eta): Spawn/write/wake + fleet status
- **engine/media/ux/qa** (Alpha/Beta/Gamma/Delta/Epsilon): Passive auto-notification + wake + dilemma escalation

## Design Decisions

1. **Delta as primary QA target**: All done_worktree → Delta. Commander re-routes to Epsilon if overloaded.
2. **done_main → next agent wake**: After merge, find oldest pending task by role, wake that agent.
3. **Heartbeat is pull-based**: Commander/cron calls `synapse_heartbeat_check()`, not push-based timer.
4. **Scout manifest is advisory**: Overlap risks are logged and returned but don't block merge.
5. **Never block on notification failure**: All notify calls wrapped in try/except.
