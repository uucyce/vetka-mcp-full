"""
VETKA Git Tool.

Git operations with approval flow for agent safety. Provides safe read operations
(status, diff, log) and approval-gated write operations (add, commit, push).

@status: active
@phase: 96
@depends: subprocess, pathlib, approval_manager
@used_by: src/tools/__init__, src/agents/

Usage:
    from src.tools.git_tool import GitTool, GitResult

    git = GitTool()

    # Safe operations (no approval needed)
    status = await git.status()
    diff = await git.diff()

    # Approval operations (require user approval)
    result = await git.request_add(["src/main.py"], agent_id="dev-001")
    # result.needs_approval == True
"""

import subprocess
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


class GitOperationType(Enum):
    """Types of git operations"""
    STATUS = "status"
    DIFF = "diff"
    LOG = "log"
    BRANCHES = "branches"
    ADD = "add"
    COMMIT = "commit"
    PUSH = "push"
    CHECKOUT = "checkout"
    CREATE_BRANCH = "create_branch"


@dataclass
class GitResult:
    """Result of a git operation"""
    success: bool
    operation: str
    output: str
    error: Optional[str] = None
    needs_approval: bool = False
    approval_request_id: Optional[str] = None
    diff_preview: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "operation": self.operation,
            "output": self.output,
            "error": self.error,
            "needs_approval": self.needs_approval,
            "approval_request_id": self.approval_request_id,
            "diff_preview": self.diff_preview,
            "metadata": self.metadata
        }


class GitTool:
    """
    Git operations with approval flow.

    Safe operations: status, diff, log, branches
    Approval operations: add, commit, push, checkout
    """

    # Protected branches that cannot be directly modified
    PROTECTED_BRANCHES = {"main", "master", "production", "develop"}

    # Prefix for agent branches
    AGENT_BRANCH_PREFIX = "agent/"

    def __init__(
        self,
        project_root: Optional[Path] = None,
        approval_manager=None
    ):
        self.project_root = Path(project_root) if project_root else PROJECT_ROOT
        self.approval_manager = approval_manager

        # Verify git repository
        if not (self.project_root / ".git").exists():
            raise ValueError(f"Not a git repository: {self.project_root}")

    def _run_git(
        self,
        args: List[str],
        timeout: int = 30,
        capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """Run git command and return result"""
        cmd = ["git"] + args
        return subprocess.run(
            cmd,
            cwd=str(self.project_root),
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )

    # ========================================================================
    # SAFE OPERATIONS (no approval needed)
    # ========================================================================

    async def status(self) -> GitResult:
        """Get git status"""
        try:
            result = self._run_git(["status", "--porcelain"])

            # Parse status output
            files = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    status_code = line[:2]
                    filepath = line[3:]
                    files.append({"status": status_code, "path": filepath})

            return GitResult(
                success=result.returncode == 0,
                operation="status",
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                metadata={"files": files, "count": len(files)}
            )
        except subprocess.TimeoutExpired:
            return GitResult(
                success=False,
                operation="status",
                output="",
                error="Git status timeout"
            )
        except Exception as e:
            return GitResult(
                success=False,
                operation="status",
                output="",
                error=str(e)
            )

    async def diff(
        self,
        staged: bool = False,
        path: Optional[str] = None
    ) -> GitResult:
        """Get git diff"""
        try:
            args = ["diff"]
            if staged:
                args.append("--staged")
            if path:
                args.append("--")
                args.append(path)

            result = self._run_git(args)

            return GitResult(
                success=result.returncode == 0,
                operation="diff",
                output=result.stdout[:50000],  # Limit output
                error=result.stderr if result.returncode != 0 else None,
                metadata={"staged": staged, "path": path}
            )
        except subprocess.TimeoutExpired:
            return GitResult(
                success=False,
                operation="diff",
                output="",
                error="Git diff timeout"
            )
        except Exception as e:
            return GitResult(
                success=False,
                operation="diff",
                output="",
                error=str(e)
            )

    async def log(
        self,
        count: int = 10,
        oneline: bool = True
    ) -> GitResult:
        """Get git log"""
        try:
            args = ["log", f"-{count}"]
            if oneline:
                args.append("--oneline")

            result = self._run_git(args)

            # Parse log output
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    if oneline:
                        parts = line.split(' ', 1)
                        commits.append({
                            "hash": parts[0],
                            "message": parts[1] if len(parts) > 1 else ""
                        })

            return GitResult(
                success=result.returncode == 0,
                operation="log",
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                metadata={"commits": commits, "count": len(commits)}
            )
        except Exception as e:
            return GitResult(
                success=False,
                operation="log",
                output="",
                error=str(e)
            )

    async def branches(self) -> GitResult:
        """List branches"""
        try:
            result = self._run_git(["branch", "-a"])

            branches = []
            current = None
            for line in result.stdout.strip().split('\n'):
                if line:
                    if line.startswith('*'):
                        current = line[2:].strip()
                        branches.append({"name": current, "current": True})
                    else:
                        branches.append({"name": line.strip(), "current": False})

            return GitResult(
                success=result.returncode == 0,
                operation="branches",
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                metadata={"branches": branches, "current": current}
            )
        except Exception as e:
            return GitResult(
                success=False,
                operation="branches",
                output="",
                error=str(e)
            )

    async def current_branch(self) -> str:
        """Get current branch name"""
        try:
            result = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
            return result.stdout.strip()
        except Exception:
            return "unknown"

    # ========================================================================
    # APPROVAL OPERATIONS (require user approval)
    # ========================================================================

    async def request_add(
        self,
        files: List[str],
        agent_id: str
    ) -> GitResult:
        """
        Request to add files to staging.
        Returns approval request if approval_manager is set.
        """
        try:
            # Validate files exist
            valid_files = []
            for f in files:
                path = self.project_root / f
                if path.exists():
                    valid_files.append(f)

            if not valid_files:
                return GitResult(
                    success=False,
                    operation="add",
                    output="",
                    error="No valid files to add"
                )

            # Get diff preview for approval
            diff_preview = ""
            for f in valid_files[:5]:  # Limit preview to 5 files
                result = self._run_git(["diff", "--", f])
                diff_preview += f"=== {f} ===\n{result.stdout[:2000]}\n"

            if self.approval_manager:
                # Create approval request
                request_id = await self.approval_manager.create_request(
                    operation_type="git_add",
                    agent_id=agent_id,
                    description=f"Add {len(valid_files)} file(s) to staging",
                    diff_preview=diff_preview,
                    metadata={"files": valid_files}
                )

                return GitResult(
                    success=True,
                    operation="add",
                    output=f"Approval requested for adding {len(valid_files)} file(s)",
                    needs_approval=True,
                    approval_request_id=request_id,
                    diff_preview=diff_preview,
                    metadata={"files": valid_files}
                )
            else:
                # No approval manager - execute directly (for testing)
                result = self._run_git(["add"] + valid_files)
                return GitResult(
                    success=result.returncode == 0,
                    operation="add",
                    output=result.stdout or f"Added {len(valid_files)} file(s)",
                    error=result.stderr if result.returncode != 0 else None,
                    metadata={"files": valid_files}
                )

        except Exception as e:
            return GitResult(
                success=False,
                operation="add",
                output="",
                error=str(e)
            )

    async def request_commit(
        self,
        message: str,
        agent_id: str
    ) -> GitResult:
        """
        Request to commit staged changes.
        Returns approval request if approval_manager is set.
        """
        try:
            # Check if there are staged changes
            status = await self.status()
            staged_files = [
                f for f in status.metadata.get("files", [])
                if f["status"][0] in ['A', 'M', 'D', 'R']  # Added, Modified, Deleted, Renamed
            ]

            if not staged_files:
                return GitResult(
                    success=False,
                    operation="commit",
                    output="",
                    error="No staged changes to commit"
                )

            # Get staged diff for preview
            diff_result = await self.diff(staged=True)
            diff_preview = diff_result.output[:5000]

            if self.approval_manager:
                request_id = await self.approval_manager.create_request(
                    operation_type="git_commit",
                    agent_id=agent_id,
                    description=f"Commit: {message[:100]}",
                    diff_preview=diff_preview,
                    metadata={"message": message, "files_count": len(staged_files)}
                )

                return GitResult(
                    success=True,
                    operation="commit",
                    output=f"Approval requested for commit: {message[:50]}...",
                    needs_approval=True,
                    approval_request_id=request_id,
                    diff_preview=diff_preview,
                    metadata={"message": message, "staged_files": len(staged_files)}
                )
            else:
                # Execute directly
                result = self._run_git(["commit", "-m", message])
                return GitResult(
                    success=result.returncode == 0,
                    operation="commit",
                    output=result.stdout,
                    error=result.stderr if result.returncode != 0 else None,
                    metadata={"message": message}
                )

        except Exception as e:
            return GitResult(
                success=False,
                operation="commit",
                output="",
                error=str(e)
            )

    async def request_push(
        self,
        agent_id: str,
        branch: Optional[str] = None
    ) -> GitResult:
        """
        Request to push to remote.
        Returns approval request if approval_manager is set.
        """
        try:
            current = await self.current_branch()
            target_branch = branch or current

            # Check if pushing to protected branch
            if target_branch in self.PROTECTED_BRANCHES:
                return GitResult(
                    success=False,
                    operation="push",
                    output="",
                    error=f"Cannot push directly to protected branch: {target_branch}"
                )

            # Get commits to push
            result = self._run_git(["log", "origin/main..HEAD", "--oneline"])
            commits_to_push = result.stdout.strip()

            if self.approval_manager:
                request_id = await self.approval_manager.create_request(
                    operation_type="git_push",
                    agent_id=agent_id,
                    description=f"Push to {target_branch}",
                    diff_preview=commits_to_push,
                    metadata={"branch": target_branch}
                )

                return GitResult(
                    success=True,
                    operation="push",
                    output=f"Approval requested for push to {target_branch}",
                    needs_approval=True,
                    approval_request_id=request_id,
                    diff_preview=commits_to_push,
                    metadata={"branch": target_branch}
                )
            else:
                result = self._run_git(["push", "-u", "origin", target_branch])
                return GitResult(
                    success=result.returncode == 0,
                    operation="push",
                    output=result.stdout,
                    error=result.stderr if result.returncode != 0 else None,
                    metadata={"branch": target_branch}
                )

        except Exception as e:
            return GitResult(
                success=False,
                operation="push",
                output="",
                error=str(e)
            )

    async def create_agent_branch(
        self,
        branch_name: str,
        agent_id: str
    ) -> GitResult:
        """
        Create a new agent branch.
        Agent branches must start with 'agent/' prefix.
        """
        try:
            # Ensure branch name has agent prefix
            if not branch_name.startswith(self.AGENT_BRANCH_PREFIX):
                branch_name = f"{self.AGENT_BRANCH_PREFIX}{branch_name}"

            # Create and checkout branch
            result = self._run_git(["checkout", "-b", branch_name])

            return GitResult(
                success=result.returncode == 0,
                operation="create_branch",
                output=result.stdout or f"Created branch: {branch_name}",
                error=result.stderr if result.returncode != 0 else None,
                metadata={"branch": branch_name, "agent_id": agent_id}
            )
        except Exception as e:
            return GitResult(
                success=False,
                operation="create_branch",
                output="",
                error=str(e)
            )

    # ========================================================================
    # EXECUTE APPROVED OPERATIONS
    # ========================================================================

    async def execute_approved_add(self, files: List[str]) -> GitResult:
        """Execute add after approval"""
        try:
            result = self._run_git(["add"] + files)
            return GitResult(
                success=result.returncode == 0,
                operation="add",
                output=result.stdout or f"Added {len(files)} file(s)",
                error=result.stderr if result.returncode != 0 else None,
                metadata={"files": files}
            )
        except Exception as e:
            return GitResult(
                success=False,
                operation="add",
                output="",
                error=str(e)
            )

    async def execute_approved_commit(self, message: str) -> GitResult:
        """Execute commit after approval"""
        try:
            result = self._run_git(["commit", "-m", message])
            return GitResult(
                success=result.returncode == 0,
                operation="commit",
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                metadata={"message": message}
            )
        except Exception as e:
            return GitResult(
                success=False,
                operation="commit",
                output="",
                error=str(e)
            )

    async def execute_approved_push(self, branch: str) -> GitResult:
        """Execute push after approval"""
        try:
            result = self._run_git(["push", "-u", "origin", branch])
            return GitResult(
                success=result.returncode == 0,
                operation="push",
                output=result.stdout + result.stderr,
                error=None if result.returncode == 0 else result.stderr,
                metadata={"branch": branch}
            )
        except Exception as e:
            return GitResult(
                success=False,
                operation="push",
                output="",
                error=str(e)
            )


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'GitTool',
    'GitResult',
    'GitOperationType',
    'PROJECT_ROOT'
]
