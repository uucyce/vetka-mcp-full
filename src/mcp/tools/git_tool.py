"""
Git operations tools - status (read-only) and commit (requires approval).

@status: active
@phase: 96, 108.7
@depends: base_tool, subprocess, pathlib, json
@used_by: mcp_server, stdio_server

MARKER_108_7_AUTO_DIGEST: Auto-update project_digest.json after successful commit
- Updates git.commit hash
- Sets git.dirty = false
- Preserves all other digest fields
- Enables "breaking news" pattern for agents
"""
import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from .base_tool import BaseMCPTool

logger = logging.getLogger("VETKA_MCP")

# MARKER_178.FIX_HARDCODE: Resolve PROJECT_ROOT dynamically (worktree-safe)
def _resolve_git_root() -> Path:
    """Resolve to git toplevel, works in both main repo and worktrees."""
    fallback = Path(__file__).resolve().parents[3]  # src/mcp/tools/ → 3 levels up
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(fallback),
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except Exception:
        pass
    return fallback

PROJECT_ROOT = _resolve_git_root()
DIGEST_PATH = PROJECT_ROOT / "data" / "project_digest.json"


class GitStatusTool(BaseMCPTool):
    """Get git status (modified, staged, untracked files)"""

    @property
    def name(self) -> str:
        return "vetka_git_status"

    @property
    def description(self) -> str:
        return "Get git status (modified, staged, untracked files)"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Get porcelain status
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=10
            )

            files = {"modified": [], "staged": [], "untracked": []}
            for line in status.stdout.splitlines():
                if not line.strip():
                    continue
                code = line[:2]
                filepath = line[3:]

                # First char = staged, second char = working tree
                if code[0] in "MADRC":
                    files["staged"].append(filepath)
                if code[1] == "M":
                    files["modified"].append(filepath)
                if code == "??":
                    files["untracked"].append(filepath)

            # Get current branch
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=5
            ).stdout.strip()

            # Get last commit
            last_commit = subprocess.run(
                ["git", "log", "-1", "--oneline"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=5
            ).stdout.strip()

            return {
                "success": True,
                "result": {
                    "branch": branch,
                    "last_commit": last_commit,
                    "files": files,
                    "clean": not any(files.values())
                },
                "error": None
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git command timed out", "result": None}
        except FileNotFoundError:
            return {"success": False, "error": "Git not found", "result": None}
        except Exception as e:
            return {"success": False, "error": str(e), "result": None}


class GitCommitTool(BaseMCPTool):
    """Create git commit. REQUIRES APPROVAL. Stages specified files and commits."""

    @property
    def name(self) -> str:
        return "vetka_git_commit"

    @property
    def description(self) -> str:
        return "Create git commit. REQUIRES APPROVAL. Default: dry_run=true"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message"
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Files to stage (empty = all changed files)"
                },
                "dry_run": {
                    "type": "boolean",
                    "default": True,
                    "description": "Preview only. Set to false to commit."
                },
                "auto_push": {
                    "type": "boolean",
                    "default": False,
                    "description": "Auto-push to remote after successful commit (MARKER_GIT_AUTO_PUSH)"
                }
            },
            "required": ["message"]
        }

    @property
    def requires_approval(self) -> bool:
        return True

    def validate_arguments(self, args: Dict[str, Any]) -> str:
        message = args.get("message", "")
        if not message or len(message) < 5:
            return "Commit message must be at least 5 characters"
        files = args.get("files", [])
        if files:
            for f in files:
                if ".." in f:
                    return "Path traversal not allowed"
        return None

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        import os
        message = arguments["message"]
        files = arguments.get("files", [])
        dry_run = arguments.get("dry_run", True)
        auto_push = arguments.get("auto_push", False)  # MARKER_GIT_AUTO_PUSH: Auto-push after commit
        # MARKER_188.2: cwd override for worktree auto-commit
        git_root = Path(arguments["cwd"]) if arguments.get("cwd") else PROJECT_ROOT

        if dry_run:
            return {
                "success": True,
                "result": {
                    "status": "dry_run",
                    "message": message,
                    "files": files if files else ["(all changed files)"],
                    "hint": "Set dry_run=false to commit"
                },
                "error": None
            }

        # MARKER_210.MCP_GUARD: Block real commits without a claimed task.
        # Secondary defense (primary = pre-commit hook). Checks VETKA_AGENT_ROLE env var.
        # Bypass: set VETKA_COMMIT_GUARDRAIL_BYPASS=1 for emergency (e.g. Commander hotfix).
        _guard_role = os.environ.get("VETKA_AGENT_ROLE", "").strip()
        if _guard_role and not os.environ.get("VETKA_COMMIT_GUARDRAIL_BYPASS"):
            try:
                from src.orchestration.task_board import check_claimed_task_for_hook, get_task_board
                _claimed = check_claimed_task_for_hook(_guard_role)
                if not _claimed:
                    # Fetch top-3 pending high-priority tasks as suggestions
                    _suggestions = []
                    try:
                        _board = get_task_board()
                        _pending = _board.list_tasks(filter_status="pending", limit=3)
                        _suggestions = [
                            f"  • {t['id']}: {t['title'][:60]}"
                            for t in (_pending.get("tasks") or [])[:3]
                        ]
                    except Exception:
                        pass
                    _suggest_str = "\n".join(_suggestions) if _suggestions else "  (none found)"
                    return {
                        "success": False,
                        "error": (
                            f"Task Board Compliance: no claimed task for role '{_guard_role}'.\n"
                            f"Claim a task first:\n"
                            f"  vetka_task_board action=claim task_id=tb_XXXXX\n"
                            f"Top pending tasks:\n{_suggest_str}\n"
                            f"Emergency bypass: set VETKA_COMMIT_GUARDRAIL_BYPASS=1"
                        ),
                        "result": None,
                        "guardrail": True,
                    }
            except ImportError:
                logger.debug("[MCP_GUARD] task_board import failed — guard skipped")

        try:
            # Stage files
            if files:
                for f in files:
                    result = subprocess.run(
                        ["git", "add", f],
                        cwd=str(git_root),
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode != 0:
                        # MARKER_178.FIX: Skip files that no longer exist
                        # (already committed in previous attempt, or deleted)
                        stderr = result.stderr or ""
                        if "did not match any files" in stderr or "pathspec" in stderr:
                            continue  # Not fatal — proceed with next file
                        return {"success": False, "error": f"Failed to stage {f}: {stderr}", "result": None}
            else:
                result = subprocess.run(
                    ["git", "add", "-A"],
                    cwd=str(git_root),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    return {"success": False, "error": f"Failed to stage files: {result.stderr}", "result": None}

            # MARKER_196.FIX: Capture HEAD before commit for false-positive detection
            _head_before = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(git_root), capture_output=True, text=True, timeout=5,
            ).stdout.strip()

            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=str(git_root),
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                if "nothing to commit" in result.stdout.lower() or "nothing to commit" in result.stderr.lower():
                    return {"success": False, "error": "Nothing to commit", "result": None}

                # MARKER_196.FIX: Check if commit actually succeeded despite non-zero exit
                # Pre-commit hook stdout/stderr can cause git to report failure even when
                # the commit was created. Defensive: never lose a commit due to hook noise.
                _head_after = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(git_root), capture_output=True, text=True, timeout=5,
                ).stdout.strip()
                if _head_after != _head_before:
                    # Commit exists! Treat as success despite returncode.
                    import logging as _lg
                    _lg.getLogger("vetka.git").warning(
                        "[GitTool] Commit succeeded (HEAD changed) despite returncode=%d. "
                        "Hook output: %s", result.returncode, (result.stderr or result.stdout)[:200],
                    )
                else:
                    return {"success": False, "error": result.stderr or result.stdout, "result": None}

            # Get commit hash
            commit_hash = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(git_root),
                capture_output=True,
                text=True,
                timeout=5
            ).stdout.strip()[:8]

            result_data = {
                "status": "committed",
                "hash": commit_hash,
                "message": message
            }

            # MARKER_108_7_AUTO_DIGEST: Update digest after successful commit
            digest_update = self._update_digest_after_commit(commit_hash, message)
            if digest_update:
                result_data["digest_updated"] = True
                result_data["digest_status"] = digest_update
            else:
                result_data["digest_updated"] = False

            # MARKER_130.C17B: Auto-complete tasks matching commit message
            auto_completed = self._auto_complete_tasks(commit_hash, message)
            if auto_completed:
                result_data["auto_completed_tasks"] = auto_completed

            # MARKER_198.P1.9: Surface tasks whose allowed_paths overlap committed files
            try:
                _diff_result = subprocess.run(
                    ["git", "diff-tree", "--no-commit-id", "-r", "--name-only", commit_hash],
                    capture_output=True, text=True, cwd=str(git_root),
                )
                if _diff_result.returncode == 0:
                    _committed_files = [f.strip() for f in _diff_result.stdout.strip().split("\n") if f.strip()]
                    if _committed_files:
                        from src.orchestration.task_board import get_task_board as _get_tb
                        _board = _get_tb()
                        _matched = _board.find_tasks_by_changed_files(_committed_files)
                        if _matched:
                            result_data["matched_tasks"] = _matched
                            logger.info(f"[P1.9] {len(_matched)} tasks match committed files")
            except Exception as _e:
                logger.debug(f"[P1.9] Post-commit task match failed: {_e}")

            # MARKER_GIT_AUTO_PUSH: Auto-push to remote if requested
            if auto_push:
                push_result = self._git_push()
                if push_result["success"]:
                    result_data["status"] = "committed_and_pushed"
                    result_data["push"] = push_result["result"]
                else:
                    # Commit succeeded but push failed
                    result_data["push_error"] = push_result["error"]
                    result_data["status"] = "committed_push_failed"

            return {
                "success": True,
                "result": result_data,
                "error": None
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git command timed out", "result": None}
        except Exception as e:
            return {"success": False, "error": str(e), "result": None}

    def _update_digest_after_commit(self, commit_hash: str, message: str) -> Optional[str]:
        """
        MARKER_108_7_AUTO_DIGEST: Update project_digest.json after successful commit.

        NOTE (MARKER_142.FIX): The pre-commit hook already runs
        scripts/update_project_digest.py which handles full digest update
        (system status, git info, staging). This method now only does a
        lightweight JSON patch (commit hash + dirty flag) to avoid the
        double-write conflict that caused Errno 30 from worktrees.

        If even this lightweight write fails (e.g. read-only FS in worktree),
        it logs the error instead of silently swallowing it.
        """
        try:
            if not DIGEST_PATH.exists():
                return "digest file not found, skipped"

            with open(DIGEST_PATH, 'r') as f:
                digest = json.load(f)

            # Lightweight patch — only commit hash and dirty flag
            if "git" not in digest:
                digest["git"] = {}
            digest["git"]["commit"] = commit_hash
            digest["git"]["dirty"] = False
            digest["last_updated"] = datetime.now(timezone.utc).isoformat()

            # Write updated digest
            with open(DIGEST_PATH, 'w') as f:
                json.dump(digest, f, indent=2)

            return f"Updated: commit={commit_hash}, dirty=false"

        except OSError as e:
            # MARKER_142.FIX: Log instead of silently swallowing
            # Common in worktree context where data/ may be read-only
            import logging
            logging.getLogger("vetka.git").warning(
                f"Digest update skipped (OSError {e.errno}): {e}. "
                f"Pre-commit hook should have handled this."
            )
            return f"skipped: {e}"
        except Exception as e:
            import logging
            logging.getLogger("vetka.git").warning(f"Digest update failed: {e}")
            return f"skipped: {e}"

    def _auto_complete_tasks(self, commit_hash: str, message: str) -> Optional[list]:
        """
        MARKER_130.C17B: Auto-complete tasks mentioned in commit message.
        MARKER_191.1: Only closes tasks explicitly referenced via [task:tb_xxxx]
        or direct tb_xxxx ID. Title keyword matching removed (false positive risk).

        Called after successful commit to update TaskBoard.
        """
        try:
            from src.orchestration.task_board import get_task_board
            board = get_task_board()
            completed = board.auto_complete_by_commit(commit_hash, message)
            return completed if completed else None
        except Exception:
            # Don't fail commit if task completion fails
            return None

    def _git_push(self, remote: str = "origin", branch: str = None) -> Dict[str, Any]:
        """
        MARKER_GIT_AUTO_PUSH: Push commits to remote repository.

        Helper method for auto-push after commit.
        Returns dict with success, result, and error.
        """
        try:
            # Get current branch if not specified
            if not branch:
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                branch = result.stdout.strip() if result.returncode == 0 else "main"

            # Push to remote
            result = subprocess.run(
                ["git", "push", remote, branch],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "result": {
                        "status": "pushed",
                        "remote": remote,
                        "branch": branch
                    },
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr or result.stdout or "Push failed with unknown error",
                    "result": None
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git push command timed out", "result": None}
        except Exception as e:
            return {"success": False, "error": str(e), "result": None}
