"""
ProtocolGuard — Stateless rule engine evaluating protocol compliance.

Checks a SessionActions snapshot against a fixed set of protocol rules
and returns a list of violations (warn / block).

MARKER_195.2
"""

import fnmatch
import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ProtocolViolation:
    """Single protocol rule violation."""

    rule_id: str        # "read_before_edit", "task_before_code", etc.
    severity: str       # "warn" | "block"
    message: str        # Human-readable
    suggestion: str     # What to do instead


# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG: Dict[str, Any] = {
    "rules": {
        "read_before_edit": {"severity": "warn", "enabled": True},
        "task_before_code": {"severity": "warn", "enabled": True},
        "taskboard_before_work": {"severity": "warn", "enabled": True},
        "recon_before_code": {"severity": "warn", "enabled": True},
        "session_init_first": {"severity": "warn", "enabled": True},
        "roadmap_before_tasks": {"severity": "warn", "enabled": True},
    },
    "exempt_paths": ["docs/", "tests/", "data/"],
    "enforce_paths": ["src/**/*.py", "client/src/**/*.ts", "client/src/**/*.tsx"],
}

# Edit/Write tool names that trigger code-edit rules
_EDIT_TOOL_NAMES = {"Edit", "Write", "vetka_edit_file", "NotebookEdit"}

# All known MCP tool prefixes
_MCP_TOOL_PREFIXES = ("vetka_",)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_enforced_path(file_path: str, enforce_patterns: List[str], exempt_prefixes: List[str]) -> bool:
    """Return True if *file_path* matches an enforce pattern and is NOT exempt."""
    if not file_path:
        return False

    # Check exemptions first
    for prefix in exempt_prefixes:
        # Normalise: "docs/" matches paths starting with "docs/"
        clean = prefix.rstrip("/")
        if file_path == clean or file_path.startswith(clean + "/"):
            return False
        # Also check common extensions used as exemptions
        if prefix.startswith("*.") and file_path.endswith(prefix[1:]):
            return False

    # Check enforcement patterns
    for pattern in enforce_patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True

    return False


def _is_mcp_tool(tool_name: str) -> bool:
    """Return True if *tool_name* looks like a VETKA MCP tool."""
    for prefix in _MCP_TOOL_PREFIXES:
        if tool_name.startswith(prefix):
            return True
    return False


# ---------------------------------------------------------------------------
# ProtocolGuard
# ---------------------------------------------------------------------------

class ProtocolGuard:
    """Stateless rule engine for protocol compliance checks."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._config_path = config_path
        self._config: Dict[str, Any] = {}
        self._load_config()

    # ------------------------------------------------------------------
    # Config management
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        """Load severity overrides from JSON config.  Create defaults if missing."""
        try:
            if self._config_path and os.path.isfile(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as fh:
                    self._config = json.load(fh)
                logger.debug("protocol_guard: loaded config from %s", self._config_path)
            else:
                self._config = dict(_DEFAULT_CONFIG)
                # Attempt to persist the default config
                if self._config_path:
                    self._write_default_config()
        except Exception:
            logger.exception("protocol_guard: failed to load config, using defaults")
            self._config = dict(_DEFAULT_CONFIG)

    def _write_default_config(self) -> None:
        """Persist the default config to *self._config_path*."""
        try:
            path = Path(self._config_path)  # type: ignore[arg-type]
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(_DEFAULT_CONFIG, fh, indent=2)
            logger.debug("protocol_guard: wrote default config to %s", self._config_path)
        except Exception:
            logger.exception("protocol_guard: could not write default config")

    # ------------------------------------------------------------------
    # Rule helpers
    # ------------------------------------------------------------------

    def _rule_cfg(self, rule_id: str) -> Dict[str, Any]:
        """Return the config dict for a rule, with defaults."""
        rules = self._config.get("rules", {})
        return rules.get(rule_id, _DEFAULT_CONFIG["rules"].get(rule_id, {}))

    def _is_enabled(self, rule_id: str) -> bool:
        return self._rule_cfg(rule_id).get("enabled", True)

    def _severity(self, rule_id: str) -> str:
        return self._rule_cfg(rule_id).get("severity", "warn")

    @property
    def _enforce_patterns(self) -> List[str]:
        return self._config.get("enforce_paths", _DEFAULT_CONFIG["enforce_paths"])

    @property
    def _exempt_prefixes(self) -> List[str]:
        return self._config.get("exempt_paths", _DEFAULT_CONFIG["exempt_paths"])

    # ------------------------------------------------------------------
    # Individual rule checks
    # ------------------------------------------------------------------

    def _check_read_before_edit(self, session: Any, tool_name: str, args: Dict) -> Optional[ProtocolViolation]:
        """Edit/Write on a file not yet read."""
        if tool_name not in _EDIT_TOOL_NAMES:
            return None
        if not self._is_enabled("read_before_edit"):
            return None

        file_path = args.get("file_path") or args.get("path") or ""
        if not _is_enforced_path(file_path, self._enforce_patterns, self._exempt_prefixes):
            return None

        if file_path not in session.files_read:
            return ProtocolViolation(
                rule_id="read_before_edit",
                severity=self._severity("read_before_edit"),
                message=f"You haven't read {file_path} yet.",
                suggestion="Read the file before editing to understand its current state.",
            )
        return None

    def _check_task_before_code(self, session: Any, tool_name: str, args: Dict) -> Optional[ProtocolViolation]:
        """Edit/Write without a claimed task."""
        if tool_name not in _EDIT_TOOL_NAMES:
            return None
        if not self._is_enabled("task_before_code"):
            return None
        if session.task_claimed:
            return None

        return ProtocolViolation(
            rule_id="task_before_code",
            severity=self._severity("task_before_code"),
            message="No task claimed.",
            suggestion="Claim a task from the task board before writing code.",
        )

    def _check_taskboard_before_work(self, session: Any, tool_name: str, args: Dict) -> Optional[ProtocolViolation]:
        """Edit/Write without checking the task board."""
        if tool_name not in _EDIT_TOOL_NAMES:
            return None
        if not self._is_enabled("taskboard_before_work"):
            return None
        if session.task_board_checked:
            return None

        return ProtocolViolation(
            rule_id="taskboard_before_work",
            severity=self._severity("taskboard_before_work"),
            message="Haven't checked task board.",
            suggestion="Check the task board (list or get) before starting work.",
        )

    def _check_recon_before_code(self, session: Any, tool_name: str, args: Dict) -> Optional[ProtocolViolation]:
        """Edit/Write on a claimed task that lacks recon docs."""
        if tool_name not in _EDIT_TOOL_NAMES:
            return None
        if not self._is_enabled("recon_before_code"):
            return None
        if not session.task_claimed:
            return None
        if session.claimed_task_has_recon_docs:
            return None

        return ProtocolViolation(
            rule_id="recon_before_code",
            severity=self._severity("recon_before_code"),
            message="Task has no recon_docs.",
            suggestion="Add reconnaissance documentation to the task before coding.",
        )

    def _check_session_init_first(self, session: Any, tool_name: str, args: Dict) -> Optional[ProtocolViolation]:
        """Any MCP tool called before session_init."""
        if not _is_mcp_tool(tool_name):
            return None
        if tool_name == "vetka_session_init":
            return None
        if not self._is_enabled("session_init_first"):
            return None
        if session.session_init_called:
            return None

        return ProtocolViolation(
            rule_id="session_init_first",
            severity=self._severity("session_init_first"),
            message="Call session_init first.",
            suggestion="Run vetka_session_init before using other MCP tools.",
        )

    def _check_roadmap_before_tasks(self, session: Any, tool_name: str, args: Dict) -> Optional[ProtocolViolation]:
        """task_board action=add without a roadmap."""
        if tool_name != "vetka_task_board":
            return None
        if args.get("action") != "add":
            return None
        if not self._is_enabled("roadmap_before_tasks"):
            return None
        if session.roadmap_exists:
            return None

        return ProtocolViolation(
            rule_id="roadmap_before_tasks",
            severity=self._severity("roadmap_before_tasks"),
            message="No roadmap found.",
            suggestion="Create or verify a roadmap before adding tasks to the board.",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, session: Any, tool_name: str, args: Optional[Dict] = None) -> List[ProtocolViolation]:
        """Evaluate all rules against the given tool invocation.

        Returns a list of violations (may be empty).
        """
        args = args or {}
        violations: List[ProtocolViolation] = []

        checkers = [
            self._check_read_before_edit,
            self._check_task_before_code,
            self._check_taskboard_before_work,
            self._check_recon_before_code,
            self._check_session_init_first,
            self._check_roadmap_before_tasks,
        ]

        for checker in checkers:
            try:
                v = checker(session, tool_name, args)
                if v is not None:
                    violations.append(v)
            except Exception:
                logger.exception("protocol_guard: rule check failed in %s", checker.__name__)

        return violations

    def check_all_pending(self, session: Any) -> List[ProtocolViolation]:
        """Check all rules without a specific tool context (advisory mode).

        Useful at session_init to surface any pending protocol gaps.
        """
        violations: List[ProtocolViolation] = []

        try:
            if self._is_enabled("session_init_first") and not session.session_init_called:
                violations.append(ProtocolViolation(
                    rule_id="session_init_first",
                    severity=self._severity("session_init_first"),
                    message="Call session_init first.",
                    suggestion="Run vetka_session_init before using other MCP tools.",
                ))

            if self._is_enabled("taskboard_before_work") and not session.task_board_checked:
                violations.append(ProtocolViolation(
                    rule_id="taskboard_before_work",
                    severity=self._severity("taskboard_before_work"),
                    message="Haven't checked task board.",
                    suggestion="Check the task board (list or get) before starting work.",
                ))

            if self._is_enabled("task_before_code") and not session.task_claimed:
                violations.append(ProtocolViolation(
                    rule_id="task_before_code",
                    severity=self._severity("task_before_code"),
                    message="No task claimed.",
                    suggestion="Claim a task from the task board before writing code.",
                ))

            if self._is_enabled("recon_before_code") and session.task_claimed and not session.claimed_task_has_recon_docs:
                violations.append(ProtocolViolation(
                    rule_id="recon_before_code",
                    severity=self._severity("recon_before_code"),
                    message="Task has no recon_docs.",
                    suggestion="Add reconnaissance documentation to the task before coding.",
                ))

            if self._is_enabled("roadmap_before_tasks") and not session.roadmap_exists:
                violations.append(ProtocolViolation(
                    rule_id="roadmap_before_tasks",
                    severity=self._severity("roadmap_before_tasks"),
                    message="No roadmap found.",
                    suggestion="Create or verify a roadmap before adding tasks to the board.",
                ))
        except Exception:
            logger.exception("protocol_guard: check_all_pending failed")

        return violations


# ---------------------------------------------------------------------------
# Module-level singleton access
# ---------------------------------------------------------------------------

_guard_instance: Optional[ProtocolGuard] = None
_guard_lock = threading.Lock()

# Default config path relative to project root
_DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "data", "protocol_guard_config.json",
)


def get_protocol_guard(config_path: Optional[str] = None) -> ProtocolGuard:
    """Return the process-wide *ProtocolGuard* singleton."""
    global _guard_instance
    if _guard_instance is None:
        with _guard_lock:
            if _guard_instance is None:
                path = config_path or os.path.normpath(_DEFAULT_CONFIG_PATH)
                _guard_instance = ProtocolGuard(config_path=path)
    return _guard_instance


def reset_protocol_guard() -> None:
    """Destroy the singleton (useful for tests)."""
    global _guard_instance
    with _guard_lock:
        _guard_instance = None
