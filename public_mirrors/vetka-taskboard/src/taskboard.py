"""
TaskBoard — Lightweight Multi-Agent Task Queue (SQLite)

A standalone task board for coordinating work between AI agents.
Supports task creation, claiming, completion, and audit logging.

This is a simplified version of VETKA's full TaskBoard (5700+ lines),
extracted for public use with the Agent Gateway.

@license MIT
@version 1.0.0
"""

import hashlib
import json
import logging
import os
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("taskboard")

# ---------------------------------------------------------------------------
# Valid statuses
# ---------------------------------------------------------------------------

VALID_STATUSES = {
    "pending",
    "queued",
    "claimed",
    "running",
    "done",
    "done_worktree",
    "need_qa",
    "done_main",
    "failed",
    "cancelled",
    "hold",
    "verified",
    "needs_fix",
}

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


class TaskBoard:
    """SQLite-backed task board with agent registry and audit logging."""

    def __init__(self, db_path: str = "data/taskboard.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=15000")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                description TEXT DEFAULT '',
                priority    INTEGER DEFAULT 3,
                status      TEXT DEFAULT 'pending',
                phase_type  TEXT DEFAULT 'build',
                complexity  TEXT DEFAULT 'medium',
                project_id  TEXT DEFAULT '',
                assigned_to TEXT DEFAULT '',
                agent_type  TEXT DEFAULT '',
                assigned_at TEXT DEFAULT '',
                created_at  TEXT NOT NULL,
                completed_at TEXT DEFAULT '',
                commit_hash TEXT DEFAULT '',
                commit_message TEXT DEFAULT '',
                extra       TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS agents (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                agent_type      TEXT NOT NULL DEFAULT 'external',
                capabilities    TEXT,
                model_tier      TEXT,
                api_key_hash    TEXT NOT NULL,
                status          TEXT DEFAULT 'active',
                max_concurrent  INTEGER DEFAULT 3,
                last_heartbeat  TEXT,
                created_at      TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id        TEXT,
                action          TEXT NOT NULL,
                task_id         TEXT,
                ip_address      TEXT,
                request_body    TEXT,
                response_status INTEGER,
                created_at      TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to);
            CREATE INDEX IF NOT EXISTS idx_agents_key ON agents(api_key_hash);
            CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_log(agent_id);
        """)
        conn.commit()
        conn.close()

    # -----------------------------------------------------------------------
    # Task CRUD
    # -----------------------------------------------------------------------

    def add_task(
        self,
        title: str,
        description: str = "",
        priority: int = 3,
        phase_type: str = "build",
        complexity: str = "medium",
        project_id: str = "",
        tags: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        """Create a new task. Returns task_id."""
        task_id = f"tb_{int(time.time())}_{secrets.token_hex(3)}"
        now = datetime.now(timezone.utc).isoformat()
        extra = json.dumps({"tags": tags or [], **kwargs})

        conn = self._conn()
        conn.execute(
            """INSERT INTO tasks (id, title, description, priority, status, phase_type,
               complexity, project_id, created_at, extra)
               VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)""",
            (
                task_id,
                title,
                description,
                priority,
                phase_type,
                complexity,
                project_id,
                now,
                extra,
            ),
        )
        conn.commit()
        conn.close()
        logger.info(f"[TaskBoard] Created task {task_id}: {title}")
        return task_id

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        conn = self._conn()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.close()
        if not row:
            return None
        task = dict(row)
        task["tags"] = json.loads(task.get("extra", "{}") or "{}").get("tags", [])
        return task

    def list_tasks(
        self,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List tasks with optional filters."""
        conn = self._conn()
        query = "SELECT * FROM tasks WHERE 1=1"
        params: list = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if assigned_to:
            query += " AND assigned_to = ?"
            params.append(assigned_to)
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)

        query += " ORDER BY priority ASC, created_at ASC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        tasks = []
        for row in rows:
            t = dict(row)
            t["tags"] = json.loads(t.get("extra", "{}") or "{}").get("tags", [])
            tasks.append(t)
        return tasks

    def update_task(self, task_id: str, **kwargs) -> bool:
        """Update task fields."""
        allowed = {
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
            "completed_at",
            "commit_hash",
            "commit_message",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [task_id]

        conn = self._conn()
        cursor = conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def remove_task(self, task_id: str) -> bool:
        """Delete a task."""
        conn = self._conn()
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    # -----------------------------------------------------------------------
    # Claim / Complete
    # -----------------------------------------------------------------------

    def claim_task(
        self, task_id: str, agent_name: str, agent_type: str = "external"
    ) -> Dict[str, Any]:
        """Claim a task for an agent."""
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task '{task_id}' not found"}
        if task["status"] != "pending":
            return {
                "success": False,
                "error": f"Task status is '{task['status']}', expected 'pending'",
            }

        now = datetime.now(timezone.utc).isoformat()
        self.update_task(
            task_id,
            status="claimed",
            assigned_to=agent_name,
            agent_type=agent_type,
            assigned_at=now,
        )
        logger.info(f"[TaskBoard] {agent_name} claimed {task_id}")
        return {"success": True, "task_id": task_id, "assigned_to": agent_name}

    def complete_task(
        self,
        task_id: str,
        commit_hash: str = "",
        commit_message: str = "",
        branch: str = "",
        closed_by: str = "",
    ) -> Dict[str, Any]:
        """Mark a task as completed."""
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task '{task_id}' not found"}
        if task["status"] not in ("claimed", "running"):
            return {
                "success": False,
                "error": f"Task status is '{task['status']}', expected 'claimed' or 'running'",
            }

        now = datetime.now(timezone.utc).isoformat()
        new_status = "done_worktree" if branch else "done_main"
        self.update_task(
            task_id,
            status=new_status,
            completed_at=now,
            commit_hash=commit_hash,
            commit_message=commit_message,
        )
        logger.info(
            f"[TaskBoard] {task_id} completed by {closed_by or task['assigned_to']}"
        )
        return {"success": True, "task_id": task_id, "status": new_status}

    # -----------------------------------------------------------------------
    # Agent Registry
    # -----------------------------------------------------------------------

    def register_agent(
        self,
        name: str,
        agent_type: str = "external",
        capabilities: Optional[List[str]] = None,
        model_tier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register a new agent. Returns agent info + API key."""
        agent_id = f"agent_{int(time.time())}_{secrets.token_hex(4)}"
        api_key = f"vka_{secrets.token_urlsafe(32)}"
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        now = datetime.now(timezone.utc).isoformat()

        conn = self._conn()
        conn.execute(
            """INSERT INTO agents (id, name, agent_type, capabilities, model_tier,
               api_key_hash, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'active', ?)""",
            (
                agent_id,
                name,
                agent_type,
                json.dumps(capabilities),
                model_tier,
                api_key_hash,
                now,
            ),
        )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "agent": {
                "id": agent_id,
                "name": name,
                "agent_type": agent_type,
                "capabilities": capabilities,
                "model_tier": model_tier,
                "status": "active",
            },
            "api_key": api_key,
        }

    def get_agent_by_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Look up agent by API key."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM agents WHERE api_key_hash = ? AND status = 'active'",
            (key_hash,),
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        conn = self._conn()
        rows = conn.execute("SELECT * FROM agents ORDER BY created_at DESC").fetchall()
        conn.close()
        agents = []
        for row in rows:
            a = dict(row)
            a.pop("api_key_hash", None)
            agents.append(a)
        return agents

    def suspend_agent(self, agent_id: str) -> bool:
        """Suspend an agent."""
        conn = self._conn()
        cursor = conn.execute(
            "UPDATE agents SET status = 'suspended' WHERE id = ?", (agent_id,)
        )
        conn.commit()
        ok = cursor.rowcount > 0
        conn.close()
        return ok

    def activate_agent(self, agent_id: str) -> bool:
        """Reactivate a suspended agent."""
        conn = self._conn()
        cursor = conn.execute(
            "UPDATE agents SET status = 'active' WHERE id = ?", (agent_id,)
        )
        conn.commit()
        ok = cursor.rowcount > 0
        conn.close()
        return ok

    def rotate_agent_key(self, agent_id: str) -> Optional[str]:
        """Generate a new API key for an agent."""
        new_key = f"vka_{secrets.token_urlsafe(32)}"
        new_hash = hashlib.sha256(new_key.encode()).hexdigest()
        conn = self._conn()
        cursor = conn.execute(
            "UPDATE agents SET api_key_hash = ? WHERE id = ?", (new_hash, agent_id)
        )
        conn.commit()
        ok = cursor.rowcount > 0
        conn.close()
        return new_key if ok else None

    def heartbeat_agent(self, agent_id: str) -> Dict[str, Any]:
        """Update agent heartbeat timestamp."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._conn()
        conn.execute(
            "UPDATE agents SET last_heartbeat = ? WHERE id = ?", (now, agent_id)
        )
        conn.commit()
        conn.close()
        return {"success": True, "agent_id": agent_id, "heartbeat": now}

    # -----------------------------------------------------------------------
    # Audit Log
    # -----------------------------------------------------------------------

    def log_audit(
        self,
        action: str,
        agent_id: str = "",
        task_id: str = "",
        ip_address: str = "",
        request_body: str = "",
        response_status: int = 200,
    ) -> None:
        """Write an audit log entry."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._conn()
        conn.execute(
            """INSERT INTO audit_log (agent_id, action, task_id, ip_address,
               request_body, response_status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (agent_id, action, task_id, ip_address, request_body, response_status, now),
        )
        conn.commit()
        conn.close()

    def get_audit_log(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Read audit log entries."""
        conn = self._conn()
        if agent_id:
            rows = conn.execute(
                "SELECT * FROM audit_log WHERE agent_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (agent_id, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_board: Optional[TaskBoard] = None


def get_task_board(db_path: Optional[str] = None) -> TaskBoard:
    """Get or create the global TaskBoard instance."""
    global _board
    if _board is None:
        _board = TaskBoard(
            db_path=db_path or os.getenv("TASKBOARD_DB", "data/taskboard.db")
        )
    return _board
