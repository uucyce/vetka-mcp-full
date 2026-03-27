# HANDOFF: TaskBoard Forever — Clean Restart Protocol

**Date:** 2026-03-27 05:40 UTC
**Author:** Zeta (Harness Engineer)
**Commit:** `a662c64ff` on main
**Phase:** 200 — TaskBoard Forever

---

## What Was Broken

Phase 199 MARKER changes accumulated over 3 days (14 commits) and turned TaskBoard from instant (<100ms) to unusable (60+ seconds):

| Problem | Root Cause | Impact |
|---------|-----------|--------|
| `_backfill_modules()` in `__init__` | 50 writes × 14 processes = 700 competing writes at startup | Init deadlock |
| `timeout=30` in `sqlite3.connect()` | Processes hang 30s instead of failing fast | 60s session_init |
| `busy_timeout=30000` | Same — 30s wait at SQLite level | Compounded hang |
| `_execute_with_retry()` with sleep | 5 retries × exponential backoff on TOP of 30s timeout | +3s per write |
| `get_queue()` via SQL | 7 calls × 450 rows × json.loads = 3150 deserializations | Slow reads |
| `_save_task()` no cache update | Cache stale after writes | Incoherent reads |

## What Was Fixed (commit `a662c64ff`)

6 surgical changes in `src/orchestration/task_board.py`:

1. **`_backfill_modules()` removed from `__init__`** — available via `action=backfill_modules`
2. **`sqlite3.connect()` — no `timeout=` parameter** — back to Python default (5s)
3. **`busy_timeout=5000`** — canonical value from Phase 192 architecture doc
4. **`_execute_with_retry()` deleted entirely** — `_save_task()` uses `with self.db:` directly
5. **`get_queue()` reads from `self.tasks` cache** — zero SQL, zero json.loads
6. **`_save_task()` updates `self.tasks[id]`** — write-through cache coherence

**Verified:** 14 concurrent inits complete in 0.17 seconds (was 60+).

## Architecture Bible

`docs/200_taskboard_forever/ARCHITECTURE_TASKBOARD_BIBLE.md` — 16 sections covering:
- Connection contract (PRAGMA values, why each matters)
- Read path (cache) vs Write path (SQL + cache)
- Init sequence (what MUST and MUST NOT happen)
- Concurrency model (WAL, busy_timeout, why it works)
- Integration points (MCP, REST, session_init, protocol_guard, heartbeat)
- Performance invariants (targets for every operation)
- NEVER DO list (8 rules, each learned from a real incident)

## Clean Restart Protocol

### Step 1: Kill everything

```bash
# Close ALL Claude Code terminal windows (every agent)
# Then verify no Python processes hold the DB:
lsof /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/task_board.db

# If anything remains, kill them:
lsof -t /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/task_board.db | xargs kill

# Optional: restart Qdrant docker
docker restart qdrant
```

### Step 2: Clean WAL (optional but recommended)

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# Check WAL size
ls -lh data/task_board.db-wal

# Force checkpoint to clean WAL (only when no processes are connected)
python3 -c "
import sqlite3
conn = sqlite3.connect('data/task_board.db')
print(conn.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone())
conn.close()
print('WAL cleaned')
"
```

### Step 3: Verify the fix is in place

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# Confirm commit
git log --oneline -1
# Should show: a662c64ff fix: MARKER_200.FOREVER ...

# Confirm no _backfill_modules in __init__
python3 -c "
import inspect
from src.orchestration.task_board import TaskBoard
src = inspect.getsource(TaskBoard.__init__)
assert '_backfill_modules' not in src, 'FAIL: _backfill_modules still in __init__!'
print('PASS: __init__ clean')
"

# Confirm busy_timeout=5000
python3 -c "
from src.orchestration.task_board import get_task_board
board = get_task_board()
bt = board.db.execute('PRAGMA busy_timeout').fetchone()[0]
assert bt == 5000, f'FAIL: busy_timeout={bt}'
print(f'PASS: busy_timeout={bt}')
board.db.close()
"

# Confirm get_queue uses cache (works even with closed DB)
python3 -c "
from src.orchestration.task_board import get_task_board
board = get_task_board()
n = len(board.get_queue(status='pending'))
board.db.close()  # Close DB connection
n2 = len(board.get_queue(status='pending'))  # Should still work from cache
assert n == n2, f'FAIL: cache broken ({n} vs {n2})'
print(f'PASS: get_queue from cache ({n} pending tasks)')
"
```

### Step 4: Open agents

Open new Claude Code terminals. Each will start fresh MCP with the fixed code.

First agent to test: run `vetka_session_init` — should complete in <2 seconds.

---

## What Delta Needs To Do

After clean restart, pull main and update two tests in `tests/test_phase200_taskboard_forever.py`:

1. `test_busy_timeout_is_30000` -> rename to `test_busy_timeout_is_5000`, assert `== 5000`
2. `test_connect_uses_timeout_30` -> rename to `test_connect_timeout_default`, assert NO `timeout=` in source

Then run: `python3 -m pytest tests/test_phase200_taskboard_forever.py -v`

Expected: 15/15 PASS, 0 xfail, 0 fail.

---

## What Epsilon Needs To Do

Update docs (already dispatched):
- S3: `get_queue()` now reads from cache, not SQL
- S3.init: remove `_backfill_modules()` from init sequence
- Add full MCC integration map (task_routes.py, mcc_routes.py, group_message_handler.py, agent_pipeline.py, mycelium_heartbeat.py)

---

## Files Changed

| File | Change |
|------|--------|
| `src/orchestration/task_board.py` | 6 surgical fixes (see above) |
| `docs/200_taskboard_forever/ARCHITECTURE_TASKBOARD_BIBLE.md` | Architecture bible (new) |
| `docs/200_taskboard_forever/HANDOFF_CLEAN_RESTART_2026-03-27.md` | This document (new) |

## Related Documents

| Doc | Location |
|-----|----------|
| Original SQLite architecture | `docs/192_task_SQLite/ARCHITECTURE_TASKBOARD_SQLITE.md` |
| Original SQLite roadmap | `docs/192_task_SQLite/ROADMAP_192_TASKBOARD_SQLITE.md` |
| Epsilon Manual | `docs/200_taskboard_forever/TASKBOARD_MANUAL.md` |
| Epsilon Bible | `docs/200_taskboard_forever/TASKBOARD_ARCHITECTURE_BIBLE_EPSILON.md` |
| Delta Tests | `tests/test_phase200_taskboard_forever.py` |

---

*The evil spirit was 14 commits of accumulated workarounds, each trying to fix the symptoms of the previous one. The exorcism was 6 deletions.*
