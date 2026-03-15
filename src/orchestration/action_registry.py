"""
MARKER_182.ACTIONREGISTRY: Central log of all agent actions during pipeline execution.

Every edit, read, create, delete, test action by an agent is logged here.
Verifier reads this log to batch-merge all changes into a single git commit.

@status: active
@phase: 182
@depends: pathlib, json, uuid, time
@used_by: agent_pipeline, task_board_tools, verifier_merge
"""

import json
import time
import uuid
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vetka.action_registry")

# Default storage path (relative to project root)
DEFAULT_LOG_PATH = Path(__file__).resolve().parents[2] / "data" / "action_log.json"
MAX_ENTRIES = 10_000
FLUSH_THRESHOLD = 50  # Flush buffer to disk every N entries


class ActionLogEntry:
    """Single action performed by an agent."""

    __slots__ = (
        "id", "run_id", "session_id", "task_id", "agent",
        "action", "file", "result", "duration_ms", "timestamp", "metadata"
    )

    def __init__(
        self,
        run_id: str,
        agent: str,
        action: str,
        file: str,
        result: str = "success",
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        duration_ms: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = uuid.uuid4().hex[:16]
        self.run_id = run_id
        self.session_id = session_id
        self.task_id = task_id
        self.agent = agent
        self.action = action  # edit|read|create|delete|test|commit|merge
        self.file = file
        self.result = result  # success|failed
        self.duration_ms = duration_ms
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "agent": self.agent,
            "action": self.action,
            "file": self.file,
            "result": self.result,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionLogEntry":
        entry = cls(
            run_id=data.get("run_id", ""),
            agent=data.get("agent", ""),
            action=data.get("action", ""),
            file=data.get("file", ""),
            result=data.get("result", "success"),
            session_id=data.get("session_id"),
            task_id=data.get("task_id"),
            duration_ms=data.get("duration_ms", 0),
            metadata=data.get("metadata", {}),
        )
        entry.id = data.get("id", entry.id)
        entry.timestamp = data.get("timestamp", entry.timestamp)
        return entry


class ActionRegistry:
    """Central registry for agent actions.

    Provides:
    - log_action(): Log a single action (buffered)
    - flush(): Write buffer to disk
    - get_actions_for_run(run_id): Query by run
    - get_actions_for_session(session_id): Query by session
    - get_actions_for_file(file): Query by file path
    - get_edit_files_for_run(run_id): Get list of edited files (for Verifier merge)

    Thread-safe via lock. Auto-flushes every FLUSH_THRESHOLD entries.
    Trims to MAX_ENTRIES on flush to prevent unbounded growth.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or DEFAULT_LOG_PATH
        self._buffer: List[ActionLogEntry] = []
        self._lock = threading.Lock()

    def log_action(
        self,
        run_id: str,
        agent: str,
        action: str,
        file: str,
        result: str = "success",
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        duration_ms: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ActionLogEntry:
        """Log a single action. Thread-safe, auto-flushes."""
        entry = ActionLogEntry(
            run_id=run_id,
            agent=agent,
            action=action,
            file=file,
            result=result,
            session_id=session_id,
            task_id=task_id,
            duration_ms=duration_ms,
            metadata=metadata,
        )

        with self._lock:
            self._buffer.append(entry)
            if len(self._buffer) >= FLUSH_THRESHOLD:
                self._flush_unlocked()

        return entry

    def flush(self) -> int:
        """Write buffered actions to disk. Returns count flushed."""
        with self._lock:
            return self._flush_unlocked()

    def _flush_unlocked(self) -> int:
        """Internal flush (caller must hold lock)."""
        if not self._buffer:
            return 0

        count = len(self._buffer)
        new_entries = [e.to_dict() for e in self._buffer]
        self._buffer.clear()

        try:
            # Read existing log
            existing = self._read_log()
            # Append new entries
            existing.extend(new_entries)
            # Trim to MAX_ENTRIES (keep newest)
            if len(existing) > MAX_ENTRIES:
                existing = existing[-MAX_ENTRIES:]
            # Write back
            self._write_log(existing)
            logger.debug(f"[ActionRegistry] Flushed {count} actions (total: {len(existing)})")
        except Exception as e:
            logger.error(f"[ActionRegistry] Flush failed: {e}")
            # Put entries back in buffer for retry
            self._buffer.extend([ActionLogEntry.from_dict(e) for e in new_entries])
            return 0

        return count

    def get_actions_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all actions for a specific pipeline run."""
        # Include unflushed buffer entries
        buffered = [e.to_dict() for e in self._buffer if e.run_id == run_id]
        persisted = [e for e in self._read_log() if e.get("run_id") == run_id]
        return persisted + buffered

    def get_actions_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all actions for a specific session (heartbeat tick)."""
        buffered = [e.to_dict() for e in self._buffer if e.session_id == session_id]
        persisted = [e for e in self._read_log() if e.get("session_id") == session_id]
        return persisted + buffered

    def get_actions_for_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Get all actions touching a specific file."""
        buffered = [e.to_dict() for e in self._buffer if e.file == file_path]
        persisted = [e for e in self._read_log() if e.get("file") == file_path]
        return persisted + buffered

    def get_edit_files_for_run(self, run_id: str) -> List[str]:
        """Get list of files edited/created in a run (for Verifier merge)."""
        actions = self.get_actions_for_run(run_id)
        files = set()
        for a in actions:
            if a.get("action") in ("edit", "create") and a.get("result") == "success":
                files.add(a["file"])
        return sorted(files)

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        log = self._read_log()
        buffered = len(self._buffer)

        # Count by action type
        action_counts: Dict[str, int] = {}
        agent_counts: Dict[str, int] = {}
        for entry in log:
            action = entry.get("action", "unknown")
            agent = entry.get("agent", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1
            agent_counts[agent] = agent_counts.get(agent, 0) + 1

        return {
            "total_persisted": len(log),
            "buffered": buffered,
            "action_counts": action_counts,
            "agent_counts": agent_counts,
        }

    def _read_log(self) -> List[Dict[str, Any]]:
        """Read the action log from disk."""
        if not self.storage_path.exists():
            return []
        try:
            text = self.storage_path.read_text(encoding="utf-8")
            if not text.strip():
                return []
            return json.loads(text)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"[ActionRegistry] Failed to read log: {e}")
            return []

    def _write_log(self, entries: List[Dict[str, Any]]) -> None:
        """Write the action log to disk."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
