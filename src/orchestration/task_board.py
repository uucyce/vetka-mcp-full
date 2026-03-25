"""
Mycelium Task Board — Central Task Queue for Multi-Agent Dispatch

Phase 121: Multi-agent task queue system.

Task Board manages a priority queue of tasks that can be dispatched
to the Mycelium Pipeline (Dragon/Titan teams). Tasks are stored in
data/task_board.json with priority, complexity, dependencies, and status.

Flow:
    [Add Tasks] → [Priority Queue] → [Dispatch] → [Pipeline] → [Update Status]
                       ↑                                            │
                       └────────── [Heartbeat @board] ──────────────┘

@status: active
@phase: 121
@depends: src/orchestration/agent_pipeline.py, src/orchestration/mycelium_heartbeat.py
"""

import json
import sqlite3
import time
import logging
import os
import re
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("VETKA_TASK_BOARD")

# MARKER_121.1: Task Board storage
# MARKER_189.11: Resolve to main repo root — safe from worktree cwd confusion.
# Priority: VETKA_MAIN_REPO env > git rev-parse > __file__-relative
def _resolve_main_repo_root() -> Path:
    """Find the main repo root, even when called from a worktree."""
    env_root = os.environ.get("VETKA_MAIN_REPO")
    if env_root and Path(env_root).is_dir():
        return Path(env_root)
    # __file__-relative: works when task_board.py lives in main repo (always true via .mcp.json)
    return Path(__file__).resolve().parent.parent.parent

_MAIN_ROOT = _resolve_main_repo_root()
TASK_BOARD_FILE = _MAIN_ROOT / "data" / "task_board.json"
TASK_BOARD_DB = _MAIN_ROOT / "data" / "task_board.db"
_TASK_BOARD_FALLBACK = Path(os.environ.get('TMPDIR', '/tmp')) / "vetka_task_board.json"
_TASK_BOARD_DB_FALLBACK = Path(os.environ.get('TMPDIR', '/tmp')) / "vetka_task_board.db"
PROJECT_ROOT = _MAIN_ROOT

# MARKER_192.1: Indexed columns for SQLite hybrid schema.
# These columns get their own DB columns + indexes for WHERE/ORDER BY.
# Everything else goes into the 'extra' JSON blob column.
INDEXED_COLUMNS = [
    "id", "title", "description", "priority", "status", "phase_type",
    "complexity", "project_id", "assigned_to", "agent_type", "assigned_at",
    "created_by", "created_at", "started_at", "completed_at", "closed_at",
    "commit_hash", "commit_message", "updated_at",
]
_INDEXED_SET = frozenset(INDEXED_COLUMNS)

# Priority levels
PRIORITY_CRITICAL = 1
PRIORITY_HIGH = 2
PRIORITY_MEDIUM = 3
PRIORITY_LOW = 4
PRIORITY_SOMEDAY = 5

# Valid statuses
# MARKER_125.1B: Added "hold" — Doctor triage puts abstract tasks on hold for human approval
# MARKER_130.C16A: Added "claimed" status for multi-agent support
# MARKER_183.10: Added "pending_user_approval" — verification gate before merge
# MARKER_186.4: Added "done_worktree" / "done_main" — worktree-aware lifecycle
#   done_worktree = committed on branch, pending merge to main
#   done_main = merged to main (or committed directly on main)
#   verified = QA gate passed (MARKER_195.20), ready for merge
#   needs_fix = QA gate failed, needs re-work
# MARKER_196.QA: Added "need_qa" — explicit QA gate request between done_worktree and verified
VALID_STATUSES = {"pending", "queued", "claimed", "running", "done", "done_worktree", "need_qa", "done_main", "failed", "cancelled", "hold", "pending_user_approval", "verified", "needs_fix"}
VALID_PHASE_TYPES = {"build", "fix", "research", "test"}

# Agent types
AGENT_TYPES = {"claude_code", "cursor", "mycelium", "grok", "human", "unknown"}

# Counter for generating IDs
_task_counter = 0
DEFAULT_PROTOCOL_VERSION = "multitask_mcp_v1"
DEFAULT_VERIFIER_PASS_THRESHOLD = float(os.getenv("VETKA_VERIFIER_PASS_THRESHOLD", "0.75"))


def _generate_task_id() -> str:
    """Generate unique task ID."""
    global _task_counter
    _task_counter += 1
    return f"tb_{int(time.time())}_{_task_counter}"


class TaskBoard:
    """Central task queue for Mycelium pipeline dispatch.

    Manages a JSON-backed priority queue of tasks. Tasks are dispatched
    to AgentPipeline with appropriate presets based on complexity and tags.

    Usage:
        board = TaskBoard()
        task_id = board.add_task("Fix bug", "Fix file positioning", priority=2)
        await board.dispatch_next(chat_id="some-chat-id")
    """

    # MARKER_133.C33C: Class-level semaphore for concurrent dispatch limiting
    _dispatch_semaphore: Optional[asyncio.Semaphore] = None
    _dispatch_semaphore_size: int = 2  # Default max concurrent

    @classmethod
    def _get_dispatch_semaphore(cls, max_concurrent: int = 2) -> asyncio.Semaphore:
        """Get or create the dispatch semaphore.

        MARKER_133.C33C: Enforces max_concurrent pipelines running.
        """
        # Create new semaphore if size changed or doesn't exist
        if cls._dispatch_semaphore is None or cls._dispatch_semaphore_size != max_concurrent:
            cls._dispatch_semaphore = asyncio.Semaphore(max_concurrent)
            cls._dispatch_semaphore_size = max_concurrent
            logger.info(f"[TaskBoard] Created dispatch semaphore with max_concurrent={max_concurrent}")
        return cls._dispatch_semaphore

    @classmethod
    def get_concurrent_info(cls, board: 'TaskBoard') -> Dict[str, Any]:
        """Get current concurrency info for monitoring.

        MARKER_133.C33C: Returns max, available slots, and running count.
        """
        max_c = board.settings.get("max_concurrent", 2)
        sem = cls._get_dispatch_semaphore(max_c)
        try:
            cursor = board.db.execute("SELECT COUNT(*) FROM tasks WHERE status = 'running'")
            running = cursor.fetchone()[0]
        except Exception:
            running = len([t for t in board.tasks.values() if t.get("status") == "running"])
        return {
            "max": max_c,
            "available": sem._value if hasattr(sem, '_value') else max_c,
            "running": running,
        }
    # MARKER_133.C33C_END

    def __init__(self, board_file: Optional[Path] = None):
        """Initialize TaskBoard with storage.

        MARKER_192.3: SQLite-first init. Accepts both .json (legacy) and .db paths.
        If board_file ends with .json, derives .db path from it.
        If board_file ends with .db, uses it directly.
        If board_file is None, uses TASK_BOARD_DB.

        Args:
            board_file: Path to storage file. Defaults to data/task_board.db.
        """
        # Determine DB path
        if board_file is not None:
            if str(board_file).endswith(".json"):
                # Legacy callers passing .json path → derive .db path
                self.board_file = board_file
                self.db_path = board_file.parent / (board_file.stem + ".db")
            elif str(board_file).endswith(".db"):
                self.db_path = board_file
                self.board_file = board_file.parent / (board_file.stem + ".json")
            else:
                self.db_path = board_file
                self.board_file = TASK_BOARD_FILE
        else:
            self.db_path = TASK_BOARD_DB
            self.board_file = TASK_BOARD_FILE

        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.settings: Dict[str, Any] = {
            "max_concurrent": 2,
            "auto_dispatch": True,  # MARKER_137.S1_1_EVENT_DISPATCH: Enable by default
            "default_preset": "dragon_silver"
        }
        self.integrity_warning: str = ""

        # MARKER_192.3: SQLite connection + schema + migration
        self.db = self._connect()
        self._ensure_schema()
        self._migrate_json_to_sqlite()

        # Load settings from DB
        db_settings = self._load_settings()
        if db_settings:
            self.settings.update(db_settings)

        # Fill in-memory cache for backward compat
        self.tasks = self._load_all_tasks()
        self._backfill_modules()

    # ==========================================
    # PERSISTENCE
    # ==========================================

    def _load(self):
        """Reload task board from SQLite.

        MARKER_192.3: Reads all tasks from DB into self.tasks cache.
        Called only for explicit full refresh (rare).
        """
        self.tasks = self._load_all_tasks()
        db_settings = self._load_settings()
        if db_settings:
            self.settings.update(db_settings)
        logger.info(f"[TaskBoard] Loaded {len(self.tasks)} tasks from SQLite")

    def _backfill_modules(self):
        """MARKER_155.2A: Backfill 'module' field for existing tasks."""
        updated = 0
        for task in self.tasks.values():
            if "module" not in task or not task.get("module"):
                task["module"] = self._auto_assign_module(
                    task.get("title", ""),
                    task.get("description", ""),
                    task.get("tags", []),
                )
                self._save_task(task)
                updated += 1
        if updated > 0:
            logger.info(f"[TaskBoard] Backfilled module for {updated} tasks")

    def _save(self, action: str = "update"):
        """Persist settings and notify UI.

        MARKER_192.3: Tasks are now saved per-operation via _save_task().
        This method only saves settings and emits the UI notification.
        """
        self._save_settings()
        # MARKER_124.3D: Emit SocketIO event for live UI updates
        self._notify_board_update(action)

    # ==========================================
    # MARKER_192.1: SQLite Storage Layer
    # ==========================================

    def _connect(self) -> sqlite3.Connection:
        """Open SQLite connection with WAL mode and busy_timeout.

        MARKER_192.1: Core DB connection setup.
        """
        db_path = self.db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        """Create tasks/settings/meta tables and indexes if they don't exist.

        MARKER_192.1: Idempotent schema creation.
        """
        with self.db:
            self.db.executescript("""
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
                    extra TEXT DEFAULT '{}',
                    updated_at TEXT DEFAULT ''
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
            """)

    @staticmethod
    def _task_to_row(task: dict) -> dict:
        """Convert in-memory task dict to DB row dict.

        MARKER_192.1: Splits indexed columns from extra JSON blob.
        """
        row = {}
        extra = {}
        for k, v in task.items():
            if k in _INDEXED_SET:
                # Coerce None to empty string for TEXT columns, keep int for priority
                if k == "priority":
                    row[k] = int(v) if v is not None else 3
                else:
                    row[k] = str(v) if v is not None else ""
            else:
                extra[k] = v
        # Ensure all indexed columns have a value
        for col in INDEXED_COLUMNS:
            if col not in row:
                row[col] = 3 if col == "priority" else ""
        row["extra"] = json.dumps(extra, default=str, ensure_ascii=False)
        return row

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> dict:
        """Convert DB row back to task dict.

        MARKER_192.1: Merges indexed columns with parsed extra JSON.
        """
        task = dict(row)
        extra_raw = task.pop("extra", "{}")
        try:
            extra = json.loads(extra_raw) if extra_raw else {}
        except (json.JSONDecodeError, TypeError):
            extra = {}
        # Merge extra into task (indexed columns take precedence)
        for k, v in extra.items():
            if k not in task:
                task[k] = v
        # Convert priority back to int
        try:
            task["priority"] = int(task.get("priority", 3))
        except (TypeError, ValueError):
            task["priority"] = 3
        # Convert empty strings back to None for nullable fields
        for field in ("started_at", "completed_at", "closed_at", "commit_hash",
                       "commit_message", "assigned_to", "assigned_at"):
            if task.get(field) == "":
                task[field] = None
        return task

    def _save_task(self, task: dict):
        """INSERT OR REPLACE a single task into SQLite.

        MARKER_192.1: Per-row atomic write — no full-board overwrite.
        """
        row = self._task_to_row(task)
        row["updated_at"] = datetime.now().isoformat()
        columns = list(row.keys())
        placeholders = ", ".join("?" for _ in columns)
        col_names = ", ".join(columns)
        values = [row[c] for c in columns]
        with self.db:
            self.db.execute(
                f"INSERT OR REPLACE INTO tasks ({col_names}) VALUES ({placeholders})",
                values,
            )

    def _delete_task(self, task_id: str):
        """DELETE a single task row from SQLite.

        MARKER_192.1: Per-row delete.
        """
        with self.db:
            self.db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def _load_all_tasks(self) -> Dict[str, dict]:
        """SELECT all tasks from SQLite → dict keyed by task ID.

        MARKER_192.1: Used for migration/startup cache fill.
        """
        cursor = self.db.execute("SELECT * FROM tasks")
        tasks = {}
        for row in cursor:
            task = self._row_to_task(row)
            tasks[task["id"]] = task
        return tasks

    def _load_task(self, task_id: str) -> Optional[dict]:
        """SELECT a single task by ID from SQLite.

        MARKER_192.1: Point query for get_task().
        """
        cursor = self.db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_task(row)

    def _save_settings(self):
        """Persist board settings to SQLite settings table.

        MARKER_192.1: Key-value storage for board config.
        """
        with self.db:
            for key, value in self.settings.items():
                if str(key).startswith("_"):
                    continue
                self.db.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (key, json.dumps(value, default=str, ensure_ascii=False)),
                )

    def _load_settings(self) -> Dict[str, Any]:
        """Read board settings from SQLite settings table.

        MARKER_192.1: Returns deserialized settings dict.
        """
        settings = {}
        try:
            cursor = self.db.execute("SELECT key, value FROM settings")
            for row in cursor:
                try:
                    settings[row["key"]] = json.loads(row["value"])
                except (json.JSONDecodeError, TypeError):
                    settings[row["key"]] = row["value"]
        except sqlite3.OperationalError:
            pass  # Table may not exist yet
        return settings

    def _migrate_json_to_sqlite(self):
        """Auto-migrate from JSON file to SQLite if DB is empty but JSON exists.

        MARKER_192.1: Zero-downtime migration on first startup.
        """
        # Check if DB already has tasks
        try:
            cursor = self.db.execute("SELECT COUNT(*) FROM tasks")
            count = cursor.fetchone()[0]
            if count > 0:
                return  # DB already populated
        except sqlite3.OperationalError:
            self._ensure_schema()

        # Find JSON file to migrate from (check .bak too for post-migration recovery)
        json_bak = TASK_BOARD_FILE.with_suffix(".json.bak")
        json_path = None
        for path in [TASK_BOARD_FILE, json_bak, _TASK_BOARD_FALLBACK]:
            if path.exists():
                json_path = path
                break

        if not json_path:
            return  # No JSON to migrate

        try:
            data = json.loads(json_path.read_text())
            tasks = data.get("tasks", {})
            settings = data.get("settings", {})

            if not tasks:
                return

            # Insert all tasks
            for task in tasks.values():
                self._save_task(task)

            # Save settings
            if settings:
                for key, value in settings.items():
                    if not str(key).startswith("_"):
                        self.settings[key] = value
                self._save_settings()

            logger.info(f"[TaskBoard] Migrated {len(tasks)} tasks from {json_path} to SQLite")
        except Exception as e:
            logger.warning(f"[TaskBoard] JSON→SQLite migration failed: {e}")

    @staticmethod
    def _history_entry(
        *,
        event: str,
        status: str,
        agent_name: str = "",
        agent_type: str = "",
        source: str = "task_board",
        reason: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        entry = {
            "ts": datetime.now().isoformat(),
            "event": str(event or status or "update"),
            "status": str(status or ""),
            "agent_name": str(agent_name or ""),
            "agent_type": str(agent_type or ""),
            "source": str(source or "task_board"),
            "reason": str(reason or "")[:300],
        }
        if isinstance(extra, dict) and extra:
            entry["extra"] = extra
        return entry

    def _append_history(
        self,
        task: Dict[str, Any],
        *,
        event: str,
        status: str,
        agent_name: str = "",
        agent_type: str = "",
        source: str = "task_board",
        reason: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        history = task.setdefault("status_history", [])
        if not isinstance(history, list):
            history = []
            task["status_history"] = history
        history.append(
            self._history_entry(
                event=event,
                status=status,
                agent_name=agent_name,
                agent_type=agent_type,
                source=source,
                reason=reason,
                extra=extra,
            )
        )
        task["status_history"] = history[-50:]

    def get_task_history(self, task_id: str) -> List[Dict[str, Any]]:
        task = self.get_task(task_id)
        if not task:
            return []
        history = task.get("status_history")
        return list(history) if isinstance(history, list) else []

    # MARKER_183.5: failure_history + eval_delta quality gate
    def record_failure(
        self,
        task_id: str,
        *,
        verifier_feedback: Optional[Dict[str, Any]] = None,
        pipeline_stats: Optional[Dict[str, Any]] = None,
        issues: Optional[List[str]] = None,
        tier_used: str = "",
    ) -> Dict[str, Any]:
        """Record a pipeline failure and reset task to pending for retry.

        Appends a failure record to task.failure_history so the next pipeline
        run (new coder) gets full context of what went wrong.

        Returns dict with success status and attempt number.
        """
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        history = task.get("failure_history", [])
        if not isinstance(history, list):
            history = []

        attempt = len(history) + 1
        record: Dict[str, Any] = {
            "attempt": attempt,
            "timestamp": datetime.now().isoformat(),
            "tier_used": tier_used,
        }
        if verifier_feedback:
            record["verifier_confidence"] = verifier_feedback.get("confidence", 0)
            record["issues"] = verifier_feedback.get("issues", [])[:10]
            record["suggestions"] = verifier_feedback.get("suggestions", [])[:5]
            record["severity"] = verifier_feedback.get("severity", "unknown")
        if pipeline_stats:
            record["verifier_avg_confidence"] = pipeline_stats.get("verifier_avg_confidence", 0)
            record["subtasks_completed"] = pipeline_stats.get("subtasks_completed", 0)
            record["subtasks_total"] = pipeline_stats.get("subtasks_total", 0)
            record["duration_s"] = pipeline_stats.get("duration_s", 0)
        if issues:
            record.setdefault("issues", []).extend(issues[:10])

        history.append(record)
        # Keep last 5 attempts to avoid bloat
        history = history[-5:]

        self.update_task(
            task_id,
            status="pending",
            failure_history=history,
            assigned_to=None,  # release — new coder picks up
            _history_event="failure_recorded",
            _history_source="eval_delta",
            _history_reason=f"attempt {attempt} failed, reset to pending for retry",
        )

        logger.info(f"[TaskBoard] Task {task_id} failure #{attempt} recorded, reset to pending")

        # MARKER_187.12: Feed failure into memory subsystems (non-blocking)
        try:
            from src.memory.failure_feedback import record_failure_feedback
            failed_tools = []
            if verifier_feedback:
                failed_tools = verifier_feedback.get("failed_tools", [])
            record_failure_feedback(
                task_id=task_id,
                error_summary="; ".join(issues[:3]) if issues else "pipeline failure",
                failed_tools=failed_tools,
                tier_used=tier_used,
                attempt=attempt,
                severity=verifier_feedback.get("severity", "major") if verifier_feedback else "major",
            )
        except Exception as e:
            logger.debug(f"[TaskBoard] Failure feedback skipped: {e}")

        return {"success": True, "attempt": attempt, "task_id": task_id}

    @staticmethod
    def compute_eval_score(pipeline_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Compute eval_delta score and verdict from pipeline stats.

        Returns: {"eval_score": float, "eval_verdict": str}
        Verdict: "improved" (≥0.65), "neutral" (0.35-0.65), "regressed" (<0.35)
        """
        # No data → neutral baseline
        if not pipeline_stats or (
            "verifier_avg_confidence" not in pipeline_stats
            and "subtasks_total" not in pipeline_stats
        ):
            return {"eval_score": 0.5, "eval_verdict": "neutral"}

        score = 0.5  # baseline = neutral

        # Verifier confidence (±0.3) — biggest signal
        confidence = pipeline_stats.get("verifier_avg_confidence", 0.75)
        score += (confidence - 0.75) * 1.2  # 0.75 = threshold

        # Completion ratio (±0.2)
        total = pipeline_stats.get("subtasks_total", 0) or 1
        completed = pipeline_stats.get("subtasks_completed", 0)
        if total > 0:
            ratio = completed / total
            score += (ratio - 0.8) * 1.0  # 80% completion = neutral

        # Retries penalty (max -0.1)
        # Not always available, degrade gracefully
        retries = pipeline_stats.get("retries", 0)
        if retries:
            score -= min(0.1, retries * 0.03)

        score = max(0.0, min(1.0, score))

        if score >= 0.65:
            verdict = "improved"
        elif score >= 0.35:
            verdict = "neutral"
        else:
            verdict = "regressed"

        return {"eval_score": round(score, 3), "eval_verdict": verdict}

    @staticmethod
    def _normalize_test_commands(commands: Any) -> List[str]:
        if isinstance(commands, str):
            return [commands.strip()] if commands.strip() else []
        if not isinstance(commands, list):
            return []
        out = []
        for item in commands:
            text = str(item or "").strip()
            if text:
                out.append(text)
        return out

    @staticmethod
    def _normalize_doc_refs(items: Any) -> List[str]:
        if isinstance(items, str):
            text = items.strip()
            return [text] if text else []
        if not isinstance(items, list):
            return []
        out: List[str] = []
        seen = set()
        for item in items:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            out.append(text)
        return out

    @staticmethod
    def _normalize_phase_type(phase_type: Optional[str]) -> str:
        value = str(phase_type or "build").strip().lower()
        if value in VALID_PHASE_TYPES:
            return value
        raise ValueError(f"Invalid phase_type '{phase_type}'. Expected one of: {sorted(VALID_PHASE_TYPES)}")

    def _normalize_protocol_fields(
        self,
        *,
        architecture_docs: Any,
        recon_docs: Any,
        protocol_version: Optional[str],
        require_closure_proof: bool,
        closure_tests: Any,
        closure_files: Any,
    ) -> Dict[str, Any]:
        docs = self._normalize_doc_refs(architecture_docs)
        recon = self._normalize_doc_refs(recon_docs)
        tests = self._normalize_test_commands(closure_tests)
        files = self._normalize_doc_refs(closure_files)
        proof_required = bool(require_closure_proof or tests)
        protocol = protocol_version or (DEFAULT_PROTOCOL_VERSION if (proof_required or docs or recon) else None)
        return {
            "architecture_docs": docs,
            "recon_docs": recon,
            "protocol_version": protocol,
            "require_closure_proof": proof_required,
            "closure_tests": tests,
            "closure_files": files,
        }

    async def _run_closure_tests(self, commands: List[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for command in commands:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(PROJECT_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            results.append(
                {
                    "command": command,
                    "passed": proc.returncode == 0,
                    "exit_code": int(proc.returncode or 0),
                    "stdout": stdout.decode("utf-8", errors="replace")[-2000:],
                    "stderr": stderr.decode("utf-8", errors="replace")[-2000:],
                }
            )
            if proc.returncode != 0:
                break
        return results

    # MARKER_192.2: Infer execution_mode from agent_type
    _MANUAL_AGENT_TYPES = {"claude_code", "cursor", "human", "grok", "codex"}
    # MARKER_191.8: Also match by agent_name when agent_type is unknown
    _MANUAL_AGENT_NAMES = {"opus", "cursor", "codex", "grok", "claude-code", "opencode"}

    @staticmethod
    def _infer_execution_mode(agent_type: Optional[str], agent_name: Optional[str] = None) -> str:
        """Infer execution_mode from agent_type or agent_name.

        MARKER_191.8: Also checks agent_name when agent_type is unknown.
        CLI agents (claude_code, cursor, codex) get 'manual' — they commit directly.
        Pipeline agents (mycelium, dragon) get 'pipeline' — they need verifier proof.
        """
        if agent_type and agent_type in TaskBoard._MANUAL_AGENT_TYPES:
            return "manual"
        if agent_name and agent_name.lower() in TaskBoard._MANUAL_AGENT_NAMES:
            return "manual"
        return "pipeline"

    def _closure_threshold(self, task: Dict[str, Any]) -> float:
        try:
            return float(task.get("verifier_threshold") or DEFAULT_VERIFIER_PASS_THRESHOLD)
        except (TypeError, ValueError):
            return DEFAULT_VERIFIER_PASS_THRESHOLD

    def _validate_closure_proof(
        self,
        task: Dict[str, Any],
        closure_proof: Optional[Dict[str, Any]],
        *,
        manual_override: bool = False,
    ) -> Optional[str]:
        if manual_override:
            return None
        if not task.get("require_closure_proof"):
            return None
        if not isinstance(closure_proof, dict):
            return "closure_proof is required for protocol tasks"

        # MARKER_192.2: execution_mode guard — manual agents skip pipeline/verifier checks
        exec_mode = task.get("execution_mode", "pipeline")
        if exec_mode == "manual":
            # Manual agents only need commit_hash proof
            if not str(closure_proof.get("commit_hash") or "").strip():
                return "closure_proof.commit_hash is required for protocol task closure"
            # If closure_tests were defined, validate them (but don't require pipeline/verifier)
            tests = closure_proof.get("tests")
            if isinstance(tests, list) and tests:
                if any(not isinstance(row, dict) or not row.get("passed") for row in tests):
                    return "all closure_proof tests must pass before closing the task"
            return None

        # --- Full pipeline proof (execution_mode == "pipeline") ---
        stats = task.get("stats") if isinstance(task.get("stats"), dict) else {}
        if not bool(closure_proof.get("pipeline_success", stats.get("success"))):
            return "pipeline_success must be true before closing the task"

        verifier_confidence = closure_proof.get("verifier_confidence", stats.get("verifier_avg_confidence", 0))
        try:
            verifier_confidence = float(verifier_confidence or 0)
        except (TypeError, ValueError):
            verifier_confidence = 0.0
        if verifier_confidence < self._closure_threshold(task):
            return f"verifier_confidence {verifier_confidence:.2f} is below threshold"

        tests = closure_proof.get("tests")
        if not isinstance(tests, list) or not tests:
            return "closure_proof.tests must contain at least one passing test"
        if any(not isinstance(row, dict) or not row.get("passed") for row in tests):
            return "all closure_proof tests must pass before closing the task"

        if not str(closure_proof.get("commit_hash") or "").strip():
            return "closure_proof.commit_hash is required for protocol task closure"
        return None

    def _mark_closure_failed(
        self,
        task_id: str,
        *,
        reason: str,
        activating_agent: str = "",
        agent_type: str = "",
        closure_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        self.update_task(
            task_id,
            status="failed",
            completed_at=datetime.now().isoformat(),
            result_summary=str(reason)[:500],
            closure_subtask={
                "status": "failed",
                "finished_at": datetime.now().isoformat(),
                "tests": closure_results or [],
                "reason": reason[:500],
            },
            _history_event="closure_failed",
            _history_source="closure_protocol",
            _history_reason=reason[:300],
            _history_agent_name=activating_agent,
            _history_agent_type=agent_type,
        )
        return {"success": False, "error": reason, "task_id": task_id, "tests": closure_results or []}

    @staticmethod
    def _detect_current_branch(cwd: str = None) -> Optional[str]:
        """MARKER_186.4: Detect current git branch. Works in worktrees.
        MARKER_195.1: Returns None instead of silently falling back to 'main'.
        MARKER_195.20: Accept cwd override for worktree-correct detection.
        Callers must handle None explicitly to avoid false branch attribution.
        """
        import subprocess
        git_cwd = cwd or str(PROJECT_ROOT)
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=git_cwd, capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        logger.warning("[TaskBoard] _detect_current_branch: could not detect branch, returning None (was silently returning 'main')")
        return None

    def _notify_board_update(self, action: str = "update", event_data: Optional[Dict[str, Any]] = None):
        """MARKER_124.3D: Emit SocketIO event for live Task Board UI updates.
        MARKER_130.C18C: Enhanced with event_data for claim/complete actions.

        Uses fire-and-forget HTTP POST to our own REST endpoint which has sio access.
        Falls back silently if server isn't running.

        Args:
            action: Event action type (update, task_claimed, task_completed, etc.)
            event_data: Optional extra data to include in event (task_id, assigned_to, etc.)
        """
        try:
            import asyncio
            summary = self.get_board_summary()

            # MARKER_130.C18C: Build payload with optional event_data
            payload = {"action": action, "summary": summary}
            if event_data:
                payload.update(event_data)

            async def _emit():
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=2.0) as client:
                        await client.post(
                            "http://localhost:5001/api/debug/task-board/notify",
                            json=payload
                        )
                except Exception:
                    pass

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_emit())
            except RuntimeError:
                pass  # No event loop (sync context)
        except Exception:
            pass  # Never block save on notification failure

    # MARKER_137.S1_1_EVENT_DISPATCH: Update board settings (auto_dispatch, max_concurrent, etc.)
    def update_settings(self, **kwargs) -> Dict[str, Any]:
        """Update board settings and persist to disk."""
        allowed_keys = {"auto_dispatch", "max_concurrent", "default_preset"}
        updated = {}
        for key, value in kwargs.items():
            if key in allowed_keys:
                self.settings[key] = value
                updated[key] = value
        if updated:
            self._save_settings()
            self._notify_board_update("settings_updated")
        return {"updated": updated, "settings": self.settings}

    # ==========================================
    # CRUD OPERATIONS
    # ==========================================

    def add_task(
        self,
        title: str,
        description: str = "",
        priority: int = PRIORITY_MEDIUM,
        phase_type: str = "build",
        complexity: str = "medium",
        preset: Optional[str] = None,
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        source: str = "manual",
        assigned_to: Optional[str] = None,  # MARKER_130.C16A
        agent_type: Optional[str] = None,   # MARKER_130.C16A
        created_by: str = "unknown",        # MARKER_133.C33D: Client attribution
        session_id: Optional[str] = None,          # MARKER_183.1: Heartbeat session ID
        source_chat_id: Optional[str] = None,   # MARKER_152.3: Chat provenance
        source_group_id: Optional[str] = None,  # MARKER_152.3: Group provenance
        module: Optional[str] = None,            # MARKER_155.2A: Roadmap module assignment
        primary_node_id: Optional[str] = None,   # MARKER_155.G1.TASK_ANCHORING_CONTRACT_V1
        affected_nodes: Optional[List[str]] = None,  # MARKER_155.G1.TASK_ANCHORING_CONTRACT_V1
        workflow_id: Optional[str] = None,       # MARKER_155.G1.TASK_ANCHORING_CONTRACT_V1
        workflow_bank: Optional[str] = None,     # MARKER_167.STATS_WORKFLOW.TASK_BINDING.V1
        workflow_family: Optional[str] = None,   # MARKER_167.STATS_WORKFLOW.TASK_BINDING.V1
        workflow_selection_origin: Optional[str] = None,  # MARKER_167.STATS_WORKFLOW.TASK_BINDING.V1
        team_profile: Optional[str] = None,      # MARKER_155.G1.TASK_ANCHORING_CONTRACT_V1
        task_origin: Optional[str] = None,       # MARKER_155.G1.TASK_ANCHORING_CONTRACT_V1
        roadmap_id: Optional[str] = None,
        roadmap_node_id: Optional[str] = None,
        roadmap_lane: Optional[str] = None,
        roadmap_title: Optional[str] = None,
        ownership_scope: Optional[str] = None,
        allowed_paths: Optional[List[str]] = None,
        owner_agent: Optional[str] = None,
        completion_contract: Optional[List[str]] = None,
        verification_agent: Optional[str] = None,
        blocked_paths: Optional[List[str]] = None,
        forbidden_scopes: Optional[List[str]] = None,
        worktree_hint: Optional[str] = None,
        touch_policy: Optional[str] = None,
        overlap_risk: Optional[str] = None,
        depends_on_docs: Optional[List[str]] = None,
        project_id: Optional[str] = None,
        project_lane: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        architecture_docs: Optional[List[str]] = None,
        recon_docs: Optional[List[str]] = None,
        protocol_version: Optional[str] = None,
        require_closure_proof: bool = False,
        closure_tests: Optional[List[str]] = None,
        closure_files: Optional[List[str]] = None,
        implementation_hints: Optional[str] = None,  # MARKER_191.6: Algorithm/approach guidance
        execution_mode: Optional[str] = None,  # MARKER_192.2: "pipeline" | "manual" — controls closure proof requirements
        role: Optional[str] = None,    # MARKER_ZETA.D4: Agent callsign (Alpha/Beta/Gamma/Delta/Commander)
        domain: Optional[str] = None,  # MARKER_ZETA.D4: Domain (engine/media/ux/qa/architect)
    ) -> str:
        """Add a new task to the board.

        Args:
            title: Short task title
            description: Detailed description for pipeline
            priority: 1 (critical) to 5 (someday)
            phase_type: "build" | "fix" | "research"
            complexity: "low" | "medium" | "high"
            preset: Optional pipeline preset override
            tags: Optional tags for categorization
            dependencies: Optional list of task IDs that must complete first
            source: Origin of task ("manual", "dragon_todo", "titan_todo", etc.)
            assigned_to: Agent name who should work on this ("opus", "cursor", "dragon")
            agent_type: Agent type ("claude_code", "cursor", "mycelium", "grok", "human")
            created_by: Client that created task ("claude-code", "cursor", "opencode", "heartbeat")

        Returns:
            Generated task ID
        """
        task_id = _generate_task_id()
        priority = max(1, min(5, priority))  # Clamp 1-5
        phase_type = self._normalize_phase_type(phase_type)
        protocol_fields = self._normalize_protocol_fields(
            architecture_docs=architecture_docs,
            recon_docs=recon_docs,
            protocol_version=protocol_version,
            require_closure_proof=require_closure_proof,
            closure_tests=closure_tests,
            closure_files=closure_files,
        )

        task_payload = {
            "id": task_id,
            "title": title,
            "description": description or title,
            "priority": priority,
            "complexity": complexity,
            "phase_type": phase_type,
            "preset": preset,
            "assigned_tier": None,
            "status": "pending",
            "source": source,
            "tags": tags or [],
            "dependencies": dependencies or [],
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "pipeline_task_id": None,
            "result_summary": None,
            "stats": None,
            # MARKER_135.DAG_BRIDGE: Result data for DAG visualization
            "result": None,  # {agents: {...}, subtasks: [...]} for DAGAggregator
            # MARKER_130.C16A: Multi-agent coordination fields
            "assigned_to": assigned_to,       # Agent name: "opus", "cursor", "dragon", "grok"
            "assigned_at": None,              # ISO timestamp when claimed
            "agent_type": agent_type,         # "claude_code", "cursor", "mycelium", "grok", "human"
            "commit_hash": None,              # Git commit that completed this task
            "commit_message": None,           # First line of commit message
            # MARKER_133.C33D: Client attribution
            "created_by": created_by,         # "claude-code", "cursor", "opencode", "heartbeat"
            # MARKER_152.3: Task provenance — trace back to originating chat
            # MARKER_183.1: Session ID links all tasks from one heartbeat tick
            "session_id": session_id,
            "source_chat_id": source_chat_id,   # VETKA chat UUID where task was created
            "source_group_id": source_group_id, # Group chat UUID (for @dragon/@doctor tasks)
            # MARKER_155.2A: Roadmap module assignment for drill-down filtering
            "module": module or self._auto_assign_module(title, description or title, tags or []),
            # MARKER_155.G1.TASK_ANCHORING_CONTRACT_V1: explicit task-to-code anchor metadata
            "primary_node_id": primary_node_id,
            "affected_nodes": affected_nodes or [],
            "workflow_id": workflow_id,
            "workflow_bank": workflow_bank,
            "workflow_family": workflow_family,
            "workflow_selection_origin": workflow_selection_origin,
            "team_profile": team_profile,
            "task_origin": task_origin,
            "roadmap_id": roadmap_id,
            "roadmap_node_id": roadmap_node_id,
            "roadmap_lane": roadmap_lane,
            "roadmap_title": roadmap_title,
            "ownership_scope": ownership_scope,
            "allowed_paths": self._normalize_doc_refs(allowed_paths),
            "owner_agent": owner_agent,
            "completion_contract": self._normalize_doc_refs(completion_contract),
            "verification_agent": verification_agent,
            "blocked_paths": self._normalize_doc_refs(blocked_paths),
            "forbidden_scopes": self._normalize_doc_refs(forbidden_scopes),
            "worktree_hint": worktree_hint,
            "touch_policy": touch_policy,
            "overlap_risk": overlap_risk,
            "depends_on_docs": self._normalize_doc_refs(depends_on_docs),
            "project_id": project_id,
            "project_lane": project_lane or project_id,
            "parent_task_id": parent_task_id,
            "architecture_docs": protocol_fields["architecture_docs"],
            "recon_docs": protocol_fields["recon_docs"],
            "protocol_version": protocol_fields["protocol_version"],
            "require_closure_proof": protocol_fields["require_closure_proof"],
            "closure_tests": protocol_fields["closure_tests"],
            "closure_files": protocol_fields["closure_files"],
            # MARKER_191.6: Structured task guidance
            "implementation_hints": implementation_hints or "",
            # MARKER_192.2: execution_mode — controls closure proof requirements
            # "pipeline" = full proof (pipeline_success + verifier + tests)
            # "manual" = relaxed proof (commit_hash only, closure_tests if defined)
            "execution_mode": execution_mode or self._infer_execution_mode(agent_type),
            # MARKER_ZETA.D4: Agent role/domain binding
            "role": role or "",        # Agent callsign from agent_registry.yaml
            "domain": domain or "",    # Domain from agent_registry.yaml
            "closure_subtask": {
                "status": "pending" if protocol_fields["require_closure_proof"] else "not_required",
                "tests": [],
                "finished_at": None,
            },
            "closed_by": None,
            "closed_at": None,
            "closure_proof": None,
            "status_history": [],
        }
        self._append_history(
            task_payload,
            event="created",
            status="pending",
            agent_name=created_by,
            agent_type=agent_type or "unknown",
            source=source,
            reason="task created",
            extra={
                "project_lane": project_lane or project_id or "",
                "parent_task_id": parent_task_id or "",
                "protocol_version": task_payload.get("protocol_version") or "",
            },
        )
        self.tasks[task_id] = task_payload
        self._save_task(task_payload)
        self._notify_board_update("added")
        logger.info(f"[TaskBoard] Added task {task_id}: {title} (P{priority}, {phase_type})")
        return task_id

    # MARKER_155.2A: Auto-assign module from task content
    # Maps keywords in title/description/tags to roadmap module IDs
    _MODULE_KEYWORDS: dict = {
        "backend_api": ["api", "routes", "endpoint", "rest", "http", "backend route"],
        "backend_orchestration": ["pipeline", "orchestration", "agent", "dragon", "mycelium", "heartbeat"],
        "backend_mcp": ["mcp", "mcp server", "mcp tool"],
        "backend_services": ["service", "roadmap", "config", "project config"],
        "backend_memory": ["memory", "cam", "stm", "engram", "qdrant", "vector"],
        "backend_elisya": ["elisya", "llm", "model", "provider", "call_model"],
        "backend_tools": ["tool", "fc_loop", "patch", "registry"],
        "backend_scanners": ["scanner", "scan", "watcher", "indexer"],
        "frontend_components": ["component", "ui", "panel", "view", "dag", "node", "mcc", "dagview",
                                "frontend", "canvas", "chat", "button", "toggle", "import", "drag"],
        "frontend_hooks": ["hook", "useSocket", "useStore", "useMCC"],
        "frontend_store": ["store", "zustand", "state"],
        "tests": ["test", "pytest", "e2e", "playwright"],
        "scripts": ["script", "setup", "deploy", "ci"],
    }

    @staticmethod
    def _auto_assign_module(title: str, description: str, tags: list) -> str:
        """Match task content to a roadmap module ID."""
        text = f"{title} {description} {' '.join(tags)}".lower()
        best_module = ""
        best_score = 0
        for module_id, keywords in TaskBoard._MODULE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_module = module_id
        return best_module

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID.

        MARKER_192.3: Reads from SQLite, updates in-memory cache.

        Args:
            task_id: Task identifier

        Returns:
            Task dict or None if not found
        """
        task = self._load_task(task_id)
        if task is not None:
            self.tasks[task_id] = task
        else:
            self.tasks.pop(task_id, None)
        return task

    def update_task(self, task_id: str, **updates) -> bool:
        """Update task fields.

        Args:
            task_id: Task identifier
            **updates: Field=value pairs to update

        Returns:
            True if task was found and updated
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"[TaskBoard] Task {task_id} not found for update")
            return False

        history_event = updates.pop("_history_event", None)
        history_source = updates.pop("_history_source", "task_board")
        history_reason = updates.pop("_history_reason", "")
        history_agent_name = updates.pop("_history_agent_name", "")
        history_agent_type = updates.pop("_history_agent_type", "")
        history_extra = updates.pop("_history_extra", None)

        old_status = str(task.get("status") or "")
        new_status = str(updates.get("status") or old_status)

        # Validate status if being updated
        if "status" in updates:
            if updates["status"] not in VALID_STATUSES:
                logger.warning(f"[TaskBoard] Invalid status: {updates['status']}")
                return False
            # MARKER_198.GUARD: Block done_worktree without commit_hash
            if updates["status"] == "done_worktree":
                has_commit = updates.get("commit_hash") or task.get("commit_hash")
                if not has_commit:
                    logger.warning(f"[TaskBoard] Blocked done_worktree for {task_id}: no commit_hash")
                    return False
        if "phase_type" in updates:
            try:
                updates["phase_type"] = self._normalize_phase_type(updates["phase_type"])
            except ValueError as e:
                logger.warning(f"[TaskBoard] {e}")
                return False

        protocol_update_keys = {"architecture_docs", "recon_docs", "protocol_version", "require_closure_proof", "closure_tests", "closure_files"}
        if any(key in updates for key in protocol_update_keys):
            protocol_fields = self._normalize_protocol_fields(
                architecture_docs=updates.get("architecture_docs", task.get("architecture_docs")),
                recon_docs=updates.get("recon_docs", task.get("recon_docs")),
                protocol_version=updates.get("protocol_version", task.get("protocol_version")),
                require_closure_proof=bool(updates.get("require_closure_proof", task.get("require_closure_proof"))),
                closure_tests=updates.get("closure_tests", task.get("closure_tests")),
                closure_files=updates.get("closure_files", task.get("closure_files")),
            )
            updates.update(protocol_fields)
            if "closure_subtask" not in updates:
                current = task.get("closure_subtask") if isinstance(task.get("closure_subtask"), dict) else {}
                if current.get("status") not in {"done", "manual_override"}:
                    updates["closure_subtask"] = {
                        **current,
                        "status": "pending" if protocol_fields["require_closure_proof"] else "not_required",
                        "tests": current.get("tests", []),
                        "finished_at": current.get("finished_at"),
                    }

        # MARKER_137.S1_4: Allow adding 'result' field even if not present
        # MARKER_151.12A: Added result_status for user feedback (applied/rejected/rework)
        # MARKER_152.3: Added source_chat_id, source_group_id for task provenance
        # MARKER_155.2A: Added 'module' for roadmap module assignment
        # MARKER_155.G1.TASK_ANCHORING_CONTRACT_V1: Added anchor metadata fields
        # MARKER_167.STATS_WORKFLOW.TASK_BINDING.V1: Added workflow binding metadata fields
        ADDABLE_FIELDS = {"result", "stats", "result_summary", "result_status", "feedback",
                          "session_id", "source_chat_id", "source_group_id", "module",
                          "primary_node_id", "affected_nodes", "workflow_id", "workflow_bank",
                          "workflow_family", "workflow_selection_origin", "team_profile", "task_origin",
                          "roadmap_id", "roadmap_node_id", "roadmap_lane", "roadmap_title",
                          "ownership_scope", "allowed_paths", "owner_agent", "completion_contract",
                          "verification_agent", "blocked_paths", "forbidden_scopes", "worktree_hint",
                          "touch_policy", "overlap_risk", "depends_on_docs",
                          "project_id", "project_lane", "parent_task_id", "architecture_docs",
                          "recon_docs", "protocol_version", "require_closure_proof", "closure_tests",
                          "closure_files", "closure_subtask", "closed_by", "closed_at",
                          "closure_proof", "status_history",
                          "branch_name", "merge_commits", "merge_strategy", "merge_result",  # MARKER_184.5
                          "failure_history",  # MARKER_183.5: Verifier failure records for retry learning
                          "implementation_hints",  # MARKER_191.6: Algorithm/approach guidance
                          }
        for key, value in updates.items():
            if key in task or key in ADDABLE_FIELDS:
                task[key] = value

        if history_event or ("status" in updates and new_status != old_status):
            self._append_history(
                task,
                event=str(history_event or f"status_{new_status}"),
                status=new_status,
                agent_name=history_agent_name or str(task.get("assigned_to") or ""),
                agent_type=history_agent_type or str(task.get("agent_type") or ""),
                source=str(history_source or "task_board"),
                reason=str(history_reason or ""),
                extra=history_extra if isinstance(history_extra, dict) else None,
            )

        self._save_task(task)
        self._notify_board_update("updated")
        logger.debug(f"[TaskBoard] Updated {task_id}: {list(updates.keys())}")
        return True

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the board.

        MARKER_192.3: Deletes from SQLite + in-memory cache.

        Args:
            task_id: Task identifier

        Returns:
            True if task was found and removed
        """
        task = self.get_task(task_id)
        if task is not None:
            self._delete_task(task_id)
            self.tasks.pop(task_id, None)
            self._notify_board_update("removed")
            logger.info(f"[TaskBoard] Removed task {task_id}")
            return True
        return False

    # ==========================================
    # MARKER_133.C33F: STALE TASK CLEANUP
    # ==========================================

    def cleanup_stale(
        self,
        running_timeout_min: int = 10,
        claimed_timeout_min: int = 5,
    ) -> int:
        """Mark stale running tasks as failed, release stale claimed tasks.

        Args:
            running_timeout_min: Max minutes a task can be "running" before marked failed
            claimed_timeout_min: Max minutes a task can be "claimed" before reset to pending

        Returns:
            Number of tasks cleaned up
        """
        now = datetime.now()
        cleaned = 0

        for task in self.tasks.values():
            status = task.get("status")

            if status == "running":
                started_at = task.get("started_at")
                if started_at:
                    try:
                        started = datetime.fromisoformat(started_at.replace("Z", "+00:00").replace("+00:00", ""))
                        if (now - started).total_seconds() > running_timeout_min * 60:
                            task["status"] = "failed"
                            task["result_summary"] = f"Timeout: running > {running_timeout_min}min"
                            self._append_history(
                                task,
                                event="stale_running_timeout",
                                status="failed",
                                agent_name=str(task.get("assigned_to") or ""),
                                agent_type=str(task.get("agent_type") or ""),
                                source="cleanup",
                                reason=f"running > {running_timeout_min}min",
                            )
                            self._save_task(task)
                            cleaned += 1
                            logger.info(f"[TaskBoard] Cleaned stale running task {task.get('id')}")
                    except Exception:
                        pass

            elif status == "claimed":
                assigned_at = task.get("assigned_at")
                if assigned_at:
                    try:
                        claimed = datetime.fromisoformat(assigned_at.replace("Z", "+00:00").replace("+00:00", ""))
                        if (now - claimed).total_seconds() > claimed_timeout_min * 60:
                            task["status"] = "pending"
                            task["assigned_to"] = None
                            task["assigned_at"] = None
                            self._append_history(
                                task,
                                event="stale_claim_released",
                                status="pending",
                                source="cleanup",
                                reason=f"claimed > {claimed_timeout_min}min",
                            )
                            self._save_task(task)
                            cleaned += 1
                            logger.info(f"[TaskBoard] Released stale claimed task {task.get('id')}")
                    except Exception:
                        pass

        if cleaned:
            self._notify_board_update("cleanup")
            logger.info(f"[TaskBoard] Cleaned {cleaned} stale tasks")

        return cleaned

    # ==========================================
    # MARKER_198.STALE: STALE TASK DETECTION
    # ==========================================

    def stale_check(self, limit: int = 50, auto_close: bool = False) -> Dict[str, Any]:
        """MARKER_198.STALE: Detect pending/needs_fix tasks that are already implemented.

        Searches git log --all for [task:ID] commits across ALL branches.
        Also checks if task title keywords appear in recent commit messages.

        Args:
            limit: Max pending tasks to scan (default 50, most recent first)
            auto_close: If True, close confirmed stale tasks. If False, only flag them.

        Returns:
            {candidates: [{task_id, title, evidence, score}], closed: [...], scanned: int}
        """
        import subprocess

        cursor = self.db.execute(
            "SELECT * FROM tasks WHERE status IN ('pending', 'needs_fix') "
            "ORDER BY priority ASC, created_at DESC LIMIT ?",
            (limit,),
        )
        tasks = [self._row_to_task(row) for row in cursor]

        candidates = []
        closed = []

        for task in tasks:
            tid = task["id"]
            title = task.get("title", "")
            evidence = []
            score = 0.0

            # Check 1: git log --all for [task:ID] tag in commit messages
            try:
                tag_result = subprocess.run(
                    ["git", "log", "--all", "--oneline", "--fixed-strings",
                     f"--grep=[task:{tid}]", "-1"],
                    cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=5,
                )
                if tag_result.returncode == 0 and tag_result.stdout.strip():
                    commit_line = tag_result.stdout.strip()
                    evidence.append(f"commit_tagged: {commit_line}")
                    score += 0.9  # Very strong signal
            except Exception:
                pass

            # Check 2: title keywords in recent commit messages (weaker signal)
            if score < 0.5 and title:
                # Extract key terms from title (skip common prefixes)
                _title_clean = title
                for _prefix in ("ZETA-FIX:", "ALPHA-P1:", "BETA-", "GAMMA-", "DELTA-",
                                 "EPSILON-", "MERGE-REQUEST:", "ZETA:", "ZETA-RECON:"):
                    _title_clean = _title_clean.replace(_prefix, "").strip()
                # Use first 3 significant words as grep pattern
                _words = [w for w in _title_clean.split() if len(w) > 3][:3]
                if len(_words) >= 2:
                    _pattern = ".*".join(_words[:2])
                    try:
                        kw_result = subprocess.run(
                            ["git", "log", "--all", "--oneline", f"--grep={_pattern}",
                             "-i", "-1"],
                            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=5,
                        )
                        if kw_result.returncode == 0 and kw_result.stdout.strip():
                            commit_line = kw_result.stdout.strip()
                            evidence.append(f"title_keyword_match: {commit_line}")
                            score += 0.4
                    except Exception:
                        pass

            # Check 3: allowed_paths have commits newer than task creation
            if score < 0.5:
                allowed = task.get("allowed_paths") or []
                created_at = task.get("created_at", "")
                if allowed and created_at:
                    try:
                        for ap in allowed[:3]:
                            ap_result = subprocess.run(
                                ["git", "log", "--all", "--oneline",
                                 f"--since={created_at[:10]}", "-1", "--", ap],
                                cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=5,
                            )
                            if ap_result.returncode == 0 and ap_result.stdout.strip():
                                evidence.append(f"path_changed_after_creation: {ap} → {ap_result.stdout.strip()}")
                                score += 0.2
                                break
                    except Exception:
                        pass

            if evidence:
                entry = {
                    "task_id": tid,
                    "title": title[:80],
                    "status": task.get("status"),
                    "score": round(score, 2),
                    "evidence": evidence,
                }
                candidates.append(entry)

                if auto_close and score >= 0.8:
                    self.update_task(
                        tid,
                        status="done_main",
                        _history_event="stale_auto_closed",
                        _history_source="stale_check",
                        _history_reason=f"score={score:.2f}: {evidence[0][:100]}",
                    )
                    closed.append(tid)
                    logger.info(f"[TaskBoard] Stale auto-closed {tid}: {evidence[0][:60]}")

        candidates.sort(key=lambda x: x["score"], reverse=True)

        return {
            "success": True,
            "scanned": len(tasks),
            "candidates": candidates,
            "candidates_count": len(candidates),
            "closed": closed,
            "closed_count": len(closed),
            "auto_close": auto_close,
        }

    # ==========================================
    # MARKER_130.C16A: AGENT COORDINATION
    # ==========================================

    def claim_task(self, task_id: str, agent_name: str, agent_type: str = "unknown", *, worktree_path: Optional[str] = None) -> Dict[str, Any]:
        """Claim a task for an agent.

        Args:
            task_id: Task identifier
            agent_name: Name of agent claiming ("opus", "cursor", "dragon", "grok")
            agent_type: Type of agent ("claude_code", "cursor", "mycelium", "grok", "human")

        Returns:
            Result dict with success/error
        """
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        if task["status"] not in ("pending", "queued", "needs_fix"):
            return {"success": False, "error": f"Task {task_id} is {task['status']}, can't claim"}

        # MARKER_192.2 + MARKER_191.8: Update execution_mode on claim if not explicitly set
        inferred_mode = self._infer_execution_mode(agent_type, agent_name)
        update_fields: Dict[str, Any] = {
            "status": "claimed",
            "assigned_to": agent_name,
            "agent_type": agent_type,
            "assigned_at": datetime.now().isoformat(),
        }
        # Set execution_mode if: (a) not set at all, or (b) was default "pipeline" but no agent claimed yet
        if (not task.get("execution_mode")
                or (task.get("execution_mode") == "pipeline" and not task.get("agent_type"))):
            update_fields["execution_mode"] = inferred_mode

        self.update_task(task_id,
            **update_fields,
            _history_event="claimed",
            _history_source="task_board",
            _history_reason="task claimed by agent",
            _history_agent_name=agent_name,
            _history_agent_type=agent_type,
        )

        # MARKER_130.C18C: Emit enhanced event for claim
        self._notify_board_update("task_claimed", {
            "task_id": task_id,
            "title": task.get("title", ""),
            "assigned_to": agent_name,
            "agent_type": agent_type,
        })

        # MARKER_ZETA.D4: Warn-mode domain validation via AgentRegistry
        domain_warning = None
        try:
            from src.services.agent_registry import get_agent_registry
            registry = get_agent_registry()
            agent_role = registry.get_by_branch(self._detect_current_branch(cwd=worktree_path) or "")
            task_domain = task.get("domain", "")
            if agent_role and task_domain:
                matches, msg = registry.validate_domain_match(agent_role.callsign, task_domain)
                if not matches:
                    domain_warning = msg
                    logger.warning(f"[TaskBoard] ZETA domain warning on claim: {msg}")
                # Auto-set role on task if not already set
                if not task.get("role"):
                    self.update_task(task_id, role=agent_role.callsign)
        except Exception as e:
            logger.debug(f"[TaskBoard] ZETA domain check skipped (non-fatal): {e}")

        logger.info(f"[TaskBoard] Task {task_id} claimed by {agent_name} ({agent_type})")
        result = {"success": True, "task_id": task_id, "assigned_to": agent_name}
        if domain_warning:
            result["domain_warning"] = domain_warning
        return result

    def complete_task(
        self,
        task_id: str,
        commit_hash: Optional[str] = None,
        commit_message: Optional[str] = None,
        *,
        closure_proof: Optional[Dict[str, Any]] = None,
        closed_by: Optional[str] = None,
        manual_override: bool = False,
        override_reason: Optional[str] = None,
        branch: Optional[str] = None,
        worktree_path: Optional[str] = None,  # MARKER_195.20: cwd for branch detection
        execution_mode: Optional[str] = None,  # MARKER_192.2: override task's execution_mode at close time
    ) -> Dict[str, Any]:
        """Mark a task as complete with optional commit info.

        MARKER_186.4: Worktree-aware completion.
        MARKER_195.20: worktree_path used as cwd for branch auto-detection.
        If branch is provided and is not 'main', status = done_worktree.
        If branch is 'main' or None (legacy), status = done_main.
        'done' is kept as alias for done_main for backward compat.

        Args:
            task_id: Task identifier
            commit_hash: Git commit hash that completed this task
            commit_message: First line of commit message
            branch: Git branch name (auto-detected if None)

        Returns:
            Result dict with success/error
        """
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        # MARKER_191.1: Guard against double-close (done/done_main/done_worktree)
        if task.get("status", "").startswith("done"):
            return {"success": True, "task_id": task_id, "status": task["status"], "note": "already closed"}

        # MARKER_192.2: Allow execution_mode override at close time
        if execution_mode and execution_mode in ("pipeline", "manual"):
            task["execution_mode"] = execution_mode

        proof = dict(closure_proof or {})
        if commit_hash and not proof.get("commit_hash"):
            proof["commit_hash"] = commit_hash
        if commit_message and not proof.get("commit_message"):
            proof["commit_message"] = commit_message[:200]
        if closed_by and not proof.get("activating_agent"):
            proof["activating_agent"] = closed_by
        if override_reason and not proof.get("override_reason"):
            proof["override_reason"] = override_reason[:300]

        proof_error = self._validate_closure_proof(task, proof if proof else closure_proof, manual_override=manual_override)
        if proof_error:
            return {"success": False, "error": proof_error, "task_id": task_id}

        # MARKER_186.4: Auto-detect branch if not provided
        # MARKER_195.20: Use worktree_path as cwd for correct branch detection
        if branch is None:
            branch = self._detect_current_branch(cwd=worktree_path)
        is_worktree = branch != "main"
        final_status = "done_worktree" if is_worktree else "done_main"

        # MARKER_198.GUARD: Require commit_hash for done_worktree — prevent phantom task closures
        if final_status == "done_worktree" and not commit_hash and not manual_override:
            return {
                "success": False,
                "error": (
                    f"Cannot mark task {task_id} as done_worktree without commit_hash. "
                    "Use action=complete with branch= to auto-commit, or provide commit_hash manually."
                ),
                "task_id": task_id,
            }

        update = {
            "status": final_status,
            "completed_at": datetime.now().isoformat(),
            "closed_at": datetime.now().isoformat(),
            "closed_by": closed_by or task.get("assigned_to"),
            "closure_proof": proof or None,
        }
        # MARKER_195.20c: Save branch as branch_name — needed by merge_request later
        if branch and branch != "main":
            update["branch_name"] = branch
        if commit_hash:
            update["commit_hash"] = commit_hash
        elif manual_override and final_status == "done_worktree":
            # MARKER_198.GUARD: manual_override bypasses commit_hash guard —
            # set marker so update_task's done_worktree guard passes
            update["commit_hash"] = "manual_override"
        if commit_message:
            update["commit_message"] = commit_message[:200]  # Truncate
        if task.get("require_closure_proof"):
            update["closure_subtask"] = {
                "status": "done" if not manual_override else "manual_override",
                "tests": (proof or {}).get("tests", []),
                "finished_at": datetime.now().isoformat(),
                "commit_hash": (proof or {}).get("commit_hash"),
            }

        self.update_task(
            task_id,
            **update,
            _history_event="closed_manual" if manual_override else "closed",
            _history_source="task_board",
            _history_reason=override_reason or ("task closed by closure protocol" if task.get("require_closure_proof") else "task completed"),
            _history_agent_name=closed_by or str(task.get("assigned_to") or ""),
            _history_agent_type=str(task.get("agent_type") or ""),
        )

        # MARKER_130.C18C: Emit enhanced event for completion
        self._notify_board_update("task_completed", {
            "task_id": task_id,
            "title": task.get("title", ""),
            "assigned_to": task.get("assigned_to"),
            "commit_hash": commit_hash,
            "commit_message": commit_message[:50] if commit_message else None,
        })

        # MARKER_ZETA.D4: Warn-mode allowed_paths validation on complete
        ownership_warnings = []
        try:
            task_role = task.get("role", "")
            task_allowed = task.get("allowed_paths", [])
            if task_role and task_allowed:
                from src.services.agent_registry import get_agent_registry
                registry = get_agent_registry()
                for ap in task_allowed:
                    result_check = registry.validate_file_ownership(task_role, ap)
                    if result_check.is_blocked:
                        warn_msg = f"File '{ap}' is BLOCKED for {task_role}"
                        ownership_warnings.append(warn_msg)
                        logger.warning(f"[TaskBoard] ZETA ownership warning: {warn_msg}")
        except Exception as e:
            logger.debug(f"[TaskBoard] ZETA ownership check skipped (non-fatal): {e}")

        branch_info = f" on {branch}" if branch else ""
        logger.info(f"[TaskBoard] Task {task_id} → {final_status}{branch_info}" +
                    (f" (commit: {commit_hash[:8]})" if commit_hash else ""))
        result = {"success": True, "task_id": task_id, "commit_hash": commit_hash, "status": final_status}
        if ownership_warnings:
            result["ownership_warnings"] = ownership_warnings

        # MARKER_SC_C.D5: Auto-debrief on phase closure
        try:
            phase_prefix = self._extract_phase_prefix(task.get("title", ""))
            if phase_prefix:
                remaining = self._count_pending_for_phase(phase_prefix)
                if remaining == 0:
                    debrief_prompt = self._generate_debrief_prompt(phase_prefix, task)
                    result["debrief_prompt"] = debrief_prompt
                    result["is_last_phase_task"] = True
                    logger.info(f"[TaskBoard] Phase {phase_prefix} complete — debrief prompt attached")
        except Exception as e:
            logger.debug(f"[TaskBoard] Auto-debrief check skipped (non-fatal): {e}")

        return result

    # ------------------------------------------------------------------
    # MARKER_SC_C.D5: Phase-closure debrief helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_phase_prefix(title: str) -> Optional[str]:
        """Extract numeric phase prefix from task title.

        Examples:
            "195.2.1: Some title" → "195"
            "42.3: Another task"  → "42"
            "D4: Non-numeric"     → None
            ""                    → None
        """
        if not title:
            return None
        m = re.match(r'^(\d+)\.', title)
        return m.group(1) if m else None

    def _count_pending_for_phase(self, prefix: str) -> int:
        """Count tasks with matching phase prefix still pending or claimed."""
        count = 0
        pattern = re.compile(r'^' + re.escape(prefix) + r'\.')
        try:
            for status in ("pending", "claimed"):
                tasks = self.list_tasks(status=status)
                for t in tasks:
                    if pattern.match(t.get("title", "")):
                        count += 1
        except Exception:
            logger.debug("[TaskBoard] _count_pending_for_phase failed, returning 0")
        return count

    @staticmethod
    def _generate_debrief_prompt(phase: str, task: Dict[str, Any]) -> str:
        """Return a structured 3-question debrief prompt for the completed phase."""
        return (
            f"Phase {phase} complete (last task: {task.get('title', 'unknown')}). "
            f"Please write a debrief:\n"
            f"1. Top broken tool or pain point this phase?\n"
            f"2. Best discovery or technique that worked well?\n"
            f"3. What would you change if doing this phase again?"
        )

    # ==========================================
    # MARKER_195.20: QA VERIFICATION GATE
    # ==========================================

    def verify_task(
        self,
        task_id: str,
        verdict: str,
        notes: str = "",
        verified_by: str = "",
    ) -> Dict[str, Any]:
        """MARKER_195.20: QA gate — verify a completed worktree task.

        Args:
            task_id: Task to verify
            verdict: 'pass' or 'fail'
            notes: Verification notes (truncated to 300 chars)
            verified_by: Agent performing verification (default: 'Delta')

        Returns:
            Result dict with new status (verified or needs_fix)
        """
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        # MARKER_196.QA: Accept both done_worktree and need_qa for verification
        if task["status"] not in ("done_worktree", "need_qa"):
            return {
                "success": False,
                "error": f"Task {task_id} is '{task['status']}', expected done_worktree or need_qa",
            }

        if verdict == "pass":
            new_status = "verified"
        elif verdict == "fail":
            new_status = "needs_fix"
        else:
            return {"success": False, "error": f"Invalid verdict: '{verdict}'. Use 'pass' or 'fail'"}

        verifier = verified_by or "Delta"
        self.update_task(
            task_id,
            status=new_status,
            verification_agent=verifier,
            _history_event="verified" if verdict == "pass" else "verification_failed",
            _history_source="qa_gate",
            _history_reason=notes[:300] or f"QA verdict: {verdict}",
            _history_agent_name=verifier,
        )

        if verdict == "fail":
            self._notify_board_update("task_needs_fix", {
                "task_id": task_id,
                "title": task.get("title", ""),
                "notes": notes[:200],
            })

        logger.info(f"[TaskBoard] Task {task_id} QA {verdict} by {verifier} → {new_status}")
        return {"success": True, "task_id": task_id, "status": new_status, "verdict": verdict}

    @staticmethod
    def _is_commit_on_main(commit_hash: str) -> bool:
        """MARKER_195.1: Verify commit is actually on main branch using git merge-base."""
        import subprocess
        try:
            result = subprocess.run(
                ["git", "merge-base", "--is-ancestor", commit_hash, "main"],
                cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def promote_to_main(self, task_id: str, merge_commit_hash: Optional[str] = None, *, role: str = "") -> Dict[str, Any]:
        """MARKER_195.20c: Validate that merge happened, then set done_main.

        REQUIRES commit_hash proving the merge is on main.
        Without commit_hash → ERROR. No paper status changes.

        To actually merge, use action=merge_request first, then promote_to_main
        with the resulting commit_hash. Or pass commit_hash from manual cherry-pick.

        Intended flow:
          merge_request → cherry-pick + tests + ActionRegistry → returns commit_hash
          promote_to_main commit_hash=<hash> → verify on main → done_main
        """
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        if task.get("status") not in ("done_worktree", "done", "verified"):
            return {"success": False, "error": f"Task {task_id} status is '{task.get('status')}', expected verified or done_worktree"}

        # Warn if not Commander (soft enforcement)
        if role and role != "Commander":
            logger.warning(f"[TaskBoard] promote_to_main called by {role} (expected Commander)")

        # REQUIRE commit_hash — no paper promotions
        if not merge_commit_hash:
            return {
                "success": False,
                "error": (
                    f"commit_hash required — promote_to_main does not merge code. "
                    f"Use action=merge_request first to cherry-pick, then promote_to_main "
                    f"with the resulting commit_hash."
                ),
            }

        # Verify commit is actually on main
        if not self._is_commit_on_main(merge_commit_hash):
            reason = f"Task {task_id} commit {merge_commit_hash[:8]} is NOT on main branch (git merge-base failed)"
            logger.warning(f"[TaskBoard] BLOCKED promote: {reason}")
            return {"success": False, "error": reason}

        self.update_task(
            task_id,
            status="done_main",
            commit_hash=merge_commit_hash,
            _history_event="promoted_to_main",
            _history_source="task_board",
            _history_reason="merge verified on main",
        )
        logger.info(f"[TaskBoard] Task {task_id} promoted: → done_main (commit {merge_commit_hash[:8]} verified on main)")
        return {"success": True, "task_id": task_id, "status": "done_main"}

    async def run_closure_protocol(
        self,
        task_id: str,
        *,
        activating_agent: str = "unknown",
        agent_type: str = "unknown",
        commit_message: Optional[str] = None,
        auto_push: bool = False,
        manual_override: bool = False,
        override_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        stats = task.get("stats") if isinstance(task.get("stats"), dict) else {}
        verifier_confidence = float(stats.get("verifier_avg_confidence") or 0.0)
        proof: Dict[str, Any] = {
            "protocol_version": task.get("protocol_version") or DEFAULT_PROTOCOL_VERSION,
            "pipeline_success": bool(stats.get("success")),
            "verifier_confidence": verifier_confidence,
            "activating_agent": activating_agent,
            "agent_type": agent_type,
            "manual_override": bool(manual_override),
            "override_reason": str(override_reason or "")[:300],
            "pipeline_task_id": task.get("pipeline_task_id"),
        }

        if manual_override:
            return self.complete_task(
                task_id,
                closure_proof=proof,
                closed_by=activating_agent,
                manual_override=True,
                override_reason=override_reason,
            )

        if not stats.get("success"):
            return self._mark_closure_failed(
                task_id,
                reason="pipeline did not finish successfully",
                activating_agent=activating_agent,
                agent_type=agent_type,
            )

        if verifier_confidence < self._closure_threshold(task):
            return self._mark_closure_failed(
                task_id,
                reason=f"verifier confidence {verifier_confidence:.2f} is below threshold",
                activating_agent=activating_agent,
                agent_type=agent_type,
            )

        test_commands = self._normalize_test_commands(task.get("closure_tests"))
        if not test_commands:
            return self._mark_closure_failed(
                task_id,
                reason="protocol task requires closure_tests before it can be closed",
                activating_agent=activating_agent,
                agent_type=agent_type,
            )

        closure_results = await self._run_closure_tests(test_commands)
        proof["tests"] = closure_results
        if any(not row.get("passed") for row in closure_results):
            return self._mark_closure_failed(
                task_id,
                reason="closure tests failed",
                activating_agent=activating_agent,
                agent_type=agent_type,
                closure_results=closure_results,
            )

        closure_files = [str(path) for path in (task.get("closure_files") or []) if str(path).strip()]
        if not closure_files:
            return self._mark_closure_failed(
                task_id,
                reason="protocol task requires explicit closure_files for scoped auto-commit",
                activating_agent=activating_agent,
                agent_type=agent_type,
                closure_results=closure_results,
            )

        commit_title = commit_message or f"[Task {task_id}] {task.get('title', '')[:72]}".strip()
        from src.mcp.tools.git_tool import GitCommitTool

        commit_tool = GitCommitTool()
        commit_result = commit_tool.execute(
            {
                "message": commit_title,
                "files": closure_files,
                "dry_run": False,
                "auto_push": auto_push,
            }
        )
        if not commit_result.get("success"):
            return self._mark_closure_failed(
                task_id,
                reason=f"auto-commit failed: {commit_result.get('error') or 'unknown error'}",
                activating_agent=activating_agent,
                agent_type=agent_type,
                closure_results=closure_results,
            )

        commit_payload = commit_result.get("result") or {}
        commit_hash = str(commit_payload.get("hash") or "").strip()
        proof["commit_hash"] = commit_hash
        proof["commit_message"] = commit_title
        proof["digest_updated"] = bool(commit_payload.get("digest_updated"))

        completed = self.complete_task(
            task_id,
            commit_hash=commit_hash,
            commit_message=commit_title,
            closure_proof=proof,
            closed_by=activating_agent,
        )
        if not completed.get("success"):
            return completed

        try:
            from src.services.task_tracker import on_task_completed

            tracker_stats = dict(stats)
            tracker_stats["closure_tests"] = closure_results
            tracker_stats["commit_hash"] = commit_hash
            await on_task_completed(
                task_id=task_id,
                task_title=str(task.get("title") or task_id),
                status="done",
                stats=tracker_stats,
                source=f"{activating_agent}:{agent_type}" if agent_type else activating_agent,
            )
        except Exception as track_err:
            logger.debug(f"[TaskBoard] Tracker update skipped for {task_id}: {track_err}")

        return {
            "success": True,
            "task_id": task_id,
            "commit_hash": commit_hash,
            "tests": closure_results,
            "commit": commit_payload,
            "closed_by": activating_agent,
        }

    def get_active_agents(self) -> List[Dict[str, Any]]:
        """Get list of agents with active (claimed/running) tasks.

        MARKER_192.3: Queries from SQLite.

        Returns:
            List of dicts with agent_name, agent_type, task_id, task_title, elapsed_time
        """
        active = []
        now = datetime.now()

        cursor = self.db.execute("SELECT * FROM tasks WHERE status IN ('claimed', 'running')")
        for row in cursor:
            task = self._row_to_task(row)
            if True:  # replaces the old `if task["status"] in ...` filter
                agent = task.get("assigned_to")
                if agent:
                    assigned_at = task.get("assigned_at") or task.get("started_at")
                    elapsed = 0
                    if assigned_at:
                        try:
                            start = datetime.fromisoformat(assigned_at)
                            elapsed = int((now - start).total_seconds())
                        except (ValueError, TypeError):
                            pass

                    active.append({
                        "agent_name": agent,
                        "agent_type": task.get("agent_type", "unknown"),
                        "task_id": task["id"],
                        "task_title": task["title"],
                        "status": task["status"],
                        "elapsed_seconds": elapsed,
                    })

        return active

    # ==========================================
    # MARKER_130.C17A: GIT COMMIT AUTO-DETECTION
    # ==========================================

    def auto_complete_by_commit(self, commit_hash: str, commit_message: str, *, agent_id: Optional[str] = None) -> List[str]:
        """Auto-complete tasks mentioned in commit message.

        MARKER_191.1: Hardened against false positives.
        MARKER_195.2: activating_agent records real committer, not task's assigned_to.

        Only closes tasks that are:
        - Explicitly referenced via [task:tb_xxxx] or direct tb_xxxx ID in commit
        - Already claimed/running (not pending/queued — unclaimed tasks cannot auto-close)
        - NOT protected by require_closure_proof

        Args:
            commit_hash: Git commit hash
            commit_message: Full commit message
            agent_id: Real agent/committer identity (MARKER_195.2). Falls back to "git_auto_close".

        Returns:
            List of task IDs that were auto-completed
        """
        completed = []
        msg_lower = commit_message.lower()
        # MARKER_195.2: Record actual committer, not task's assigned_to
        real_closer = agent_id or "git_auto_close"

        # MARKER_192.3 + MARKER_191.1: Query eligible tasks from DB.
        # Only claimed/running tasks without closure_proof requirement.
        cursor = self.db.execute(
            "SELECT * FROM tasks WHERE status IN ('claimed', 'running')"
        )
        all_candidates = [self._row_to_task(row) for row in cursor]
        eligible = [t for t in all_candidates if not t.get("require_closure_proof")]

        for task in eligible:
            if self._commit_matches_task(task, commit_message, msg_lower):
                result = self.complete_task(
                    task["id"],
                    commit_hash,
                    commit_message.split('\n')[0],
                    closure_proof={
                        "commit_hash": commit_hash,
                        "commit_message": commit_message.split('\n')[0],
                        "pipeline_success": bool((task.get("stats") or {}).get("success")),
                        "verifier_confidence": float((task.get("stats") or {}).get("verifier_avg_confidence") or 0),
                        "tests": [{"command": "git auto-close", "passed": True, "exit_code": 0}],
                        "activating_agent": real_closer,
                        "auto_close_method": "commit_match",
                    },
                    closed_by=real_closer,
                )
                if result.get("success"):
                    completed.append(task["id"])
                    logger.info(f"[TaskBoard] Auto-completed {task['id']} (closer: {real_closer}) from commit {commit_hash[:8]}")
                else:
                    logger.warning(f"[TaskBoard] Auto-close FAILED for {task['id']}: {result.get('error')}")

        return completed

    def find_tasks_by_changed_files(self, changed_files: list) -> list:
        """MARKER_198.P1.9: Find pending/claimed/running tasks whose allowed_paths intersect changed_files.

        Uses prefix matching: file 'src/mcp/tools/foo.py' matches allowed_path 'src/mcp/tools/'.
        Returns list of task dicts (id, title, status, allowed_paths).
        """
        if not changed_files:
            return []
        cursor = self.db.execute(
            "SELECT * FROM tasks WHERE status IN ('pending', 'claimed', 'running')"
        )
        candidates = []
        for row in cursor:
            task = self._row_to_task(row)
            allowed = task.get("allowed_paths") or []
            if not allowed:
                continue
            matched = False
            for cf in changed_files:
                for ap in allowed:
                    ap_norm = ap.rstrip("/")
                    if cf == ap or cf.startswith(ap_norm + "/"):
                        matched = True
                        break
                if matched:
                    break
            if matched:
                candidates.append({
                    "id": task["id"],
                    "title": task.get("title", ""),
                    "status": task.get("status", ""),
                    "allowed_paths": allowed,
                })
        return candidates

    def _commit_matches_task(self, task: Dict[str, Any], commit_msg: str, msg_lower: str) -> bool:
        """Check if commit message matches a task.

        MARKER_191.1: Hardened matching — only explicit references.

        Matches (HIGH confidence only):
        - [task:tb_xxxx] explicit tag (strongest signal)
        - Direct task ID mention: tb_xxxx as standalone token
        - Phase/MARKER pattern with matching task tag (e.g., "Phase 130.C16" + tag "C16")

        REMOVED (false positive risk):
        - Title keyword matching (3 words was too loose)
        - Loose tag substring matching (short tags like "fix" matched everything)

        Args:
            task: Task dict
            commit_msg: Original commit message
            msg_lower: Lowercased commit message for case-insensitive matching

        Returns:
            True if commit explicitly references this task
        """
        task_id = task["id"]
        tags = task.get("tags", [])

        # 1. Explicit [task:tb_xxxx] tag — strongest signal
        if f"[task:{task_id}]" in commit_msg:
            return True

        # 2. Direct ID mention as standalone token (not substring of another ID)
        # Use word boundary to avoid tb_123 matching inside tb_1234_5
        if re.search(r'\b' + re.escape(task_id) + r'\b', commit_msg):
            return True

        # 3. Phase/MARKER pattern (e.g., "Phase 130.C16" matches task tagged "C16")
        # Only match tags that look like phase codes (uppercase letter + digits)
        phase_match = re.search(r'Phase\s*(\d+)[\.\s]*([A-Z]\d+[A-Z]?)', commit_msg, re.IGNORECASE)
        if phase_match:
            phase_tag = phase_match.group(2).upper()
            if phase_tag in [t.upper() for t in tags if re.match(r'^[A-Z]\d+', t, re.IGNORECASE)]:
                return True

        return False

    # ==========================================
    # QUEUE OPERATIONS
    # ==========================================

    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get the highest-priority pending task with satisfied dependencies.

        MARKER_192.3: Queries pending tasks from SQLite.
        Returns tasks sorted by: priority (ascending), then created_at (oldest first).
        Skips tasks whose dependencies haven't completed.

        Returns:
            Next task dict or None if queue is empty
        """
        cursor = self.db.execute(
            "SELECT * FROM tasks WHERE status = 'pending' ORDER BY priority, created_at"
        )
        pending = [self._row_to_task(row) for row in cursor]

        if not pending:
            return None

        # Filter by satisfied dependencies (Sugiyama-style: all deps must be done)
        ready = []
        for task in pending:
            deps = task.get("dependencies", [])
            if not deps:
                ready.append(task)
            else:
                all_done = all(
                    self.tasks.get(dep_id, {}).get("status") == "done"
                    for dep_id in deps
                )
                if all_done:
                    ready.append(task)

        if not ready:
            return None

        # Sort by priority (1=highest), then by creation time (oldest first)
        ready.sort(key=lambda t: (t["priority"], t["created_at"]))
        return ready[0]

    def get_queue(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tasks filtered by status, sorted by priority.

        MARKER_192.3: Reads from SQLite with ORDER BY.

        Args:
            status: Filter by status. None = all tasks.

        Returns:
            List of task dicts sorted by priority
        """
        if status:
            cursor = self.db.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY priority, created_at",
                (status,),
            )
        else:
            cursor = self.db.execute(
                "SELECT * FROM tasks ORDER BY priority, created_at"
            )
        return [self._row_to_task(row) for row in cursor]

    # MARKER_181.5.6: Backwards-compatible alias (used by dag_aggregator, agent_pipeline, tests)
    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Alias for get_queue() — backwards compatibility."""
        return self.get_queue(status=status)

    # MARKER_191.16: Smart project_id matching — case-insensitive, RU layout fix, prefix autocomplete
    # Keyboard layout map: Russian ЙЦУКЕН → English QWERTY
    _RU_TO_EN: Dict[str, str] = dict(zip(
        "йцукенгшщзхъфывапролджэячсмитьбюЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ",
        "qwertyuiop[]asdfghjkl;'zxcvbnm,.QWERTYUIOP[]ASDFGHJKL;'ZXCVBNM,.",
    ))

    def _transliterate_ru_to_en(self, text: str) -> str:
        """Convert Russian keyboard layout input to English equivalent."""
        return "".join(self._RU_TO_EN.get(ch, ch) for ch in text)

    def resolve_project_id(self, query: str) -> Dict[str, Any]:
        """Smart project_id resolver: case-insensitive, RU→EN layout, prefix match.

        Returns:
            {
                "resolved": "cut" | None,
                "exact": True/False,
                "candidates": ["cut", "CUT"],
                "method": "exact" | "case_insensitive" | "layout_fix" | "prefix" | "none"
            }
        """
        query = str(query or "").strip()
        if not query:
            return {"resolved": None, "exact": False, "candidates": [], "method": "none"}

        # MARKER_192.3: Collect all known project_ids from SQLite
        known: Dict[str, str] = {}  # lowercase → original
        cursor = self.db.execute("SELECT DISTINCT project_id FROM tasks WHERE project_id != ''")
        for row in cursor:
            pid = str(row["project_id"]).strip()
            if pid:
                key = pid.lower()
                if key not in known:
                    known[key] = pid

        # 1. Exact match
        if query in known.values():
            return {"resolved": query, "exact": True, "candidates": [query], "method": "exact"}

        # 2. Case-insensitive match
        q_lower = query.lower()
        if q_lower in known:
            resolved = known[q_lower]
            return {"resolved": resolved, "exact": True, "candidates": [resolved], "method": "case_insensitive"}

        # 3. RU→EN layout fix (СГЕ → CUT)
        en_query = self._transliterate_ru_to_en(query).lower()
        if en_query != q_lower and en_query in known:
            resolved = known[en_query]
            return {"resolved": resolved, "exact": True, "candidates": [resolved], "method": "layout_fix"}

        # 4. Prefix match (c → cut, p → parallax)
        prefix_matches = sorted(set(
            original for key, original in known.items()
            if key.startswith(q_lower) or key.startswith(en_query)
        ))
        if len(prefix_matches) == 1:
            return {"resolved": prefix_matches[0], "exact": False, "candidates": prefix_matches, "method": "prefix"}
        if len(prefix_matches) > 1:
            # Ambiguous prefix — check if one candidate matches exactly (e.g. "vetka" matches "vetka" not "vetka_pulse")
            exact_prefix = [p for p in prefix_matches if p.lower() == q_lower or p.lower() == en_query]
            if len(exact_prefix) == 1:
                return {"resolved": exact_prefix[0], "exact": False, "candidates": prefix_matches, "method": "prefix_exact"}
            return {"resolved": None, "exact": False, "candidates": prefix_matches, "method": "prefix_ambiguous"}

        return {"resolved": None, "exact": False, "candidates": [], "method": "none"}

    def filter_tasks_by_project(self, tasks: List[Dict[str, Any]], query: str) -> tuple:
        """Filter tasks by project_id with smart matching.

        Returns:
            (filtered_tasks, resolve_info)
        """
        resolve = self.resolve_project_id(query)

        # Ambiguous prefix: show tasks from ALL candidates so agent can see scope
        if resolve["method"] == "prefix_ambiguous":
            candidate_set = {c.lower() for c in resolve["candidates"]}
            filtered = [
                t for t in tasks
                if str(t.get("project_id") or "").strip().lower() in candidate_set
            ]
            return filtered, resolve

        if not resolve["resolved"]:
            return [], resolve

        resolved_lower = resolve["resolved"].lower()
        # Match all case variants of the resolved project
        filtered = [
            t for t in tasks
            if str(t.get("project_id") or "").strip().lower() == resolved_lower
        ]
        return filtered, resolve

    # MARKER_183.1: Query tasks by heartbeat session
    def get_tasks_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all tasks created in a specific heartbeat session.

        MARKER_192.3: session_id is in the extra JSON, so we load all and filter.
        """
        # session_id is in extra blob, so we can't use SQL WHERE efficiently
        # But this is a rare query, so full scan is acceptable
        cursor = self.db.execute("SELECT * FROM tasks")
        return [
            self._row_to_task(row) for row in cursor
            if json.loads(row["extra"] or "{}").get("session_id") == session_id
        ]

    def get_board_summary(self) -> Dict[str, Any]:
        """Get summary counts of tasks by status.

        MARKER_192.3: Uses SQL COUNT/GROUP BY for efficiency.

        Returns:
            Dict with counts per status, total, and next task preview
        """
        counts = {}
        total = 0
        cursor = self.db.execute("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status")
        for row in cursor:
            counts[row["status"]] = row["cnt"]
            total += row["cnt"]

        next_task = self.get_next_task()
        return {
            "total": total,
            "by_status": counts,
            "next_task": {
                "id": next_task["id"],
                "title": next_task["title"],
                "priority": next_task["priority"],
                "phase_type": next_task["phase_type"]
            } if next_task else None
        }

    # ── MARKER_184.5: Worktree → Main merge via TaskBoard ────────────

    async def merge_request(self, task_id: str) -> Dict[str, Any]:
        """Request merge of worktree branch into main via verification flow.

        MARKER_184.5: Agents call this instead of manual cherry-pick.

        Flow:
        1. Validate task has branch_name
        2. Run closure_tests on the branch (if defined)
        3. Check merge compatibility (dry-run)
        4. Execute merge (cherry-pick by default)
        5. Log to ActionRegistry
        6. Auto-close task with merge commit hash

        Returns:
            {success, merge_result, eval_delta, ...} or {error}
        """
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        branch = task.get("branch_name")
        # MARKER_195.21: Auto-infer branch from role via AgentRegistry
        if not branch:
            try:
                role = task.get("role", "")
                if role:
                    from src.services.agent_registry import get_agent_registry
                    registry = get_agent_registry()
                    agent_role = registry.get_by_callsign(role)
                    if agent_role and agent_role.branch:
                        branch = agent_role.branch
                        self.update_task(task_id, branch_name=branch)
                        logger.info(f"[MergeRequest] Auto-inferred branch_name={branch} from role={role}")
            except Exception as e:
                logger.debug(f"[MergeRequest] Branch inference failed: {e}")
        if not branch:
            return {"success": False, "error": "Task has no branch_name and role-based inference failed. Set branch_name via action=update."}

        strategy = task.get("merge_strategy", "cherry-pick")
        commits = task.get("merge_commits", [])

        # Step 1: Validate branch exists
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "--verify", branch,
                cwd=str(PROJECT_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                return {"success": False, "error": f"Branch '{branch}' not found: {stderr.decode().strip()}"}
        except Exception as e:
            return {"success": False, "error": f"Git check failed: {e}"}

        # Step 2: Get commits to merge (if not specified, get all ahead of main)
        if not commits:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "git", "log", "--oneline", f"main..{branch}",
                    cwd=str(PROJECT_ROOT),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                log_lines = stdout.decode().strip().split("\n")
                commits = [line.split()[0] for line in log_lines if line.strip()]
            except Exception:
                pass

        if not commits:
            return {"success": False, "error": f"No commits found on '{branch}' ahead of main"}

        # Step 3: Count tests before merge
        tests_before = await self._count_tests()

        # Step 4: Run closure_tests if defined
        closure_results = []
        closure_tests = task.get("closure_tests", [])
        if closure_tests:
            closure_results = await self._run_closure_tests(closure_tests)
            failed = [r for r in closure_results if not r["passed"]]
            if failed:
                self.update_task(task_id, merge_result={
                    "status": "tests_failed",
                    "closure_results": closure_results,
                })
                return {
                    "success": False,
                    "error": "Closure tests failed",
                    "closure_results": closure_results,
                }

        # Step 5: Execute merge
        merge_result = await self._execute_merge(branch, strategy, commits)
        if not merge_result.get("success"):
            self.update_task(task_id, merge_result=merge_result)
            return merge_result

        # Step 6: Count tests after merge
        tests_after = await self._count_tests()
        eval_delta = {
            "tests_before": tests_before,
            "tests_after": tests_after,
            "tests_delta": tests_after - tests_before,
            "commits_merged": len(commits),
            "strategy": strategy,
            "branch": branch,
        }

        # Step 7: Log to ActionRegistry
        try:
            from src.orchestration.action_registry import ActionRegistry
            registry = ActionRegistry()
            registry.log_action(
                run_id=f"merge_{task_id}",
                agent="opus",
                action="merge",
                file=f"{branch}→main",
                result="success",
                session_id=task.get("session_id"),
                task_id=task_id,
                metadata={
                    "strategy": strategy,
                    "commits": commits,
                    "commit_hash": merge_result.get("commit_hash"),
                },
            )
            registry.flush()
        except Exception as e:
            logger.debug(f"[MergeRequest] ActionRegistry log failed (non-fatal): {e}")

        # Step 8: Update task with result and close
        # MARKER_195.20c: done_main (not "done") — code is actually on main now
        full_result = {
            "status": "merged",
            "commit_hash": merge_result.get("commit_hash"),
            "commits_merged": commits,
            "strategy": strategy,
            "eval_delta": eval_delta,
            "closure_results": closure_results,
        }
        self.update_task(
            task_id,
            merge_result=full_result,
            status="done_main",
            commit_hash=merge_result.get("commit_hash"),
            _history_event="merged_to_main",
            _history_source="merge_request",
            _history_reason=f"{branch} → main via {strategy}: {len(commits)} commits",
        )

        logger.info(f"[MergeRequest] {branch} → main via {strategy}: {len(commits)} commits, "
                     f"tests_delta={eval_delta['tests_delta']}")

        # MARKER_198.STALE: Post-merge stale scan — flag pending tasks that may be resolved by this merge
        stale_hint = None
        try:
            stale_result = self.stale_check(limit=30, auto_close=False)
            if stale_result.get("candidates_count", 0) > 0:
                stale_hint = {
                    "stale_candidates": stale_result["candidates_count"],
                    "top_stale": stale_result["candidates"][:5],
                    "hint": "Run action=stale_check auto_close=true to close confirmed stale tasks",
                }
                logger.info(f"[MergeRequest] Post-merge stale scan found {stale_result['candidates_count']} candidates")
        except Exception as _e:
            logger.debug(f"[MergeRequest] Post-merge stale scan failed (non-fatal): {_e}")

        result = {"success": True, "task_id": task_id, "status": "done_main", "merge_result": full_result, "eval_delta": eval_delta}
        if stale_hint:
            result["stale_hint"] = stale_hint
        return result

    async def _execute_merge(
        self, branch: str, strategy: str, commits: List[str]
    ) -> Dict[str, Any]:
        """Execute the actual git merge operation.

        Strategies:
        - cherry-pick: Cherry-pick each commit (default, safest)
        - merge: Git merge --no-ff
        - squash: Git merge --squash + commit
        """
        try:
            # Ensure we're on main
            proc = await asyncio.create_subprocess_exec(
                "git", "checkout", "main",
                cwd=str(PROJECT_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            if strategy == "cherry-pick":
                # Cherry-pick commits in order (oldest first)
                for commit_hash in reversed(commits):
                    proc = await asyncio.create_subprocess_exec(
                        "git", "cherry-pick", commit_hash,
                        cwd=str(PROJECT_ROOT),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await proc.communicate()
                    if proc.returncode != 0:
                        stderr_text = stderr.decode().strip()
                        # MARKER_198.P1.MERGE: Handle empty cherry-pick (commit already on main)
                        if "empty" in stderr_text or "nothing to commit" in stderr_text:
                            skip_proc = await asyncio.create_subprocess_exec(
                                "git", "cherry-pick", "--skip",
                                cwd=str(PROJECT_ROOT),
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE,
                            )
                            await skip_proc.communicate()
                            logger.info(f"[MergeRequest] Skipped empty cherry-pick {commit_hash} (already on main)")
                            continue
                        # Abort cherry-pick on real conflict
                        abort_proc = await asyncio.create_subprocess_exec(
                            "git", "cherry-pick", "--abort",
                            cwd=str(PROJECT_ROOT),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        await abort_proc.communicate()
                        return {
                            "success": False,
                            "error": f"Cherry-pick failed for {commit_hash}: {stderr_text}",
                            "conflicting_commit": commit_hash,
                        }

            elif strategy == "merge":
                proc = await asyncio.create_subprocess_exec(
                    "git", "merge", "--no-ff", branch,
                    "-m", f"Merge {branch} into main via TaskBoard",
                    cwd=str(PROJECT_ROOT),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode != 0:
                    # Abort merge
                    abort_proc = await asyncio.create_subprocess_exec(
                        "git", "merge", "--abort",
                        cwd=str(PROJECT_ROOT),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await abort_proc.communicate()
                    return {
                        "success": False,
                        "error": f"Merge failed: {stderr.decode().strip()}",
                    }

            elif strategy == "squash":
                proc = await asyncio.create_subprocess_exec(
                    "git", "merge", "--squash", branch,
                    cwd=str(PROJECT_ROOT),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode != 0:
                    return {"success": False, "error": f"Squash failed: {stderr.decode().strip()}"}

                # Commit the squash
                proc = await asyncio.create_subprocess_exec(
                    "git", "commit", "-m", f"Squash merge {branch} into main via TaskBoard",
                    cwd=str(PROJECT_ROOT),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
            else:
                return {"success": False, "error": f"Unknown strategy: {strategy}"}

            # Get resulting commit hash
            proc = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "HEAD",
                cwd=str(PROJECT_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            commit_hash = stdout.decode().strip()[:12]

            return {"success": True, "commit_hash": commit_hash}

        except Exception as e:
            return {"success": False, "error": f"Merge execution failed: {e}"}

    async def _count_tests(self) -> int:
        """Run pytest --co -q to count available tests. Returns count or 0."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "python", "-m", "pytest", "--co", "-q",
                cwd=str(PROJECT_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            # Last line: "X tests collected"
            output = stdout.decode()
            for line in output.strip().split("\n"):
                if "test" in line and "selected" in line or "collected" in line:
                    parts = line.split()
                    for p in parts:
                        if p.isdigit():
                            return int(p)
            return 0
        except Exception:
            return 0
    # MARKER_126.11B stubs removed — superseded by live claim_task() at line ~1377

    # ==========================================
    # STATISTICS (MARKER_126.0B)
    # ==========================================

    def record_pipeline_stats(self, task_id: str, stats: dict) -> bool:
        """Record pipeline execution statistics for a task.

        MARKER_126.0B: Called by AgentPipeline at end of execute().
        Stats include: preset, league, llm_calls, tokens, duration, success.
        """
        task = self.get_task(task_id)
        if not task:
            return False
        task["stats"] = stats
        self.tasks[task_id] = task
        self._save_task(task)
        self._notify_board_update("stats_recorded")
        logger.info(f"[TaskBoard] Stats recorded for {task_id}: {stats.get('preset', '?')}")
        return True

    # MARKER_151.12B: Compute adjusted success blending verifier + user feedback
    def compute_adjusted_stats(self, task_id: str) -> dict:
        """Blend pipeline self-assessment with user feedback for adjusted success score.

        Formula: adjusted_success = 0.7 * verifier_success + 0.3 * user_feedback
        User feedback values: applied=1.0, rework=0.5, rejected=0.0, None=passthrough

        Returns dict with original stats + adjusted_success, user_feedback, has_user_feedback.
        Empty dict if task not found or has no stats.
        """
        task = self.get_task(task_id)
        if not task or "stats" not in task:
            return {}

        stats = task["stats"]
        result_status = task.get("result_status")

        # Verifier self-assessment: pipeline success flag
        verifier_success = 1.0 if stats.get("success", False) else 0.0

        # Map user feedback to numeric value
        user_feedback_map = {
            "applied": 1.0,
            "rework": 0.5,
            "rejected": 0.0,
            None: verifier_success,  # No feedback → trust verifier
        }
        user_success = user_feedback_map.get(result_status, verifier_success)

        # Blend: 70% verifier + 30% user
        adjusted_success = 0.7 * verifier_success + 0.3 * user_success

        return {
            **stats,
            "adjusted_success": round(adjusted_success, 3),
            "user_feedback": result_status,
            "has_user_feedback": result_status is not None,
        }

    # ==========================================
    # CANCEL (MARKER_126.5D)
    # ==========================================

    # MARKER_126.5D: Global registry of running pipelines for cancellation
    _running_pipelines: dict = {}  # task_id -> AgentPipeline instance

    @classmethod
    def register_pipeline(cls, task_id: str, pipeline) -> None:
        """Register a running pipeline for future cancellation."""
        cls._running_pipelines[task_id] = pipeline
        logger.debug(f"[TaskBoard] Pipeline registered: {task_id}")

    @classmethod
    def unregister_pipeline(cls, task_id: str) -> None:
        """Unregister pipeline after completion."""
        cls._running_pipelines.pop(task_id, None)

    def cancel_task(self, task_id: str, reason: str = "Cancelled by user") -> bool:
        """Cancel a running or pending task.

        MARKER_126.5D: If task is running and pipeline is registered,
        signals cancellation via asyncio.Event.

        Returns:
            True if task was found and cancel was initiated
        """
        task = self.get_task(task_id)
        if not task:
            logger.warning(f"[TaskBoard] Task {task_id} not found for cancel")
            return False

        old_status = task["status"]

        if old_status in ("done", "cancelled", "failed"):
            logger.info(f"[TaskBoard] Task {task_id} already {old_status}, skip cancel")
            return False

        # If running — signal pipeline to stop
        if old_status == "running" and task_id in self._running_pipelines:
            pipeline = self._running_pipelines[task_id]
            pipeline.cancel(reason)
            logger.info(f"[TaskBoard] Pipeline {task_id} cancel signal sent")
            # Status will be set to "cancelled" by pipeline's except handler
            return True

        # For pending/queued/hold — just set status directly
        task["status"] = "cancelled"
        self._append_history(
            task,
            event="cancelled",
            status="cancelled",
            agent_name=str(task.get("assigned_to") or ""),
            agent_type=str(task.get("agent_type") or ""),
            source="task_board",
            reason=reason,
        )
        self._save_task(task)
        self._notify_board_update("cancelled")
        logger.info(f"[TaskBoard] Task {task_id} cancelled (was {old_status})")
        return True

    # ==========================================
    # DISPATCH
    # ==========================================

    async def dispatch_next(
        self,
        chat_id: Optional[str] = None,
        selected_key: Optional[Dict[str, str]] = None  # MARKER_126.9E
    ) -> Dict[str, Any]:
        """Pick highest-priority task and dispatch to pipeline.

        Args:
            chat_id: Optional chat ID for progress streaming
            selected_key: Optional {provider, key_masked} for specific API key

        Returns:
            Dispatch result dict
        """
        task = self.get_next_task()
        if not task:
            return {"success": False, "error": "No pending tasks with satisfied dependencies"}

        return await self.dispatch_task(task["id"], chat_id=chat_id, selected_key=selected_key)

    # ==========================================
    # MARKER_189.15: DOCS CONTENT INJECTION
    # ==========================================

    async def _inject_docs_content(
        self,
        task: Dict[str, Any],
        preset: Optional[str] = None,
    ) -> str:
        """Read architecture_docs + recon_docs files and inject content into task_text.

        Context Budget Guard:
        - Determines model context_length from preset → LLMModelRegistry
        - Budget = min(context_length * 0.30, 32000 tokens ≈ 128KB chars)
        - Reads files up to budget, truncates per-doc and total
        - Applies ELISION L2 compression if available

        Args:
            task: Task dict with architecture_docs/recon_docs fields
            preset: Pipeline preset name (e.g. "dragon_silver")

        Returns:
            Formatted docs section string, or empty string if no docs
        """
        # Collect all doc paths
        doc_paths = []
        for field in ("architecture_docs", "recon_docs"):
            for doc_ref in (task.get(field) or []):
                doc_ref = str(doc_ref).strip()
                if doc_ref:
                    doc_paths.append((field, doc_ref))

        if not doc_paths:
            return ""

        # Determine context budget from model
        budget_chars = 32000  # Conservative default (~8K tokens)
        try:
            model_id = self._get_coder_model_from_preset(preset)
            if model_id:
                from src.elisya.llm_model_registry import LLMModelRegistry
                registry = LLMModelRegistry()
                profile = await registry.get_profile(model_id)
                context_length = profile.context_length
                # Budget: 30% of context, capped at 128K chars (~32K tokens)
                budget_chars = min(int(context_length * 0.30 * 4), 128000)
                logger.info(f"[TaskBoard] Docs budget: {budget_chars} chars "
                            f"(model={model_id}, context={context_length})")
        except Exception as e:
            logger.warning(f"[TaskBoard] Failed to get model context, using default budget: {e}")

        # Read docs up to budget
        sections = []
        total_chars = 0
        per_doc_cap = max(budget_chars // max(len(doc_paths), 1), 2000)
        docs_included = 0
        docs_skipped = []

        for field, doc_ref in doc_paths:
            if total_chars >= budget_chars:
                docs_skipped.append(doc_ref)
                continue

            # Resolve path relative to project root
            full_path = _MAIN_ROOT / doc_ref
            if not full_path.exists():
                # Try without leading slash
                full_path = _MAIN_ROOT / doc_ref.lstrip("/")
            if not full_path.exists():
                docs_skipped.append(f"{doc_ref} (not found)")
                continue

            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
                # Per-doc cap
                if len(content) > per_doc_cap:
                    content = content[:per_doc_cap] + f"\n... [truncated, {len(content)} chars total]"

                remaining = budget_chars - total_chars
                if len(content) > remaining:
                    content = content[:remaining] + "\n... [budget exceeded]"

                sections.append(f"### {doc_ref} ({field})\n{content}")
                total_chars += len(content)
                docs_included += 1
            except Exception as e:
                docs_skipped.append(f"{doc_ref} (read error: {e})")

        if not sections:
            return ""

        # Try ELISION compression if total is large
        docs_text = "\n\n".join(sections)
        compressed = False
        try:
            if total_chars > 8000:
                from src.memory.elision import compress_context
                result = compress_context(docs_text, level=2)
                if result.get("compressed"):
                    ratio = result.get("ratio", 1.0)
                    if ratio > 1.1:  # Only use if actually compressed
                        docs_text = result["compressed"]
                        compressed = True
                        logger.info(f"[TaskBoard] Docs compressed: ratio={ratio:.2f}")
        except Exception:
            pass  # ELISION optional, proceed with raw text

        # Build final section
        header = f"\n\n--- ARCHITECTURE & RECON DOCS ({docs_included} files"
        if docs_skipped:
            header += f", {len(docs_skipped)} skipped"
        if compressed:
            header += ", ELISION L2"
        header += ") ---\n"

        footer = "\n--- END DOCS ---\n"

        logger.info(f"[TaskBoard] Injected {docs_included} docs ({total_chars} chars) "
                     f"into task {task.get('id', '?')}")

        return header + docs_text + footer

    @staticmethod
    def _get_coder_model_from_preset(preset: Optional[str]) -> Optional[str]:
        """Extract the coder model_id from a preset name.

        Reads model_presets.json and returns the 'coder' role model.
        Falls back to None if preset not found.
        """
        if not preset:
            return None
        try:
            presets_path = _MAIN_ROOT / "data" / "templates" / "model_presets.json"
            if not presets_path.exists():
                return None
            data = json.loads(presets_path.read_text())
            preset_data = data.get("presets", {}).get(preset)
            if preset_data and "roles" in preset_data:
                return preset_data["roles"].get("coder")
        except Exception:
            pass
        return None

    async def dispatch_task(
        self,
        task_id: str,
        chat_id: Optional[str] = None,
        selected_key: Optional[Dict[str, str]] = None  # MARKER_126.9E
    ) -> Dict[str, Any]:
        """Dispatch a specific task to the Mycelium pipeline.

        Creates an AgentPipeline with appropriate preset based on task
        complexity and phase_type. Updates task status through lifecycle.

        MARKER_133.C33C: Enforces max_concurrent via semaphore.

        Args:
            task_id: Task to dispatch
            chat_id: Optional chat ID for progress streaming
            selected_key: Optional {provider, key_masked} for specific API key

        Returns:
            Dict with success status, pipeline_task_id, and result
        """
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        if task["status"] not in ("pending", "queued"):
            return {"success": False, "error": f"Task {task_id} is {task['status']}, not dispatchable"}

        # MARKER_133.C33C: Check concurrent limit before dispatching
        max_concurrent = self.settings.get("max_concurrent", 2)
        sem = TaskBoard._get_dispatch_semaphore(max_concurrent)

        # Non-blocking check: if semaphore locked, return queued status
        if sem.locked():
            running_count = len([t for t in self.tasks.values() if t.get("status") == "running"])
            logger.warning(f"[TaskBoard] Max concurrent ({max_concurrent}) reached, queuing {task_id}. Running: {running_count}")
            self.update_task(
                task_id,
                status="queued",
                _history_event="queued",
                _history_source="dispatch",
                _history_reason=f"max_concurrent={max_concurrent} reached",
            )
            return {"success": False, "error": f"max_concurrent ({max_concurrent}) reached", "queued": True, "task_id": task_id}

        # Acquire semaphore and dispatch
        # MARKER_133.C33C: Pipeline execution inside semaphore context
        async with sem:
            # Mark as running (inside semaphore to ensure accurate count)
            self.update_task(
                task_id,
                status="running",
                started_at=datetime.now().isoformat(),
                _history_event="running",
                _history_source="dispatch",
                _history_reason="pipeline dispatch started",
                _history_agent_name=str(task.get("assigned_to") or ""),
                _history_agent_type=str(task.get("agent_type") or ""),
            )

            try:
                from src.orchestration.agent_pipeline import AgentPipeline

                # Determine preset: task-specific > phase-based > default
                preset = task.get("preset") or self.settings.get("default_preset")

                # MARKER_133.FIX1: auto_write=True — Dragon writes real code to disk
                pipeline = AgentPipeline(
                    chat_id=chat_id,
                    auto_write=True,
                    preset=preset
                )
                # MARKER_121.2: Tag pipeline with board task ID for callback
                pipeline._board_task_id = task_id
                # MARKER_183.1: Pass session_id from task to pipeline
                if task.get("session_id"):
                    pipeline._session_id = task["session_id"]

                # MARKER_126.9E: Pass selected key to pipeline for preferred key routing
                if selected_key:
                    pipeline.selected_key = selected_key

                # MARKER_126.5E: Register pipeline for cancellation support
                TaskBoard.register_pipeline(task_id, pipeline)

                # Build task description from title + description
                task_text = task["title"]
                if task.get("description") and task["description"] != task["title"]:
                    task_text += f"\n\n{task['description']}"

                # MARKER_183.5: Inject failure_history so new coder learns from past attempts
                failure_history = task.get("failure_history", [])
                if failure_history:
                    task_text += "\n\n--- PREVIOUS FAILURE HISTORY ---\n"
                    task_text += f"This task has failed {len(failure_history)} previous attempt(s).\n"
                    task_text += "Learn from these errors — do NOT repeat the same approach.\n\n"
                    for rec in failure_history[-3:]:  # last 3 attempts max
                        task_text += f"Attempt #{rec.get('attempt', '?')} (tier: {rec.get('tier_used', '?')}):\n"
                        issues = rec.get("issues", [])
                        if issues:
                            for iss in issues[:5]:
                                task_text += f"  - {iss}\n"
                        suggestions = rec.get("suggestions", [])
                        if suggestions:
                            task_text += f"  Suggestions: {'; '.join(str(s)[:80] for s in suggestions[:3])}\n"
                        conf = rec.get("verifier_confidence") or rec.get("verifier_avg_confidence")
                        if conf:
                            task_text += f"  Confidence: {conf}\n"
                        task_text += "\n"
                    task_text += "--- END FAILURE HISTORY ---\n"

                # MARKER_189.15: Auto-inject architecture_docs + recon_docs content
                # Context Budget Guard: reads files, respects model context_length
                docs_section = await self._inject_docs_content(task, preset)
                if docs_section:
                    task_text += docs_section

                # MARKER_191.6: Inject implementation_hints if present
                hints = task.get("implementation_hints", "").strip()
                if hints:
                    task_text += f"\n\n--- IMPLEMENTATION HINTS ---\n{hints}\n--- END HINTS ---\n"

                try:
                    # Execute pipeline
                    result = await pipeline.execute(task_text, task["phase_type"])
                finally:
                    # Always unregister after completion
                    TaskBoard.unregister_pipeline(task_id)

                # Update task with results
                pipeline_status = result.get("status", "unknown")
                completed = pipeline_status == "done"

                # MARKER_C21A: Expanded result storage (2KB limit)
                pipeline_results = {
                    "subtasks_completed": result.get("results", {}).get("subtasks_completed", 0),
                    "subtasks_total": result.get("results", {}).get("subtasks_total", 0),
                    "files_created": result.get("results", {}).get("files_created", [])[:20],  # Limit to 20 files
                    "stats": result.get("results", {}).get("stats", {}),
                    "approval_status": result.get("results", {}).get("approval_status", "unknown"),
                    "success": result.get("results", {}).get("success", completed),
                }
                result_summary = json.dumps(pipeline_results)[:2000]  # 2KB limit

                self.update_task(
                    task_id,
                    pipeline_task_id=result.get("task_id"),
                    assigned_tier=pipeline.preset_name,
                    result_summary=result_summary,
                )

                if completed and task.get("require_closure_proof"):
                    closure_result = await self.run_closure_protocol(
                        task_id,
                        activating_agent=str(task.get("assigned_to") or "pipeline"),
                        agent_type=str(task.get("agent_type") or "mycelium"),
                    )
                    final_status = "done" if closure_result.get("success") else "failed"
                    logger.info(f"[TaskBoard] Task {task_id} closure protocol → {final_status}")
                    return {
                        "success": bool(closure_result.get("success")),
                        "task_id": task_id,
                        "pipeline_task_id": result.get("task_id"),
                        "status": final_status,
                        "tier_used": pipeline.preset_name,
                        "subtasks_completed": result.get("results", {}).get("subtasks_completed", 0),
                        "subtasks_total": result.get("results", {}).get("subtasks_total", 0),
                        "closure": closure_result,
                    }

                if completed:
                    self.update_task(
                        task_id,
                        status="done",
                        completed_at=datetime.now().isoformat(),
                        _history_event="pipeline_done",
                        _history_source="dispatch",
                        _history_reason="pipeline finished",
                        _history_agent_name=str(task.get("assigned_to") or ""),
                        _history_agent_type=str(task.get("agent_type") or ""),
                    )
                    # MARKER_183.5: Compute eval_delta for successful runs
                    eval_result = TaskBoard.compute_eval_score(pipeline_results.get("stats", {}))
                    logger.info(f"[TaskBoard] Task {task_id} done — eval: {eval_result}")
                else:
                    # MARKER_183.5: Record failure + reset to pending for retry
                    # Extract verifier feedback from pipeline results
                    stats = pipeline_results.get("stats", {})
                    self.record_failure(
                        task_id,
                        pipeline_stats=stats,
                        tier_used=pipeline.preset_name or "",
                    )
                    eval_result = TaskBoard.compute_eval_score(stats)

                logger.info(f"[TaskBoard] Task {task_id} dispatched → {'done' if completed else 'pending (retry)'}")

                return {
                    "success": completed,
                    "task_id": task_id,
                    "pipeline_task_id": result.get("task_id"),
                    "status": "done" if completed else "pending",
                    "tier_used": pipeline.preset_name,
                    "subtasks_completed": result.get("results", {}).get("subtasks_completed", 0),
                    "subtasks_total": result.get("results", {}).get("subtasks_total", 0),
                    "eval_delta": eval_result,
                }

            except Exception as e:
                logger.error(f"[TaskBoard] Dispatch failed for {task_id}: {e}")
                # MARKER_183.5: Record failure with error context, reset to pending
                self.record_failure(
                    task_id,
                    issues=[f"Dispatch exception: {str(e)[:200]}"],
                    tier_used=task.get("preset", ""),
                )
                return {"success": False, "task_id": task_id, "error": str(e)}

    # ==========================================
    # BULK IMPORT
    # ==========================================

    def import_from_todo(self, file_path: str, source_tag: str = "imported") -> int:
        """Import tasks from a plain-text todo file.

        Parses lines looking for task descriptions. Each non-empty line
        that doesn't look like a header becomes a task.

        Format heuristics:
        - Lines with "баг" / "fix" / "исправ" → phase_type="fix", priority=2
        - Lines with "research" / "исследов" / "выяснить" → phase_type="research", priority=3
        - Lines with "test" / "pytest" / "e2e" → phase_type="test", priority=3
        - Other lines → phase_type="build", priority=3

        Args:
            file_path: Path to todo file
            source_tag: Tag for task source tracking

        Returns:
            Number of tasks imported
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"[TaskBoard] Todo file not found: {file_path}")
            return 0

        content = path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        imported = 0
        for line in lines:
            line = line.strip()
            # Skip empty lines, very short lines, headers
            if not line or len(line) < 10:
                continue
            # Skip lines that look like section headers
            if line.startswith("#") or line.startswith("="):
                continue

            # Determine phase_type and priority from content
            line_lower = line.lower()

            if any(w in line_lower for w in ["баг", "fix", "исправ", "broken", "не работает", "кривой"]):
                phase_type = "fix"
                priority = PRIORITY_HIGH
            elif any(w in line_lower for w in ["research", "исследов", "выяснить", "diagnose", "узнать"]):
                phase_type = "research"
                priority = PRIORITY_MEDIUM
            elif any(w in line_lower for w in ["test", "pytest", "e2e", "spec", "smoke"]):
                phase_type = "test"
                priority = PRIORITY_MEDIUM
            elif any(w in line_lower for w in ["нужно сделать", "добавить", "add", "create", "implement"]):
                phase_type = "build"
                priority = PRIORITY_MEDIUM
            else:
                phase_type = "build"
                priority = PRIORITY_LOW

            # Determine complexity
            if len(line) > 200:
                complexity = "high"
            elif len(line) > 80:
                complexity = "medium"
            else:
                complexity = "low"

            # Truncate title to first 100 chars
            title = line[:100]
            if len(line) > 100:
                title += "..."

            self.add_task(
                title=title,
                description=line,
                priority=priority,
                phase_type=phase_type,
                complexity=complexity,
                source=source_tag
            )
            imported += 1

        logger.info(f"[TaskBoard] Imported {imported} tasks from {file_path}")
        return imported


# ==========================================
# SINGLETON ACCESS
# ==========================================

_board_instance: Optional[TaskBoard] = None


def get_task_board() -> TaskBoard:
    """Get or create the singleton TaskBoard instance."""
    global _board_instance
    if _board_instance is None:
        _board_instance = TaskBoard()
    return _board_instance


def reset_task_board() -> None:
    """MARKER_196.FIX: Close SQLite connection and reset singleton.

    Call before importlib.reload() to prevent connection leak.
    """
    global _board_instance
    if _board_instance is not None:
        try:
            _board_instance.db.close()
        except Exception:
            pass
        _board_instance = None
