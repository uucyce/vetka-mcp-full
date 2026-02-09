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
    _CODE_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".py", ".rs", ".go", ".java", ".css", ".scss"]
    _SKIP_NAMES = {"__init__.py"}

    async def execute(self, query: str = "", limit: int = 10, **kwargs) -> ToolResult:
        """Hybrid search: semantic results + Qdrant code-only filtered search.

        MARKER_124.5A: Embedding models rank docs (.md, .txt) above code files.
        Fix: run TWO searches — general semantic + code-only filtered via Qdrant.
        Merge results, dedup by path, code files first.
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
        """Search Qdrant with code-extension filter (MARKER_124.5A helper)."""
        try:
            import httpx
            # Get query embedding from Ollama (same model as indexer)
            embedding = await self._get_query_embedding(query)
            if not embedding:
                return []

            body = {
                "vector": embedding,
                "filter": {
                    "should": [{"key": "extension", "match": {"value": ext}} for ext in self._CODE_EXTENSIONS]
                },
                "limit": limit,
                "with_payload": ["name", "path", "extension"],
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "http://localhost:6333/collections/vetka_elisya/points/search",
                    json=body,
                )
                if resp.status_code == 200:
                    return [
                        {
                            "name": p["payload"].get("name", ""),
                            "path": p["payload"].get("path", ""),
                            "score": p.get("score", 0),
                        }
                        for p in resp.json().get("result", [])
                    ]
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
    """

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
            description="Read file content from VETKA project. Returns full file content with line numbers.",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read (relative to project root)"
                    }
                },
                "required": ["file_path"]
            },
            permission_level=PermissionLevel.READ,
            needs_user_approval=False
        )

    async def execute(self, file_path: str = "", **kwargs) -> ToolResult:
        try:
            if not self._tool:
                return ToolResult(success=False, result=None, error="ReadFileTool not available")

            # Map FC loop's "file_path" to MCP tool's "path"
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

    async def execute(self, query: str = "", search_type: str = "content", limit: int = 10, **kwargs) -> ToolResult:
        """Delegates to VetkaSearchSemanticTool hybrid search (MARKER_124.5A)."""
        # Both tools now use the same hybrid search (semantic + code-only)
        semantic_tool = VetkaSearchSemanticTool()
        result = await semantic_tool.execute(query=query, limit=limit)
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

    async def execute(self, path: str = "", pattern: str = "*", recursive: bool = False, **kwargs) -> ToolResult:
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

# Export for direct access
__all__ = [
    "VetkaSearchSemanticTool",
    "VetkaCameraFocusTool",
    "GetTreeContextTool",
    "VetkaEditArtifactTool",
    "VetkaReadFileTool",
    "VetkaSearchFilesTool",
    "VetkaListFilesTool",
]
