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
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from .base_tool import BaseMCPTool

PROJECT_ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
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
        message = arguments["message"]
        files = arguments.get("files", [])
        dry_run = arguments.get("dry_run", True)
        auto_push = arguments.get("auto_push", False)  # MARKER_GIT_AUTO_PUSH: Auto-push after commit

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

        try:
            # Stage files
            if files:
                for f in files:
                    result = subprocess.run(
                        ["git", "add", f],
                        cwd=str(PROJECT_ROOT),
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode != 0:
                        return {"success": False, "error": f"Failed to stage {f}: {result.stderr}", "result": None}
            else:
                result = subprocess.run(
                    ["git", "add", "-A"],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    return {"success": False, "error": f"Failed to stage files: {result.stderr}", "result": None}

            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                if "nothing to commit" in result.stdout.lower() or "nothing to commit" in result.stderr.lower():
                    return {"success": False, "error": "Nothing to commit", "result": None}
                return {"success": False, "error": result.stderr or result.stdout, "result": None}

            # Get commit hash
            commit_hash = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(PROJECT_ROOT),
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

        This is the "breaking news" pattern - agents reading digest will see
        the latest commit immediately, enabling context-aware collaboration.

        Updates:
        - git.commit: new hash
        - git.dirty: false
        - last_updated: now
        - Extracts phase from commit message if present (e.g., "Phase 109.1: ...")
        """
        try:
            if not DIGEST_PATH.exists():
                return None

            with open(DIGEST_PATH, 'r') as f:
                digest = json.load(f)

            # Update git section
            if "git" not in digest:
                digest["git"] = {}
            digest["git"]["commit"] = commit_hash
            digest["git"]["dirty"] = False

            # Update timestamp
            digest["last_updated"] = datetime.now(timezone.utc).isoformat()

            # Extract phase from commit message if present
            # Pattern: "Phase 109.1: ..." or "Phase 108.7 - ..."
            import re
            phase_match = re.search(r'Phase\s+(\d+)\.?(\d*)', message, re.IGNORECASE)
            if phase_match:
                phase_num = int(phase_match.group(1))
                subphase = phase_match.group(2) or None

                # Add to recent commits in summary
                commit_entry = f"Phase {phase_num}"
                if subphase:
                    commit_entry += f".{subphase}"
                commit_entry += f": {message[:50]}..."

                # Add to key_achievements if not already there
                if "summary" in digest and "key_achievements" in digest["summary"]:
                    achievements = digest["summary"]["key_achievements"]
                    # Prepend new achievement (breaking news at top!)
                    new_achievement = f"[{commit_hash}] {commit_entry}"
                    if new_achievement not in achievements:
                        achievements.insert(0, new_achievement)
                        # Keep max 10 achievements
                        digest["summary"]["key_achievements"] = achievements[:10]

            # Write updated digest
            with open(DIGEST_PATH, 'w') as f:
                json.dump(digest, f, indent=2)

            return f"Updated: commit={commit_hash}, dirty=false"

        except Exception as e:
            # Don't fail commit if digest update fails
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
