"""
SessionActionTracker — Per-session state tracker for protocol compliance.

Records tool calls, maintains protocol checkpoint flags, and tracks
file read/edit operations per session.

MARKER_195.1
MARKER_200.CHECKPOINT: Disk persistence for compaction survival.
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SessionActions:
    """Accumulated actions and checkpoint flags for a single session."""

    session_id: str
    created_at: float = field(default_factory=time.time)

    # Protocol checkpoints
    session_init_called: bool = False
    task_board_checked: bool = False        # action=list or action=get
    task_claimed: bool = False               # action=claim
    claimed_task_id: Optional[str] = None
    claimed_task_has_recon_docs: bool = False
    roadmap_exists: bool = False

    # MARKER_196.2.1: Role binding — set via session_init(role=X)
    role_callsign: Optional[str] = None
    role_domain: Optional[str] = None
    role_branch: Optional[str] = None
    role_pipeline_stage: Optional[str] = None

    # File tracking
    files_read: Set[str] = field(default_factory=set)
    files_edited: Set[str] = field(default_factory=set)

    # Experience lifecycle (MARKER_ZETA.D2)
    tasks_completed: int = 0
    experience_report_submitted: bool = False
    experience_report_path: Optional[str] = None

    # Counters
    read_count: int = 0
    edit_count: int = 0
    search_count: int = 0
    task_board_calls: int = 0


# ---------------------------------------------------------------------------
# Tool-name classification sets
# ---------------------------------------------------------------------------

_READ_TOOLS: Set[str] = {
    "Read",
    "vetka_read_file",
    "Grep",
    "Glob",
    "vetka_search_files",
    "vetka_search_semantic",
}

_EDIT_TOOLS: Set[str] = {
    "Edit",
    "Write",
    "vetka_edit_file",
    "NotebookEdit",
}

_SEARCH_TOOLS: Set[str] = {
    "Grep",
    "Glob",
    "vetka_search_files",
    "vetka_search_semantic",
    "WebSearch",
}

# Session TTL: 1 hour
_SESSION_TTL: float = 3600.0

# MARKER_200.CHECKPOINT: Worktree-safe project root (same pattern as stm_buffer.py)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_parts = str(_PROJECT_ROOT).split(".claude")
if len(_parts) > 1:
    _PROJECT_ROOT = Path(_parts[0].rstrip("/"))

_CHECKPOINT_DIR = _PROJECT_ROOT / "data"


# ---------------------------------------------------------------------------
# Tracker (singleton)
# ---------------------------------------------------------------------------

class SessionActionTracker:
    """Thread-safe, singleton-per-process tracker of session actions."""

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionActions] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_action(
        self,
        session_id: str,
        tool_name: str,
        args: Optional[Dict] = None,
    ) -> None:
        """Categorise *tool_name* and update the session's state."""
        args = args or {}
        with self._lock:
            session = self._get_or_create(session_id)

            # --- read tools ---
            if tool_name in _READ_TOOLS:
                file_path = args.get("file_path") or args.get("path") or args.get("pattern")
                if file_path:
                    session.files_read.add(str(file_path))
                session.read_count += 1

            # --- edit tools ---
            if tool_name in _EDIT_TOOLS:
                file_path = args.get("file_path") or args.get("path")
                if file_path:
                    session.files_edited.add(str(file_path))
                session.edit_count += 1

            # --- search tools ---
            if tool_name in _SEARCH_TOOLS:
                session.search_count += 1

            # --- task_board ---
            if tool_name == "vetka_task_board":
                session.task_board_calls += 1
                action = args.get("action")
                if action in ("list", "get"):
                    session.task_board_checked = True
                elif action == "claim":
                    session.task_claimed = True
                    session.claimed_task_id = args.get("task_id")
                elif action == "complete":
                    session.tasks_completed += 1

            # --- experience report (MARKER_ZETA.D2) ---
            if tool_name == "vetka_submit_experience_report":
                session.experience_report_submitted = True
                session.experience_report_path = args.get("report_path")

            # --- session_init ---
            if tool_name == "vetka_session_init":
                session.session_init_called = True

            logger.debug(
                "session_tracker: recorded %s for session %s",
                tool_name,
                session_id,
            )

    def get_session(self, session_id: str) -> SessionActions:
        """Return the *SessionActions* for *session_id*, creating if needed.

        Expired sessions are silently purged before lookup.
        """
        with self._lock:
            self._purge_expired()
            return self._get_or_create(session_id)

    def set_role(self, session_id: str, role) -> None:
        """Bind an AgentRole to this session. Called from session_init(role=X).

        Args:
            session_id: MCP session identifier
            role: AgentRole dataclass from agent_registry
        """
        with self._lock:
            session = self._get_or_create(session_id)
            session.role_callsign = role.callsign
            session.role_domain = role.domain
            session.role_branch = role.branch
            session.role_pipeline_stage = getattr(role, "pipeline_stage", None)
            logger.info(
                "session_tracker: bound role %s (domain=%s, branch=%s) to session %s",
                role.callsign, role.domain, role.branch, session_id,
            )

    def get_role(self, session_id: str) -> Optional[Dict]:
        """Return role binding for session, or None if no role set.

        Returns dict with callsign, domain, branch, pipeline_stage.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session and session.role_callsign:
                return {
                    "callsign": session.role_callsign,
                    "domain": session.role_domain,
                    "branch": session.role_branch,
                    "pipeline_stage": session.role_pipeline_stage,
                }
            return None

    def reset_session(self, session_id: str) -> None:
        """Remove all state for *session_id*."""
        with self._lock:
            self._sessions.pop(session_id, None)
            logger.debug("session_tracker: reset session %s", session_id)

    # ------------------------------------------------------------------
    # MARKER_200.CHECKPOINT: Disk persistence
    # ------------------------------------------------------------------

    def save_checkpoint(
        self,
        session_id: str,
        *,
        task_title: Optional[str] = None,
        completion_contract: Optional[List[str]] = None,
        decisions: Optional[List[str]] = None,
    ) -> Optional[Path]:
        """Persist session state to disk (survives context compaction).

        Uses HERMES 7-section template as FORMAT (zero LLM).
        Called at action=claim and action=complete.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None

            callsign = session.role_callsign or "unknown"
            checkpoint: Dict[str, Any] = {
                "format": "hermes_7s_v1",
                "checkpoint_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "session_id": session_id,
                # Section 1: Goal
                "goal": {
                    "claimed_task_id": session.claimed_task_id,
                    "task_title": task_title,
                },
                # Section 2: Constraints
                "constraints": {
                    "role": callsign,
                    "domain": session.role_domain,
                    "branch": session.role_branch,
                },
                # Section 3: Progress
                "progress": {
                    "tasks_completed": session.tasks_completed,
                    "files_read": len(session.files_read),
                    "files_edited": len(session.files_edited),
                },
                # Section 4: Decisions
                "decisions": decisions or [],
                # Section 5: Relevant Files
                "files": {
                    "read": sorted(session.files_read)[-20:],  # last 20
                    "edited": sorted(session.files_edited),
                },
                # Section 6: Next Steps
                "next_steps": completion_contract or [],
                # Section 7: Protocol state
                "protocol": {
                    "session_init": session.session_init_called,
                    "task_board_checked": session.task_board_checked,
                    "task_claimed": session.task_claimed,
                    "experience_report": session.experience_report_submitted,
                },
            }

            path = _CHECKPOINT_DIR / f"session_checkpoint_{callsign.lower()}.json"
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(checkpoint, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                logger.info(
                    "session_tracker: checkpoint saved for %s at %s",
                    callsign, path,
                )
                return path
            except Exception as exc:
                logger.warning("session_tracker: checkpoint save failed: %s", exc)
                return None

    @staticmethod
    def load_checkpoint(callsign: str) -> Optional[Dict[str, Any]]:
        """Load checkpoint from disk for a given role callsign.

        Returns parsed JSON dict or None if not found / expired (>2h).
        """
        path = _CHECKPOINT_DIR / f"session_checkpoint_{callsign.lower()}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # Expire checkpoints older than 2 hours
            checkpoint_at = data.get("checkpoint_at", "")
            if checkpoint_at:
                from datetime import datetime, timezone
                try:
                    ts = datetime.fromisoformat(checkpoint_at)
                    age_s = (datetime.now(timezone.utc) - ts.replace(
                        tzinfo=timezone.utc if ts.tzinfo is None else ts.tzinfo
                    )).total_seconds()
                    if age_s > 7200:  # 2 hours
                        logger.debug(
                            "session_tracker: checkpoint for %s expired (%.0fs old)",
                            callsign, age_s,
                        )
                        return None
                except (ValueError, TypeError):
                    pass  # Can't parse timestamp — still return data
            return data
        except Exception as exc:
            logger.warning("session_tracker: checkpoint load failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create(self, session_id: str) -> SessionActions:
        """Return existing session or create a cold-start one (no lock)."""
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionActions(session_id=session_id)
            logger.debug("session_tracker: cold-start session %s", session_id)
        return self._sessions[session_id]

    def _purge_expired(self) -> None:
        """Remove sessions older than *_SESSION_TTL* (no lock)."""
        now = time.time()
        expired = [
            sid
            for sid, s in self._sessions.items()
            if (now - s.created_at) > _SESSION_TTL
        ]
        for sid in expired:
            del self._sessions[sid]
            logger.debug("session_tracker: purged expired session %s", sid)


# ---------------------------------------------------------------------------
# Module-level singleton access
# ---------------------------------------------------------------------------

_tracker_instance: Optional[SessionActionTracker] = None
_tracker_lock = threading.Lock()


def get_session_tracker() -> SessionActionTracker:
    """Return the process-wide *SessionActionTracker* singleton."""
    global _tracker_instance
    if _tracker_instance is None:
        with _tracker_lock:
            if _tracker_instance is None:
                _tracker_instance = SessionActionTracker()
    return _tracker_instance


def reset_session_tracker() -> None:
    """Destroy the singleton (useful for tests)."""
    global _tracker_instance
    with _tracker_lock:
        _tracker_instance = None
