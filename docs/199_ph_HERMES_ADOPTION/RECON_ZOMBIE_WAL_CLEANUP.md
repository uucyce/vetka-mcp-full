# RECON: Zombie Process Cleanup + WAL Checkpoint Hardening

**Phase:** 199
**Status:** Active
**Owner:** Zeta (Harness)
**Created:** 2026-03-26
**Branch:** claude/harness

---

## Problem

Stale MCP/agent processes hold open SQLite connections, preventing WAL
checkpointing and bloating the WAL file. Combined with 48 concurrent
inits all fighting for exclusive locks, the system grinds to a halt.

## Tasks

### 1. Kill Zombie Processes (Immediate)

Find and kill stale Python processes holding SQLite locks on task_board.db:

```bash
# Find processes with open handles on task_board.db
lsof +D /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/ 2>/dev/null | grep task_board

# Kill stale MCP bridge / mycelium processes
# (careful: only kill orphaned ones, not active sessions)
```

### 2. WAL Checkpoint Hardening

Current code (line 210-213):
```python
try:
    self.db.execute("PRAGMA wal_checkpoint(PASSIVE)")
except Exception:
    pass
```

Improvement:
- Move WAL checkpoint to AFTER full init (after _load_all_tasks)
- Add TRUNCATE checkpoint option for clean startup
- Log checkpoint result (pages checkpointed vs total)

### 3. Connection Cleanup

Add `__del__` or context manager to TaskBoard to ensure connections
are closed on process exit. Orphaned connections = orphaned WAL readers.

## Files to Modify

| File | Change |
|------|--------|
| `src/orchestration/task_board.py` | WAL checkpoint logging + TRUNCATE option |
| `src/orchestration/task_board.py` | `close()` method + atexit registration |
| `src/memory/mgc_cache.py` | Connection lifecycle cleanup |

## Constraints

- **DO NOT touch FTS5** — it works fine
- Zombie kill is a one-time manual action, not code change
- WAL checkpoint should remain PASSIVE during normal operation
- Only use TRUNCATE at explicit startup/shutdown boundaries
