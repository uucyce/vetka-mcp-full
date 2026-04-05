"""
ELYSIA Tools — Weaviate elysia-ai wrapper for tool selection.
Status: DORMANT (zero callers since Phase 75.2)

MARKER_198.P1.4: This wrapper misuses ELYSIA for filesystem/git operations
(read_file, write_file, git_commit) — these are deterministic ops that don't
benefit from LLM-driven decision trees.

ELYSIA's real value = Weaviate collection retrieval (semantic queries against
stored tool descriptions, clip metadata, agent memory). This is NOT currently
needed but is the planned path for REFLEX Signal 9 (see ARCHITECTURE_198).

Do NOT delete — revive when Weaviate collections store tool/artifact data.
See: docs/73_ph/THE_LEGENDARY_ELISYA_MISHAP.md for full history.
See: task 198.P3.2 for REFLEX Signal 9 integration plan.

@file elysia_tools.py
@status DORMANT
@phase Phase 75.2 — Hybrid Architecture
@calledBy langgraph_nodes.py (dev_qa_parallel_node)
@lastAudit 2026-01-20

This module integrates Weaviate's Elysia framework for automatic code tool selection.
IMPORTANT: tree = Tree(optimize=False) — NO DSPy overhead!

Elysia handles CODE tools (read, write, test, git):
- read_file(path) — Read file content
- write_file(path, content) — Write to file
- run_tests(path) — Run pytest
- git_commit(message) — Git commit

VETKA tools (3D, viewport, search) are handled by CAM Tool Memory (Phase 75.1).

Architecture:
    User Query (code-related)
         ↓
    Elysia Tree (decision agent)
         ↓
    @tool decorated functions
         ↓
    Result → LangGraph Dev/QA node
"""

import os
import subprocess
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger("VETKA_ELYSIA")

# ═══════════════════════════════════════════════════════════════════
# [PHASE75.2-1] Elysia Import with Graceful Fallback
# ═══════════════════════════════════════════════════════════════════

try:
    from elysia import tool, Tree
    ELYSIA_AVAILABLE = True
    logger.info("[Elysia] elysia-ai library loaded successfully")
except ImportError:
    ELYSIA_AVAILABLE = False
    logger.warning("[Elysia] elysia-ai not installed. Code tool selection disabled.")
    logger.warning("[Elysia] Install with: pip install elysia-ai")

    # Dummy decorators for graceful degradation
    def tool(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    class Tree:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, query: str) -> str:
            return f"[Elysia not available] Query: {query}"

        async def arun(self, query: str) -> str:
            return self(query)


# ═══════════════════════════════════════════════════════════════════
# [PHASE75.2-2] Elysia Tree Configuration
# IMPORTANT: optimize=False — без DSPy overhead!
# ═══════════════════════════════════════════════════════════════════

# Initialize tree WITHOUT DSPy optimization (saves latency + cost)
# The decision agent still works, just doesn't use DSPy prompting
_elysia_tree: Optional[Tree] = None


def get_elysia_tree() -> Tree:
    """
    Get or create Elysia Tree singleton.

    Returns:
        Tree instance configured for VETKA code tools
    """
    global _elysia_tree

    if _elysia_tree is None:
        if ELYSIA_AVAILABLE:
            # CRITICAL: optimize=False disables DSPy prompt optimization
            # This significantly reduces latency while keeping tool selection
            _elysia_tree = Tree(optimize=False)
            logger.info("[Elysia] Tree initialized (optimize=False)")
        else:
            _elysia_tree = Tree()
            logger.warning("[Elysia] Using dummy Tree (library not installed)")

    return _elysia_tree


# Get tree for tool registration
tree = get_elysia_tree()


# ═══════════════════════════════════════════════════════════════════
# [PHASE75.2-3] Code Tools with @tool Decorator
# These tools are for CODE operations only.
# VETKA/3D tools go through CAM Tool Memory (Phase 75.1).
# ═══════════════════════════════════════════════════════════════════

# Project root detection
def _get_project_root() -> Path:
    """Get VETKA project root."""
    # Try environment variable first
    if os.getenv("VETKA_PROJECT_ROOT"):
        return Path(os.getenv("VETKA_PROJECT_ROOT"))

    # Default to current working directory
    cwd = Path.cwd()

    # Walk up to find pyproject.toml or setup.py
    for parent in [cwd] + list(cwd.parents):
        if (parent / "pyproject.toml").exists() or (parent / "setup.py").exists():
            return parent
        if (parent / "requirements.txt").exists():
            return parent

    return cwd


PROJECT_ROOT = _get_project_root()


@tool(tree=tree)
def read_file(path: str) -> str:
    """
    Read file content from the VETKA project.

    Use this tool when you need to examine code, configuration, or documentation.
    CAM activation: High when user is in close-up viewport or has pinned this file.

    Args:
        path: Relative or absolute path to file

    Returns:
        File content as string, or error message
    """
    try:
        # Resolve path
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = PROJECT_ROOT / path

        if not file_path.exists():
            return f"[ERROR] File not found: {path}"

        if not file_path.is_file():
            return f"[ERROR] Not a file: {path}"

        # Read with size limit (100KB max)
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        if len(content) > 100_000:
            content = content[:100_000] + "\n\n... [truncated at 100KB]"

        logger.info(f"[Elysia read_file] Read {len(content)} chars from {path}")
        return content

    except Exception as e:
        logger.error(f"[Elysia read_file] Error: {e}")
        return f"[ERROR] Failed to read {path}: {str(e)}"


@tool(tree=tree)
def write_file(path: str, content: str) -> str:
    """
    Write content to a file in the VETKA project.

    Use this tool to create or modify code files.
    Creates parent directories if they don't exist.
    CAM activation: High after successful read_file on same path.

    Args:
        path: Relative or absolute path to file
        content: Content to write

    Returns:
        Success message or error
    """
    try:
        # Resolve path
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = PROJECT_ROOT / path

        # Security check: must be within project
        try:
            file_path.resolve().relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            return f"[ERROR] Path outside project: {path}"

        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        file_path.write_text(content, encoding='utf-8')

        logger.info(f"[Elysia write_file] Wrote {len(content)} chars to {path}")
        return f"[SUCCESS] Wrote {len(content)} characters to {path}"

    except Exception as e:
        logger.error(f"[Elysia write_file] Error: {e}")
        return f"[ERROR] Failed to write {path}: {str(e)}"


@tool(tree=tree)
def run_tests(path: Optional[str] = None, verbose: bool = False) -> str:
    """
    Run pytest tests for the VETKA project.

    Use this tool to verify code changes or check test coverage.
    CAM activation: High after write_file operations.

    Args:
        path: Optional path to specific test file or directory
        verbose: If True, show detailed output

    Returns:
        Test results summary
    """
    try:
        cmd = ["python", "-m", "pytest"]

        if path:
            test_path = Path(path)
            if not test_path.is_absolute():
                test_path = PROJECT_ROOT / path
            cmd.append(str(test_path))
        else:
            # Default: run all tests in tests/ directory
            cmd.append(str(PROJECT_ROOT / "tests"))

        # Add flags
        cmd.extend(["-q", "--tb=short"])
        if verbose:
            cmd.append("-v")

        # Run with timeout
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        output = result.stdout
        if result.stderr:
            output += f"\n\nSTDERR:\n{result.stderr}"

        # Truncate if too long
        if len(output) > 10_000:
            output = output[:10_000] + "\n\n... [truncated]"

        status = "PASSED" if result.returncode == 0 else "FAILED"
        logger.info(f"[Elysia run_tests] {status} (return code: {result.returncode})")

        return f"[TESTS {status}]\n{output}"

    except subprocess.TimeoutExpired:
        logger.error("[Elysia run_tests] Timeout after 5 minutes")
        return "[ERROR] Tests timed out after 5 minutes"

    except Exception as e:
        logger.error(f"[Elysia run_tests] Error: {e}")
        return f"[ERROR] Failed to run tests: {str(e)}"


@tool(tree=tree)
def git_status() -> str:
    """
    Get current git status of the VETKA project.

    Use this tool to check what files have been modified before committing.
    CAM activation: Medium, increases before git_commit.

    Returns:
        Git status output
    """
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout or "(no changes)"

        # Also get current branch
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=10
        )
        branch = branch_result.stdout.strip() or "unknown"

        logger.info(f"[Elysia git_status] Branch: {branch}")
        return f"[GIT STATUS] Branch: {branch}\n\n{output}"

    except Exception as e:
        logger.error(f"[Elysia git_status] Error: {e}")
        return f"[ERROR] Git status failed: {str(e)}"


@tool(tree=tree)
def git_commit(message: str, files: Optional[List[str]] = None) -> str:
    """
    Create a git commit with staged changes.

    Use this tool after making code changes that should be saved.
    If files are specified, only those files are staged.
    If no files specified, commits all staged changes.
    CAM activation: High after successful write_file + run_tests.

    Args:
        message: Commit message
        files: Optional list of files to stage and commit

    Returns:
        Commit result or error
    """
    try:
        # Stage files
        if files:
            for f in files:
                file_path = Path(f)
                if not file_path.is_absolute():
                    file_path = PROJECT_ROOT / f
                subprocess.run(
                    ["git", "add", str(file_path)],
                    cwd=str(PROJECT_ROOT),
                    check=True,
                    timeout=30
                )
            logger.info(f"[Elysia git_commit] Staged {len(files)} files")
        else:
            # Check if there are staged changes
            status = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=30
            )
            if not status.stdout.strip():
                return "[WARNING] No staged changes to commit. Use files parameter or 'git add' first."

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            logger.info(f"[Elysia git_commit] Success: {message[:50]}...")
            return f"[COMMIT SUCCESS]\n{result.stdout}"
        else:
            logger.warning(f"[Elysia git_commit] Failed: {result.stderr}")
            return f"[COMMIT FAILED]\n{result.stderr}"

    except subprocess.CalledProcessError as e:
        logger.error(f"[Elysia git_commit] CalledProcessError: {e}")
        return f"[ERROR] Git operation failed: {str(e)}"

    except Exception as e:
        logger.error(f"[Elysia git_commit] Error: {e}")
        return f"[ERROR] Commit failed: {str(e)}"


# ═══════════════════════════════════════════════════════════════════
# [PHASE75.2-4] Entry Point for LangGraph Integration
# ═══════════════════════════════════════════════════════════════════

async def execute_code_task(query: str) -> str:
    """
    Execute a code-related task using Elysia tool selection.

    This is the main entry point called from dev_qa_parallel_node.
    Elysia's decision agent analyzes the query and selects appropriate tool(s).

    Args:
        query: Natural language query about code operations

    Returns:
        Tool execution result
    """
    if not ELYSIA_AVAILABLE:
        logger.warning("[Elysia] Library not available, returning query as-is")
        return f"[Elysia unavailable] Query: {query}"

    try:
        tree = get_elysia_tree()

        # Execute with Elysia decision tree
        # The tree will analyze the query and call appropriate tool(s)
        result = await tree.arun(query)

        logger.info(f"[Elysia execute_code_task] Completed for query: {query[:50]}...")
        return result

    except Exception as e:
        logger.error(f"[Elysia execute_code_task] Error: {e}")
        return f"[ERROR] Elysia execution failed: {str(e)}"


def execute_code_task_sync(query: str) -> str:
    """
    Synchronous wrapper for execute_code_task.

    Use this when async is not available.

    Args:
        query: Natural language query

    Returns:
        Tool execution result
    """
    import asyncio

    async def _run():
        return await execute_code_task(query)

    try:
        # Try to get running loop
        try:
            loop = asyncio.get_running_loop()
            # Already in async context - use thread pool
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _run())
                return future.result(timeout=120)
        except RuntimeError:
            # No running loop - safe to use asyncio.run
            return asyncio.run(_run())

    except Exception as e:
        logger.error(f"[Elysia sync] Error: {e}")
        return f"[ERROR] Sync execution failed: {str(e)}"


# ═══════════════════════════════════════════════════════════════════
# [PHASE75.2-5] Utility Functions
# ═══════════════════════════════════════════════════════════════════

def get_available_tools() -> List[str]:
    """Get list of available Elysia code tools."""
    return [
        'read_file',
        'write_file',
        'run_tests',
        'git_status',
        'git_commit',
    ]


def is_elysia_available() -> bool:
    """Check if Elysia library is available."""
    return ELYSIA_AVAILABLE


def get_elysia_stats() -> Dict[str, Any]:
    """Get Elysia integration statistics."""
    return {
        'available': ELYSIA_AVAILABLE,
        'tools_count': len(get_available_tools()),
        'tools': get_available_tools(),
        'project_root': str(PROJECT_ROOT),
        'optimize': False,  # Always False for performance
    }


# ═══════════════════════════════════════════════════════════════════
# [PHASE75.2-6] Direct Tool Access (bypass Elysia for specific calls)
# ═══════════════════════════════════════════════════════════════════

class ElysiaToolsDirect:
    """
    Direct access to Elysia tools without decision tree.

    Use when you know exactly which tool to call.
    Bypasses Elysia's decision agent for lower latency.
    """

    @staticmethod
    def read(path: str) -> str:
        """Direct read_file call."""
        return read_file(path)

    @staticmethod
    def write(path: str, content: str) -> str:
        """Direct write_file call."""
        return write_file(path, content)

    @staticmethod
    def test(path: Optional[str] = None) -> str:
        """Direct run_tests call."""
        return run_tests(path)

    @staticmethod
    def status() -> str:
        """Direct git_status call."""
        return git_status()

    @staticmethod
    def commit(message: str, files: Optional[List[str]] = None) -> str:
        """Direct git_commit call."""
        return git_commit(message, files)


# Export direct tools instance
elysia_direct = ElysiaToolsDirect()


# ═══════════════════════════════════════════════════════════════════
# Module Exports
# ═══════════════════════════════════════════════════════════════════

__all__ = [
    # Main entry points
    'execute_code_task',
    'execute_code_task_sync',
    'get_elysia_tree',

    # Tools (for direct import)
    'read_file',
    'write_file',
    'run_tests',
    'git_status',
    'git_commit',

    # Direct access
    'elysia_direct',
    'ElysiaToolsDirect',

    # Utilities
    'get_available_tools',
    'is_elysia_available',
    'get_elysia_stats',

    # Constants
    'ELYSIA_AVAILABLE',
    'PROJECT_ROOT',
]
