"""
VETKA MCP Tools Registry for Group Chat.

Registers MCP bridge tools (from src.bridge.shared_tools) with the global ToolRegistry
so they can be used by agents in group chat contexts.

Tools registered:
- vetka_search_semantic: Semantic search in VETKA knowledge base
- vetka_camera_focus: Control 3D camera visualization
- get_tree_context: Get VETKA 3D tree structure

@status: active
@phase: 96
@depends: src.tools.base_tool, src.bridge.shared_tools
@used_by: src.tools.__init__, src.agents, src.services.group_chat_manager
"""

from typing import Any, Dict
from src.tools.base_tool import BaseTool, ToolDefinition, ToolResult, PermissionLevel, registry
from src.bridge.shared_tools import (
    SharedCameraFocusTool,
    TreeStructureTool
)
# Note: SemanticSearchTool removed — VetkaSearchSemanticTool now uses REST API (MARKER_124.3E)


class VetkaSearchSemanticTool(BaseTool):
    """
    Semantic search in VETKA knowledge base using Qdrant.

    Searches for concepts, ideas, or topics across all indexed documents
    using vector similarity search. Returns relevant content with similarity scores.

    MARKER_124.3E: Fixed to use REST API (same as MCP bridge) instead of broken
    shared_tools.SemanticSearchTool which returned 0 results.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="vetka_search_semantic",
            description="Semantic search in VETKA knowledge base. Searches for concepts, ideas, or topics across all indexed documents using vector similarity search.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Semantic search query (e.g., 'authentication logic', 'how to handle errors')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10, max: 50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": ["query"]
            },
            permission_level=PermissionLevel.READ,
            needs_user_approval=False
        )

    # MARKER_124.5A: Hybrid search — semantic + code-only filtered search
    # MARKER_124.6A: Refined filters — separate frontend vs all code extensions
    _FRONTEND_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".css", ".scss"]
    _CODE_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".py", ".rs", ".go", ".java", ".css", ".scss"]
    _SKIP_NAMES = {"__init__.py", "index.ts", "index.js"}
    _SKIP_PATH_PARTS = {"node_modules", "__pycache__", ".git", "dist", "build"}

    async def execute(self, query: str = "", limit: int = 10, _base_path: str = "", **kwargs) -> ToolResult:
        """Hybrid search: semantic results + Qdrant code-only filtered search.

        MARKER_124.5A: Embedding models rank docs (.md, .txt) above code files.
        Fix: run TWO searches — general semantic + code-only filtered via Qdrant.
        Merge results, dedup by path, code files first.

        MARKER_150.2_PLAYGROUND: _base_path accepted but not actively used here
        (Qdrant indexes main project; semantic search returns same results regardless).
        File reading from playground is handled by VetkaReadFileTool + VetkaSearchCodeTool.
        """
        try:
            if not query or len(query) < 2:
                return ToolResult(success=False, result=None, error="Query too short (min 2 chars)")

            import httpx

            # Search 1: General semantic search via REST API
            general_results = []
            async with httpx.AsyncClient(base_url="http://localhost:5001", timeout=10.0) as client:
                resp = await client.get(
                    "/api/search/semantic",
                    params={"q": query, "limit": limit}
                )
                if resp.status_code == 200:
                    general_results = resp.json().get("files", [])

            # Search 2: Code-only via Qdrant direct (filtered by extension)
            code_results = await self._search_code_only(query, limit)

            # Merge: code results first (they're what coders need), then general
            seen_paths = set()
            merged = []

            for f in code_results:
                path = f.get("path", "")
                name = f.get("name", "")
                if path in seen_paths or name in self._SKIP_NAMES:
                    continue
                seen_paths.add(path)
                merged.append({"file_path": path, "name": name, "score": round(f.get("score", 0), 3)})

            for f in general_results:
                path = f.get("path", f.get("file_path", ""))
                name = f.get("name", "")
                if path in seen_paths or name in self._SKIP_NAMES:
                    continue
                if any(skip in path for skip in self._SKIP_PATH_PARTS):
                    continue
                seen_paths.add(path)
                merged.append({"file_path": path, "name": name, "score": round(f.get("score", 0), 3)})

            top = merged[:limit]
            formatted_text = f"Search: '{query}' — {len(top)} results\n"
            for r in top:
                formatted_text += f"\n  {r['file_path']} (score: {r['score']})"

            return ToolResult(success=True, result=formatted_text)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    async def _search_code_only(self, query: str, limit: int) -> list:
        """Search Qdrant with code-extension filter (MARKER_124.5A helper).

        MARKER_124.6A: Two-pass search — first frontend (.ts/.tsx/.jsx),
        then all code extensions. Filter out node_modules, __init__.py, test files.
        """
        try:
            import httpx
            embedding = await self._get_query_embedding(query)
            if not embedding:
                return []

            results = []

            # Pass 1: Frontend extensions only (.ts, .tsx, .jsx, .css)
            frontend_body = {
                "vector": embedding,
                "filter": {
                    "must": [
                        {"should": [{"key": "extension", "match": {"value": ext}} for ext in self._FRONTEND_EXTENSIONS]}
                    ],
                    "must_not": [
                        {"key": "name", "match": {"value": "__init__.py"}},
                    ]
                },
                "limit": limit,
                "with_payload": ["name", "path", "extension"],
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "http://localhost:6333/collections/vetka_elisya/points/search",
                    json=frontend_body,
                )
                if resp.status_code == 200:
                    for p in resp.json().get("result", []):
                        name = p["payload"].get("name", "")
                        path = p["payload"].get("path", "")
                        # Skip node_modules, tests, etc
                        if any(skip in path for skip in self._SKIP_PATH_PARTS):
                            continue
                        if name in self._SKIP_NAMES:
                            continue
                        results.append({
                            "name": name,
                            "path": path,
                            "score": p.get("score", 0),
                        })

            # Pass 2: If frontend pass returned < limit/2, fill with all code
            if len(results) < limit // 2:
                all_body = {
                    "vector": embedding,
                    "filter": {
                        "must": [
                            {"should": [{"key": "extension", "match": {"value": ext}} for ext in self._CODE_EXTENSIONS]}
                        ],
                        "must_not": [
                            {"key": "name", "match": {"value": "__init__.py"}},
                        ]
                    },
                    "limit": limit,
                    "with_payload": ["name", "path", "extension"],
                }
                seen = {r["path"] for r in results}
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        "http://localhost:6333/collections/vetka_elisya/points/search",
                        json=all_body,
                    )
                    if resp.status_code == 200:
                        for p in resp.json().get("result", []):
                            name = p["payload"].get("name", "")
                            path = p["payload"].get("path", "")
                            if path in seen:
                                continue
                            if any(skip in path for skip in self._SKIP_PATH_PARTS):
                                continue
                            if name in self._SKIP_NAMES:
                                continue
                            results.append({
                                "name": name,
                                "path": path,
                                "score": p.get("score", 0),
                            })

            return results[:limit]
        except Exception:
            pass
        return []

    @staticmethod
    async def _get_query_embedding(query: str) -> list:
        """Get embedding vector for query via Ollama."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "http://localhost:11434/api/embed",
                    json={"model": "embeddinggemma:300m", "input": query}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    embeddings = data.get("embeddings", data.get("embedding", []))
                    if embeddings and isinstance(embeddings[0], list):
                        return embeddings[0]
                    return embeddings
        except Exception:
            pass
        return []


class VetkaCameraFocusTool(BaseTool):
    """
    Move 3D camera to focus on a specific target in VETKA visualization.
    
    Controls the VETKA 3D visualization camera to focus on files, branches,
    or provide an overview. Requires active VETKA UI session.
    """
    
    def __init__(self):
        self._tool = SharedCameraFocusTool()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="vetka_camera_focus",
            description="Move 3D camera to focus on a specific target in VETKA visualization. Controls the camera to focus on files, branches, or provide an overview.",
            parameters={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "File path, branch name, or 'overview' to focus on"
                    },
                    "zoom": {
                        "type": "string",
                        "description": "Zoom level: 'close', 'medium', or 'far'",
                        "enum": ["close", "medium", "far"],
                        "default": "medium"
                    },
                    "highlight": {
                        "type": "boolean",
                        "description": "Highlight target with glow effect",
                        "default": True
                    },
                    "animate": {
                        "type": "boolean",
                        "description": "Use smooth camera animation",
                        "default": True
                    }
                },
                "required": ["target"]
            },
            permission_level=PermissionLevel.EXECUTE,
            needs_user_approval=False
        )
    
    async def execute(self, target: str, zoom: str = "medium", highlight: bool = True, animate: bool = True) -> ToolResult:
        try:
            arguments = {
                "target": target,
                "zoom": zoom,
                "highlight": highlight,
                "animate": animate
            }
            
            # Validate arguments
            error = self._tool.validate_arguments(arguments)
            if error:
                return ToolResult(success=False, result=None, error=error)
            
            # Execute camera focus
            result = await self._tool.execute(arguments)
            
            if not result.get("success", False):
                return ToolResult(
                    success=False,
                    result=None,
                    error=result.get("error", "Camera focus failed")
                )
            
            return ToolResult(
                success=True,
                result={
                    "message": result.get("message", f"Camera focused on {target}"),
                    "target": target,
                    "zoom": zoom
                }
            )
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


class GetTreeContextTool(BaseTool):
    """
    Get VETKA 3D tree structure and context.
    
    Returns the hierarchical file/folder structure used by VETKA's 3D
    visualization. Supports summary or full tree output.
    """
    
    def __init__(self):
        self._tool = TreeStructureTool()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_tree_context",
            description="Get VETKA 3D tree structure and context. Returns the hierarchical file/folder structure used by VETKA's 3D visualization.",
            parameters={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "Output format - 'tree' for full structure, 'summary' for statistics",
                        "enum": ["tree", "summary"],
                        "default": "summary"
                    }
                },
                "required": []
            },
            permission_level=PermissionLevel.READ,
            needs_user_approval=False
        )
    
    async def execute(self, format: str = "summary") -> ToolResult:
        try:
            arguments = {"format": format}
            
            # Execute tree query
            result = await self._tool.execute(arguments)
            
            if result.get("error"):
                return ToolResult(success=False, result=None, error=result["error"])
            
            if format == "summary":
                return ToolResult(
                    success=True,
                    result={
                        "summary": result.get("summary", {}),
                        "format": "summary"
                    }
                )
            else:
                return ToolResult(
                    success=True,
                    result={
                        "tree": result.get("tree", {}),
                        "format": "tree"
                    }
                )
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


# MARKER_114.3_CREATE_ARTIFACT: Wrapper for MCP EditArtifactTool → internal registry
# Restores create_artifact capability for Architect/Dev (removed by Big Pickle Phase 92)
# Phase 108.4 MCP tools (vetka_edit_artifact) are the replacement
class VetkaEditArtifactTool(BaseTool):
    """
    Create/edit artifacts for Architect/PM/Dev review workflow.

    MARKER_114.3: Wraps MCP EditArtifactTool (Phase 108.4) for internal registry.
    Replaces CreateArtifactTool removed in Phase 92.
    """

    def __init__(self):
        try:
            from src.mcp.tools.artifact_tools import EditArtifactTool
            self._tool = EditArtifactTool()
        except ImportError:
            self._tool = None

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="vetka_edit_artifact",
            description="Create or edit an artifact (code file) and submit for approval. Use for generating code, configs, or documents that need review.",
            parameters={
                "type": "object",
                "properties": {
                    "artifact_id": {
                        "type": "string",
                        "description": "Artifact ID to edit (optional for new artifacts)"
                    },
                    "path": {
                        "type": "string",
                        "description": "File path for the artifact (e.g., 'artifacts/my_module.py')"
                    },
                    "new_content": {
                        "type": "string",
                        "description": "Content for the artifact"
                    }
                },
                "required": ["new_content"]
            },
            permission_level=PermissionLevel.WRITE,
            needs_user_approval=True
        )

    async def execute(self, new_content: str, artifact_id: str = None, path: str = None) -> ToolResult:
        try:
            if not self._tool:
                return ToolResult(success=False, result=None, error="EditArtifactTool not available (import failed)")

            arguments = {"new_content": new_content}
            if artifact_id:
                arguments["artifact_id"] = artifact_id
            if path:
                arguments["path"] = path

            result = self._tool.execute(arguments)

            if not result.get("success", False):
                return ToolResult(success=False, result=None, error=result.get("error", "Artifact edit failed"))

            return ToolResult(
                success=True,
                result=result.get("result", {"message": "Artifact saved"})
            )
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))
# MARKER_114.3_CREATE_ARTIFACT_END


# ============================================================================
# MARKER_124.0A: FC Loop Tool Wrappers
# Wraps MCP-only tools as BaseTool for SafeToolExecutor in FC loop.
# Phase 124.0: vetka_read_file, vetka_search_files, vetka_list_files
# ============================================================================

class VetkaReadFileTool(BaseTool):
    """
    Read file content from VETKA project.
    Wraps MCP ReadFileTool for internal ToolRegistry.

    MARKER_124.8B: Added 'marker' parameter — reads only ±20 lines around
    a specific MARKER_ tag instead of the full file. Saves tokens for large files.
    """

    _PROJECT_ROOT = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
    _MARKER_CONTEXT_LINES = 20  # Lines above and below marker to include

    def __init__(self):
        try:
            from src.mcp.tools.read_file_tool import ReadFileTool
            self._tool = ReadFileTool()
        except ImportError:
            self._tool = None

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="vetka_read_file",
            description=(
                "Read file content from VETKA project. "
                "Optionally pass 'marker' to read only the code block around a specific MARKER_ tag "
                "(saves tokens for large files)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read (relative to project root)"
                    },
                    "marker": {
                        "type": "string",
                        "description": "Optional MARKER_ tag to focus on (e.g., 'MARKER_108_3'). Returns only ±20 lines around it."
                    }
                },
                "required": ["file_path"]
            },
            permission_level=PermissionLevel.READ,
            needs_user_approval=False
        )

    async def execute(self, file_path: str = "", marker: str = "", _base_path: str = "", **kwargs) -> ToolResult:
        try:
            if not self._tool:
                return ToolResult(success=False, result=None, error="ReadFileTool not available")

            # MARKER_150.2_PLAYGROUND: Use playground path if provided
            effective_root = _base_path or self._PROJECT_ROOT

            # MARKER_124.8B: If marker specified, do focused read
            if marker:
                return await self._read_marker_focused(file_path, marker, effective_root)

            # Normal full-file read
            arguments = {"path": file_path, "max_lines": 500}

            error = self._tool.validate_arguments(arguments)
            if error:
                return ToolResult(success=False, result=None, error=error)

            result = self._tool.execute(arguments)

            if not result.get("success", False):
                return ToolResult(success=False, result=None, error=result.get("error", "Read failed"))

            # Extract content for LLM consumption
            res_data = result.get("result", {})
            content = res_data.get("content", "")
            path = res_data.get("path", file_path)
            total_lines = res_data.get("total_lines", 0)
            truncated = res_data.get("truncated", False)

            # Format as numbered lines for coder readability
            formatted = f"File: {path} ({total_lines} lines"
            if truncated:
                formatted += ", truncated"
            formatted += f")\n\n{content}"

            return ToolResult(success=True, result=formatted)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    async def _read_marker_focused(self, file_path: str, marker: str, effective_root: str = "") -> ToolResult:
        """Read only the code block around a specific MARKER_ tag.

        MARKER_124.8B: Instead of reading 500+ lines, reads ±20 lines
        around the marker. Massive token savings for large files.

        MARKER_124.9C: Also supports Scout virtual markers (MARKER_SCOUT_X)
        that aren't written to disk. If marker not found in file text,
        tries to extract line number from marker format (e.g., 'line:42')
        or uses a fallback line param passed as 'MARKER_SCOUT_1:42'.

        MARKER_150.2_PLAYGROUND: effective_root overrides _PROJECT_ROOT
        when running inside a playground worktree.
        """
        from pathlib import Path

        root = effective_root or self._PROJECT_ROOT

        # Resolve path
        p = Path(file_path)
        if not p.is_absolute():
            p = Path(root) / p

        if not p.exists():
            return ToolResult(success=False, result=None, error=f"File not found: {file_path}")

        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            total = len(lines)

            # Find marker line(s)
            marker_lines = []
            # MARKER_124.9C: Support "MARKER_SCOUT_1:42" format (marker_id:line_number)
            marker_text = marker
            forced_line = None
            if ":" in marker and marker.split(":")[-1].isdigit():
                parts = marker.rsplit(":", 1)
                marker_text = parts[0]
                forced_line = int(parts[1]) - 1  # 0-indexed

            for i, line in enumerate(lines):
                if marker_text in line:
                    marker_lines.append(i)

            # MARKER_124.9C: Virtual marker fallback — use forced line number
            if not marker_lines and forced_line is not None:
                if 0 <= forced_line < total:
                    marker_lines = [forced_line]

            if not marker_lines:
                return ToolResult(
                    success=False, result=None,
                    error=f"Marker '{marker_text}' not found in {file_path} ({total} lines). "
                          f"Tip: append line number like 'MARKER_SCOUT_1:42' to jump to line 42."
                )

            # Check for _START/_END block
            start_line = marker_lines[0]
            end_line = start_line
            end_marker = marker_text.replace("_START", "_END")
            if "_START" in marker_text:
                for i, line in enumerate(lines[start_line:], start_line):
                    if end_marker in line:
                        end_line = i
                        break

            # If no block markers, use context window
            if start_line == end_line:
                ctx = self._MARKER_CONTEXT_LINES
                from_line = max(0, start_line - ctx)
                to_line = min(total, start_line + ctx + 1)
            else:
                # Block markers: include some context before/after
                from_line = max(0, start_line - 3)
                to_line = min(total, end_line + 4)

            # Format with line numbers
            snippet_lines = []
            for i in range(from_line, to_line):
                # MARKER_124.9C: For virtual markers (forced_line), highlight the target line
                is_marker_line = (marker_text in lines[i]) or (forced_line is not None and i == forced_line)
                prefix = ">>>" if is_marker_line else "   "
                snippet_lines.append(f"{prefix} {i+1:4d} | {lines[i]}")

            snippet = "\n".join(snippet_lines)
            formatted = (
                f"File: {file_path} (focused on {marker_text}, lines {from_line+1}-{to_line}, "
                f"total {total} lines)\n\n{snippet}"
            )

            return ToolResult(success=True, result=formatted)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


class VetkaSearchFilesTool(BaseTool):
    """
    Search for files by name or content pattern.
    Uses REST API for consistent results (MARKER_124.4A).
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="vetka_search_files",
            description="Search for files by name or content pattern using ripgrep-style search.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (text pattern or regex)"
                    },
                    "search_type": {
                        "type": "string",
                        "description": "Type of search: 'content' (default) or 'filename'"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of results (default: 10)"
                    }
                },
                "required": ["query"]
            },
            permission_level=PermissionLevel.READ,
            needs_user_approval=False
        )

    async def execute(self, query: str = "", search_type: str = "content", limit: int = 10, _base_path: str = "", **kwargs) -> ToolResult:
        """Delegates to VetkaSearchSemanticTool hybrid search (MARKER_124.5A)."""
        # Both tools now use the same hybrid search (semantic + code-only)
        semantic_tool = VetkaSearchSemanticTool()
        result = await semantic_tool.execute(query=query, limit=limit, _base_path=_base_path)
        # Rebrand output
        if result.success and result.result:
            result = ToolResult(
                success=True,
                result=result.result.replace("Search:", "Search files:", 1)
            )
        return result


class VetkaListFilesTool(BaseTool):
    """
    List files in a directory or matching a pattern.
    Wraps MCP ListFilesTool for internal ToolRegistry.
    """

    def __init__(self):
        try:
            from src.mcp.tools.list_files_tool import ListFilesTool as MCPListFiles
            self._tool = MCPListFiles()
        except ImportError:
            self._tool = None

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="vetka_list_files",
            description="List files in a directory or matching a pattern. Returns file paths with metadata.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path (relative to project root)"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File pattern to filter (e.g., '*.tsx', '*.py')"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Search recursively in subdirectories"
                    }
                }
            },
            permission_level=PermissionLevel.READ,
            needs_user_approval=False
        )

    async def execute(self, path: str = "", pattern: str = "*", recursive: bool = False, _base_path: str = "", **kwargs) -> ToolResult:
        try:
            if not self._tool:
                return ToolResult(success=False, result=None, error="ListFilesTool not available")

            depth = 3 if recursive else 1
            arguments = {"path": path, "pattern": pattern, "depth": depth}

            error = self._tool.validate_arguments(arguments)
            if error:
                return ToolResult(success=False, result=None, error=error)

            result = self._tool.execute(arguments)

            if not result.get("success", False):
                return ToolResult(success=False, result=None, error=result.get("error", "List failed"))

            res_data = result.get("result", {})
            items = res_data.get("items", [])

            formatted = f"Directory: {path or '/'} ({len(items)} items)\n"
            for item in items[:50]:  # Limit display
                icon = "📁" if item.get("type") == "directory" else "📄"
                formatted += f"\n  {icon} {item.get('path', item.get('name', ''))}"

            if len(items) > 50:
                formatted += f"\n  ... and {len(items) - 50} more"

            return ToolResult(success=True, result=formatted)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

# MARKER_124.0A_END


# ============================================================================
# MARKER_124.7: Contextual Code Search — ripgrep + Qdrant name filter
# Fast, exact search for coder agents. Replaces semantic-only VetkaSearchFilesTool.
# ============================================================================

class VetkaSearchCodeTool(BaseTool):
    """
    Fast code search: ripgrep for content + Qdrant name filter for filenames.

    MARKER_124.7: Designed for pipeline coder agents who need to find
    SPECIFIC files by name or content pattern, not semantic similarity.

    Strategy:
    1. Filename match: Qdrant scroll with name filter (instant)
    2. ripgrep content search: subprocess rg for exact text (fast)
    3. Fallback: semantic search if both empty (for conceptual queries)
    """

    _PROJECT_ROOT = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
    _SKIP_DIRS = ["node_modules", "__pycache__", ".git", "dist", "build", ".venv", "venv"]

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="vetka_search_code",
            description=(
                "Fast code search by filename or content pattern. "
                "Use this to find specific files (e.g., 'useStore.ts') or "
                "search for code patterns (e.g., 'toggleBookmark', 'interface Chat'). "
                "Much faster and more precise than semantic search for exact matches."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query: filename (e.g., 'useStore.ts') or code pattern (e.g., 'toggleBookmark')"
                    },
                    "file_type": {
                        "type": "string",
                        "description": "Filter by file type: 'ts', 'tsx', 'py', 'rs', or empty for all",
                        "default": ""
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
            },
            permission_level=PermissionLevel.READ,
            needs_user_approval=False
        )

    async def execute(self, query: str = "", file_type: str = "", limit: int = 10, _base_path: str = "", **kwargs) -> ToolResult:
        """Multi-strategy code search: name → ripgrep → semantic fallback.

        MARKER_150.2_PLAYGROUND: _base_path overrides _PROJECT_ROOT for
        playground-scoped ripgrep searches.
        """
        if not query or len(query) < 2:
            return ToolResult(success=False, result=None, error="Query too short (min 2 chars)")

        # MARKER_150.2_PLAYGROUND: Use playground path if provided
        effective_root = _base_path or self._PROJECT_ROOT

        try:
            results = []
            seen_paths = set()
            strategies_used = []

            # Strategy 1: Qdrant filename match (for queries like "useStore.ts", "ChatPanel")
            name_results = await self._search_by_name(query, limit)
            if name_results:
                strategies_used.append("name")
                for r in name_results:
                    path = r.get("path", "")
                    if path not in seen_paths:
                        seen_paths.add(path)
                        results.append(r)

            # Strategy 2: ripgrep content search (for code patterns like "toggleBookmark", "interface Chat")
            rg_results = await self._search_by_ripgrep(query, file_type, limit, effective_root)
            if rg_results:
                strategies_used.append("ripgrep")
                for r in rg_results:
                    path = r.get("path", "")
                    if path not in seen_paths:
                        seen_paths.add(path)
                        results.append(r)

            # Strategy 3: Semantic fallback only if both empty
            if not results:
                strategies_used.append("semantic")
                semantic_tool = VetkaSearchSemanticTool()
                sem_result = await semantic_tool.execute(query=query, limit=limit)
                if sem_result.success and sem_result.result:
                    return ToolResult(
                        success=True,
                        result=f"Code search (semantic fallback): {sem_result.result}"
                    )

            # Format output
            top = results[:limit]
            strat_str = "+".join(strategies_used)
            formatted = f"Code search: '{query}' — {len(top)} results ({strat_str})\n"
            for r in top:
                rel_path = r["path"].replace(effective_root + "/", "").replace(self._PROJECT_ROOT + "/", "")
                match_info = r.get("match", "")
                context = r.get("context", "")
                if match_info:
                    formatted += f"\n  {rel_path} — {match_info}"
                else:
                    formatted += f"\n  {rel_path}"
                # MARKER_124.8A: Include code context for marker searches
                if context:
                    formatted += f"\n    ---\n    {context}\n    ---"

            return ToolResult(success=True, result=formatted)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    async def _search_by_name(self, query: str, limit: int) -> list:
        """Search Qdrant by filename (substring match via scroll + filter)."""
        import httpx

        results = []
        try:
            # Extract likely filename from query (e.g., "useStore.ts" or "useStore")
            # Use Qdrant scroll with name substring — Qdrant text match
            query_clean = query.strip().split("/")[-1]  # Take last path component

            body = {
                "filter": {
                    "must": [
                        {"key": "name", "match": {"text": query_clean}}
                    ]
                },
                "limit": limit,
                "with_payload": ["name", "path", "extension"],
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    "http://localhost:6333/collections/vetka_elisya/points/scroll",
                    json=body,
                )
                if resp.status_code == 200:
                    points = resp.json().get("result", {}).get("points", [])
                    for p in points:
                        path = p["payload"].get("path", "")
                        name = p["payload"].get("name", "")
                        # Skip junk paths
                        if any(skip in path for skip in self._SKIP_DIRS):
                            continue
                        results.append({
                            "path": path,
                            "name": name,
                            "match": f"filename: {name}",
                        })
        except Exception:
            pass
        return results

    async def _search_by_ripgrep(self, query: str, file_type: str, limit: int, search_root: str = "") -> list:
        """Search file contents using ripgrep subprocess.

        MARKER_124.8A: If query looks like a MARKER_, use context mode (-C 5)
        to return surrounding code lines for precise location.

        MARKER_150.2_PLAYGROUND: search_root overrides _PROJECT_ROOT
        for playground-scoped searches.
        """
        import asyncio

        root = search_root or self._PROJECT_ROOT
        is_marker_query = query.startswith("MARKER_")
        results = []
        try:
            if is_marker_query:
                # Marker search: return file:line + context
                cmd = ["rg", "-n", "-C", "5", "--max-count", "1"]
            else:
                # Normal search: just file paths
                cmd = ["rg", "--files-with-matches", "--max-count", "1", "-l"]

            # Add file type filter
            if file_type:
                cmd.extend(["--type", file_type])

            # Skip directories
            for skip in self._SKIP_DIRS:
                cmd.extend(["--glob", f"!{skip}"])

            # Add query and path
            cmd.append(query)
            cmd.append(root)

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)

            if stdout:
                output = stdout.decode().strip()
                if is_marker_query:
                    # Parse rg context output: group by file
                    results = self._parse_marker_context(output, query, limit)
                else:
                    lines = output.split("\n")
                    for line in lines[:limit]:
                        path = line.strip()
                        if not path:
                            continue
                        name = path.split("/")[-1]
                        results.append({
                            "path": path,
                            "name": name,
                            "match": f"content: '{query}'",
                        })
        except Exception:
            pass
        return results

    @staticmethod
    def _parse_marker_context(output: str, query: str, limit: int) -> list:
        """Parse ripgrep context output for marker searches.

        MARKER_124.8A: Groups ripgrep -C output by file, extracts
        file path + line number + surrounding code context.
        """
        results = []
        current_file = None
        context_lines = []

        for line in output.split("\n"):
            # rg context format: /path/to/file.ts-42-  code line
            # or: /path/to/file.ts:42:  matched line
            if ":" in line or "-" in line:
                # Extract file path from rg output
                for sep in [":", "-"]:
                    parts = line.split(sep, 2)
                    if len(parts) >= 3 and "/" in parts[0]:
                        filepath = parts[0]
                        if filepath != current_file:
                            # Save previous file's context
                            if current_file and context_lines:
                                name = current_file.split("/")[-1]
                                context = "\n".join(context_lines[-15:])  # Max 15 lines
                                results.append({
                                    "path": current_file,
                                    "name": name,
                                    "match": f"marker: {query}",
                                    "context": context,
                                })
                            current_file = filepath
                            context_lines = []
                        context_lines.append(line)
                        break

        # Save last file
        if current_file and context_lines:
            name = current_file.split("/")[-1]
            context = "\n".join(context_lines[-15:])
            results.append({
                "path": current_file,
                "name": name,
                "match": f"marker: {query}",
                "context": context,
            })

        return results[:limit]

# MARKER_124.7_END


# ============================================================================
# REGISTER MCP TOOLS
# ============================================================================

# Register tools with the global registry
registry.register(VetkaSearchSemanticTool())
registry.register(VetkaCameraFocusTool())
registry.register(GetTreeContextTool())
registry.register(VetkaEditArtifactTool())  # MARKER_114.3: Artifact tool for Architect/Dev
# MARKER_124.0A: FC loop tool wrappers
registry.register(VetkaReadFileTool())
registry.register(VetkaSearchFilesTool())
registry.register(VetkaListFilesTool())
registry.register(VetkaSearchCodeTool())  # MARKER_124.7: Fast code search for coder FC loop

# Export for direct access
__all__ = [
    "VetkaSearchSemanticTool",
    "VetkaCameraFocusTool",
    "GetTreeContextTool",
    "VetkaEditArtifactTool",
    "VetkaReadFileTool",
    "VetkaSearchFilesTool",
    "VetkaListFilesTool",
    "VetkaSearchCodeTool",
]
