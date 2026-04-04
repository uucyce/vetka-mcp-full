# Architecture: Agent Auto-Spawn — Phase 205
**Date:** 2026-04-04 | **Authors:** Commander (Opus), Grok-4.1-fast (research), User (direction)
**Status:** APPROVED — ready for implementation
**Depends on:** Phase 204 Signal Delivery (DONE)
**Parent docs:** ROADMAP_SIGNAL_DELIVERY_204.md, VETKA_RT_COMMS_ARCHITECTURE.md

---

## Problem

Phase 204 delivers notifications to **running** agents. But spawning/killing agents
is manual — user opens terminal, runs `claude --worktree X`. Need programmatic
spawn from Commander or daemon when agent is offline.

## Research Summary (Grok-4.1-fast)

### Claude Code CLI Capabilities
- **No headless/batch mode**: `--non-interactive`, `--batch`, `--initial-prompt` do NOT exist
- **No `--resume`**: Sessions are stateless (each `claude` invocation = fresh)
- **SDK (@anthropic-ai/claude-code)**: Node wrapper for API, not CLI orchestration
- **Workaround**: `claude --worktree X` in **detached tmux session** = programmatic spawn + persistent TTY
- **Tested**: `tmux new-session -d -s Alpha "cd worktree && claude --worktree cut-engine"` — works 100%

### Transport Options Evaluated

| Transport | Verdict | Reason |
|-----------|---------|--------|
| Named pipes (mkfifo) | **REJECTED** | Blocks on write if no reader → hangs notify() in task_board.py |
| fswatch/entr | **REJECTED** | Extra brew dependency, we already have UDS daemon |
| Polling daemon (sleep 30) | **REJECTED** | Wastes CPU, not event-driven |
| UDS daemon + tmux | **APPROVED** | Already built (Phase 204), add spawn logic ~15 lines |
| SSE/WebSocket | **FUTURE** | For MCC UI dashboard, not CLI agents |

### Key Insight
Phase 204 infrastructure (UDS daemon + file signals + hooks) is **already the trigger mechanism**.
The only missing piece is: UDS daemon detects "agent offline" → spawns tmux session.
No new transport needed.

## Architecture

```
Commander: action=notify target_role=Alpha message="claim tb_xxx"
  │
  ├─→ SQLite notifications table          (Phase 204.1 — DONE)
  ├─→ File signal ~/.claude/signals/Alpha.json  (Phase 204.1 — DONE)
  └─→ UDS Daemon push                     (Phase 204.2 — DONE)
        │
        ├─ Agent ONLINE (tmux has-session -t Alpha = true)
        │    └─→ PreToolUse hook reads signal file  (Phase 204.3 — DONE)
        │         └─→ Agent sees notification
        │
        └─ Agent OFFLINE (tmux has-session -t Alpha = false)
             └─→ spawn_agent.sh Alpha cut-engine   (Phase 205 — NEW)
                  └─→ tmux new-session -d -s Alpha "claude --worktree cut-engine"
                       └─→ Agent boots → session_init → reads notification → claims task
```

## Implementation Plan

### 205.1 — spawn_agent.sh (Zeta, ~15 lines)
```bash
#!/bin/bash
# scripts/spawn_agent.sh — spawn Claude Code agent in tmux
ROLE="${1:?Usage: spawn_agent.sh ROLE WORKTREE}"
WORKTREE="${2:?Usage: spawn_agent.sh ROLE WORKTREE}"
PROJECT_ROOT="$HOME/Documents/VETKA_Project/vetka_live_03"
WORKTREE_PATH="$PROJECT_ROOT/.claude/worktrees/$WORKTREE"
SESSION_NAME="vetka-$ROLE"

# Guard: don't duplicate
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "[SPAWN] $ROLE already running in tmux session $SESSION_NAME"
    exit 0
fi

# Spawn detached
tmux new-session -d -s "$SESSION_NAME" \
    "cd '$WORKTREE_PATH' && claude --worktree '$WORKTREE'"

echo "[SPAWN] $ROLE spawned → tmux attach -t $SESSION_NAME"
```

**Acceptance:** `./scripts/spawn_agent.sh Alpha cut-engine` → tmux session exists, claude running.

### 205.2 — UDS daemon: auto-spawn on notify if offline (Zeta, ~15 lines)
In `scripts/uds_daemon.py`, after receiving notify event:
```python
def on_notify(event: AgentEvent):
    role = event.target_role
    session_name = f"vetka-{role}"

    # Check if agent tmux session exists
    result = subprocess.run(["tmux", "has-session", "-t", session_name],
                          capture_output=True)
    if result.returncode != 0:
        # Agent offline — spawn
        worktree = AGENT_REGISTRY.get(role, {}).get("worktree")
        if worktree:
            subprocess.Popen(["./scripts/spawn_agent.sh", role, worktree])
            logger.info(f"[AUTOSPAWN] {role} was offline, spawning in {worktree}")
```

**Acceptance:** Notify to offline Alpha → daemon auto-spawns → Alpha boots and sees notification.

### 205.3 — agent_registry.yaml: add worktree mapping (Zeta, 5 lines)
Add `worktree` field to each agent entry for spawn_agent.sh lookup.

### 205.4 — Graceful exit on idle (Eta, ~10 lines)
Agent has no tasks for >10min → `exit 0`. tmux session closes.
Prevents zombie agents consuming API quota.

### 205.5 — E2E test (Delta)
1. Ensure no Alpha tmux session
2. Commander notify Alpha
3. Verify tmux session spawned within 10s
4. Verify agent did session_init
5. Kill session, cleanup

## What NOT to Build (Anti-patterns from Research)

| Anti-pattern | Why rejected |
|--------------|-------------|
| Named pipes (mkfifo) | Write blocks if no reader — hangs task_board.py |
| fswatch/entr | Extra dependency, UDS already exists |
| Polling daemon (sleep loop) | CPU waste, not event-driven |
| pm2/supervisord | Overkill for tmux sessions |
| `--initial-prompt` flag | Does not exist in Claude Code CLI |
| Custom WebSocket transport | MCP is request-response, can't server-push |

## Ownership

| Task | Owner | Lines | Depends on |
|------|-------|-------|------------|
| 205.1 spawn_agent.sh | Zeta | 15 | — |
| 205.2 UDS auto-spawn | Zeta | 15 | 205.1 |
| 205.3 Registry update | Zeta | 5 | — |
| 205.4 Graceful exit | Eta | 10 | — |
| 205.5 E2E test | Delta | 30 | 205.1, 205.2 |

**Total new code: ~75 lines.** Everything else reuses Phase 204 infrastructure.

## Success Criteria

Commander sends `action=notify target_role=Alpha` when Alpha is NOT running →
Alpha tmux session auto-spawns within 10s →
Alpha does session_init, sees notification, claims task →
**Zero user intervention. Zero polling. Pure event-driven.**
