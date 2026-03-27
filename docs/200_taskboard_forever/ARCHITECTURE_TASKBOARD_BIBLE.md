# TaskBoard Architecture Bible
# Phase 200 — TaskBoard Forever

**Date:** 2026-03-27
**Author:** Zeta (Harness Engineer) + Commander review
**Status:** CANONICAL — this document is the single source of truth for TaskBoard architecture.
**Supersedes:** docs/192_task_SQLite/ARCHITECTURE_TASKBOARD_SQLITE.md (Phase 192 design, partially implemented)

---

## 1. Purpose

TaskBoard is the central nervous system of VETKA multi-agent orchestration. Every agent (Alpha, Beta, Gamma, Delta, Epsilon, Zeta) and every process (6 MCP vetka, 6 MCP mycelium, Flask API, heartbeat) reads and writes tasks through one shared SQLite database.

If TaskBoard is slow or locked, **the entire team stops**. This document defines the architecture that makes it permanently fast and stable.

---

## 2. Architecture Diagram

```
                        ┌─────────────────────────┐
                        │   data/task_board.db     │
                        │   (SQLite WAL mode)      │
                        │                          │
                        │  tables: tasks, settings,│
                        │          meta, tasks_fts  │
                        └────────────┬────────────┘
                                     │
                        ┌────────────┴────────────┐
                        │    SQLite WAL Engine     │
                        │  - Multiple readers OK   │
                        │  - Writers queue (<1ms)   │
                        │  - busy_timeout=5000ms   │
                        └────────────┬────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
    ┌─────┴─────┐            ┌──────┴──────┐           ┌──────┴──────┐
    │ MCP Process│            │ MCP Process │           │ Flask API   │
    │ (Alpha)    │            │ (Beta)      │           │ (:5001)     │
    │            │            │             │           │             │
    │ singleton: │            │ singleton:  │           │ singleton:  │
    │ TaskBoard()│            │ TaskBoard() │           │ TaskBoard() │
    │            │            │             │           │             │
    │ self.tasks │            │ self.tasks  │           │ self.tasks  │
    │ (in-memory │            │ (in-memory  │           │ (in-memory  │
    │  cache)    │            │  cache)     │           │  cache)     │
    └───────────┘            └─────────────┘           └─────────────┘
          │                          │                          │
     Each process has its own cache loaded at init.
     Writes go to SQL first, then update local cache.
     Reads use local cache (fast) or SQL (when freshness needed).
```

### Key Principle: Write-Through Cache

```
WRITE: caller → _save_task(task) → SQL INSERT OR REPLACE → self.tasks[id] = task
READ:  caller → self.tasks (cache) → instant (no SQL, no json.loads)
REFRESH: get_task(id) → SQL SELECT → self.tasks[id] = result (cache update)
```

- **Writes always go to SQL first** (durability), then update cache (speed).
- **Reads prefer cache** (populated at init by `_load_all_tasks()`).
- **Point-reads via `get_task(id)`** go to SQL and update cache (freshness for specific task).
- **Bulk reads via `get_queue(status)`** use cache (speed for counts/lists).

---

## 3. SQLite Connection Contract

```python
# CANONICAL connection parameters — DO NOT CHANGE
conn = sqlite3.connect(str(db_path), check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=5000")
conn.row_factory = sqlite3.Row
```

| Parameter | Value | Why |
|-----------|-------|-----|
| `journal_mode` | `WAL` | Allows concurrent readers + serialized writers |
| `busy_timeout` | `5000` (5 seconds) | Single INSERT takes <1ms. 14 queued writes = 14ms. 5s = 350x safety margin |
| `check_same_thread` | `False` | Singleton shared across async handlers in same process |
| `timeout` | **NOT SET** (Python default 5s) | Python-level timeout. Default is sufficient. DO NOT increase. |
| `isolation_level` | **NOT SET** (default `""`) | Deferred transactions. `with conn:` gives atomic batch writes |
| `row_factory` | `sqlite3.Row` | Named column access in `_row_to_task()` |

### NEVER DO:
- `timeout=30` — makes processes hang 30s instead of failing fast
- `busy_timeout=30000` — same problem at SQLite level
- `isolation_level=None` — breaks batch transactions, each INSERT auto-commits (50x slower)
- `_execute_with_retry()` with `time.sleep()` — masks the real problem, adds latency

---

## 4. Database Schema

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    priority INTEGER DEFAULT 3,
    status TEXT DEFAULT 'pending',
    phase_type TEXT DEFAULT 'build',
    complexity TEXT DEFAULT 'medium',
    project_id TEXT DEFAULT '',
    assigned_to TEXT DEFAULT '',
    agent_type TEXT DEFAULT '',
    assigned_at TEXT DEFAULT '',
    created_by TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    started_at TEXT DEFAULT '',
    completed_at TEXT DEFAULT '',
    closed_at TEXT DEFAULT '',
    commit_hash TEXT DEFAULT '',
    commit_message TEXT DEFAULT '',
    extra TEXT DEFAULT '{}',    -- JSON blob for all other fields
    updated_at TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to);

-- FTS5 full-text search (Phase 199)
CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
    task_id, title, description, tags, project_id,
    content='', contentless_delete=1
);

CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
```

### Hybrid Schema: Indexed Columns + JSON Blob

19 columns are indexed (WHERE/ORDER BY fast). Everything else lives in `extra` JSON blob:
- `tags`, `dependencies`, `allowed_paths`, `completion_contract`, `status_history`, `failure_history`, `closure_proof`, `module`, `domain`, `role`, etc.

**Rule:** Fields used in SQL WHERE/ORDER BY get their own column. Fields only read after task is loaded go in `extra`.

**Critical:** `module` lives in `extra`, NOT as a SQL column. Any SQL query like `WHERE module IS NULL` will fail with `OperationalError`.

---

## 5. Init Sequence

```python
def __init__(self, board_file=None):
    # 1. Resolve db_path (always points to main repo data/task_board.db)
    # 2. self.tasks = {}
    # 3. self.settings = {defaults}
    # 4. self.db = self._connect()        # SQLite WAL + busy_timeout=5000
    # 5. self._ensure_schema()            # DDL fast-path: skip if tables exist
    # 6. self._run_migrations()           # Version-gated, idempotent
    # 7. self._migrate_json_to_sqlite()   # One-time JSON import (if DB empty)
    # 8. self._load_settings()            # Read settings table
    # 9. self.tasks = self._load_all_tasks()  # Fill cache from SQL
    # 10. atexit.register(self.close)      # Cleanup on exit
```

### What __init__ MUST do:
- Open connection
- Ensure schema exists (fast-path: 1 read from sqlite_master)
- Run migrations (fast-path: check schema_version)
- Load all tasks into cache (1 SELECT * + json.loads per row)
- Register cleanup

### What __init__ MUST NOT do:
- Bulk writes (INSERT/UPDATE) — causes lock storm with 14 concurrent processes
- `_backfill_modules()` — moved to `action=backfill_modules` (lazy, on-demand)
- `_backfill_fts()` — already moved to `action=backfill_fts`
- WAL checkpoint — unnecessary, WAL self-manages
- Any operation that takes >100ms

### Init Performance Target:
- 14 concurrent processes init in <5 seconds total
- Single process init in <500ms (with 500 tasks)

---

## 6. Read Path

### `get_queue(status=None)` — Bulk read (HOT PATH)

```python
# CANONICAL implementation — reads from cache
def get_queue(self, status=None):
    tasks = list(self.tasks.values())
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    tasks.sort(key=lambda t: (t.get("priority", 3), t.get("created_at", "")))
    return tasks
```

**Why cache, not SQL:**
- Called 7+ times per `session_init` (once per status bucket)
- 450 tasks × 7 calls = 3150 json.loads if going to SQL
- Cache: 450 dict lookups × 7 = instant (<1ms total)
- Cache is populated at init and kept coherent by write path

**When cache is stale:**
- Another process wrote a task since this process's init
- This is acceptable for `session_init` (advisory counts, not transactional)
- For transactional reads (e.g., claim race), use `get_task(id)` which hits SQL

### `get_task(task_id)` — Point read (FRESH)

```python
# Reads from SQL, updates cache
def get_task(self, task_id):
    task = self._load_task(task_id)  # SELECT WHERE id=?
    if task:
        self.tasks[task_id] = task   # Update cache
    else:
        self.tasks.pop(task_id, None)
    return task
```

**Why SQL, not cache:**
- Used before `claim_task()`, `complete_task()` — needs fresh status
- Single SELECT + 1 json.loads = <1ms
- Updates cache as side effect

### `search_fts(query)` — Full-text search

Always goes to FTS5 index (separate virtual table). Returns `{task_id, snippet, rank}`.

### `get_board_summary()` — Aggregate counts

Uses SQL `GROUP BY` for efficiency: `SELECT status, COUNT(*) FROM tasks GROUP BY status`.

### `list_tasks()` — Alias for `get_queue()`

Backward-compatibility shim. Same implementation.

---

## 7. Write Path

### `_save_task(task)` — Single row write (ATOMIC)

```python
def _save_task(self, task):
    row = self._task_to_row(task)
    row["updated_at"] = datetime.now().isoformat()
    # ... build SQL ...
    with self.db:
        self.db.execute("INSERT OR REPLACE INTO tasks (...) VALUES (...)", values)
    self.tasks[task["id"]] = task  # Cache coherence
    self._index_task_fts(task)     # Incremental FTS5 update
```

**Critical invariant:** Every `_save_task()` MUST update `self.tasks[id]` after SQL write.

### Write operations and their cache behavior:

| Method | SQL Write | Cache Update | Notes |
|--------|-----------|--------------|-------|
| `add_task()` | `_save_task()` | `self.tasks[id] = task` | Creates new task |
| `update_task()` | `_save_task()` | Reads + modifies `self.tasks[id]` | In-place update |
| `claim_task()` | via `update_task()` | via `update_task()` | Status: claimed |
| `complete_task()` | via `update_task()` | via `update_task()` | Status: done_worktree/done_main |
| `verify_task()` | via `update_task()` | via `update_task()` | Status: verified/needs_fix |
| `remove_task()` | `_delete_task()` | `del self.tasks[id]` | Permanent delete |
| `_save_settings()` | `INSERT OR REPLACE INTO settings` | `self.settings` | Settings only |

---

## 8. Task Lifecycle

```
                 ┌──────────┐
                 │ pending   │ ← add_task()
                 └────┬─────┘
                      │ claim_task()
                 ┌────▼─────┐
                 │ claimed   │
                 └────┬─────┘
                      │ dispatch_task() [optional]
                 ┌────▼─────┐
                 │ running   │
                 └────┬─────┘
                      │ complete_task()
              ┌───────┴───────┐
              │               │
    ┌─────────▼──────┐  ┌────▼──────┐
    │ done_worktree  │  │ done_main │ ← if on main branch
    └────────┬───────┘  └───────────┘
             │ verify_task(pass)
    ┌────────▼───────┐
    │   verified     │
    └────────────────┘

    verify_task(fail) → needs_fix → back to pending
    cancel_task()     → cancelled (from pending/queued/hold)
    record_failure()  → pending (from running, with failure_history)
```

### Valid Statuses (14):
`pending`, `queued`, `claimed`, `running`, `done`, `done_worktree`, `need_qa`, `done_main`, `failed`, `cancelled`, `hold`, `pending_user_approval`, `verified`, `needs_fix`

---

## 9. Concurrency Contract

### The Golden Rule

> SQLite WAL allows ONE writer at a time. Each write takes <1ms.
> With `busy_timeout=5000ms`, 14 processes can queue 14 writes = 14ms total.
> This is 350x under the timeout. **There is no lock problem IF writes are atomic single-row operations.**

### What causes lock storms:

| Anti-pattern | Impact | Example |
|--------------|--------|---------|
| Bulk writes in `__init__` | N processes × M writes = N×M contention | `_backfill_modules()` doing 50 INSERT OR REPLACE |
| Long transactions | Holds RESERVED lock, blocks all other writers | `with self.db:` around a loop of 100 inserts |
| `timeout=30` | Processes hang 30s instead of failing fast | `sqlite3.connect(timeout=30)` |
| Retry with sleep | Adds latency on top of busy_timeout | `_execute_with_retry()` with exponential backoff |
| `isolation_level=None` | Each INSERT auto-commits individually (50x slower) | Every batch becomes N separate transactions |

### What is safe:

| Pattern | Why |
|---------|-----|
| Single-row `INSERT OR REPLACE` in `with self.db:` | <1ms, atomic, queues cleanly |
| `SELECT` without transaction | WAL readers never block writers |
| `_load_all_tasks()` at init | Read-only, no lock |
| `_ensure_schema()` with DDL fast-path | Runs DDL only on first-ever process |

---

## 10. Integration Points

### 10.1 MCP Tools (`task_board_tools.py`)

Primary entry point: `handle_task_board(action, **params)`.
All actions call `get_task_board()` → singleton → method call.

| Action | Method | Read/Write | Cache OK? |
|--------|--------|------------|-----------|
| `list` | `get_queue()` | Read | Yes — cache |
| `get` | `get_task()` | Read | SQL + cache update |
| `add` | `add_task()` | Write | SQL + cache |
| `update` | `update_task()` | Write | Cache + SQL |
| `claim` | `claim_task()` | Write | SQL + cache |
| `complete` | `complete_task()` | Write | SQL + cache |
| `remove` | `remove_task()` | Write | SQL + cache |
| `summary` | `get_board_summary()` | Read | SQL GROUP BY |
| `search_fts` | `search_fts()` | Read | FTS5 index |
| `verify` | `verify_task()` | Write | SQL + cache |
| `merge_request` | `merge_request()` | Write | SQL + cache + git |
| `promote_to_main` | `promote_to_main()` | Write | SQL + cache + git |
| `stale_check` | `stale_check()` | Read + optional write | SQL + git |
| `batch_merge` | loop of `merge_request()` | Write | Sequential |
| `active_agents` | `get_active_agents()` | Read | SQL |
| `backfill_fts` | `_backfill_fts()` | Write (bulk) | Manual only |
| `debrief_skipped` | `get_debrief_skipped_tasks()` | Read | SQL |
| `context_packet` | `get_context_packet()` | Read | SQL + files |

### 10.2 Session Init (`session_tools.py`)

Calls `get_queue()` 7 times (one per status) + 1 duplicate `claimed` query.
**Must use cache** — advisory counts, not transactional.

### 10.3 Protocol Guard (`protocol_guard.py`)

Calls `get_task(claimed_task_id)` on every Edit/Write tool invocation.
Can use cache with 60s TTL — claimed task rarely changes during edit session.

### 10.4 Git Tool (`git_tool.py`)

- `find_tasks_by_changed_files()` — after commit, informational
- `auto_complete_by_commit()` — after commit, writes (closes matching tasks)

### 10.5 REST API (`task_routes.py`, `debug_routes.py`, `mcc_routes.py`)

Full CRUD via HTTP. Same singleton. Same cache/SQL rules.

### 10.6 Heartbeat (`mycelium_heartbeat.py`)

`get_queue()` on every tick (~30-60s). Must use cache.

### 10.7 Agent Pipeline (`agent_pipeline.py`)

`update_task()`, `record_pipeline_stats()` during/after pipeline execution.
Write path — must go to SQL.

---

## 11. Performance Invariants

These MUST hold at all times. Any change that breaks these is rejected.

| Metric | Target | How to test |
|--------|--------|-------------|
| `session_init` total time | <2 seconds | `time vetka_session_init` end-to-end |
| `claim_task()` latency | <100ms | Single-task claim with concurrent load |
| `get_queue()` latency | <10ms | From cache, no SQL |
| `_save_task()` latency | <5ms | Single INSERT OR REPLACE |
| 14 concurrent inits | <5 seconds total | Spawn 14 threads, each creates TaskBoard |
| `__init__` single process | <500ms | With 500 tasks in DB |
| `search_fts()` latency | <50ms | FTS5 query on 500 tasks |

---

## 12. NEVER DO List

These rules are permanent. They exist because each was learned the hard way.

### 12.1 NEVER: Bulk writes in `__init__`
**Why:** 14 MCP processes start simultaneously. N bulk writes × 14 = lock storm.
**Learned:** Phase 199 — `_backfill_fts()` in init caused 14-process deadlock. Then `_backfill_modules()` caused the same.
**Rule:** `__init__` may only READ from SQLite. All writes go to lazy/on-demand actions.

### 12.2 NEVER: `timeout > 5` in `sqlite3.connect()`
**Why:** Makes processes hang for timeout duration instead of failing fast.
**Learned:** Phase 199 — `timeout=30` caused 60-second session_init.
**Rule:** Use Python default (5s). If you need more, the architecture is wrong.

### 12.3 NEVER: `busy_timeout > 5000`
**Why:** Same as timeout. Masks the real problem.
**Learned:** Phase 199 — `busy_timeout=30000` compounded the hang.
**Rule:** 5000ms. If 5s isn't enough, fix the write that takes >5s.

### 12.4 NEVER: Retry loops with `time.sleep()` for SQL
**Why:** Adds latency on top of SQLite's own retry mechanism.
**Learned:** Phase 199 — `_execute_with_retry()` added up to 3.1s per write.
**Rule:** Let `busy_timeout` handle contention. If it fails, the operation fails. Don't mask it.

### 12.5 NEVER: `get_queue()` via SQL when cache exists
**Why:** 450 rows × json.loads × 7 calls = 3150 deserializations per session_init.
**Learned:** Phase 199/200 — session_init took 60+ seconds.
**Rule:** `get_queue()` reads from `self.tasks` cache. Always.

### 12.6 NEVER: SQL WHERE on fields in `extra` JSON blob
**Why:** `module`, `domain`, `role`, `tags` etc. are NOT SQL columns. `WHERE module IS NULL` → OperationalError.
**Learned:** Phase 199 — `_backfill_modules()` SQL fast-path was always failing silently.
**Rule:** Filter `extra` fields in Python after loading tasks, not in SQL.

### 12.7 NEVER: `isolation_level=None` without understanding batch consequences
**Why:** Disables implicit transactions. Each INSERT auto-commits = 50x slower for batch operations.
**Learned:** Phase 199 — LOCK_FIX_V2 broke batch transactions, session_init > 1 minute.
**Rule:** Keep default `isolation_level=""` (deferred transactions).

### 12.8 NEVER: WAL checkpoint TRUNCATE in close() with concurrent readers
**Why:** TRUNCATE requires exclusive lock. With 14 processes, some are always reading.
**Rule:** Use PASSIVE (non-blocking, best-effort) or let SQLite auto-checkpoint.

---

## 13. Good MARKER_199 Additions (KEEP)

These are net-positive additions from Phase 199 that must be preserved:

| Feature | Files/Methods | Why keep |
|---------|--------------|----------|
| FTS5 search | `search_fts()`, `_index_task_fts()`, `_remove_task_fts()` | Full-text search across tasks |
| FTS5 incremental indexing | Called from `_save_task()` and `_delete_task()` | No bulk writes, maintains index lazily |
| FTS5 query sanitization | `search_fts()` regex strip | Prevents FTS5 syntax errors from special chars |
| Migration system | `_run_migrations()`, `_get/set_schema_version()` | Version-gated schema changes |
| DDL fast-path | `_ensure_schema()` checks `sqlite_master` first | Avoids DDL exclusive lock on subsequent inits |
| `get_context_packet()` | MCC-ready task packet | Read-only, no side effects |
| `owner_agent` on claim | One field in `claim_task()` | Metadata, no perf impact |
| `get_debrief_skipped_tasks()` | SQL query | Read-only |
| `close()` + `atexit` | WAL PASSIVE checkpoint on exit | Clean shutdown |
| Merge safety | Stash + returncode checks in `_execute_merge()` | Prevents silent merge failures |
| `_backfill_fts()` as action | `action=backfill_fts` | Manual, on-demand, not in init |

---

## 14. Fix Specification (Phase 200 P0)

### Change 1: Remove `_backfill_modules()` from `__init__`

**Before:**
```python
# __init__
self.tasks = self._load_all_tasks()
self._backfill_modules()  # REMOVE THIS
```

**After:**
```python
# __init__
self.tasks = self._load_all_tasks()
# _backfill_modules() available via action=backfill_modules
```

Move invocation to `handle_task_board(action="backfill_modules")`.

### Change 2: Restore `_connect()` to canonical values

**Before:**
```python
conn = sqlite3.connect(str(db_path), timeout=30, check_same_thread=False)
conn.execute("PRAGMA busy_timeout=30000")
```

**After:**
```python
conn = sqlite3.connect(str(db_path), check_same_thread=False)
conn.execute("PRAGMA busy_timeout=5000")
```

### Change 3: Remove `_execute_with_retry()`

Delete the method entirely. Revert `_save_task()` to use `with self.db:` directly.

### Change 4: `get_queue()` from cache

**Before:**
```python
def get_queue(self, status=None):
    query = "SELECT * FROM tasks"
    # ... SQL query ...
```

**After:**
```python
def get_queue(self, status=None):
    tasks = list(self.tasks.values())
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    tasks.sort(key=lambda t: (t.get("priority", 3), t.get("created_at", "")))
    return tasks
```

### Change 5: `_save_task()` cache coherence

**Before:**
```python
def _save_task(self, task):
    # ... SQL INSERT OR REPLACE ...
    self._index_task_fts(task)
```

**After:**
```python
def _save_task(self, task):
    # ... SQL INSERT OR REPLACE ...
    self.tasks[task["id"]] = task  # Cache coherence
    self._index_task_fts(task)
```

### Change 6: Remove WAL checkpoint from `__init__`

**Before:**
```python
# __init__
self.db.execute("PRAGMA wal_checkpoint(PASSIVE)")
```

**After:** Remove this line. WAL auto-checkpoints. `close()` still does PASSIVE.

---

## 15. File References

| File | Role |
|------|------|
| `src/orchestration/task_board.py` | Core implementation (~3900 lines) |
| `src/mcp/tools/task_board_tools.py` | MCP tool handler (actions) |
| `src/mcp/tools/session_tools.py` | Session init (reads task counts) |
| `src/mcp/tools/git_tool.py` | Auto-complete by commit |
| `src/services/protocol_guard.py` | Claimed task checks |
| `src/orchestration/agent_pipeline.py` | Pipeline stats + updates |
| `src/services/smart_debrief.py` | Auto-task creation from debrief |
| `src/api/routes/task_routes.py` | REST API CRUD |
| `src/api/routes/debug_routes.py` | Debug/admin endpoints |
| `src/api/routes/mcc_routes.py` | MCC overlay |
| `src/orchestration/mycelium_heartbeat.py` | Heartbeat task checks |
| `src/api/handlers/group_message_handler.py` | Telegram intake |
| `data/task_board.db` | SQLite database file |
| `data/task_board.json.bak` | Legacy JSON backup |

---

## 16. Testing Requirements

See `tests/test_phase200_taskboard_forever.py` for the regression test suite.

Every change to `task_board.py` MUST pass:
1. Concurrent init test (14 processes, <5s)
2. Cache coherence test (write → cache reflects write)
3. `get_queue()` cache test (no SQL, same results)
4. Concurrent claim test (no deadlock)
5. FTS5 test (search still works)
6. Connection params test (busy_timeout=5000, no timeout=30)

---

## Appendix A: Caller Map Summary

| Caller | Methods Used | Frequency | Cache OK? |
|--------|-------------|-----------|-----------|
| `session_init` | `get_queue()` x8 | Every agent session start | YES — cache |
| `protocol_guard` | `get_task(claimed_id)` | Every Edit/Write call | YES — 60s TTL |
| `heartbeat` | `get_queue()` | Every 30-60s tick | YES — cache |
| `task_board_tools` (list) | `get_queue()` | On-demand | YES — cache |
| `task_board_tools` (write) | `claim/complete/add/update` | On-demand | SQL + cache |
| `git_tool` | `auto_complete_by_commit()` | After commits | SQL (writes) |
| `agent_pipeline` (stats) | `update_task()`, `record_pipeline_stats()` | During pipeline | SQL + cache |
| `REST API` (read) | `get_queue()`, `get_task()`, `summary()` | HTTP requests | Mixed |
| `REST API` (write) | `add/update/claim/complete` | HTTP requests | SQL + cache |

---

*This document was forged in the fire of a 3-day lock storm that blocked the entire 6-agent team.
It exists so that this never happens again.*
