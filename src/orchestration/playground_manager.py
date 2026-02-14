"""
VETKA Playground Manager — Git worktree-based isolated sandboxes.

Creates isolated copies of the codebase using git worktrees for safe
agent experimentation. Pipeline code writes go to the worktree, not main.

Strategy: git worktree (not rsync)
- Instant creation (~0.5s vs 30s rsync)
- Git-native: branches, diffs, cherry-pick back to main
- Shared .git objects (no disk waste)
- Clean removal via git worktree remove

MARKER_146.PLAYGROUND

@status: active
@phase: 146
@depends: git, asyncio, pathlib
@used_by: mycelium_mcp_server.py (pipeline sandbox), agent_pipeline.py
"""

import asyncio
import json
import logging
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Project root (3 levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Default playground base directory
PLAYGROUND_BASE = PROJECT_ROOT / ".playgrounds"

# Max concurrent playgrounds (prevent disk abuse)
MAX_PLAYGROUNDS = 5

# Auto-cleanup after this many seconds of inactivity (4 hours)
PLAYGROUND_TTL_SECONDS = 4 * 60 * 60


@dataclass
class PlaygroundConfig:
    """Configuration for a playground instance."""
    playground_id: str
    branch_name: str
    worktree_path: str
    created_at: float
    last_used_at: float
    source_branch: str = "main"
    auto_write: bool = True      # Pipeline can write files in playground
    preset: str = "dragon_silver"
    task_description: str = ""
    status: str = "active"       # active | completed | failed | expired
    files_created: List[str] = field(default_factory=list)
    pipeline_runs: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PlaygroundConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class PlaygroundManager:
    """Manages git worktree-based playground instances.

    Usage:
        manager = PlaygroundManager()

        # Create playground
        pg = await manager.create("Add bookmark feature")

        # Get scoped root for pipeline
        root = manager.get_playground_root(pg.playground_id)

        # List active playgrounds
        active = manager.list_playgrounds()

        # Cleanup expired
        await manager.cleanup_expired()

        # Destroy specific
        await manager.destroy(pg.playground_id)
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self._base_dir = Path(base_dir) if base_dir else PLAYGROUND_BASE
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._config_file = self._base_dir / "playgrounds.json"
        self._playgrounds: Dict[str, PlaygroundConfig] = {}
        self._load_config()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create(
        self,
        task_description: str = "",
        preset: str = "dragon_silver",
        source_branch: str = "main",
        auto_write: bool = True,
    ) -> PlaygroundConfig:
        """Create a new playground with a git worktree.

        Args:
            task_description: What the agent will work on
            preset: Dragon team preset
            source_branch: Branch to base the worktree on
            auto_write: Whether pipeline can write files (True in playground)

        Returns:
            PlaygroundConfig with paths and metadata

        Raises:
            RuntimeError: If max playgrounds reached or git fails
        """
        # Check limits
        active = [p for p in self._playgrounds.values() if p.status == "active"]
        if len(active) >= MAX_PLAYGROUNDS:
            # Try cleanup first
            await self.cleanup_expired()
            active = [p for p in self._playgrounds.values() if p.status == "active"]
            if len(active) >= MAX_PLAYGROUNDS:
                raise RuntimeError(
                    f"Max {MAX_PLAYGROUNDS} concurrent playgrounds. "
                    f"Destroy one first: {[p.playground_id for p in active]}"
                )

        # Generate unique ID and branch
        pg_id = f"pg_{uuid.uuid4().hex[:8]}"
        branch_name = f"playground/{pg_id}"
        worktree_path = self._base_dir / pg_id

        # Create git worktree
        await self._create_worktree(
            worktree_path=worktree_path,
            branch_name=branch_name,
            source_branch=source_branch,
        )

        # Ensure worktree dir exists (git worktree add creates it,
        # but we ensure in case of partial setup)
        worktree_path.mkdir(parents=True, exist_ok=True)

        # Create config
        now = time.time()
        config = PlaygroundConfig(
            playground_id=pg_id,
            branch_name=branch_name,
            worktree_path=str(worktree_path),
            created_at=now,
            last_used_at=now,
            source_branch=source_branch,
            auto_write=auto_write,
            preset=preset,
            task_description=task_description,
        )

        # Create playground metadata file inside the worktree
        meta_file = worktree_path / ".playground.json"
        meta_file.write_text(json.dumps({
            "playground_id": pg_id,
            "task": task_description,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "restrictions": {
                "scoped_to": str(worktree_path),
                "can_write_main": False,
                "auto_write": auto_write,
            }
        }, indent=2))

        self._playgrounds[pg_id] = config
        self._save_config()

        logger.info(
            "Playground created: %s at %s (branch=%s, preset=%s)",
            pg_id, worktree_path, branch_name, preset
        )
        return config

    async def destroy(self, playground_id: str) -> bool:
        """Destroy a playground and its git worktree.

        Args:
            playground_id: The playground to destroy

        Returns:
            True if destroyed, False if not found
        """
        config = self._playgrounds.get(playground_id)
        if not config:
            logger.warning("Playground not found: %s", playground_id)
            return False

        worktree_path = Path(config.worktree_path)

        # Remove git worktree
        try:
            await self._remove_worktree(worktree_path, config.branch_name)
        except Exception as e:
            logger.warning("Failed to remove worktree cleanly: %s (force removing)", e)
            # Force remove the directory
            if worktree_path.exists():
                shutil.rmtree(worktree_path, ignore_errors=True)
            # Force prune worktrees
            await self._run_git(["worktree", "prune"])

        # Set final status (preserve "expired" if set by cleanup)
        if config.status not in ("expired", "failed"):
            config.status = "completed"
        self._save_config()

        logger.info("Playground destroyed: %s", playground_id)
        return True

    def get_playground_root(self, playground_id: str) -> Optional[Path]:
        """Get the filesystem root of a playground for path scoping.

        Args:
            playground_id: The playground ID

        Returns:
            Path to the worktree root, or None if not found/inactive
        """
        config = self._playgrounds.get(playground_id)
        if not config:
            # MARKER_146.CROSS_PROCESS: Reload from disk — playground may have been
            # created by another process (e.g., Claude Code creates, MYCELIUM resolves)
            self._load_config()
            config = self._playgrounds.get(playground_id)
        if not config or config.status != "active":
            return None

        root = Path(config.worktree_path)
        if not root.exists():
            logger.warning("Playground dir missing: %s", root)
            return None

        # Update last_used timestamp
        config.last_used_at = time.time()
        self._save_config()

        return root

    def list_playgrounds(self, include_inactive: bool = False) -> List[PlaygroundConfig]:
        """List playground instances.

        Args:
            include_inactive: If True, include completed/failed/expired

        Returns:
            List of PlaygroundConfig
        """
        if include_inactive:
            return list(self._playgrounds.values())
        return [p for p in self._playgrounds.values() if p.status == "active"]

    async def cleanup_expired(self) -> int:
        """Remove playgrounds that have exceeded TTL.

        Returns:
            Number of playgrounds cleaned up
        """
        now = time.time()
        expired = []
        for pg_id, config in self._playgrounds.items():
            if config.status == "active" and (now - config.last_used_at) > PLAYGROUND_TTL_SECONDS:
                expired.append(pg_id)

        for pg_id in expired:
            self._playgrounds[pg_id].status = "expired"
            await self.destroy(pg_id)
            logger.info("Expired playground cleaned: %s", pg_id)

        return len(expired)

    def validate_path(self, playground_id: str, file_path: str) -> bool:
        """Check if a file path is within the playground boundary.

        CRITICAL SECURITY: Prevents path traversal attacks.

        Args:
            playground_id: Playground to check against
            file_path: Path to validate

        Returns:
            True if path is inside playground, False otherwise
        """
        root = self.get_playground_root(playground_id)
        if not root:
            return False

        try:
            resolved = Path(file_path).resolve()
            root_resolved = root.resolve()
            return str(resolved).startswith(str(root_resolved))
        except (ValueError, OSError):
            return False

    def scope_path(self, playground_id: str, relative_path: str) -> Optional[Path]:
        """Convert a relative path to an absolute path within the playground.

        Args:
            playground_id: Playground ID
            relative_path: Path relative to project root (e.g., "src/main.py")

        Returns:
            Absolute path within playground, or None if invalid
        """
        root = self.get_playground_root(playground_id)
        if not root:
            return None

        # Block path traversal attempts
        if ".." in relative_path:
            logger.warning("Path traversal blocked: %s (playground=%s)", relative_path, playground_id)
            return None

        # Strip leading / or ./ for safety
        clean = relative_path.lstrip("/")
        if clean.startswith("./"):
            clean = clean[2:]
        full_path = root / clean

        # Validate it's still within playground (prevent ../../../ attacks)
        if not self.validate_path(playground_id, str(full_path)):
            logger.warning("Path traversal blocked: %s (playground=%s)", relative_path, playground_id)
            return None

        return full_path

    def record_pipeline_run(self, playground_id: str, files_created: Optional[List[str]] = None):
        """Record that a pipeline ran in this playground.

        Args:
            playground_id: Which playground
            files_created: List of files the pipeline created
        """
        config = self._playgrounds.get(playground_id)
        if not config:
            return

        config.pipeline_runs += 1
        config.last_used_at = time.time()
        if files_created:
            config.files_created.extend(files_created)
        self._save_config()

    async def get_diff(self, playground_id: str) -> Optional[str]:
        """Get git diff of changes made in the playground vs source branch.

        Args:
            playground_id: Playground to diff

        Returns:
            Git diff string, or None if not found
        """
        config = self._playgrounds.get(playground_id)
        if not config:
            return None

        worktree_path = Path(config.worktree_path)
        if not worktree_path.exists():
            return None

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["git", "diff", "--stat", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(worktree_path),
                timeout=10,
            )
            return result.stdout if result.returncode == 0 else None
        except Exception as e:
            logger.warning("Failed to get diff for %s: %s", playground_id, e)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _create_worktree(
        self,
        worktree_path: Path,
        branch_name: str,
        source_branch: str,
    ):
        """Create a git worktree with a new branch."""
        # Ensure source branch exists
        await self._run_git(["rev-parse", "--verify", source_branch])

        # Create worktree with new branch
        await self._run_git([
            "worktree", "add",
            "-b", branch_name,
            str(worktree_path),
            source_branch,
        ])

    async def _remove_worktree(self, worktree_path: Path, branch_name: str):
        """Remove a git worktree and its branch."""
        if worktree_path.exists():
            await self._run_git(["worktree", "remove", str(worktree_path), "--force"])

        # Delete the branch (cleanup)
        try:
            await self._run_git(["branch", "-D", branch_name])
        except RuntimeError:
            pass  # Branch may already be gone

    async def _run_git(self, args: List[str], cwd: Optional[str] = None) -> str:
        """Run a git command asynchronously.

        Args:
            args: Git command arguments (without 'git' prefix)
            cwd: Working directory (default: PROJECT_ROOT)

        Returns:
            Command stdout

        Raises:
            RuntimeError: If git command fails
        """
        cmd = ["git"] + args
        work_dir = cwd or str(PROJECT_ROOT)

        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            cwd=work_dir,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"git {' '.join(args)} failed (rc={result.returncode}): {result.stderr.strip()}"
            )

        return result.stdout.strip()

    def _load_config(self):
        """Load playground configs from disk."""
        if not self._config_file.exists():
            self._playgrounds = {}
            return

        try:
            data = json.loads(self._config_file.read_text())
            self._playgrounds = {
                k: PlaygroundConfig.from_dict(v)
                for k, v in data.items()
            }
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to load playground config: %s", e)
            self._playgrounds = {}

    def _save_config(self):
        """Save playground configs to disk."""
        data = {k: v.to_dict() for k, v in self._playgrounds.items()}
        self._config_file.write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_manager: Optional[PlaygroundManager] = None


def get_playground_manager() -> PlaygroundManager:
    """Get or create the singleton PlaygroundManager."""
    global _manager
    if _manager is None:
        _manager = PlaygroundManager()
    return _manager


# ---------------------------------------------------------------------------
# Convenience functions for MCP tools
# ---------------------------------------------------------------------------

async def create_playground(
    task: str = "",
    preset: str = "dragon_silver",
    auto_write: bool = True,
) -> Dict:
    """Create a playground — convenience for MCP tools.

    Returns:
        Dict with playground_id, worktree_path, branch_name
    """
    manager = get_playground_manager()
    config = await manager.create(
        task_description=task,
        preset=preset,
        auto_write=auto_write,
    )
    return {
        "playground_id": config.playground_id,
        "worktree_path": config.worktree_path,
        "branch_name": config.branch_name,
        "status": config.status,
    }


async def destroy_playground(playground_id: str) -> Dict:
    """Destroy a playground — convenience for MCP tools."""
    manager = get_playground_manager()
    success = await manager.destroy(playground_id)
    return {"success": success, "playground_id": playground_id}


def list_playgrounds_summary() -> List[Dict]:
    """List active playgrounds — convenience for MCP tools."""
    manager = get_playground_manager()
    return [
        {
            "playground_id": p.playground_id,
            "task": p.task_description[:80],
            "status": p.status,
            "branch": p.branch_name,
            "pipeline_runs": p.pipeline_runs,
            "files_created": len(p.files_created),
            "age_minutes": round((time.time() - p.created_at) / 60, 1),
        }
        for p in manager.list_playgrounds(include_inactive=True)
    ]
