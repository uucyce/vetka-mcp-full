"""
FastAPI routes for OpenCode Bridge.
Local-only, no authentication needed.

Phase 95.6: Bridge Unification - All 18 VETKA tools now available via REST API.

@status: active
@phase: 96
@depends: fastapi, src.opencode_bridge.open_router_bridge, src.bridge
@used_by: src.api.routes
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import os
from .open_router_bridge import get_openrouter_bridge

# Import shared tools from unified bridge module
from src.bridge import (
    # Read tools
    SemanticSearchTool,
    ReadFileTool,
    TreeStructureTool,
    HealthCheckTool,
    ListFilesTool,
    SearchFilesTool,
    MetricsTool,
    KnowledgeGraphTool,
    GroupMessagesTool,
    # Write tools
    SharedEditFileTool,
    SharedGitCommitTool,
    SharedGitStatusTool,
    # Execution tools
    SharedRunTestsTool,
    SharedCameraFocusTool,
    SharedCallModelTool,
    # Memory tools
    ConversationContextTool,
    UserPreferencesTool,
    MemorySummaryTool,
    # Formatters
    format_semantic_results,
    format_tree_summary,
    format_health_status,
    format_file_list,
    format_metrics,
    format_knowledge_graph_summary,
    format_group_messages,
    format_write_result,
    format_git_status,
    format_test_result,
    format_camera_result,
    format_llm_result,
    format_context_result,
    format_preferences_result,
    format_memory_summary,
    # Utils
    list_tools,
)

router = APIRouter(tags=["bridge"])

# Check if bridge is enabled
BRIDGE_ENABLED = os.getenv("OPENCODE_BRIDGE_ENABLED", "false").lower() == "true"


@router.get("/openrouter/keys")
async def get_openrouter_keys():
    """Get available OpenRouter keys (masked) for UI"""
    if not BRIDGE_ENABLED:
        return {"enabled": False, "keys": [], "message": "Bridge disabled"}

    try:
        bridge = get_openrouter_bridge()
        keys = bridge.get_available_keys()
        return {
            "enabled": True,
            "provider": "openrouter",
            "keys": keys,
            "total": len(keys),
        }
    except Exception as e:
        return {"enabled": False, "error": str(e)}


@router.post("/openrouter/invoke")
async def invoke_openrouter(request: Dict[str, Any]):
    """Invoke OpenRouter model through bridge with rotation"""
    if not BRIDGE_ENABLED:
        return {"success": False, "error": "Bridge disabled"}

    try:
        bridge = get_openrouter_bridge()

        model_id = request.get("model_id")
        messages = request.get("messages")

        if not model_id or not messages:
            return {"success": False, "error": "Missing model_id or messages"}

        # Extract only allowed kwargs to avoid conflicts
        allowed_kwargs = {
            k: v
            for k, v in request.items()
            if k not in ("model_id", "messages") and k not in ("request",)
        }
        result = await bridge.invoke(model_id, messages, **allowed_kwargs)
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/openrouter/stats")
async def get_openrouter_stats():
    """Get rotation statistics for UI"""
    if not BRIDGE_ENABLED:
        return {"enabled": False}

    try:
        bridge = get_openrouter_bridge()
        stats = bridge.get_stats()

        return {
            "enabled": True,
            "provider": "openrouter",
            "stats": {
                "total_keys": stats.total_keys,
                "active_keys": stats.active_keys,
                "rate_limited_keys": stats.rate_limited_keys,
                "current_key_index": stats.current_key_index,
                "last_rotation": stats.last_rotation,
            },
        }
    except Exception as e:
        return {"enabled": False, "error": str(e)}


@router.get("/openrouter/health")
async def health_check():
    """Health check for bridge"""
    return {
        "status": "healthy",
        "bridge_enabled": BRIDGE_ENABLED,
        "provider": "openrouter",
    }


# =============================================================================
# VETKA UNIFIED TOOLS (Phase 95.6 - Bridge Unification)
# All 18 MCP tools now available via REST API
# =============================================================================

@router.get("/tools")
async def list_available_tools():
    """List all available VETKA tools"""
    return {
        "tools": list_tools(),
        "total": len(list_tools()),
        "version": "95.6",
    }


# -----------------------------------------------------------------------------
# READ TOOLS (8 tools)
# -----------------------------------------------------------------------------

@router.get("/search/semantic")
async def search_semantic(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Max results")
):
    """Semantic search in VETKA knowledge base using Qdrant vector search"""
    tool = SemanticSearchTool()
    try:
        result = await tool.execute({"query": q, "limit": limit})
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/files/read")
async def read_file(request: Dict[str, Any]):
    """Read file content from VETKA project"""
    tool = ReadFileTool()
    file_path = request.get("file_path")
    if not file_path:
        return {"success": False, "error": "Missing file_path"}
    try:
        result = await tool.execute({"file_path": file_path})
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/tree/structure")
async def get_tree_structure(
    format: str = Query("summary", enum=["tree", "summary"])
):
    """Get VETKA 3D tree structure showing files and folders hierarchy"""
    tool = TreeStructureTool()
    try:
        result = await tool.execute({"format": format})
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/health/vetka")
async def vetka_health_check():
    """Check VETKA server health and component status"""
    tool = HealthCheckTool()
    try:
        result = await tool.execute({})
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/files/list")
async def list_files(
    path: str = Query(".", description="Directory path"),
    pattern: Optional[str] = Query(None, description="Glob pattern"),
    recursive: bool = Query(False, description="Recursive listing")
):
    """List files in a directory or matching a pattern"""
    tool = ListFilesTool()
    try:
        args = {"path": path, "recursive": recursive}
        if pattern:
            args["pattern"] = pattern
        result = await tool.execute(args)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/search/files")
async def search_files(
    q: str = Query(..., description="Search query"),
    search_type: str = Query("both", enum=["filename", "content", "both"]),
    limit: int = Query(20, ge=1, le=100)
):
    """Search for files by name or content pattern"""
    tool = SearchFilesTool()
    try:
        result = await tool.execute({
            "query": q,
            "search_type": search_type,
            "limit": limit
        })
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/metrics")
async def get_metrics(
    metric_type: str = Query("dashboard", enum=["dashboard", "agents", "all"])
):
    """Get VETKA metrics and analytics"""
    tool = MetricsTool()
    try:
        result = await tool.execute({"metric_type": metric_type})
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/knowledge-graph")
async def get_knowledge_graph(
    format: str = Query("summary", enum=["json", "summary"])
):
    """Get VETKA knowledge graph structure"""
    tool = KnowledgeGraphTool()
    try:
        result = await tool.execute({"format": format})
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# -----------------------------------------------------------------------------
# COLLABORATION TOOLS (1 tool)
# -----------------------------------------------------------------------------

@router.get("/groups/{group_id}/messages")
async def read_group_messages(
    group_id: str,
    limit: int = Query(10, ge=1, le=100)
):
    """Read messages from VETKA group chat"""
    tool = GroupMessagesTool()
    try:
        result = await tool.execute({"group_id": group_id, "limit": limit})
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# -----------------------------------------------------------------------------
# WRITE TOOLS (3 tools)
# -----------------------------------------------------------------------------

@router.post("/files/edit")
async def edit_file(request: Dict[str, Any]):
    """Edit or create a file. Default: dry_run=true (preview only)"""
    tool = SharedEditFileTool()
    path = request.get("path")
    content = request.get("content")
    if not path or content is None:
        return {"success": False, "error": "Missing path or content"}
    try:
        result = await tool.execute({
            "path": path,
            "content": content,
            "mode": request.get("mode", "write"),
            "create_dirs": request.get("create_dirs", False),
            "dry_run": request.get("dry_run", True),
        })
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/git/commit")
async def git_commit(request: Dict[str, Any]):
    """Create a git commit. Default: dry_run=true (preview only)"""
    tool = SharedGitCommitTool()
    message = request.get("message")
    if not message:
        return {"success": False, "error": "Missing commit message"}
    try:
        result = await tool.execute({
            "message": message,
            "files": request.get("files", []),
            "dry_run": request.get("dry_run", True),
        })
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/git/status")
async def git_status():
    """Get git status showing modified, staged, and untracked files"""
    tool = SharedGitStatusTool()
    try:
        result = await tool.execute({})
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# -----------------------------------------------------------------------------
# EXECUTION TOOLS (3 tools)
# -----------------------------------------------------------------------------

@router.post("/tests/run")
async def run_tests(request: Dict[str, Any]):
    """Run pytest tests with output capture"""
    tool = SharedRunTestsTool()
    try:
        result = await tool.execute({
            "test_path": request.get("test_path", "tests/"),
            "pattern": request.get("pattern"),
            "verbose": request.get("verbose", True),
            "timeout": request.get("timeout", 60),
        })
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/camera/focus")
async def camera_focus(request: Dict[str, Any]):
    """Move 3D camera to focus on a specific file or branch"""
    tool = SharedCameraFocusTool()
    target = request.get("target")
    if not target:
        return {"success": False, "error": "Missing target"}
    try:
        result = await tool.execute({
            "target": target,
            "zoom": request.get("zoom", "medium"),
            "highlight": request.get("highlight", True),
        })
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/model/call")
async def call_model(request: Dict[str, Any]):
    """Call any LLM model through VETKA infrastructure"""
    tool = SharedCallModelTool()
    model = request.get("model")
    messages = request.get("messages")
    if not model or not messages:
        return {"success": False, "error": "Missing model or messages"}
    try:
        result = await tool.execute({
            "model": model,
            "messages": messages,
            "temperature": request.get("temperature", 0.7),
            "max_tokens": request.get("max_tokens", 4096),
            "tools": request.get("tools"),
        })
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# -----------------------------------------------------------------------------
# MEMORY TOOLS (3 tools)
# -----------------------------------------------------------------------------

@router.get("/context")
async def get_conversation_context(
    group_id: Optional[str] = Query(None, description="Group ID"),
    max_messages: int = Query(20, ge=1, le=100),
    compress: bool = Query(True, description="Apply ELISION compression")
):
    """Get ELISION-compressed conversation context for prompt injection"""
    tool = ConversationContextTool()
    try:
        args = {"max_messages": max_messages, "compress": compress}
        if group_id:
            args["group_id"] = group_id
        result = await tool.execute(args)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/preferences")
async def get_user_preferences(
    user_id: str = Query("danila", description="User ID"),
    category: Optional[str] = Query(
        None,
        enum=["communication_style", "viewport_patterns", "code_preferences", "topics", "all"]
    )
):
    """Get user preferences from Engram memory"""
    tool = UserPreferencesTool()
    try:
        args = {"user_id": user_id}
        if category:
            args["category"] = category
        result = await tool.execute(args)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/memory/summary")
async def get_memory_summary(
    include_stats: bool = Query(True, description="Include compression stats"),
    include_nodes: bool = Query(False, description="Include memory nodes list")
):
    """Get CAM (Context-Aware Memory) and Elisium compression summary"""
    tool = MemorySummaryTool()
    try:
        result = await tool.execute({
            "include_stats": include_stats,
            "include_nodes": include_nodes,
        })
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
