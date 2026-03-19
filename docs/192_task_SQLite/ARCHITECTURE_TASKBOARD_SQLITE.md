# Architecture: TaskBoard JSON → SQLite Migration

**Phase:** 192
**Date:** 2026-03-19
**Author:** Opus (Architect-Commander)
**Status:** APPROVED

---

## Problem Statement

TaskBoard uses a JSON file (`data/task_board.json`) as its persistence layer. Multiple processes (FastAPI, MCP bridge, Mycelium, Claude Code) each hold an **in-memory singleton** (`get_task_board()`) loaded once at startup. When any process calls `_save()`, it writes its **entire in-memory copy** to disk — overwriting changes from other processes.

**Result:** Tasks created by one process are silently deleted when another process saves.

This is not a bug — it's a fundamental architecture mismatch: JSON file storage is single-writer, but VETKA is multi-process.

## Solution: SQLite with WAL

Replace JSON file with SQLite database. SQLite provides:
- **Atomic writes** — no partial overwrites
- **WAL mode** — concurrent readers + serialized writers
- **Per-row updates** — `_save()` writes only changed task, not entire board
- **No singleton cache needed** — each query hits DB directly

## Migration Surface

### What Changes

| Component | Before | After |
|-----------|--------|-------|
| Storage | `data/task_board.json` | `data/task_board.db` (SQLite WAL) |
| `_load()` | Read entire JSON, parse into `self.tasks` dict | `SELECT` per query |
| `_save()` | Serialize entire dict → write file | `INSERT/UPDATE` single row |
| Singleton | `_board_instance` cached forever | Singleton keeps DB connection, no task cache |
| Fallback | `/tmp/vetka_task_board.json` | `/tmp/vetka_task_board.db` |
| Integrity | SHA256 of JSON | SQLite internal checksums |

### What Stays The Same

- **Public API** — all 30+ methods keep same signatures
- **MCP tools** — `handle_task_board()` unchanged
- **REST API** — all endpoints unchanged
- **Task schema** — all 50+ fields preserved
- **Tests** — same assertions, different backend

## Database Schema

```sql
-- WAL mode for concurrent access
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;

CREATE TABLE IF NOT EXISTS tasks (
    -- Primary key
    id TEXT PRIMARY KEY,

    -- Core fields (indexed for queries)
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    priority INTEGER DEFAULT 3,
    status TEXT DEFAULT 'pending',
    phase_type TEXT DEFAULT 'build',
    complexity TEXT DEFAULT 'medium',
    project_id TEXT DEFAULT '',

    -- Assignment
    assigned_to TEXT DEFAULT '',
    agent_type TEXT DEFAULT '',
    assigned_at TEXT DEFAULT '',
    created_by TEXT DEFAULT '',

    -- Timestamps
    created_at TEXT NOT NULL,
    started_at TEXT DEFAULT '',
    completed_at TEXT DEFAULT '',
    closed_at TEXT DEFAULT '',

    -- Git
    commit_hash TEXT DEFAULT '',
    commit_message TEXT DEFAULT '',

    -- All other fields stored as JSON blob
    -- (50+ fields that are rarely queried individually)
    extra TEXT DEFAULT '{}',

    -- Metadata
    updated_at TEXT DEFAULT ''
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

### Hybrid Schema: Indexed Columns + JSON Blob

**Why not normalize all 50+ fields?**
- Most fields (roadmap_id, workflow_bank, closure_proof, etc.) are never used in WHERE/ORDER BY
- Normalizing them = 50 ALTER TABLEs every time we add a field
- JSON blob (`extra`) keeps flexibility, indexed columns keep performance

**Indexed columns** (used in queries): `id, title, priority, status, phase_type, complexity, project_id, assigned_to, agent_type, created_at, commit_hash`

**JSON blob** (`extra`): everything else — `tags, dependencies, allowed_paths, completion_contract, status_history, failure_history, closure_proof, ...`

### Serialization

```python
def _task_to_row(task: dict) -> tuple:
    """Convert in-memory task dict to DB row."""
    indexed = {k: task.get(k, '') for k in INDEXED_COLUMNS}
    extra = {k: v for k, v in task.items() if k not in INDEXED_COLUMNS}
    return (*indexed.values(), json.dumps(extra, default=str, ensure_ascii=False))

def _row_to_task(row: sqlite3.Row) -> dict:
    """Convert DB row back to task dict."""
    task = dict(row)
    extra = json.loads(task.pop('extra', '{}'))
    task.update(extra)
    return task
```

## Architecture Diagram

```
BEFORE (broken):
  FastAPI ──→ singleton ──→ _save() ──→ ┐
  MCP     ──→ singleton ──→ _save() ──→ ├──→ task_board.json (LAST WRITER WINS)
  Mycelium──→ singleton ──→ _save() ──→ ┘

AFTER (correct):
  FastAPI ──→ singleton ──→ db.execute() ──→ ┐
  MCP     ──→ singleton ──→ db.execute() ──→ ├──→ task_board.db (SQLite WAL — serialized)
  Mycelium──→ singleton ──→ db.execute() ──→ ┘
```

## Migration Strategy

### Zero-Downtime Migration

1. On startup: if `task_board.db` doesn't exist but `task_board.json` does → auto-migrate
2. Migration: read JSON → INSERT all tasks → rename JSON to `.json.bak`
3. After migration: JSON file is never written again
4. Rollback: rename `.json.bak` back, delete `.db`

### Singleton Change

```python
# BEFORE: cache all tasks in memory
class TaskBoard:
    def __init__(self):
        self._load()  # reads entire JSON into self.tasks dict

    def get_task(self, task_id):
        return self.tasks.get(task_id)  # from memory

    def _save(self):
        write_entire_dict_to_json()  # DESTRUCTIVE

# AFTER: DB connection, no task cache
class TaskBoard:
    def __init__(self):
        self.db = self._connect()  # SQLite connection
        self._ensure_schema()

    def get_task(self, task_id):
        return self.db.execute("SELECT ... WHERE id=?", (task_id,))  # from DB

    def _save_task(self, task):
        self.db.execute("INSERT OR REPLACE ...", task_to_row(task))  # SINGLE ROW
```

### Backward Compatibility

- `self.tasks` dict kept as **read-through cache** for code that accesses it directly
- `_save()` method preserved but now calls `_save_task()` for single task
- `get_queue()` reads from DB, not from cache
- Old JSON export: `action=export_json` for debugging

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| SQLite file corruption | WAL mode + busy_timeout + PRAGMA integrity_check on startup |
| Performance regression | SQLite is faster than full JSON parse/write for single-task ops |
| Schema drift | `extra` JSON blob absorbs new fields without ALTER TABLE |
| Rollback needed | `.json.bak` preserved, one-command rollback |
| Tests break | Same public API, tests need minimal changes |
