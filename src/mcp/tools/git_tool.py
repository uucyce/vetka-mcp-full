"""
Git operations tools - status (read-only) and commit (requires approval).

@status: active
@phase: 96
@depends: base_tool, subprocess, pathlib
@used_by: mcp_server, stdio_server
"""
import subprocess
from pathlib import Path
from typing import Any, Dict
from .base_tool import BaseMCPTool

PROJECT_ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


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

            return {
                "success": True,
                "result": {
                    "status": "committed",
                    "hash": commit_hash,
                    "message": message
                },
                "error": None
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git command timed out", "result": None}
        except Exception as e:
            return {"success": False, "error": str(e), "result": None}
