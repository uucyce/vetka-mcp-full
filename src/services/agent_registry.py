"""
MARKER_ZETA.D1: Agent Registry — role/domain/ownership loader.

Loads agent_registry.yaml and provides lookup by callsign, branch, worktree, or domain.
Used by task board (D4) for domain validation and by CLAUDE.md generator (D3).

Usage:
    from src.services.agent_registry import get_agent_registry

    registry = get_agent_registry()
    role = registry.get_by_callsign("Alpha")
    role = registry.get_by_branch("claude/cut-engine")
    result = registry.validate_file_ownership("Alpha", "client/src/components/cut/MenuBar.tsx")
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# Default registry path relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_REGISTRY_PATH = _PROJECT_ROOT / "data" / "templates" / "agent_registry.yaml"


@dataclass(frozen=True)
class SharedZone:
    """A file with split ownership between multiple agents."""

    file: str
    owners: dict[str, str]  # callsign -> scope description
    protocol: str


@dataclass(frozen=True)
class AgentRole:
    """Immutable agent role definition loaded from registry YAML."""

    callsign: str
    domain: str
    pipeline_stage: Optional[str]  # coder | verifier | architect | None (meta roles)
    role_title: str
    worktree: str
    branch: str
    owned_paths: tuple[str, ...]
    blocked_paths: tuple[str, ...]
    predecessor_docs: str  # glob pattern
    key_docs: tuple[str, ...]
    roadmap: str
    # MARKER_200.AUTO_PROVISION: Ephemeral roles created at runtime
    ephemeral: bool = False
    origin: str = ""  # terminal | mcc | vetka_chat | opencode | codex | subagent
    model_class: str = ""  # titan | worker | scout
    parent_role: str = ""  # callsign of the role template this was forked from


@dataclass(frozen=True)
class OwnershipResult:
    """Result of file ownership validation."""

    file_path: str
    is_owned: bool
    is_blocked: bool
    matched_owned_pattern: Optional[str] = None
    matched_blocked_pattern: Optional[str] = None
    shared_zone: Optional[SharedZone] = None


class AgentRegistry:
    """
    Loads and queries agent_registry.yaml.

    Thread-safe after construction. All lookups are O(n) where n = number of roles (5).
    """

    def __init__(self, registry_path: Optional[Path] = None):
        self._path = registry_path or _DEFAULT_REGISTRY_PATH
        self._roles: list[AgentRole] = []
        self._shared_zones: list[SharedZone] = []
        self._version: str = ""
        self._project_id: str = ""
        self._load()

    def _load(self) -> None:
        """Parse YAML and build role objects."""
        with open(self._path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._version = data.get("version", "")
        self._project_id = data.get("project_id", "")

        for entry in data.get("roles", []):
            role = AgentRole(
                callsign=entry["callsign"],
                domain=entry["domain"],
                pipeline_stage=entry.get("pipeline_stage"),  # None for meta roles
                role_title=entry.get("role_title", ""),
                worktree=entry["worktree"],
                branch=entry["branch"],
                owned_paths=tuple(entry.get("owned_paths", [])),
                blocked_paths=tuple(entry.get("blocked_paths", [])),
                predecessor_docs=entry.get("predecessor_docs", ""),
                key_docs=tuple(entry.get("key_docs", [])),
                roadmap=entry.get("roadmap", ""),
            )
            self._roles.append(role)

        for entry in data.get("shared_zones", []):
            zone = SharedZone(
                file=entry["file"],
                owners=dict(entry.get("owners", {})),
                protocol=entry.get("protocol", ""),
            )
            self._shared_zones.append(zone)

        logger.info(
            "[AgentRegistry] Loaded %d roles, %d shared zones from %s (v%s, project=%s)",
            len(self._roles),
            len(self._shared_zones),
            self._path.name,
            self._version,
            self._project_id,
        )

    # ── Properties ──────────────────────────────────────────

    @property
    def version(self) -> str:
        return self._version

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def roles(self) -> list[AgentRole]:
        return list(self._roles)

    @property
    def shared_zones(self) -> list[SharedZone]:
        return list(self._shared_zones)

    def list_callsigns(self) -> list[str]:
        """Return list of all registered callsigns."""
        return [r.callsign for r in self._roles]

    # ── Lookups ─────────────────────────────────────────────

    def get_by_callsign(self, callsign: str) -> Optional[AgentRole]:
        """Lookup role by callsign (case-insensitive)."""
        cs = callsign.strip().lower()
        for role in self._roles:
            if role.callsign.lower() == cs:
                return role
        return None

    def get_by_branch(self, branch: str) -> Optional[AgentRole]:
        """Lookup role by git branch name."""
        b = branch.strip()
        for role in self._roles:
            if role.branch == b:
                return role
        return None

    def get_by_worktree(self, worktree: str) -> Optional[AgentRole]:
        """Lookup role by worktree directory name."""
        wt = worktree.strip()
        for role in self._roles:
            if role.worktree == wt:
                return role
        return None

    def get_by_domain(self, domain: str) -> Optional[AgentRole]:
        """Lookup role by domain name."""
        d = domain.strip().lower()
        for role in self._roles:
            if role.domain.lower() == d:
                return role
        return None

    # ── Validation ──────────────────────────────────────────

    def validate_file_ownership(self, callsign: str, file_path: str) -> OwnershipResult:
        """
        Check if a file is owned/blocked for a given agent callsign.

        Uses fnmatch for glob pattern matching against owned_paths and blocked_paths.
        Also checks shared_zones for split-ownership files.

        Returns OwnershipResult with is_owned, is_blocked, and matched patterns.
        """
        role = self.get_by_callsign(callsign)
        if role is None:
            return OwnershipResult(file_path=file_path, is_owned=False, is_blocked=False)

        # Normalize path separators
        fp = file_path.replace("\\", "/")

        # Check blocked first (blocked takes precedence for safety)
        matched_blocked = None
        is_blocked = False
        for pattern in role.blocked_paths:
            if self._path_matches(fp, pattern):
                is_blocked = True
                matched_blocked = pattern
                break

        # Check owned
        matched_owned = None
        is_owned = False
        for pattern in role.owned_paths:
            if self._path_matches(fp, pattern):
                is_owned = True
                matched_owned = pattern
                break

        # Check shared zones
        shared = None
        for zone in self._shared_zones:
            if self._path_matches(fp, zone.file):
                shared = zone
                break

        return OwnershipResult(
            file_path=file_path,
            is_owned=is_owned,
            is_blocked=is_blocked,
            matched_owned_pattern=matched_owned,
            matched_blocked_pattern=matched_blocked,
            shared_zone=shared,
        )

    def validate_domain_match(self, callsign: str, task_domain: str) -> tuple[bool, str]:
        """
        Check if agent's domain matches task domain.

        Returns (matches: bool, message: str).
        """
        role = self.get_by_callsign(callsign)
        if role is None:
            return True, f"Unknown callsign '{callsign}' — skipping domain check"

        if not task_domain:
            return True, "No task domain specified — skipping check"

        if role.domain.lower() == task_domain.strip().lower():
            return True, f"{callsign} ({role.domain}) matches task domain '{task_domain}'"

        return False, (
            f"Domain mismatch: {callsign} owns '{role.domain}' "
            f"but task domain is '{task_domain}'"
        )

    # ── Auto-Provision (MARKER_200.AUTO_PROVISION) ──────────

    def add_ephemeral_role(self, role: AgentRole) -> None:
        """Add an ephemeral role at runtime (not persisted to YAML)."""
        # Check for name collision
        existing = self.get_by_callsign(role.callsign)
        if existing:
            logger.warning(
                "[AgentRegistry] Callsign '%s' already exists, skipping add",
                role.callsign,
            )
            return
        self._roles.append(role)
        logger.info(
            "[AgentRegistry] Added ephemeral role: %s (origin=%s, domain=%s, parent=%s)",
            role.callsign,
            role.origin,
            role.domain,
            role.parent_role,
        )

    def find_role_template(self, domain: str) -> Optional[AgentRole]:
        """Find a persistent (non-ephemeral) role template for a domain.

        Used to inherit owned_paths/blocked_paths when auto-provisioning.
        Prefers roles that are not ephemeral themselves.
        """
        for r in self._roles:
            if r.domain.lower() == domain.lower() and not r.ephemeral:
                return r
        return None

    @staticmethod
    def is_worktree_occupied(worktree_path: Path) -> tuple[bool, Optional[int]]:
        """Check if a worktree has an active agent (PID-based, no timeouts).

        Returns (occupied: bool, pid: Optional[int]).
        """
        import os

        lock = worktree_path / ".agent_lock"
        if not lock.exists():
            return False, None
        try:
            lines = lock.read_text().strip().split("\n")
            pid = int(lines[0])
            os.kill(pid, 0)  # signal 0 = check without killing
            return True, pid
        except (ProcessLookupError, PermissionError):
            return False, None  # process dead, worktree free
        except (ValueError, IndexError, OSError):
            return False, None

    # ── Helpers ─────────────────────────────────────────────

    @staticmethod
    def _path_matches(file_path: str, pattern: str) -> bool:
        """
        Check if file_path matches a pattern.

        Supports:
        - Exact match: "client/src/components/cut/MenuBar.tsx"
        - Glob: "e2e/*.spec.cjs", "tests/test_*.py"
        - Directory prefix: "client/src-tauri/" matches anything inside
        - Partial path: "MenuBar.tsx" matches any file ending with that name
        """
        pattern = pattern.replace("\\", "/")

        # Strip inline comments (e.g. "file.ts  # comment")
        if "  #" in pattern:
            pattern = pattern.split("  #")[0].strip()

        # Directory pattern (ends with /)
        if pattern.endswith("/"):
            return file_path.startswith(pattern) or f"/{pattern}" in f"/{file_path}"

        # Glob pattern
        if "*" in pattern:
            return fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(
                file_path.split("/")[-1], pattern.split("/")[-1]
            )

        # Exact or suffix match
        if "/" in pattern:
            return file_path == pattern or file_path.endswith(f"/{pattern}")
        else:
            # Bare filename
            return file_path.endswith(f"/{pattern}") or file_path == pattern


# ── Singleton ───────────────────────────────────────────────

_registry_instance: Optional[AgentRegistry] = None


def get_agent_registry(registry_path: Optional[Path] = None) -> AgentRegistry:
    """Get or create the singleton AgentRegistry instance."""
    global _registry_instance
    if _registry_instance is None or registry_path is not None:
        _registry_instance = AgentRegistry(registry_path)
    return _registry_instance


def reset_agent_registry() -> None:
    """Reset singleton (for testing)."""
    global _registry_instance
    _registry_instance = None
