# CURSOR BRIEF Phase 130: Agent Coordination System

## Context
Phase 129 created dual MCP (VETKA + MYCELIUM). Now we have 3+ agents working in parallel:
- **Opus** (Claude Code) — architecture, core code, tests
- **Cursor** — UI, cleanup, docs
- **Dragon** (MYCELIUM pipeline) — automated build/fix/research via LLM teams

**Problem:** No one knows what anyone else is doing. Commits land, tasks complete,
but the coordination is manual (human relays briefs between agents).

**Solution:** Extend TaskBoard + Digest into a **shared coordination layer**.
Every agent reads/writes the same board. DevPanel shows live dashboard.

## Architecture

```
                    data/task_board.json
                   ╱          │          ╲
        Opus writes      Dragon writes     Cursor reads
     (via git hook)   (via pipeline)    (via DevPanel UI)
                          │
                    MYCELIUM WS :8082
                          │
                    DevPanel (real-time)
```

**No new services.** TaskBoard JSON is the shared bus.
Git commit hook auto-records who committed what.

---

## C16: Agent Assignment in TaskBoard

### 16A: Add Agent Fields to Task Model

**File:** `src/orchestration/task_board.py`

Uncomment and implement the planned fields (lines 213-217):

```python
# In add_task() — new optional fields:
"assigned_to": assigned_to,       # "opus" | "cursor" | "dragon" | "grok" | None
"assigned_at": None,              # ISO timestamp when claimed
"agent_type": agent_type,         # "claude_code" | "cursor" | "mycelium" | "human"
"commit_hash": None,              # Git commit that completed this task
"commit_message": None,           # First line of commit message
```

**add_task()** — add `assigned_to=None, agent_type=None` params.

**Status lifecycle** — add "claimed" status:
```python
VALID_STATUSES = {"pending", "queued", "claimed", "running", "done", "failed", "cancelled", "hold"}
```

- `pending` → `claimed` (agent takes task)
- `claimed` → `running` (pipeline/work starts)
- `running` → `done` / `failed`

**claim_task(task_id, agent_name, agent_type):**
```python
def claim_task(self, task_id: str, agent_name: str, agent_type: str = "unknown"):
    task = self.get_task(task_id)
    if task["status"] not in ("pending", "queued"):
        return {"success": False, "error": f"Task {task_id} is {task['status']}, can't claim"}
    self.update_task(task_id, {
        "status": "claimed",
        "assigned_to": agent_name,
        "agent_type": agent_type,
        "assigned_at": datetime.now().isoformat(),
    })
    return {"success": True, "task_id": task_id, "assigned_to": agent_name}
```

**complete_task(task_id, commit_hash=None, commit_message=None):**
```python
def complete_task(self, task_id: str, commit_hash=None, commit_message=None):
    update = {"status": "done", "completed_at": datetime.now().isoformat()}
    if commit_hash:
        update["commit_hash"] = commit_hash
        update["commit_message"] = commit_message
    self.update_task(task_id, update)
```

### 16B: MCP Tool Update

**File:** `src/mcp/tools/task_board_tools.py`

Add to `handle_task_board`:
- action=`claim` → `board.claim_task(task_id, agent_name, agent_type)`
- action=`complete` → `board.complete_task(task_id, commit_hash, commit_message)`

Add new arguments to schema:
- `assigned_to`: string
- `agent_type`: string
- `commit_hash`: string

### 16C: REST API Update

**File:** `src/api/debug_routes.py`

Add endpoints:
- `POST /api/debug/task-board/claim` — `{task_id, agent_name, agent_type}`
- `POST /api/debug/task-board/complete` — `{task_id, commit_hash, commit_message}`

---

## C17: Commit Auto-Detection

### 17A: Git Hook Integration

**File:** `src/orchestration/task_board.py` — new method

When a commit happens (detected by digest auto-sync or git hook):

```python
def auto_complete_by_commit(self, commit_hash: str, commit_message: str):
    """Auto-complete tasks mentioned in commit message.

    Looks for patterns:
    - "Phase 129.C13" → find task with tag "C13" or title containing "C13"
    - "tb_xxxx" → direct task ID reference
    - "MARKER_129.6" → find task with matching marker
    """
    completed = []
    for task in self.get_queue(status="claimed") + self.get_queue(status="running"):
        if self._commit_matches_task(task, commit_message):
            self.complete_task(task["id"], commit_hash, commit_message)
            completed.append(task["id"])
    return completed
```

**_commit_matches_task():** Check if commit message mentions task title, ID, or tags.

### 17B: Wire Into Digest Auto-Sync

**File:** `src/orchestration/task_board.py` or git hook script

After `auto_sync_from_git()` runs (existing Phase 119.6), call:
```python
board.auto_complete_by_commit(new_commit_hash, commit_message)
```

This runs automatically on every `vetka_git_commit` call.

---

## C18: DevPanel Agent Dashboard

### 18A: Agent Status Row in Board Tab

**File:** `client/src/components/panels/DevPanel.tsx`

Above the task list, add a row showing active agents:

```
┌─────────────────────────────────────────────────┐
│ 🟢 Opus: O7 (health check)     2m ago          │
│ 🟢 Cursor: C18 (DevPanel)      now             │
│ ⏳ Dragon: tb_xxx (building)    45s             │
│ ⚫ Grok: idle                                   │
└─────────────────────────────────────────────────┘
```

**Data source:** Derive from task_board.json:
- Group tasks by `assigned_to` where status is "claimed" or "running"
- Show latest task per agent + elapsed time
- Green = active (claimed/running), Grey = idle (no active tasks)

**Style:** Nolan monochrome. Monospace. Compact row, no cards.

### 18B: Commit Column in Task List

**File:** `client/src/components/panels/TaskCard.tsx`

Add commit hash badge to completed tasks:
```
✅ Phase 129.C13  [cursor]  0a8415e9  2m ago
✅ Phase 129 MCP  [opus]    f83cdfeb  15m ago
⏳ O7 Health      [opus]    —         running
```

Show: status icon + title + [agent] + commit hash (truncated 8 chars) + time

### 18C: Task Board SocketIO Event Enhancement

When task is claimed/completed, the `task_board_updated` event should include:
```json
{
  "action": "task_claimed",
  "task_id": "tb_xxx",
  "assigned_to": "cursor",
  "agent_type": "cursor"
}
```

DevPanel can then show toast: "Cursor claimed: C18 DevPanel Agent Dashboard"

---

## File Summary

| File | Action | Lines | Priority |
|------|--------|-------|----------|
| `src/orchestration/task_board.py` | MODIFY | +80 | P0 |
| `src/mcp/tools/task_board_tools.py` | MODIFY | +30 | P0 |
| `src/api/debug_routes.py` | MODIFY | +25 | P1 |
| `client/src/components/panels/DevPanel.tsx` | MODIFY | +40 | P1 |
| `client/src/components/panels/TaskCard.tsx` | MODIFY | +15 | P1 |

## Markers
- MARKER_130.C16A: Agent fields in TaskBoard
- MARKER_130.C16B: MCP tool claim/complete actions
- MARKER_130.C16C: REST API claim/complete endpoints
- MARKER_130.C17A: Git commit auto-detection
- MARKER_130.C17B: Wire digest auto-sync
- MARKER_130.C18A: Agent status row in DevPanel
- MARKER_130.C18B: Commit column in TaskCard
- MARKER_130.C18C: Enhanced task_board_updated events

## Testing
- TaskBoard: claim_task, complete_task, auto_complete_by_commit
- MCP: action=claim, action=complete
- REST: POST /claim, POST /complete
- DevPanel: agent row renders from task data

## Usage After Implementation

**Opus (Claude Code) workflow:**
```
1. mycelium_task_board action=claim task_id=tb_xxx assigned_to=opus agent_type=claude_code
2. ... work on task ...
3. vetka_git_commit → auto-detects → task marked done with commit hash
```

**Cursor workflow:**
```
1. Read task_board.json → find tasks assigned_to=cursor
2. Work on task
3. Git commit with "Phase 130.C18" in message → auto-complete
```

**Dragon (MYCELIUM pipeline):**
```
1. mycelium_task_dispatch → claims task automatically
2. Pipeline runs → done/failed with stats
3. Commit hash recorded if auto_write=True
```

**DevPanel shows:**
- Who is working on what RIGHT NOW
- Completed tasks with commit hashes
- Agent idle/busy status

## Estimated Effort
- C16 (TaskBoard model): 2h
- C17 (Commit detection): 1h
- C18 (DevPanel UI): 2h
- Total: ~5h
