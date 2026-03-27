# RECON: DDL Init Optimization — sqlite_master Fast Path

**Phase:** 199
**Status:** Active
**Owner:** Zeta (Harness)
**Created:** 2026-03-26
**Branch:** claude/harness

---

## Problem

48 concurrent agent processes all call `TaskBoard.__init__()` which runs
`_ensure_schema()` → `executescript()` with 7 DDL statements (CREATE TABLE IF
NOT EXISTS × 3 + CREATE INDEX × 4). Even with `IF NOT EXISTS`, SQLite still
acquires an exclusive lock to parse and validate each statement.

This is the "48 people trying to enter one door" problem. FTS5 is NOT the
cause — it's the DDL `executescript()` blocking on every init.

## Root Cause

```
TaskBoard.__init__()
  → _connect()           # PRAGMA journal_mode=WAL (exclusive lock!)
  → _ensure_schema()     # executescript() with 7 DDL (exclusive lock!)
  → _run_migrations()    # FTS5 CREATE VIRTUAL TABLE (exclusive lock!)
  → _migrate_json_to_sqlite()
  → _load_all_tasks()
  → _backfill_modules()
  → PRAGMA wal_checkpoint(PASSIVE)
```

Even the singleton (`get_task_board()`) doesn't help when:
- Multiple Python processes (not threads) each have their own singleton
- First init in each process pays full DDL cost
- 48 processes × 7 DDL statements = 336 exclusive lock acquisitions

## Solution: sqlite_master Fast Path

**Before running any DDL, check if tables already exist:**

```python
def _ensure_schema(self):
    # Fast path: check sqlite_master for 'tasks' table
    exists = self.db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='tasks'"
    ).fetchone()
    if exists:
        return  # Schema already exists — skip all DDL

    # Slow path: first-time creation only
    with self.db:
        self.db.executescript("""...""")
```

This replaces 7 DDL exclusive-lock operations with 1 read-only query.
The `sqlite_master` query uses only a shared (reader) lock — all 48
processes can run it concurrently with zero contention.

## Files to Modify

| File | Change |
|------|--------|
| `src/orchestration/task_board.py` | `_ensure_schema()`: sqlite_master check before DDL |
| `src/orchestration/task_board.py` | `_run_migrations()`: sqlite_master check before FTS5 DDL |
| `src/memory/mgc_cache.py` | `_init_gen1_db()`: sqlite_master check before CREATE TABLE |

## Constraints

- **DO NOT touch FTS5 logic** — it works, only guard the DDL path
- **DO NOT change table schemas** — only optimize the creation check
- Keep `IF NOT EXISTS` as safety net even with fast path
- `_run_migrations()` version check is already fast — just guard the executescript inside

## Test Plan

```python
# Verify fast path: second TaskBoard() init skips DDL
board1 = TaskBoard(db_path)
# Monkey-patch executescript to raise if called
board1.db.executescript = lambda sql: (_ for _ in ()).throw(AssertionError("DDL should not run"))
board2 = TaskBoard(db_path)  # Should NOT raise — fast path skips DDL
```
