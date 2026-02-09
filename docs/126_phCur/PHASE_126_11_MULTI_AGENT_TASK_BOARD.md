# Phase 126.11: Multi-Agent Task Board Support

**Author:** Claude Opus 4.5 (Claude Code via MCP)
**Date:** 2026-02-09
**Status:** PROPOSAL

---

## Current State Analysis

### Architecture

```
Task Board (task_board.py)
    │
    ├── add_task()     → creates task with status="pending"
    ├── get_next_task() → returns highest-priority pending task
    ├── dispatch_task() → creates AgentPipeline, sets status="running"
    │       │
    │       └── AgentPipeline (Mycelium) executes task
    │               │
    │               └── On complete: status="done"|"failed"
    │
    └── MCP Tools:
        ├── vetka_task_board    → CRUD operations
        ├── vetka_task_dispatch → triggers dispatch_task()
        └── vetka_task_import   → bulk import from files
```

### Problem: Tightly Coupled to Mycelium

Current system assumes ALL tasks are executed by Mycelium Pipeline:

1. **dispatch_task()** directly creates `AgentPipeline` and runs it
2. **status="running"** only set internally by dispatch, not claimable externally
3. **No tracking** of which agent is working on a task
4. **External agents (Claude Code, Claude Desktop, Grok)** cannot:
   - See available tasks in session_init
   - Claim a task they want to work on
   - Mark task as complete when done

### What Works Today

| Agent | Can Add Tasks | Can See Tasks | Can Claim | Can Execute |
|-------|--------------|---------------|-----------|-------------|
| Mycelium Pipeline | Yes | Yes | Auto | Yes (native) |
| Claude Code (MCP) | Yes | Yes (list) | **NO** | **NO** |
| Claude Desktop | via chat | via DevPanel | **NO** | **NO** |
| Grok | via chat | via DevPanel | **NO** | **NO** |

---

## Proposed Solution

### New Fields in Task Schema

```python
# MARKER_126.11A: Multi-agent claim support
{
    "id": "tb_123",
    "title": "Fix bug",
    "status": "pending",  # NEW: "claimed" added to VALID_STATUSES

    # NEW FIELDS:
    "claimed_by": None,        # Agent ID who claimed the task
    "claimed_at": None,        # Timestamp when claimed
    "claim_expires": None,     # Auto-release if agent goes silent
    "agent_type": None,        # "mycelium" | "mcp" | "chat" | "external"
}
```

### New Methods in TaskBoard

```python
# MARKER_126.11B: Claim/release methods
def claim_task(self, task_id: str, agent_id: str, agent_type: str = "mcp") -> bool:
    """
    External agent claims a task for manual execution.
    Sets status="claimed", records agent info.
    Returns False if task is already claimed/running.
    """

def release_task(self, task_id: str, agent_id: str, new_status: str = "done") -> bool:
    """
    Agent releases task after completion.
    Sets status to done/failed/pending (if abandoned).
    """

def get_claimable_tasks(self, limit: int = 5) -> List[Dict]:
    """
    Returns pending tasks ready for claiming (deps satisfied).
    For session_init injection.
    """
```

### New MCP Tool: vetka_task_claim

```python
# MARKER_126.11C: MCP tool for claiming tasks
TASK_CLAIM_SCHEMA = {
    "action": "claim" | "release" | "my_tasks",
    "task_id": "...",           # For claim/release
    "agent_id": "...",          # Auto-filled from session
    "status": "done" | "failed" # For release
}
```

### Modified session_init Response

```python
# MARKER_126.11D: Include claimable tasks in session_init
{
    "session_id": "...",
    "project_digest": {...},

    # NEW:
    "available_tasks": [
        {
            "id": "tb_123",
            "title": "Fix file positioning",
            "priority": 2,
            "phase_type": "fix",
            "complexity": "low"
        },
        # ... up to 5 top-priority claimable tasks
    ],
    "my_claimed_tasks": []  # Tasks this agent has claimed
}
```

---

## Status Flow

### Current Flow (Mycelium-only)

```
pending → running → done/failed
            ↑
        dispatch_task() creates pipeline
```

### Proposed Flow (Multi-Agent)

```
pending → claimed → running → done/failed
    ↓         ↓         ↓
 external  manual   pipeline
  agent    work    (Mycelium)
            ↓
        release_task()
```

| Status | Who Sets It | Meaning |
|--------|------------|---------|
| pending | add_task() | Task waiting for someone |
| **claimed** | claim_task() | External agent working on it |
| running | dispatch_task() | Mycelium pipeline executing |
| done | release_task() / pipeline | Completed |
| failed | release_task() / pipeline | Failed |
| hold | Doctor triage | Needs human approval |
| cancelled | cancel_task() | Aborted |

---

## Implementation Plan

### MARKER Locations

| Marker | File | Purpose |
|--------|------|---------|
| MARKER_126.11A | task_board.py | New fields in task schema |
| MARKER_126.11B | task_board.py | claim_task(), release_task(), get_claimable_tasks() |
| MARKER_126.11C | task_board_tools.py | New vetka_task_claim MCP tool |
| MARKER_126.11D | mcp_bridge.py | session_init includes available_tasks |
| MARKER_126.11E | DevPanel.tsx | Show "claimed by" in task cards |

### Files to Modify

1. **src/orchestration/task_board.py**
   - Add "claimed" to VALID_STATUSES
   - Add claim fields to task schema
   - Implement claim_task(), release_task(), get_claimable_tasks()
   - Add claim expiry logic (e.g., 30 min auto-release)

2. **src/mcp/tools/task_board_tools.py**
   - Add vetka_task_claim tool
   - Schema: action, task_id, agent_id, status

3. **src/mcp/vetka_mcp_bridge.py** (session_init)
   - Call get_claimable_tasks() in session_init
   - Include in response for agent awareness

4. **client/src/components/panels/DevPanel.tsx** (optional)
   - Show claimed_by in TaskCard
   - Visual indicator for claimed tasks

---

## Usage Example

### Claude Code claiming a task:

```
# 1. Session init shows available tasks
session = vetka_session_init()
# Response includes: available_tasks: [{id: "tb_123", title: "Fix X", ...}]

# 2. Agent claims task
vetka_task_claim(action="claim", task_id="tb_123", agent_id="claude_code_session_abc")
# Response: {success: true, claimed: true, expires_in: 1800}

# 3. Agent works on task (manually, not via Mycelium)

# 4. Agent releases task when done
vetka_task_claim(action="release", task_id="tb_123", status="done")
# Response: {success: true, task_status: "done"}
```

---

## Open Questions

1. **Claim Expiry**: How long before auto-release? (30 min? configurable?)
2. **Agent Identity**: Use session_id? Need stable agent IDs?
3. **Concurrency**: What if Mycelium dispatch_task() called on claimed task?
4. **UI**: Should DevPanel show "Claim" button for humans?

---

## Summary

Current Task Board is Mycelium-only. To support multi-agent work:

1. Add "claimed" status and claim_* fields
2. Add claim_task() / release_task() methods
3. Add vetka_task_claim MCP tool
4. Include available_tasks in session_init

This enables Claude Code, Claude Desktop, Grok, and any MCP agent to:
- See available tasks on connect
- Claim tasks they want to work on
- Mark tasks complete when done
- Coexist with Mycelium pipeline execution

**Estimated Effort:** 1 day
**Priority:** P2 (Quality of Life)
