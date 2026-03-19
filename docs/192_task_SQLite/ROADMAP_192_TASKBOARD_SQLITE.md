# Roadmap: Phase 192 — TaskBoard SQLite Migration

**Commander:** Opus
**Date:** 2026-03-19
**Agents:** 2 parallel + Opus review
**Est. total:** 2-3 hours

---

## Execution Plan: 2 Agents

### Why 2, not 3?

The core migration is in ONE file (`task_board.py`). Three agents would conflict on the same file. Optimal split:

- **Agent A (Core):** SQLite backend — the critical path. Sequential, no parallelism possible within.
- **Agent B (Tests + Integration):** Write tests + migration script. Can start immediately in parallel.
- **Opus (Commander):** Reviews, merges, final integration test.

```
Timeline:
  ┌─ Agent A: Core backend (W1→W2→W3) ────────────────────┐
  │  task_board.py rewrite                                  │
  │                                                         ├──→ Opus: Integration
  │  ┌─ Agent B: Tests + Migration (W1→W2) ───────────┐    │     review + merge
  │  │  migration script + test suite                  │    │
  │  └─────────────────────────────────────────────────┘    │
  └─────────────────────────────────────────────────────────┘
```

---

## Wave 1 — Foundation (parallel)

### Agent A: W1 — SQLite storage layer in task_board.py

**Task:** `192.1: SQLite storage layer — _connect, _ensure_schema, _save_task, _load_task`

**What to do:**
1. Add `import sqlite3` to task_board.py
2. Add constant: `TASK_BOARD_DB = _MAIN_ROOT / "data" / "task_board.db"`
3. Add `INDEXED_COLUMNS` list (id, title, priority, status, phase_type, complexity, project_id, assigned_to, agent_type, created_at, started_at, completed_at, closed_at, commit_hash, commit_message, created_by, assigned_at, description, updated_at)
4. Add methods to TaskBoard class:
   - `_connect() -> sqlite3.Connection` — open DB, set WAL mode, busy_timeout=5000, row_factory
   - `_ensure_schema()` — CREATE TABLE IF NOT EXISTS + indexes
   - `_task_to_row(task: dict) -> dict` — split indexed vs extra JSON
   - `_row_to_task(row) -> dict` — merge row + parsed extra back to dict
   - `_save_task(task: dict)` — INSERT OR REPLACE single task
   - `_delete_task(task_id: str)` — DELETE single row
   - `_load_all_tasks() -> Dict[str, dict]` — SELECT * (for migration/startup)
   - `_save_settings()` — persist settings to `settings` table
   - `_load_settings()` — read settings from `settings` table

**Files:** `src/orchestration/task_board.py`
**Constraint:** Do NOT modify existing methods yet. Only ADD new methods.

---

### Agent B: W1 — Migration script + test scaffold

**Task:** `192.2: JSON→SQLite migration script + test suite`

**What to do:**
1. Create `src/orchestration/task_board_migrate.py`:
   - `migrate_json_to_sqlite(json_path, db_path)` — read JSON, INSERT all tasks
   - `export_sqlite_to_json(db_path, json_path)` — for rollback/debug
   - `verify_migration(json_path, db_path)` — count + spot-check tasks match
   - CLI entry: `python -m src.orchestration.task_board_migrate`
2. Create `tests/test_phase192_sqlite_migration.py`:
   - `test_create_schema` — schema creation on empty DB
   - `test_task_roundtrip` — dict → row → dict preserves all fields
   - `test_save_load_task` — write + read single task
   - `test_concurrent_writes` — two connections write simultaneously, no data loss
   - `test_migration_json_to_sqlite` — migrate real task_board.json, verify count
   - `test_migration_preserves_all_fields` — check 5 random tasks, all fields match
   - `test_project_id_filter` — query by project_id works
   - `test_status_filter` — query by status works
   - `test_get_queue_ordering` — priority + created_at sort
   - `test_settings_persistence` — save/load settings
   - `test_wal_mode` — verify WAL is active

**Files:** `src/orchestration/task_board_migrate.py`, `tests/test_phase192_sqlite_migration.py`
**Note:** Tests should import from task_board.py and test the NEW methods (W1 Agent A). Use `tmp_path` fixture for test DBs.

---

## Wave 2 — Core Rewrite (parallel)

### Agent A: W2 — Replace _load/_save + rewrite query methods

**Task:** `192.3: Replace _load/_save with SQLite, update get_queue/get_task`

**What to do:**
1. Rewrite `__init__()`:
   - Call `self._connect()` instead of `self._load()`
   - Keep `self.tasks` as empty dict (backward compat cache)
   - On first connect: if DB empty but JSON exists → auto-migrate
2. Rewrite `_load()`:
   - Now reads from SQLite: `self.tasks = self._load_all_tasks()`
   - Called only for full refresh (rare)
3. Rewrite `_save()`:
   - **Remove** the "write entire file" logic
   - Now just calls `_save_settings()` (tasks are saved per-operation)
4. Update `add_task()`:
   - After building task dict → `self._save_task(task)` instead of `self.tasks[id] = task; self._save()`
   - Still maintain `self.tasks[id] = task` for in-process cache
5. Update `update_task()`:
   - Modify task → `self._save_task(task)` instead of `self._save()`
6. Update `remove_task()`:
   - `self._delete_task(task_id)` + `del self.tasks[task_id]`
7. Update `get_task()`:
   - Read from DB: `SELECT WHERE id=?` → `_row_to_task()`
   - Update in-memory cache
8. Update `get_queue()`:
   - `SELECT ... WHERE status=? ORDER BY priority, created_at`
   - Return list of dicts
9. Update `claim_task()`, `complete_task()`, `cancel_task()`:
   - After modifying task dict → `self._save_task(task)`
10. Update `auto_complete_by_commit()`:
    - Query DB for matching tasks instead of iterating self.tasks
11. Update `get_board_summary()`:
    - Use SQL COUNT/GROUP BY for efficiency
12. Keep `_notify_board_update()` calls in place

**Files:** `src/orchestration/task_board.py`
**Critical rule:** Every method that modifies a task must call `self._save_task(task)`. Every method that reads must query DB.

---

### Agent B: W2 — Update existing tests + integration tests

**Task:** `192.4: Update existing tests for SQLite backend`

**What to do:**
1. Update `tests/test_phase121_task_board.py`:
   - Tests should still pass — same API
   - Change any direct JSON file reads to use board methods
   - Use tmp_path for DB location: `TaskBoard(board_file=tmp_path / "test.db")`
2. Update `tests/test_phase136_task_board_claim_complete.py`:
   - Same — should pass with minimal changes
3. Add to `tests/test_phase192_sqlite_migration.py`:
   - `test_concurrent_add_no_data_loss` — THE critical test:
     - Spawn 3 threads, each adds 10 tasks simultaneously
     - Verify all 30 tasks exist in DB
   - `test_auto_migrate_on_startup` — if JSON exists but DB doesn't → migrate
   - `test_fallback_to_json_if_sqlite_fails` — if DB locked → graceful error

**Files:** `tests/test_phase121_task_board.py`, `tests/test_phase136_task_board_claim_complete.py`, `tests/test_phase192_sqlite_migration.py`

---

## Wave 3 — Cleanup (sequential, Opus)

### Opus: W3 — Integration, cleanup, verify

**Task:** `192.5: Integration test + cleanup + JSON backup`

**What to do:**
1. Run full test suite
2. Test with real data:
   - Migrate actual `data/task_board.json` → `data/task_board.db`
   - Verify task count matches
   - Test MCP `list project_id=cut` — should return 57 tasks
   - Test MCP `list project_id=СГЕ` — smart filter works
3. Remove dead code:
   - Old `_TASK_BOARD_FALLBACK` JSON logic (replace with SQLite fallback)
   - Old `_compute_integrity_sig()` (SQLite has its own checksums)
4. Update `__init__` in `task_board.py`:
   - Accept both `.json` (legacy) and `.db` (new) as board_file
   - Auto-detect by extension
5. Rename `data/task_board.json` → `data/task_board.json.bak`
6. Create `data/task_board.db` with migrated data
7. Test: create task via MCP, verify it survives server restart

---

## Task Summary

| Wave | Task ID | Title | Agent | Depends On | Est. |
|------|---------|-------|-------|------------|------|
| W1 | 192.1 | SQLite storage layer | Agent A | — | 40min |
| W1 | 192.2 | Migration script + tests | Agent B | — | 40min |
| W2 | 192.3 | Replace _load/_save | Agent A | 192.1 | 60min |
| W2 | 192.4 | Update existing tests | Agent B | 192.2, 192.1 | 40min |
| W3 | 192.5 | Integration + cleanup | Opus | 192.3, 192.4 | 30min |

```
Parallel execution:
  Time 0    ├── A: 192.1 (SQLite layer)    ── 40min ──├── A: 192.3 (rewrite) ── 60min ──┐
            │                                          │                                  │
            ├── B: 192.2 (migration+tests) ── 40min ──├── B: 192.4 (tests)   ── 40min ──├── Opus: 192.5
            │                                                                             │   30min
  Total wall time: ~2h 10min (vs ~3h 30min sequential)
```

## Agent Instructions

### For Agent A (core rewrite):
```
Read these files FIRST:
1. docs/192_task_SQLite/ARCHITECTURE_TASKBOARD_SQLITE.md
2. src/orchestration/task_board.py (full file)

Your job: Add SQLite methods (W1), then rewrite persistence (W2).
DO NOT touch: tests, migration script, MCP tools, REST API.
DO NOT remove JSON support until Opus says so.
```

### For Agent B (tests + migration):
```
Read these files FIRST:
1. docs/192_task_SQLite/ARCHITECTURE_TASKBOARD_SQLITE.md
2. tests/test_phase121_task_board.py
3. tests/test_phase136_task_board_claim_complete.py

Your job: Write migration script (W1), then update tests (W2).
DO NOT touch: task_board.py, MCP tools, REST API.
Import new methods from task_board.py to test them.
```

## Rollback Plan

If migration fails:
1. `mv data/task_board.json.bak data/task_board.json`
2. `rm data/task_board.db`
3. Revert task_board.py changes
4. Restart all servers

SQLite and JSON coexist during development. Full cutover only after all tests pass.
