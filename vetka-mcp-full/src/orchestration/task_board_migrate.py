"""
Phase 192: TaskBoard JSON → SQLite Migration
MARKER_192.2: Migration script + SQLite storage helpers

Provides:
- SQLite schema creation (WAL mode)
- Task serialization: dict ↔ row
- JSON → SQLite migration
- SQLite → JSON export (rollback/debug)
- Verification (count + field check)
- CLI entry: python -m src.orchestration.task_board_migrate

Does NOT modify task_board.py — pure standalone module.
"""

import json
import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("VETKA_TASK_BOARD_MIGRATE")

# MARKER_192.2: Indexed columns — used in WHERE/ORDER BY.
# Everything else goes into the `extra` JSON blob.
INDEXED_COLUMNS = [
    "id",
    "title",
    "description",
    "priority",
    "status",
    "phase_type",
    "complexity",
    "project_id",
    "assigned_to",
    "agent_type",
    "assigned_at",
    "created_by",
    "created_at",
    "started_at",
    "completed_at",
    "closed_at",
    "commit_hash",
    "commit_message",
    "updated_at",
]

_INDEXED_SET = frozenset(INDEXED_COLUMNS)

# SQL schema
_SCHEMA_SQL = """
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
    updated_at TEXT DEFAULT '',
    extra TEXT DEFAULT '{}'
);

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
"""


# ============================================================
# SQLite helpers
# ============================================================

def connect_db(db_path: Path) -> sqlite3.Connection:
    """Open SQLite connection with WAL mode and row_factory."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables and indexes if they don't exist."""
    conn.executescript(_SCHEMA_SQL)
    conn.commit()


def task_to_row(task: Dict[str, Any]) -> Dict[str, Any]:
    """Convert in-memory task dict to DB row dict.

    Indexed fields → their own columns.
    Everything else → JSON blob in `extra`.
    """
    row = {}
    extra = {}
    for k, v in task.items():
        if k in _INDEXED_SET:
            # Coerce None to empty string for TEXT columns, keep int for priority
            if k == "priority":
                try:
                    row[k] = int(v) if v is not None else 3
                except (TypeError, ValueError):
                    row[k] = 3
            else:
                row[k] = str(v) if v is not None else ""
        else:
            extra[k] = v
    # Ensure required fields have defaults
    row.setdefault("id", "")
    row.setdefault("title", "")
    row.setdefault("created_at", datetime.now().isoformat())
    row["extra"] = json.dumps(extra, default=str, ensure_ascii=False)
    return row


def row_to_task(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert DB row back to task dict."""
    task = dict(row)
    extra_raw = task.pop("extra", "{}")
    try:
        extra = json.loads(extra_raw) if extra_raw else {}
    except (json.JSONDecodeError, TypeError):
        extra = {}
    task.update(extra)
    # Restore None for empty strings on nullable fields
    for field in ("assigned_to", "agent_type", "assigned_at", "started_at",
                  "completed_at", "closed_at", "commit_hash", "commit_message",
                  "updated_at", "project_id", "created_by"):
        if task.get(field) == "":
            task[field] = None
    # priority back to int
    try:
        task["priority"] = int(task["priority"])
    except (TypeError, ValueError, KeyError):
        pass
    return task


def save_task(conn: sqlite3.Connection, task: Dict[str, Any]) -> None:
    """INSERT OR REPLACE a single task into the DB."""
    row = task_to_row(task)
    columns = list(row.keys())
    placeholders = ", ".join("?" for _ in columns)
    col_names = ", ".join(columns)
    values = [row[c] for c in columns]
    conn.execute(
        f"INSERT OR REPLACE INTO tasks ({col_names}) VALUES ({placeholders})",
        values,
    )
    conn.commit()


def delete_task(conn: sqlite3.Connection, task_id: str) -> bool:
    """DELETE a single task by id. Returns True if a row was deleted."""
    cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    return cursor.rowcount > 0


def load_task(conn: sqlite3.Connection, task_id: str) -> Optional[Dict[str, Any]]:
    """SELECT a single task by id."""
    cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    return row_to_task(row) if row else None


def load_all_tasks(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    """SELECT all tasks, return as {id: task_dict}."""
    cursor = conn.execute("SELECT * FROM tasks")
    result = {}
    for row in cursor.fetchall():
        task = row_to_task(row)
        result[task["id"]] = task
    return result


def query_tasks(
    conn: sqlite3.Connection,
    *,
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    order_by: str = "priority ASC, created_at ASC",
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Query tasks with optional filters and ordering."""
    where_clauses = []
    params: list = []
    if status is not None:
        where_clauses.append("status = ?")
        params.append(status)
    if project_id is not None:
        where_clauses.append("project_id = ?")
        params.append(project_id)
    if assigned_to is not None:
        where_clauses.append("assigned_to = ?")
        params.append(assigned_to)

    sql = "SELECT * FROM tasks"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    sql += f" ORDER BY {order_by}"
    if limit:
        sql += f" LIMIT {int(limit)}"

    cursor = conn.execute(sql, params)
    return [row_to_task(row) for row in cursor.fetchall()]


def save_settings(conn: sqlite3.Connection, settings: Dict[str, Any]) -> None:
    """Persist settings dict to settings table (key-value pairs)."""
    for key, value in settings.items():
        if str(key).startswith("_"):
            continue
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (str(key), json.dumps(value, default=str, ensure_ascii=False)),
        )
    conn.commit()


def load_settings(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Read all settings from settings table."""
    cursor = conn.execute("SELECT key, value FROM settings")
    result = {}
    for row in cursor.fetchall():
        try:
            result[row["key"]] = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            result[row["key"]] = row["value"]
    return result


def get_task_count(conn: sqlite3.Connection, status: Optional[str] = None) -> int:
    """COUNT tasks, optionally filtered by status."""
    if status:
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM tasks WHERE status = ?", (status,))
    else:
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM tasks")
    return cursor.fetchone()["cnt"]


def get_status_counts(conn: sqlite3.Connection) -> Dict[str, int]:
    """GROUP BY status → count."""
    cursor = conn.execute("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status")
    return {row["status"]: row["cnt"] for row in cursor.fetchall()}


# ============================================================
# Migration functions
# ============================================================

def migrate_json_to_sqlite(json_path: Path, db_path: Path) -> Dict[str, Any]:
    """Read JSON task board, INSERT all tasks into SQLite.

    Returns migration report with counts.
    """
    if not json_path.exists():
        return {"success": False, "error": f"JSON file not found: {json_path}"}

    try:
        data = json.loads(json_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        return {"success": False, "error": f"Failed to read JSON: {e}"}

    tasks = data.get("tasks", {})
    settings = data.get("settings", {})

    conn = connect_db(db_path)
    ensure_schema(conn)

    migrated = 0
    errors = []
    for task_id, task_dict in tasks.items():
        task_dict.setdefault("id", task_id)
        try:
            save_task(conn, task_dict)
            migrated += 1
        except Exception as e:
            errors.append({"task_id": task_id, "error": str(e)})

    if settings:
        save_settings(conn, settings)

    # Store migration metadata
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        ("migrated_at", datetime.now().isoformat()),
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        ("migrated_from", str(json_path)),
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        ("source_task_count", str(len(tasks))),
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "migrated": migrated,
        "total_in_json": len(tasks),
        "errors": errors,
        "db_path": str(db_path),
    }


def export_sqlite_to_json(db_path: Path, json_path: Path) -> Dict[str, Any]:
    """Export SQLite DB back to JSON format (for rollback/debug)."""
    if not db_path.exists():
        return {"success": False, "error": f"DB file not found: {db_path}"}

    conn = connect_db(db_path)
    tasks = load_all_tasks(conn)
    settings = load_settings(conn)
    conn.close()

    data = {
        "_meta": {
            "version": "1.0",
            "phase": "192",
            "updated": datetime.now().isoformat(),
            "exported_from": "sqlite",
        },
        "tasks": tasks,
        "settings": settings,
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False))

    return {
        "success": True,
        "exported": len(tasks),
        "json_path": str(json_path),
    }


def verify_migration(json_path: Path, db_path: Path) -> Dict[str, Any]:
    """Verify migration: count match + spot-check 5 random tasks.

    Returns verification report.
    """
    if not json_path.exists():
        return {"success": False, "error": f"JSON not found: {json_path}"}
    if not db_path.exists():
        return {"success": False, "error": f"DB not found: {db_path}"}

    data = json.loads(json_path.read_text())
    json_tasks = data.get("tasks", {})

    conn = connect_db(db_path)
    db_count = get_task_count(conn)

    report: Dict[str, Any] = {
        "json_count": len(json_tasks),
        "db_count": db_count,
        "count_match": len(json_tasks) == db_count,
        "spot_checks": [],
    }

    # Spot-check up to 5 tasks
    import random
    task_ids = list(json_tasks.keys())
    check_ids = random.sample(task_ids, min(5, len(task_ids))) if task_ids else []

    all_match = True
    for tid in check_ids:
        json_task = json_tasks[tid]
        db_task = load_task(conn, tid)
        check = {"task_id": tid, "found_in_db": db_task is not None}
        if db_task:
            # Compare key fields
            mismatches = []
            for field in ("title", "status", "priority", "phase_type", "description"):
                jv = json_task.get(field)
                dv = db_task.get(field)
                # Normalize for comparison
                if field == "priority":
                    try:
                        jv = int(jv) if jv is not None else 3
                        dv = int(dv) if dv is not None else 3
                    except (TypeError, ValueError):
                        pass
                if str(jv or "") != str(dv or ""):
                    mismatches.append({"field": field, "json": jv, "db": dv})
            check["mismatches"] = mismatches
            check["match"] = len(mismatches) == 0
            if not check["match"]:
                all_match = False
        else:
            check["match"] = False
            all_match = False
        report["spot_checks"].append(check)

    conn.close()
    report["success"] = report["count_match"] and all_match
    return report


# ============================================================
# CLI entry
# ============================================================

def main():
    """CLI: python -m src.orchestration.task_board_migrate"""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="TaskBoard JSON → SQLite migration")
    parser.add_argument("--json", type=str, help="Path to task_board.json")
    parser.add_argument("--db", type=str, help="Path to task_board.db")
    parser.add_argument("--action", choices=["migrate", "export", "verify"], default="migrate")
    args = parser.parse_args()

    # Resolve paths relative to project root
    root = Path(__file__).resolve().parent.parent.parent
    json_path = Path(args.json) if args.json else root / "data" / "task_board.json"
    db_path = Path(args.db) if args.db else root / "data" / "task_board.db"

    if args.action == "migrate":
        print(f"Migrating {json_path} → {db_path}")
        result = migrate_json_to_sqlite(json_path, db_path)
        print(json.dumps(result, indent=2))
        if result.get("success"):
            print(f"\nVerifying...")
            verify_result = verify_migration(json_path, db_path)
            print(json.dumps(verify_result, indent=2))
    elif args.action == "export":
        print(f"Exporting {db_path} → {json_path}")
        result = export_sqlite_to_json(db_path, json_path)
        print(json.dumps(result, indent=2))
    elif args.action == "verify":
        print(f"Verifying {json_path} vs {db_path}")
        result = verify_migration(json_path, db_path)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
