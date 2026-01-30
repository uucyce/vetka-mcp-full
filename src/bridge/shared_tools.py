"""
VETKA Shared Tools - Unified tool implementations for MCP and OpenCode bridges.

This module contains all tool implementations that can be shared between:
- MCP Bridge (vetka_mcp_bridge.py) - for Claude Desktop/Code
- OpenCode Bridge (opencode/routes.py) - for VS Code/IDE integration

Architecture:
    VETKATool (ABC)
    ├── ReadTool      - Read-only operations (no side effects)
    │   ├── SemanticSearchTool    [UNIFY-002]
    │   ├── ReadFileTool          [UNIFY-003]
    │   ├── TreeStructureTool     [UNIFY-004]
    │   ├── HealthCheckTool       [UNIFY-005]
    │   ├── ListFilesTool         [UNIFY-006]
    │   ├── SearchFilesTool       [UNIFY-007]
    │   ├── MetricsTool           [UNIFY-008]
    │   └── KnowledgeGraphTool    [UNIFY-009]
    ├── WriteTool     - File/Git operations (Phase 95.4)
    └── ExecutionTool - LLM calls, tests (Phase 95.5)

Phase 95.3 - Bridge Unification
Created: 2026-01-26
Source: Extracted from vetka_mcp_bridge.py lines 611-765

@status: active
@phase: 96
@depends: httpx, abc, src.mcp.tools, src.memory
@used_by: src.bridge.__init__, vetka_mcp_bridge
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import httpx
import json


# =============================================================================
# CONFIGURATION
# =============================================================================

VETKA_BASE_URL = "http://localhost:5001"
VETKA_TIMEOUT = 30.0


# =============================================================================
# BASE CLASSES
# =============================================================================

class VETKATool(ABC):
    """
    Base class for all VETKA tools.

    Provides:
    - Async HTTP client for VETKA REST API
    - Standard execute() interface
    - Error handling patterns

    Args:
        client: Optional httpx.AsyncClient instance. If not provided,
                creates a new client with default VETKA configuration.
    """

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        """
        Initialize the tool with an optional HTTP client.

        Args:
            client: Pre-configured httpx.AsyncClient, or None to create one.
        """
        self._client = client
        self._owns_client = client is None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=VETKA_BASE_URL,
                timeout=VETKA_TIMEOUT,
                follow_redirects=True
            )
        return self._client

    async def close(self):
        """Close the HTTP client if we own it."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with the given arguments.

        Args:
            arguments: Tool-specific arguments dictionary.

        Returns:
            Result dictionary with tool-specific data.

        Raises:
            httpx.HTTPError: On HTTP communication errors.
            ValueError: On invalid arguments.
        """
        pass

    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """
        Validate tool arguments.

        Override in subclasses for custom validation.

        Args:
            arguments: Arguments to validate.

        Returns:
            Error message string if validation fails, None if valid.
        """
        return None


class ReadTool(VETKATool):
    """
    Base class for read-only tools.

    Read tools:
    - Do not modify state
    - Are safe to retry
    - Can be cached
    """
    pass


class WriteTool(VETKATool):
    """
    Base class for write tools.

    Write tools:
    - May modify files or state
    - Support dry_run mode
    - Create backups when appropriate
    """
    pass


class ExecutionTool(VETKATool):
    """
    Base class for execution tools.

    Execution tools:
    - Run external processes (tests, LLM calls)
    - May have side effects
    - Support timeout configuration
    """
    pass


# =============================================================================
# READ TOOLS - Phase 95.3
# =============================================================================

class SemanticSearchTool(ReadTool):
    """
    [UNIFY-002] Semantic search in VETKA knowledge base using Qdrant.

    Searches for concepts, ideas, or topics across all indexed documents
    using vector similarity search.

    Source: vetka_mcp_bridge.py lines 611-619

    Arguments:
        query (str): Semantic search query (e.g., 'authentication logic')
        limit (int): Max results to return (default: 10, max: 50)

    Returns:
        dict: {
            "results": [
                {
                    "content": str,
                    "score": float,
                    "metadata": {"file_path": str, ...}
                },
                ...
            ],
            "query": str,
            "total": int
        }
    """

    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """Validate search arguments."""
        query = arguments.get("query", "")
        if not query or not query.strip():
            return "Query cannot be empty"

        limit = arguments.get("limit", 10)
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            return "Limit must be an integer between 1 and 50"

        return None

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute semantic search.

        Args:
            arguments: {"query": str, "limit": int}

        Returns:
            Search results with scores and metadata.
        """
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)

        response = await self.client.get(
            "/api/search/semantic",
            params={"q": query, "limit": limit}
        )
        response.raise_for_status()

        data = response.json()
        return {
            "results": data.get("results", []),
            "query": query,
            "total": len(data.get("results", []))
        }


class ReadFileTool(ReadTool):
    """
    [UNIFY-003] Read file content from VETKA project.

    Returns full file content with line numbers. Supports any text file
    within the VETKA project directory.

    Source: vetka_mcp_bridge.py lines 621-628

    Arguments:
        file_path (str): Path to file (relative to project root)

    Returns:
        dict: {
            "content": str,      # File content with line numbers
            "file_path": str,    # Requested path
            "exists": bool,      # Whether file was found
            "error": str | None  # Error message if failed
        }
    """

    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """Validate file path argument."""
        file_path = arguments.get("file_path", "")
        if not file_path or not file_path.strip():
            return "file_path cannot be empty"

        # Basic path traversal check
        if ".." in file_path:
            return "Path traversal (..) is not allowed"

        return None

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read file content.

        Args:
            arguments: {"file_path": str}

        Returns:
            File content and metadata.
        """
        file_path = arguments.get("file_path", "")

        response = await self.client.post(
            "/api/files/read",
            json={"file_path": file_path}
        )
        response.raise_for_status()

        data = response.json()
        return {
            "content": data.get("content", ""),
            "file_path": file_path,
            "exists": data.get("exists", True),
            "error": data.get("error")
        }


class TreeStructureTool(ReadTool):
    """
    [UNIFY-004] Get VETKA 3D tree structure.

    Returns the hierarchical file/folder structure used by VETKA's 3D
    visualization. Supports summary or full tree output.

    Source: vetka_mcp_bridge.py lines 630-664

    Arguments:
        format (str): Output format - 'tree' for full, 'summary' for stats

    Returns:
        dict: {
            "tree": {...} | None,     # Full tree data (if format='tree')
            "summary": {...} | None,  # Stats (if format='summary')
            "format": str
        }
    """

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get tree structure.

        Args:
            arguments: {"format": "tree" | "summary"}

        Returns:
            Tree data or summary statistics.
        """
        format_type = arguments.get("format", "summary")

        response = await self.client.get("/api/tree/data")
        response.raise_for_status()

        data = response.json()
        tree_data = data.get("tree", {})
        nodes = tree_data.get("nodes", [])

        if format_type == "summary":
            # Count by type
            # FIX_101.5: API returns type="leaf" for files, not "file"
            file_count = sum(1 for n in nodes if n.get("type") == "leaf")
            folder_count = sum(1 for n in nodes if n.get("type") == "branch")

            return {
                "summary": {
                    "total_nodes": len(nodes),
                    "files": file_count,
                    "folders": folder_count,
                    "root": tree_data.get("name", "VETKA")
                },
                "tree": None,
                "format": "summary"
            }
        else:
            # Return full tree
            return {
                "tree": data,
                "summary": None,
                "format": "tree"
            }


class HealthCheckTool(ReadTool):
    """
    [UNIFY-005] Check VETKA server health and component status.

    Returns health information about VETKA server and its components
    (Qdrant, metrics, model router, etc.).

    Source: vetka_mcp_bridge.py lines 666-668

    Arguments:
        None

    Returns:
        dict: {
            "status": str,           # "healthy" | "degraded" | "unhealthy"
            "version": str,
            "phase": str,
            "components": {
                "component_name": bool,  # True if healthy
                ...
            }
        }
    """

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check VETKA health.

        Args:
            arguments: {} (no arguments required)

        Returns:
            Health status and component states.
        """
        response = await self.client.get("/api/health")
        response.raise_for_status()

        return response.json()


class ListFilesTool(ReadTool):
    """
    [UNIFY-006] List files in a directory or matching a pattern.

    Uses the tree endpoint with filtering to list files. Supports
    glob patterns for filtering.

    Source: vetka_mcp_bridge.py lines 670-701

    Arguments:
        path (str): Directory path to list (default: project root)
        pattern (str): Glob pattern to filter (e.g., '*.py')
        recursive (bool): List subdirectories recursively

    Returns:
        dict: {
            "files": [
                {"path": str, "name": str, "type": str},
                ...
            ],
            "total": int,
            "truncated": bool  # True if results were limited
        }
    """

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        List files in directory.

        Args:
            arguments: {"path": str, "pattern": str, "recursive": bool}

        Returns:
            List of files with metadata.
        """
        path = arguments.get("path", ".")
        pattern = arguments.get("pattern")
        # recursive = arguments.get("recursive", False)  # TODO: implement

        response = await self.client.get("/api/tree/data")
        response.raise_for_status()

        data = response.json()
        tree_data = data.get("tree", {})
        nodes = tree_data.get("nodes", [])

        # Filter to files only
        files = []
        for node in nodes:
            if node.get("type") != "file":
                continue

            file_path = node.get("metadata", {}).get("path", node.get("name", ""))

            # Apply pattern filter if specified
            if pattern and pattern not in file_path:
                continue

            # Apply path filter
            if path != "." and not file_path.startswith(path):
                continue

            files.append({
                "path": file_path,
                "name": node.get("name", ""),
                "type": "file"
            })

        # Limit results
        max_results = 50
        truncated = len(files) > max_results

        return {
            "files": files[:max_results],
            "total": len(files),
            "truncated": truncated
        }


class SearchFilesTool(ReadTool):
    """
    [UNIFY-007] Search for files by name or content pattern.

    Uses semantic search as the underlying implementation. Supports
    searching in filenames, content, or both.

    Source: vetka_mcp_bridge.py lines 703-714

    Arguments:
        query (str): Search query (filename or content pattern)
        search_type (str): 'filename', 'content', or 'both'
        limit (int): Max results (default: 20)

    Returns:
        dict: {
            "results": [
                {
                    "file_path": str,
                    "content_preview": str,
                    "score": float
                },
                ...
            ],
            "query": str,
            "total": int
        }
    """

    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """Validate search arguments."""
        query = arguments.get("query", "")
        if not query or not query.strip():
            return "Query cannot be empty"

        search_type = arguments.get("search_type", "both")
        if search_type not in ("filename", "content", "both"):
            return "search_type must be 'filename', 'content', or 'both'"

        return None

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search files by name or content.

        Args:
            arguments: {"query": str, "search_type": str, "limit": int}

        Returns:
            Search results with file paths and previews.
        """
        query = arguments.get("query", "")
        search_type = arguments.get("search_type", "both")
        limit = arguments.get("limit", 20)

        # Use semantic search endpoint
        # TODO: Add dedicated file search endpoint for better filename matching
        response = await self.client.get(
            "/api/search/semantic",
            params={"q": query, "limit": limit}
        )
        response.raise_for_status()

        data = response.json()
        results = []

        for item in data.get("results", []):
            metadata = item.get("metadata", {})
            results.append({
                "file_path": metadata.get("file_path", "unknown"),
                "content_preview": item.get("content", "")[:200],
                "score": item.get("score", 0.0)
            })

        return {
            "results": results,
            "query": query,
            "search_type": search_type,
            "total": len(results)
        }


class MetricsTool(ReadTool):
    """
    [UNIFY-008] Get VETKA metrics and analytics.

    Returns system performance metrics, query statistics, and usage data.
    Supports dashboard, agents, or combined view.

    Source: vetka_mcp_bridge.py lines 716-737

    Arguments:
        metric_type (str): 'dashboard', 'agents', or 'all'

    Returns:
        dict: {
            "dashboard": {...} | None,  # Dashboard metrics
            "agents": {...} | None,     # Agent metrics
            "metric_type": str
        }
    """

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get VETKA metrics.

        Args:
            arguments: {"metric_type": str}

        Returns:
            Metrics data based on requested type.
        """
        metric_type = arguments.get("metric_type", "dashboard")

        if metric_type == "dashboard":
            response = await self.client.get("/api/metrics/dashboard")
            response.raise_for_status()
            return {
                "dashboard": response.json(),
                "agents": None,
                "metric_type": "dashboard"
            }

        elif metric_type == "agents":
            response = await self.client.get("/api/metrics/agents")
            response.raise_for_status()
            return {
                "dashboard": None,
                "agents": response.json(),
                "metric_type": "agents"
            }

        else:  # "all"
            dashboard_resp = await self.client.get("/api/metrics/dashboard")
            agents_resp = await self.client.get("/api/metrics/agents")

            return {
                "dashboard": dashboard_resp.json() if dashboard_resp.status_code == 200 else None,
                "agents": agents_resp.json() if agents_resp.status_code == 200 else None,
                "metric_type": "all"
            }


class KnowledgeGraphTool(ReadTool):
    """
    [UNIFY-009] Get VETKA knowledge graph structure.

    Returns the knowledge graph showing relationships between code entities,
    concepts, and documents. Useful for understanding architecture.

    Source: vetka_mcp_bridge.py lines 739-765

    Arguments:
        format (str): 'json' for full data, 'summary' for stats

    Returns:
        dict: {
            "nodes": [...] | None,    # Graph nodes (if format='json')
            "edges": [...] | None,    # Graph edges (if format='json')
            "summary": {...} | None,  # Stats (if format='summary')
            "format": str
        }
    """

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get knowledge graph.

        Args:
            arguments: {"format": str}

        Returns:
            Knowledge graph data or summary.
        """
        format_type = arguments.get("format", "summary")

        response = await self.client.get("/api/tree/knowledge-graph")
        response.raise_for_status()

        data = response.json()

        if format_type == "summary":
            nodes = data.get("nodes", [])
            edges = data.get("edges", [])

            return {
                "summary": {
                    "nodes_count": len(nodes),
                    "edges_count": len(edges)
                },
                "nodes": None,
                "edges": None,
                "format": "summary"
            }
        else:
            return {
                "nodes": data.get("nodes", []),
                "edges": data.get("edges", []),
                "summary": None,
                "format": "json"
            }


# =============================================================================
# COLLABORATION TOOLS - Phase 95.4 (UNIFY-010)
# =============================================================================

class GroupMessagesTool(ReadTool):
    """
    [UNIFY-010] Read messages from VETKA group chat.

    Retrieves recent messages from a specified group chat. Useful for
    understanding conversation context or seeing what other agents wrote.

    Source: vetka_mcp_bridge.py lines 837-845

    Arguments:
        group_id (str): Group chat ID (default: MCP log group)
        limit (int): Maximum messages to return (default: 10, max: 50)

    Returns:
        dict: {
            "messages": [
                {
                    "id": str,
                    "sender_id": str,
                    "content": str,
                    "timestamp": str,
                    "metadata": {...}
                },
                ...
            ],
            "group_id": str,
            "total": int
        }
    """

    # Default MCP log group ID
    DEFAULT_GROUP_ID = "mcp-log-group"

    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """Validate group messages arguments."""
        limit = arguments.get("limit", 10)
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            return "Limit must be an integer between 1 and 50"
        return None

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read group messages.

        Args:
            arguments: {"group_id": str, "limit": int}

        Returns:
            List of messages from the group.
        """
        group_id = arguments.get("group_id", self.DEFAULT_GROUP_ID)
        limit = arguments.get("limit", 10)

        response = await self.client.get(
            f"/api/groups/{group_id}/messages",
            params={"limit": limit}
        )
        response.raise_for_status()

        data = response.json()
        messages = data.get("messages", [])

        return {
            "messages": messages,
            "group_id": group_id,
            "total": len(messages)
        }


# =============================================================================
# WRITE TOOLS - Phase 95.4 (UNIFY-011 through UNIFY-013)
# =============================================================================

class SharedEditFileTool(WriteTool):
    """
    [UNIFY-011] Edit or create a file with backup.

    Creates a backup of existing files before modification. Supports
    write (replace) and append modes. Default is dry_run=true (preview only).

    Source: vetka_mcp_bridge.py lines 771-782
    Internal: src/mcp/tools/edit_file_tool.py

    Arguments:
        path (str): File path relative to project root
        content (str): New file content
        mode (str): 'write' (replace) or 'append' (default: 'write')
        create_dirs (bool): Create parent directories if missing (default: false)
        dry_run (bool): Preview only, no changes (default: true)

    Returns:
        dict: {
            "success": bool,
            "result": {
                "status": str,       # "dry_run" | "written"
                "path": str,
                "mode": str,
                "bytes_written": int | None,
                "backup": str | None  # Backup path if created
            },
            "error": str | None
        }
    """

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        """Initialize with lazy-loaded internal tool."""
        super().__init__(client)
        self._internal_tool = None

    @property
    def internal_tool(self):
        """Lazy-load internal EditFileTool to avoid circular imports."""
        if self._internal_tool is None:
            from src.mcp.tools.edit_file_tool import EditFileTool
            self._internal_tool = EditFileTool()
        return self._internal_tool

    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """Validate using internal tool's validator."""
        return self.internal_tool.validate_arguments(arguments)

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute file edit operation.

        Args:
            arguments: {"path": str, "content": str, "mode": str, "create_dirs": bool, "dry_run": bool}

        Returns:
            Result dict with status, path, and backup info.
        """
        # Validate first
        error = self.validate_arguments(arguments)
        if error:
            return {"success": False, "error": error, "result": None}

        # Execute synchronously (internal tool is sync)
        return self.internal_tool.execute(arguments)


class SharedGitCommitTool(WriteTool):
    """
    [UNIFY-012] Create a git commit with optional file staging.

    Stages specified files (or all changed files) and creates a commit.
    Requires approval. Default is dry_run=true (preview only).

    Source: vetka_mcp_bridge.py lines 784-795
    Internal: src/mcp/tools/git_tool.py (GitCommitTool)

    Arguments:
        message (str): Commit message (min 5 characters)
        files (list[str]): Files to stage (empty = all changed files)
        dry_run (bool): Preview only, no commit (default: true)

    Returns:
        dict: {
            "success": bool,
            "result": {
                "status": str,     # "dry_run" | "committed"
                "hash": str,       # Commit hash (if committed)
                "message": str,
                "files": list[str] # Files that were/would be staged
            },
            "error": str | None
        }
    """

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        """Initialize with lazy-loaded internal tool."""
        super().__init__(client)
        self._internal_tool = None

    @property
    def internal_tool(self):
        """Lazy-load internal GitCommitTool to avoid circular imports."""
        if self._internal_tool is None:
            from src.mcp.tools.git_tool import GitCommitTool
            self._internal_tool = GitCommitTool()
        return self._internal_tool

    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """Validate using internal tool's validator."""
        return self.internal_tool.validate_arguments(arguments)

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute git commit operation.

        Args:
            arguments: {"message": str, "files": list[str], "dry_run": bool}

        Returns:
            Result dict with commit status and hash.
        """
        # Validate first
        error = self.validate_arguments(arguments)
        if error:
            return {"success": False, "error": error, "result": None}

        # Execute synchronously (internal tool is sync)
        return self.internal_tool.execute(arguments)


class SharedGitStatusTool(ReadTool):
    """
    [UNIFY-013] Get git status showing modified, staged, and untracked files.

    Read-only operation that shows current repository state including
    branch name, last commit, and file changes.

    Source: vetka_mcp_bridge.py lines 797-802
    Internal: src/mcp/tools/git_tool.py (GitStatusTool)

    Arguments:
        None required

    Returns:
        dict: {
            "success": bool,
            "result": {
                "branch": str,           # Current branch name
                "last_commit": str,      # Last commit (hash + message)
                "files": {
                    "modified": list[str],   # Modified but unstaged
                    "staged": list[str],     # Staged for commit
                    "untracked": list[str]   # Untracked files
                },
                "clean": bool  # True if no changes
            },
            "error": str | None
        }
    """

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        """Initialize with lazy-loaded internal tool."""
        super().__init__(client)
        self._internal_tool = None

    @property
    def internal_tool(self):
        """Lazy-load internal GitStatusTool to avoid circular imports."""
        if self._internal_tool is None:
            from src.mcp.tools.git_tool import GitStatusTool
            self._internal_tool = GitStatusTool()
        return self._internal_tool

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get git status.

        Args:
            arguments: {} (no arguments required)

        Returns:
            Git status with branch, commit, and file changes.
        """
        # Execute synchronously (internal tool is sync)
        return self.internal_tool.execute(arguments)


# =============================================================================
# EXECUTION TOOLS - Phase 95.4 (UNIFY-014 through UNIFY-016)
# =============================================================================

class SharedRunTestsTool(ExecutionTool):
    """
    [UNIFY-014] Run pytest tests with output capture.

    Executes pytest tests with configurable path, pattern, and timeout.
    Returns stdout, stderr, and exit code.

    Source: vetka_mcp_bridge.py lines 804-815
    Internal: src/mcp/tools/run_tests_tool.py

    Arguments:
        test_path (str): Path to test file or directory (default: 'tests/')
        pattern (str): Test name pattern for -k flag (optional)
        verbose (bool): Verbose output (default: true)
        timeout (int): Timeout in seconds (default: 60, max: 300)

    Returns:
        dict: {
            "success": bool,
            "result": {
                "passed": bool,
                "returncode": int,
                "stdout": str,
                "stderr": str
            },
            "error": str | None
        }
    """

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        """Initialize with lazy-loaded internal tool."""
        super().__init__(client)
        self._internal_tool = None

    @property
    def internal_tool(self):
        """Lazy-load internal RunTestsTool to avoid circular imports."""
        if self._internal_tool is None:
            from src.mcp.tools.run_tests_tool import RunTestsTool
            self._internal_tool = RunTestsTool()
        return self._internal_tool

    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """Validate using internal tool's validator."""
        return self.internal_tool.validate_arguments(arguments)

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run pytest tests.

        Args:
            arguments: {"test_path": str, "pattern": str, "verbose": bool, "timeout": int}

        Returns:
            Test results with stdout/stderr.
        """
        # Validate first
        error = self.validate_arguments(arguments)
        if error:
            return {"success": False, "error": error, "result": None}

        # Execute synchronously (internal tool is sync)
        return self.internal_tool.execute(arguments)


class SharedCameraFocusTool(ExecutionTool):
    """
    [UNIFY-015] Move 3D camera to focus on a specific target.

    Controls the VETKA 3D visualization camera to focus on files, branches,
    or provide an overview. Requires active VETKA UI session.

    Source: vetka_mcp_bridge.py lines 817-822
    Internal: src/mcp/tools/camera_tool.py

    Arguments:
        target (str): File path, branch name, or 'overview'
        zoom (str): 'close', 'medium', or 'far' (default: 'medium')
        highlight (bool): Highlight target with glow (default: true)
        animate (bool): Smooth camera animation (default: true)

    Returns:
        dict: {
            "success": bool,
            "message": str,  # Description of camera action
            "error": str | None
        }
    """

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        """Initialize with lazy-loaded internal tool."""
        super().__init__(client)
        self._internal_tool = None

    @property
    def internal_tool(self):
        """Lazy-load internal CameraControlTool to avoid circular imports."""
        if self._internal_tool is None:
            from src.mcp.tools.camera_tool import CameraControlTool
            self._internal_tool = CameraControlTool()
        return self._internal_tool

    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """Validate camera focus arguments."""
        target = arguments.get("target", "")
        if not target or not target.strip():
            return "Target is required (file path, branch name, or 'overview')"

        zoom = arguments.get("zoom", "medium")
        if zoom not in ("close", "medium", "far"):
            return "Zoom must be 'close', 'medium', or 'far'"

        return None

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Focus camera on target.

        Args:
            arguments: {"target": str, "zoom": str, "highlight": bool, "animate": bool}

        Returns:
            Result with success status and message.
        """
        # Validate first
        error = self.validate_arguments(arguments)
        if error:
            return {"success": False, "error": error}

        # Execute synchronously (internal tool is sync)
        return self.internal_tool.execute(arguments)


class SharedCallModelTool(ExecutionTool):
    """
    [UNIFY-016] Call any LLM model through VETKA infrastructure.

    Routes requests to appropriate providers (Grok, GPT, Claude, Gemini,
    Ollama, OpenRouter). Supports function calling for compatible models.

    Phase 55.2: Now supports inject_context for automatic VETKA context injection!

    Source: vetka_mcp_bridge.py lines 824-835
    Internal: src/mcp/tools/llm_call_tool.py

    Arguments:
        model (str): Model identifier (e.g., 'grok-4', 'gpt-4o', 'claude-opus-4-5')
        messages (list[dict]): Chat messages [{"role": str, "content": str}, ...]
        temperature (float): Sampling temperature 0.0-2.0 (default: 0.7)
        max_tokens (int): Maximum tokens to generate (default: 4096)
        tools (list[dict]): Optional function calling tools (OpenAI format)
        inject_context (dict): Phase 55.2 - Auto-inject VETKA context:
            - files: List of file paths to read and inject
            - session_id: MCPStateManager session ID
            - include_prefs: Include Engram user preferences
            - include_cam: Include CAM active nodes
            - semantic_query: Semantic search query
            - compress: Apply ELISION compression (default: true)

    Returns:
        dict: {
            "success": bool,
            "result": {
                "content": str,      # Model response text
                "model": str,        # Actual model used
                "provider": str,     # Provider name
                "usage": {...},      # Token usage stats
                "tool_calls": [...]  # Function calls (if any)
            },
            "error": str | None
        }
    """

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        """Initialize with lazy-loaded internal tool."""
        super().__init__(client)
        self._internal_tool = None

    @property
    def internal_tool(self):
        """Lazy-load internal LLMCallTool to avoid circular imports."""
        if self._internal_tool is None:
            from src.mcp.tools.llm_call_tool import LLMCallTool
            self._internal_tool = LLMCallTool()
        return self._internal_tool

    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """Validate LLM call arguments."""
        model = arguments.get("model", "")
        if not model or not model.strip():
            return "Model name is required"

        messages = arguments.get("messages", [])
        if not messages or not isinstance(messages, list):
            return "Messages must be a non-empty array"

        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                return f"Message {i} must be an object with role and content"
            if "role" not in msg or "content" not in msg:
                return f"Message {i} missing role or content"

        temperature = arguments.get("temperature", 0.7)
        if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2:
            return "Temperature must be between 0.0 and 2.0"

        return None

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call LLM model.

        Args:
            arguments: {"model": str, "messages": list, "temperature": float, "max_tokens": int, "tools": list}

        Returns:
            Model response with content and usage stats.
        """
        # Validate first
        error = self.validate_arguments(arguments)
        if error:
            return {"success": False, "error": error, "result": None}

        # Execute synchronously (internal tool is sync)
        return self.internal_tool.execute(arguments)


# =============================================================================
# MEMORY TOOLS - Phase 95.5 (UNIFY-017 through UNIFY-019)
# =============================================================================

class MemoryTool(VETKATool):
    """
    Base class for memory-related tools.

    Memory tools provide access to VETKA's multi-layer memory system:
    - Engram (RAM cache for hot preferences)
    - Qdrant (vector DB for cold storage)
    - ELISION compression for token savings
    - CAM (Context-Aware Memory) integration
    """
    pass


class ConversationContextTool(MemoryTool):
    """
    [UNIFY-017] Get ELISION-compressed conversation context.

    Retrieves conversation history and optionally applies ELISION compression
    for 40-60% token savings. Useful for getting relevant conversation history
    before responding.

    Source: vetka_mcp_bridge.py lines 851-899

    Arguments:
        group_id (str): Group ID for group chat (optional)
        max_messages (int): Maximum messages to retrieve (default: 20)
        compress (bool): Apply ELISION compression (default: True)

    Returns:
        dict: {
            "context": str | list,         # Compressed or raw messages
            "original_messages": int,       # Number of messages retrieved
            "compression_applied": bool,    # Whether compression was applied
            "savings_estimate": str | None  # Estimated token savings (if compressed)
        }
    """

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get conversation context with optional ELISION compression.

        Args:
            arguments: {"group_id": str, "max_messages": int, "compress": bool}

        Returns:
            Conversation context (compressed or raw).
        """
        group_id = arguments.get("group_id")
        max_messages = arguments.get("max_messages", 20)
        compress = arguments.get("compress", True)

        try:
            # Get messages from group or recent chat
            if group_id:
                response = await self.client.get(
                    f"/api/groups/{group_id}/messages",
                    params={"limit": max_messages}
                )
            else:
                # Use default chat history endpoint
                response = await self.client.get(
                    "/api/chat/history",
                    params={"limit": max_messages}
                )

            if response.status_code != 200:
                return {
                    "error": f"Failed to get messages: HTTP {response.status_code}",
                    "context": None,
                    "original_messages": 0,
                    "compression_applied": False
                }

            messages = response.json().get("messages", [])

            # Apply ELISION compression if requested
            if compress and messages:
                try:
                    from src.memory.elision import compress_context
                    context_data = {"messages": messages}
                    compressed = compress_context(context_data)
                    return {
                        "context": compressed,
                        "original_messages": len(messages),
                        "compression_applied": True,
                        "savings_estimate": "40-60% tokens"
                    }
                except ImportError as e:
                    # ELISION module not available, return raw
                    return {
                        "context": messages,
                        "original_messages": len(messages),
                        "compression_applied": False,
                        "error": f"ELISION compression unavailable: {e}"
                    }
                except Exception as e:
                    # Compression failed, return raw
                    return {
                        "context": messages,
                        "original_messages": len(messages),
                        "compression_applied": False,
                        "error": f"Compression failed: {e}"
                    }
            else:
                return {
                    "context": messages,
                    "original_messages": len(messages),
                    "compression_applied": False,
                    "savings_estimate": None
                }

        except Exception as e:
            return {
                "error": f"Error getting context: {e}",
                "context": None,
                "original_messages": 0,
                "compression_applied": False
            }


class UserPreferencesTool(MemoryTool):
    """
    [UNIFY-018] Get user preferences from Engram memory.

    Retrieves user preferences from VETKA's hybrid RAM/Qdrant storage.
    Hot preferences (frequently accessed) are served from RAM cache for O(1) lookup.
    Cold preferences are retrieved from Qdrant with semantic search.

    Source: vetka_mcp_bridge.py lines 901-930
    Internal: src/memory/engram_user_memory.py

    Arguments:
        user_id (str): User identifier (default: 'danila')
        category (str): Preference category or 'all' (default: 'all')
                       Categories: viewport_patterns, tree_structure,
                       project_highlights, communication_style,
                       temporal_patterns, tool_usage_patterns

    Returns:
        dict: {
            "user_id": str,
            "category": str,
            "preferences": dict,  # Preference data
            "source": str         # "engram_ram_cache" or "qdrant"
        }
    """

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        """Initialize with lazy-loaded memory components."""
        super().__init__(client)
        self._memory = None
        self._qdrant = None

    def _init_memory(self) -> bool:
        """Lazy-load Engram memory components."""
        if self._memory is not None:
            return True

        try:
            from src.memory.engram_user_memory import EngramUserMemory
            from src.memory.qdrant_client import get_qdrant_client

            qdrant_wrapper = get_qdrant_client()
            if qdrant_wrapper and hasattr(qdrant_wrapper, 'client'):
                self._qdrant = qdrant_wrapper.client
            self._memory = EngramUserMemory(self._qdrant)
            return True
        except ImportError:
            return False
        except Exception:
            return False

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get user preferences from Engram memory.

        Args:
            arguments: {"user_id": str, "category": str}

        Returns:
            User preferences with source information.
        """
        user_id = arguments.get("user_id", "danila")
        category = arguments.get("category", "all")

        try:
            # Initialize memory lazily
            if not self._init_memory():
                return {
                    "error": "Engram memory not available (module not initialized)",
                    "user_id": user_id,
                    "category": category,
                    "preferences": {},
                    "source": "unavailable"
                }

            # Get preferences
            if category == "all":
                prefs_obj = self._memory.get_user_preferences(user_id)
                prefs = prefs_obj.to_dict() if prefs_obj else {}
            else:
                # Get specific category
                prefs_obj = self._memory.get_user_preferences(user_id)
                if prefs_obj:
                    category_obj = getattr(prefs_obj, category, None)
                    prefs = category_obj.__dict__ if category_obj else {}
                else:
                    prefs = {}

            # Determine source
            source = "engram_ram_cache" if self._memory.ram_cache.get(user_id) else "qdrant"

            return {
                "user_id": user_id,
                "category": category,
                "preferences": prefs if prefs else {},
                "source": source
            }

        except Exception as e:
            return {
                "error": f"Error getting preferences: {e}",
                "user_id": user_id,
                "category": category,
                "preferences": {},
                "source": "error"
            }


class MemorySummaryTool(MemoryTool):
    """
    [UNIFY-019] Get CAM (Context-Aware Memory) and Elisium compression summary.

    Returns information about VETKA's memory system including:
    - Active memory nodes
    - Compression statistics
    - Age distribution
    - Quality scores

    Source: vetka_mcp_bridge.py lines 932-964
    Internal: src/memory/compression.py

    Arguments:
        include_stats (bool): Include compression statistics (default: True)
        include_nodes (bool): Include memory node details (default: False)

    Returns:
        dict: {
            "memory_system": str,           # "CAM + Elisium"
            "stats": {
                "compression_schedule": [...],  # Age-based compression config
                "active_nodes": int,
                "archived_nodes": int,
                "total_embeddings": int
            } | None,
            "nodes": [...] | None  # Top 10 nodes (if include_nodes=True)
        }
    """

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        """Initialize with lazy-loaded compression components."""
        super().__init__(client)
        self._compressor = None

    def _init_compressor(self) -> bool:
        """Lazy-load memory compression components."""
        if self._compressor is not None:
            return True

        try:
            from src.memory.compression import MemoryCompression
            self._compressor = MemoryCompression()
            return True
        except ImportError:
            return False
        except Exception:
            return False

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get CAM + Elisium memory summary.

        Args:
            arguments: {"include_stats": bool, "include_nodes": bool}

        Returns:
            Memory system summary with optional stats and nodes.
        """
        include_stats = arguments.get("include_stats", True)
        include_nodes = arguments.get("include_nodes", False)

        try:
            # Build base result
            result = {
                "memory_system": "CAM + Elisium",
                "stats": None,
                "nodes": None
            }

            if include_stats:
                # Compression schedule (static config)
                result["stats"] = {
                    "compression_schedule": [
                        {"days": "0-6", "dim": 768, "quality": "100%"},
                        {"days": "7-29", "dim": 384, "quality": "90%"},
                        {"days": "30-89", "dim": 256, "quality": "80%"},
                        {"days": "90+", "dim": 64, "quality": "60%"}
                    ],
                    "active_nodes": "N/A",
                    "archived_nodes": "N/A",
                    "total_embeddings": "N/A"
                }

                # Try to get live stats from compressor
                if self._init_compressor():
                    try:
                        quality_report = self._compressor.get_quality_degradation_report()
                        result["stats"]["active_nodes"] = quality_report.get("nodes_tracked", 0)
                        result["stats"]["avg_quality"] = round(quality_report.get("avg_quality", 1.0), 2)
                        result["stats"]["quality_distribution"] = quality_report.get("quality_distribution", {})
                    except Exception:
                        pass  # Keep N/A values if stats retrieval fails

            if include_nodes:
                # Return top nodes from quality tracker
                if self._init_compressor() and hasattr(self._compressor, '_quality_tracker'):
                    nodes_list = []
                    for path, quality in list(self._compressor._quality_tracker.items())[:10]:
                        nodes_list.append({
                            "path": path,
                            "quality_score": round(quality, 2)
                        })
                    result["nodes"] = nodes_list
                else:
                    result["nodes"] = []

            return result

        except Exception as e:
            return {
                "error": f"Error getting memory summary: {e}",
                "memory_system": "CAM + Elisium",
                "stats": None,
                "nodes": None
            }


# =============================================================================
# RESULT FORMATTING HELPERS
# =============================================================================

def format_semantic_results(data: Dict[str, Any]) -> str:
    """
    Format semantic search results for display.

    Args:
        data: Result from SemanticSearchTool.execute()

    Returns:
        Formatted string for human-readable output.
    """
    results = data.get("results", [])
    if not results:
        return "No results found."

    formatted = f"Found {len(results)} results:\n\n"
    for i, result in enumerate(results, 1):
        content = result.get("content", "")
        score = result.get("score", 0.0)
        metadata = result.get("metadata", {})
        file_path = metadata.get("file_path", "unknown")

        formatted += f"{i}. [{file_path}] (score: {score:.2f})\n"
        formatted += f"   {content[:200]}...\n\n"

    return formatted


def format_tree_summary(data: Dict[str, Any]) -> str:
    """
    Format tree summary for display.

    Args:
        data: Result from TreeStructureTool.execute()

    Returns:
        Formatted string for human-readable output.
    """
    if data.get("format") == "summary":
        summary = data.get("summary", {})
        return (
            f"VETKA Tree Summary\n"
            f"==================\n"
            f"Total nodes: {summary.get('total_nodes', 0)}\n"
            f"Files: {summary.get('files', 0)}\n"
            f"Folders: {summary.get('folders', 0)}\n"
            f"Root: {summary.get('root', 'VETKA')}\n"
            f"\nUse format='tree' to see full structure."
        )
    else:
        return json.dumps(data.get("tree", {}), indent=2, ensure_ascii=False)


def format_health_status(data: Dict[str, Any]) -> str:
    """
    Format health check results for display.

    Args:
        data: Result from HealthCheckTool.execute()

    Returns:
        Formatted string for human-readable output.
    """
    status = data.get("status", "unknown")
    version = data.get("version", "unknown")
    phase = data.get("phase", "unknown")
    components = data.get("components", {})

    formatted = (
        f"VETKA Health Status\n"
        f"===================\n"
        f"Status: {status}\n"
        f"Version: {version}\n"
        f"Phase: {phase}\n\n"
        f"Components:\n"
    )

    for comp_name, comp_status in components.items():
        status_icon = "[OK]" if comp_status else "[FAIL]"
        formatted += f"  {status_icon} {comp_name}\n"

    return formatted


def format_file_list(data: Dict[str, Any]) -> str:
    """
    Format file list for display.

    Args:
        data: Result from ListFilesTool.execute()

    Returns:
        Formatted string for human-readable output.
    """
    files = data.get("files", [])
    total = data.get("total", 0)
    truncated = data.get("truncated", False)

    header = f"Found {total} files"
    if truncated:
        header += f" (showing first {len(files)})"

    file_list = "\n".join([f"- {f.get('path', f.get('name', 'unknown'))}" for f in files])

    return f"{header}\n\n{file_list}"


def format_metrics(data: Dict[str, Any]) -> str:
    """
    Format metrics for display.

    Args:
        data: Result from MetricsTool.execute()

    Returns:
        Formatted string or JSON for human-readable output.
    """
    metric_type = data.get("metric_type", "unknown")

    if metric_type == "all":
        combined = {}
        if data.get("dashboard"):
            combined["dashboard"] = data["dashboard"]
        if data.get("agents"):
            combined["agents"] = data["agents"]
        return json.dumps(combined, indent=2, ensure_ascii=False)

    elif metric_type == "dashboard" and data.get("dashboard"):
        return json.dumps(data["dashboard"], indent=2, ensure_ascii=False)

    elif metric_type == "agents" and data.get("agents"):
        return json.dumps(data["agents"], indent=2, ensure_ascii=False)

    return "No metrics available."


def format_knowledge_graph_summary(data: Dict[str, Any]) -> str:
    """
    Format knowledge graph for display.

    Args:
        data: Result from KnowledgeGraphTool.execute()

    Returns:
        Formatted string for human-readable output.
    """
    if data.get("format") == "summary":
        summary = data.get("summary", {})
        return (
            f"VETKA Knowledge Graph Summary\n"
            f"============================\n"
            f"Nodes: {summary.get('nodes_count', 0)}\n"
            f"Edges: {summary.get('edges_count', 0)}\n"
            f"\nUse format='json' to see full graph data."
        )
    else:
        graph = {
            "nodes": data.get("nodes", []),
            "edges": data.get("edges", [])
        }
        return json.dumps(graph, indent=2, ensure_ascii=False)


def format_group_messages(data: Dict[str, Any]) -> str:
    """
    Format group messages for display.

    Args:
        data: Result from GroupMessagesTool.execute()

    Returns:
        Formatted string for human-readable output.
    """
    messages = data.get("messages", [])
    group_id = data.get("group_id", "unknown")
    total = data.get("total", 0)

    if not messages:
        return f"No messages in group {group_id}"

    formatted = f"Group: {group_id} ({total} messages)\n"
    formatted += "=" * 40 + "\n\n"

    for msg in messages:
        sender = msg.get("sender_id", "unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")

        # Truncate long content
        if len(content) > 200:
            content = content[:200] + "..."

        formatted += f"[{timestamp}] {sender}:\n{content}\n\n"

    return formatted


def format_write_result(tool_name: str, data: Dict[str, Any]) -> str:
    """
    Format write tool result for display.

    Args:
        tool_name: Name of the write tool
        data: Result from write tool execute()

    Returns:
        Formatted string for human-readable output.
    """
    success = data.get("success", False)
    error = data.get("error")
    result = data.get("result", {})

    if not success:
        return f"[FAILED] {tool_name}: {error}"

    status = result.get("status", "unknown")

    if status == "dry_run":
        return (
            f"[DRY RUN] {tool_name}\n"
            f"Path: {result.get('path', 'N/A')}\n"
            f"Mode: {result.get('mode', 'write')}\n"
            f"Content length: {result.get('content_length', 0)} chars\n"
            f"Would create dirs: {result.get('would_create_dirs', False)}\n"
            f"\nSet dry_run=false to apply changes."
        )

    elif status == "written":
        backup_info = f"\nBackup: {result.get('backup')}" if result.get("backup") else ""
        return (
            f"[SUCCESS] {tool_name}\n"
            f"Path: {result.get('path', 'N/A')}\n"
            f"Mode: {result.get('mode', 'write')}\n"
            f"Bytes written: {result.get('bytes_written', 0)}"
            f"{backup_info}"
        )

    elif status == "committed":
        return (
            f"[COMMITTED] {tool_name}\n"
            f"Hash: {result.get('hash', 'N/A')}\n"
            f"Message: {result.get('message', 'N/A')}"
        )

    return json.dumps(data, indent=2, ensure_ascii=False)


def format_git_status(data: Dict[str, Any]) -> str:
    """
    Format git status for display.

    Args:
        data: Result from SharedGitStatusTool.execute()

    Returns:
        Formatted string for human-readable output.
    """
    if not data.get("success"):
        return f"[ERROR] Git status failed: {data.get('error', 'unknown error')}"

    result = data.get("result", {})
    branch = result.get("branch", "unknown")
    last_commit = result.get("last_commit", "unknown")
    files = result.get("files", {})
    clean = result.get("clean", True)

    formatted = (
        f"Git Status\n"
        f"==========\n"
        f"Branch: {branch}\n"
        f"Last commit: {last_commit}\n\n"
    )

    if clean:
        formatted += "Working tree clean - no changes\n"
    else:
        modified = files.get("modified", [])
        staged = files.get("staged", [])
        untracked = files.get("untracked", [])

        if staged:
            formatted += f"Staged ({len(staged)}):\n"
            for f in staged[:10]:
                formatted += f"  + {f}\n"
            if len(staged) > 10:
                formatted += f"  ... and {len(staged) - 10} more\n"

        if modified:
            formatted += f"\nModified ({len(modified)}):\n"
            for f in modified[:10]:
                formatted += f"  M {f}\n"
            if len(modified) > 10:
                formatted += f"  ... and {len(modified) - 10} more\n"

        if untracked:
            formatted += f"\nUntracked ({len(untracked)}):\n"
            for f in untracked[:10]:
                formatted += f"  ? {f}\n"
            if len(untracked) > 10:
                formatted += f"  ... and {len(untracked) - 10} more\n"

    return formatted


def format_test_result(data: Dict[str, Any]) -> str:
    """
    Format test result for display.

    Args:
        data: Result from SharedRunTestsTool.execute()

    Returns:
        Formatted string for human-readable output.
    """
    if not data.get("success"):
        error = data.get("error", "unknown error")
        return f"[ERROR] Test execution failed: {error}"

    result = data.get("result", {})
    passed = result.get("passed", False)
    returncode = result.get("returncode", -1)
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")

    status_icon = "[PASSED]" if passed else "[FAILED]"

    formatted = f"{status_icon} Tests (exit code: {returncode})\n"
    formatted += "=" * 40 + "\n\n"

    if stdout:
        formatted += "STDOUT:\n"
        formatted += stdout + "\n"

    if stderr:
        formatted += "\nSTDERR:\n"
        formatted += stderr + "\n"

    return formatted


def format_camera_result(data: Dict[str, Any], arguments: Dict[str, Any]) -> str:
    """
    Format camera focus result for display.

    Args:
        data: Result from SharedCameraFocusTool.execute()
        arguments: Original tool arguments

    Returns:
        Formatted string for human-readable output.
    """
    if not data.get("success"):
        return f"[ERROR] Camera focus failed: {data.get('error', 'unknown error')}"

    target = arguments.get("target", "unknown")
    zoom = arguments.get("zoom", "medium")
    highlight = arguments.get("highlight", True)

    return (
        f"[CAMERA] Focused on: {target}\n"
        f"Zoom: {zoom}\n"
        f"Highlight: {'enabled' if highlight else 'disabled'}"
    )


def format_llm_result(data: Dict[str, Any]) -> str:
    """
    Format LLM call result for display.

    Args:
        data: Result from SharedCallModelTool.execute()

    Returns:
        Formatted string for human-readable output.
    """
    if not data.get("success"):
        return f"[ERROR] LLM call failed: {data.get('error', 'unknown error')}"

    result = data.get("result", {})
    content = result.get("content", "")
    model = result.get("model", "unknown")
    provider = result.get("provider", "unknown")
    usage = result.get("usage", {})
    tool_calls = result.get("tool_calls")

    formatted = f"[{provider}/{model}]\n"
    formatted += "-" * 40 + "\n"
    formatted += content + "\n"

    if usage:
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        formatted += f"\n[Tokens: {prompt_tokens} -> {completion_tokens} (total: {total_tokens})]"

    if tool_calls:
        formatted += f"\n\n[Tool calls: {len(tool_calls)}]"
        for tc in tool_calls[:3]:
            func_name = tc.get("function", {}).get("name", "unknown")
            formatted += f"\n  - {func_name}"

    return formatted


# =============================================================================
# MEMORY RESULT FORMATTING HELPERS - Phase 95.5
# =============================================================================

def format_context_result(data: Dict[str, Any]) -> str:
    """
    Format conversation context for display.

    Args:
        data: Result from ConversationContextTool.execute()

    Returns:
        Formatted string for human-readable output.
    """
    if data.get("error"):
        return f"Error: {data['error']}"

    compressed = data.get("compression_applied", False)
    msg_count = data.get("original_messages", 0)
    savings = data.get("savings_estimate", "")

    header = f"Conversation Context ({msg_count} messages"
    if compressed:
        header += f", ELISION compressed ~{savings}"
    header += ")\n"
    header += "=" * 40 + "\n\n"

    context = data.get("context")
    if isinstance(context, dict):
        # Compressed result
        return header + json.dumps(context, indent=2, ensure_ascii=False)
    elif isinstance(context, list):
        # Raw messages
        formatted = header
        for i, msg in enumerate(context[:10], 1):  # Limit display
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:100]
            formatted += f"{i}. [{role}] {content}...\n"
        if len(context) > 10:
            formatted += f"\n... and {len(context) - 10} more messages"
        return formatted
    else:
        return header + str(context)


def format_preferences_result(data: Dict[str, Any]) -> str:
    """
    Format user preferences for display.

    Args:
        data: Result from UserPreferencesTool.execute()

    Returns:
        Formatted string for human-readable output.
    """
    if data.get("error"):
        return f"Error: {data['error']}"

    user_id = data.get("user_id", "unknown")
    category = data.get("category", "all")
    source = data.get("source", "unknown")
    prefs = data.get("preferences", {})

    header = (
        f"User Preferences: {user_id}\n"
        f"{'=' * 40}\n"
        f"Category: {category}\n"
        f"Source: {source}\n\n"
    )

    if not prefs:
        return header + "No preferences found."

    return header + json.dumps(prefs, indent=2, ensure_ascii=False)


def format_memory_summary(data: Dict[str, Any]) -> str:
    """
    Format memory summary for display.

    Args:
        data: Result from MemorySummaryTool.execute()

    Returns:
        Formatted string for human-readable output.
    """
    if data.get("error"):
        return f"Error: {data['error']}"

    system = data.get("memory_system", "Unknown")
    stats = data.get("stats")
    nodes = data.get("nodes")

    formatted = (
        f"VETKA Memory Summary\n"
        f"{'=' * 40}\n"
        f"System: {system}\n\n"
    )

    if stats:
        formatted += "Compression Schedule:\n"
        for sched in stats.get("compression_schedule", []):
            formatted += f"  - {sched['days']} days: {sched['dim']}D ({sched['quality']})\n"

        formatted += f"\nActive nodes: {stats.get('active_nodes', 'N/A')}\n"
        formatted += f"Archived nodes: {stats.get('archived_nodes', 'N/A')}\n"

        if stats.get("avg_quality"):
            formatted += f"Avg quality: {stats['avg_quality']}\n"

    if nodes:
        formatted += f"\nTop {len(nodes)} Memory Nodes:\n"
        for node in nodes:
            formatted += f"  - {node['path']}: quality={node['quality_score']}\n"

    return formatted


# =============================================================================
# TOOL REGISTRY
# =============================================================================

# Map tool names to classes for dynamic instantiation
TOOL_REGISTRY: Dict[str, type] = {
    # Read tools (Phase 95.3)
    "vetka_search_semantic": SemanticSearchTool,
    "vetka_read_file": ReadFileTool,
    "vetka_get_tree": TreeStructureTool,
    "vetka_health": HealthCheckTool,
    "vetka_list_files": ListFilesTool,
    "vetka_search_files": SearchFilesTool,
    "vetka_get_metrics": MetricsTool,
    "vetka_get_knowledge_graph": KnowledgeGraphTool,

    # Collaboration tools (Phase 95.4 - UNIFY-010)
    "vetka_read_group_messages": GroupMessagesTool,

    # Write tools (Phase 95.4 - UNIFY-011 to UNIFY-013)
    "vetka_edit_file": SharedEditFileTool,
    "vetka_git_commit": SharedGitCommitTool,
    "vetka_git_status": SharedGitStatusTool,

    # Execution tools (Phase 95.4 - UNIFY-014 to UNIFY-016)
    "vetka_run_tests": SharedRunTestsTool,
    "vetka_camera_focus": SharedCameraFocusTool,
    "vetka_call_model": SharedCallModelTool,

    # Memory tools (Phase 95.5 - UNIFY-017 to UNIFY-019)
    "vetka_get_conversation_context": ConversationContextTool,
    "vetka_get_user_preferences": UserPreferencesTool,
    "vetka_get_memory_summary": MemorySummaryTool,
}


def get_tool(name: str, client: Optional[httpx.AsyncClient] = None) -> Optional[VETKATool]:
    """
    Get a tool instance by name.

    Args:
        name: Tool name (e.g., "vetka_search_semantic")
        client: Optional HTTP client to use

    Returns:
        Tool instance or None if not found.
    """
    tool_class = TOOL_REGISTRY.get(name)
    if tool_class:
        return tool_class(client)
    return None


def list_tools() -> List[str]:
    """
    Get list of available tool names.

    Returns:
        List of registered tool names.
    """
    return list(TOOL_REGISTRY.keys())
