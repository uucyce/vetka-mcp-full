# ROADMAP: Synapse Recovery + Snapshot Fix + Session Init Debug
**Date:** 2026-04-05 | **Author:** Commander (pedantic-bell, session #5)
**Status:** IN PROGRESS
**Depends on:** Session #4 debrief, Grok RECON_SNAPSHOT_MERGE_FILE_LOSS

---

## Problem 1: Synapse Files Lost on Main

Session #4 merged ~30 commits via snapshot merge (`strategy=snapshot`).
The snapshot logic on main copies ONLY `allowed_paths` from worktree branches.
Eta's fix `MARKER_205.SNAPSHOT_AUTO_EXPAND` (auto-detects sidecar files) was itself
on `claude/harness-eta` — so the fix was lost by the same bug it fixes.

**Missing from main (exist on worktree branches):**
| File | Branch | Task |
|------|--------|------|
| `scripts/spawn_synapse.sh` | harness, harness-eta | tb_1775329516_99331_1 |
| `scripts/synapse_write.sh` | harness-eta | tb_1775329537_99331_4 |
| `scripts/synapse_wake.sh` | harness-eta | tb_1775329543_99331_5 |
| `scripts/vibe_bridge.py` | harness-eta | tb_1775329556_99331_7 |
| `data/templates/agent_registry.yaml` v2 | both | tb_1775329521_99331_2 |
| `SNAPSHOT_AUTO_EXPAND` in task_board.py | harness-eta | tb_1775327127_71582_1 |

**Present on main (OK):**
- `src/orchestration/task_board.py` (partial — no auto-expand, but Scout code present: 36 refs)
- `src/orchestration/event_bus.py`
- `scripts/uds_daemon.py`
- Welcome screen fix (`f5a3d6430`)
- Scout service (`fc9244bf3` — MARKER_203.SCOUT)

TaskBoard shows all 11 tasks as `verified` but git shows files missing. Desync.

### Fix Steps

**Step 1: Manual file recovery (worktree → main)**
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
git checkout main

# From harness-eta (most complete set)
git checkout claude/harness-eta -- \
  scripts/spawn_synapse.sh \
  scripts/synapse_write.sh \
  scripts/synapse_wake.sh \
  scripts/vibe_bridge.py \
  data/templates/agent_registry.yaml

git add scripts/spawn_synapse.sh scripts/synapse_write.sh \
  scripts/synapse_wake.sh scripts/vibe_bridge.py \
  data/templates/agent_registry.yaml

git commit -m "fix: recover Synapse scripts lost by snapshot merge (no auto-expand) [RECOVERY]"
```

**Step 2: Patch task_board.py — add SNAPSHOT_AUTO_EXPAND**

Insert ~25 lines after the `for fpath in allowed_paths:` loop in snapshot strategy block.
Source: `claude/harness-eta:src/orchestration/task_board.py` lines 4952-4977.
Target: main's `task_board.py`, same location in snapshot block.

```bash
git commit -m "fix: MARKER_205.SNAPSHOT_AUTO_EXPAND — auto-detect sidecar files in snapshot merge"
```

**STOP HERE** — reinit session, verify MCP vetka bridge, then continue.

**Step 3: ACK notifications**
```
vetka_task_board action=ack_notifications role=Commander
```

**Step 4: Fix Zeta workflow violation**
```
vetka_task_board action=update task_id=tb_1775332654_99331_15 status=done_worktree
```

**Step 5: Promote verified tasks to done_main**
11 task IDs: tb_1775329516_99331_1, tb_1775329521_99331_2, tb_1775329525_99331_3,
tb_1775329537_99331_4, tb_1775329543_99331_5, tb_1775329551_99331_6,
tb_1775325630_71181_1, tb_1775327127_71582_1, tb_1775326898_71181_1,
tb_1774336723_1, tb_1774337717_1

**Step 6: Verify**
```bash
ls -la scripts/spawn_synapse.sh scripts/synapse_write.sh scripts/synapse_wake.sh scripts/vibe_bridge.py
grep -c "SNAPSHOT_AUTO_EXPAND" src/orchestration/task_board.py  # > 0
git status  # clean
```

---

## Problem 2: Session Init Loads Stale Docs

### Symptom
New Commander session reads March 22 docs instead of latest session #4 debrief.

### Root Cause
`CLAUDE.md` in worktree `pedantic-bell` has hardcoded Required Reading:
```
- docs/190_ph_CUT_WORKFLOW_ARCH/COMMANDER_ROLE_PROMPT.md          ← March 2026, generic
- docs/190_ph_CUT_WORKFLOW_ARCH/HANDOFF_CUT_COMMANDER_PEDANTIC_BELL_2026-03-22.md  ← session #1 handoff
```

These files DON'T EXIST in the worktree (session #4 confirmed: `Glob` returned empty).
The latest debrief is:
```
docs/190_ph_CUT_WORKFLOW_ARCH/feedback/FEEDBACK_COMMANDER_PEDANTIC_BELL_SESSION4_2026-04-04.md
```

**`vetka_session_init` IS a real tool** — it exists in `vetka_mcp_bridge.py`. The problem
is that the vetka MCP server itself is not connecting, so ALL `mcp__vetka__*` tools
(including `session_init`) are unavailable. This cascades to stale doc loading because
session_init normally provides the correct predecessor advice and doc references.

### Fix: Resolve Problem 3 (vetka bridge) first — then session_init will work automatically.

### Fallback (while vetka bridge is down):
Update CLAUDE.md Required Reading to point to latest debrief as backup init.

---

## Problem 3: MCP vetka-bridge Not Connecting (P1)

**Task:** `tb_1775338576_17631_2` — "FIX: VETKA MCP server disconnects"
**Status:** `scout_recon` (Scout already ran, context attached)
**Priority:** P1 — blocks ALL vetka tools including session_init

### Current State
- **mycelium MCP:** RUNNING (PID 19685) — all `mcp__mycelium__*` tools work (backup)
- **vetka MCP bridge:** NOT RUNNING — zero processes, `mcp__vetka__*` completely absent
- **playwright MCP:** available in deferred tools

### Config (.mcp.json in worktree)
```json
{
  "vetka": {
    "command": ".venv/bin/python",
    "args": ["src/mcp/vetka_mcp_bridge.py"],
    "env": { "VETKA_API_URL": "http://localhost:5001", ... }
  }
}
```
Config looks correct. File exists (125KB), syntax OK. But process never started or was SIGTERM'd.

Note: worktree `.mcp.json` is MISSING playwright entry (main has it). This is the
session #4 bug — `.mcp.json` in worktrees diverged from main.

### Scout Context (from task)
- Bridge starts OK, lists tools, then receives SIGTERM (signal 15) and shuts down
- Possible causes: Flask/FastAPI port conflict on 5001, venv python stale, Claude killing
  process due to timeout/memory, import crash

### Investigation Steps (after Step 2 recovery)
1. Try manual launch: `.venv/bin/python src/mcp/vetka_mcp_bridge.py` — check stderr
2. Check port 5001: `lsof -i :5001` — conflict with VETKA FastAPI?
3. Check if bridge needs FastAPI running first (dependency)
4. Verify `.mcp.json` in worktree matches main (add playwright if missing)
5. Restart Claude Code session after fix to re-trigger MCP init

### Key insight
Mycelium works as full backup — task_board, notifications, health, workflows all
available via `mcp__mycelium__*`. But session_init, AURA memory, and ~30 VETKA-specific
tools are blocked until bridge is fixed

---

## Problem 4: Synapse UX — Window Management + Agent Lifecycle

### Bugs Found (session #5 testing)

1. **osascript iTerm2 syntax error** — `spawn_synapse.sh` кавычки в `$TMUX_CMD` ломают AppleScript. Manual osascript `do script` работает, но скрипт — нет.

2. **`do script` opens in SAME window** — Terminal.app `do script` без `in (make new window)` переиспользует существующее окно. Eta убила Zeta потому что открылась в том же табе.

3. **No auto-init** — Claude Code стартует, показывает меню, но не запускает `vetka session init` автоматически. Агент ждёт промпт.

4. **No session registry** — Commander не знает какой агент в каком окне. Нет маппинга window_id → role.

5. **Zombie cleanup incomplete** — `tmux kill-server` убивает tmux, но Terminal.app окна остаются. Нет единого "kill all agents".

### Required Features (Phase 206.9+)

| Feature | Description | Priority |
|---------|-------------|----------|
| **New window per agent** | `osascript make new window` или iTerm2 `create window`, не `do script` в текущее | P1 |
| **Auto-init prompt** | После spawn, synapse_write отправляет `vetka session init` автоматически | P1 |
| **Session registry** | JSON файл `data/synapse_sessions.json`: role → {pid, window_id, tmux_session, worktree, started_at} | P1 |
| **Commander dashboard** | `action=active_agents` показывает кто жив, кто мёртв, какой таск | P2 |
| **Clean shutdown** | `synapse_kill.sh ROLE` — закрывает tmux + Terminal окно + чистит registry | P2 |
| **Auto-notify on claim** | Agent claims task → Commander gets notification автоматически (уже работает) | Done |
| **Auto-notify Delta on done_worktree** | Agent completes → Delta auto-notified for QA | P2 |
| **Heartbeat ping** | Agents ping Commander каждые 5 минут через notifications (или tmux pane_activity) | P3 |
| **Window title** | Окно Terminal.app показывает `[VETKA] Zeta — harness` в заголовке | P3 |

### spawn_synapse.sh v2 Fix Plan

```bash
# FIX 1: New window every time
osascript -e '
tell application "Terminal"
    activate
    set newWindow to (make new window)
    do script "tmux new-session -s vetka-ROLE \"cd WORKTREE && claude --dangerously-skip-permissions\"" in newWindow
end tell'

# FIX 2: After spawn, wait 5s for Claude to boot, then inject init
sleep 5
bash scripts/synapse_write.sh ROLE "vetka session init"
```

---

## Feedback Memory

Save: `feedback_snapshot_bootstrap.md` — snapshot merge can't bootstrap its own fix.
When the fix for file loss is itself in a worktree, manual `git checkout` is the only escape.

## Commander Code Violation Note

Steps 1-2 of Problem 1 require Commander to write to main. This violates
"Commander never writes code" but the merge pipeline itself is broken —
no agent can fix it through normal flow. Same pattern as session #4.
Document in session #5 debrief.
