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
    SemanticSearchTool,
    SharedCameraFocusTool,
    TreeStructureTool
)


class VetkaSearchSemanticTool(BaseTool):
    """
    Semantic search in VETKA knowledge base using Qdrant.
    
    Searches for concepts, ideas, or topics across all indexed documents
    using vector similarity search. Returns relevant content with similarity scores.
    """
    
    def __init__(self):
        self._tool = SemanticSearchTool()
    
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
    
    async def execute(self, query: str, limit: int = 10) -> ToolResult:
        try:
            arguments = {"query": query, "limit": limit}
            
            # Validate arguments
            error = self._tool.validate_arguments(arguments)
            if error:
                return ToolResult(success=False, result=None, error=error)
            
            # Execute the search
            result = await self._tool.execute(arguments)
            
            if result.get("error"):
                return ToolResult(success=False, result=None, error=result["error"])
            
            return ToolResult(
                success=True,
                result={
                    "results": result.get("results", []),
                    "query": result.get("query", query),
                    "total": result.get("total", 0)
                }
            )
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


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
# REGISTER MCP TOOLS
# ============================================================================

# Register tools with the global registry
registry.register(VetkaSearchSemanticTool())
registry.register(VetkaCameraFocusTool())
registry.register(GetTreeContextTool())
registry.register(VetkaEditArtifactTool())  # MARKER_114.3: Artifact tool for Architect/Dev

# Export for direct access
__all__ = [
    "VetkaSearchSemanticTool",
    "VetkaCameraFocusTool",
    "GetTreeContextTool",
    "VetkaEditArtifactTool",
]
