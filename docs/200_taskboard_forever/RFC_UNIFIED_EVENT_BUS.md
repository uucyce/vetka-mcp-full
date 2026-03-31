# RFC: Unified Event Bus for TaskBoard
**Date:** 2026-03-28 | **Authors:** Eta (Q6 insight), Zeta (formalization)
**Status:** RFC — approved direction
**Phase:** 201+
**Referenced in:** `ARCHITECTURE_TASKBOARD_BIBLE.md` Section 17
**Implementation design:** `VETKA_RT_COMMS_ARCHITECTURE.md` Section 3

## Origin

Independently proposed by two consecutive Eta agents:

1. **Eta Session 1** (predecessor): "one event bus instead of 15 subsystems"
2. **Eta Session 2** (2026-03-28): Full Q6 answer — "a single event stream where
   notification = task = memory"

## Problem Statement

VETKA multi-agent system has 6+ communication channels that evolved independently:

```
Agent Action
    ├── status_history (task_board.py: _append_history)
    ├── notifications  (task_board.py: notify action → SQLite)
    ├── CORTEX memory  (cortex.py: embeddings → Qdrant)
    ├── ENGRAM L1      (engram_l1.py: danger/pattern cache)
    ├── debrief Q1-Q3  (smart_debrief.py: task completion)
    └── _notify_board_update (task_board.py: HTTP callback)
```

**Consequences:**
- 37% of REFLEX entries are "dead signals" — emitted, never consumed
- Commander sends a directive → notification but NOT in status_history → lost context
- Agent completes task → 3 separate writes, 3 failure modes
- No unified "what happened in the system" query

## Solution: Event Bus

One trigger point, multiple subscribers. See `VETKA_RT_COMMS_ARCHITECTURE.md` for
full implementation design including AgentEvent dataclass, EventBus class,
subscriber interfaces, UDS daemon, and piggyback delivery.

### One Action, Five Outcomes

```
Alpha completes task
    → EventBus.emit(AgentEvent(type="task_completed", ...))
        ├── TaskBoardSubscriber   → status_history + done_worktree
        ├── NotificationSubscriber → Commander inbox entry
        ├── AuditSubscriber       → event_log row
        ├── UDSPublisher          → push to all MCP servers
        └── (future) MemorySubscriber → Q1-Q3 → CORTEX embed
```

Zero data loss. Zero intervals. Zero dead signals.

## Migration Path

Phase 1: AgentEvent + EventBus + AuditSubscriber + piggyback delivery
Phase 2: UDS Daemon + UDSPublisher
Phase 3: MemorySubscriber + EngramSubscriber
Phase 4: MCCSubscriber (WebSocket)

Each phase is standalone useful. See VETKA_RT_COMMS_ARCHITECTURE.md Section 5.

## Constraints

- Emit <1ms, subscriber failures don't block emitter
- SQLite remains authoritative — bus is routing, not storage
- No distributed bus needed — all in one process (+ UDS for cross-process)
