"""
VETKA Debug Routes - Browser Agent Bridge

@file debug_routes.py
@status ACTIVE
@phase Phase 80.3
@lastAudit 2026-01-21

Debug API endpoints for external agents (Browser Claude, etc).
These endpoints provide access to VETKA's internal state and limited
control capabilities, allowing browser-based AI assistants to help
with debugging and visualization.

Endpoints (READ-ONLY):
- GET /api/debug/inspect - Full tree state inspection
- GET /api/debug/formulas - Current layout formulas and values
- GET /api/debug/tree-state - Quick tree health check
- GET /api/debug/recent-errors - Last N errors from logs
- GET /api/debug/modes - Current mode states (blend values, etc)
- GET /api/debug/chat-context - Get current chat context (like internal agents)

Endpoints (ACTIONS):
- POST /api/debug/camera-focus - Control 3D camera position
"""

from fastapi import APIRouter, Request, Query, Body
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncio
import logging
import json  # MARKER_137.S2_FIX: Required for heartbeat config save
import os    # MARKER_137.S2_FIX: Required for env sync
import time
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/debug", tags=["debug"])


# ============================================================
# INTERNAL STATE TRACKERS
# ============================================================

# Recent errors buffer (circular buffer, max 100)
_recent_errors: List[Dict[str, Any]] = []
_max_errors = 100

# Debug log buffer
_debug_logs: List[Dict[str, Any]] = []
_max_logs = 200

# Detached media debug snapshots (latest-first, small rolling buffer)
_media_window_snapshots: List[Dict[str, Any]] = []
_max_media_window_snapshots = 25

# ============================================================
# PHASE 80.2: AGENT-TO-AGENT TEAM CHAT
# ============================================================
# Simple in-memory message buffer for browser agents to communicate
# with Claude Code (MCP) through VETKA

team_messages: List[Dict[str, Any]] = []
_max_team_messages = 100

# Alias for backward compatibility
_team_messages = team_messages

# Known agent identities with display info
# Using Lucide icon names for frontend SVG rendering
# Phase 80.3: Strict monochrome design - white/gray/black only
KNOWN_AGENTS = {
    "browser_haiku": {
        "name": "Browser Haiku",
        "icon": "eye",  # Lucide: eye icon (tester/observer)
        "role": "Tester",
        "description": "QA/Observer in Chrome Console",
        "can_modify": False,
        "capabilities": ["testing", "chat", "vision"],
        "model_id": "mcp/browser_haiku"  # Links to ModelRegistry
    },
    "claude_code": {
        "name": "Claude Code",
        "icon": "terminal",  # Lucide: terminal icon
        "role": "Executor",
        "description": "Code executor with MCP access",
        "can_modify": True,
        "capabilities": ["code", "reasoning", "execute"],
        "model_id": "mcp/claude_code"  # Links to ModelRegistry
    },
    "vetka_internal": {
        "name": "VETKA Agent",
        "icon": "tree-pine",  # Lucide: tree-pine icon
        "role": "Orchestrator",
        "description": "Internal orchestrator agent",
        "can_modify": True,
        "capabilities": ["reasoning", "chat"],
        "model_id": None  # Internal, no ModelRegistry entry
    },
    "user": {
        "name": "Human",
        "icon": "user",  # Lucide: user icon
        "role": "Owner",
        "description": "Project owner",
        "can_modify": True,
        "capabilities": ["all"],
        "model_id": None  # Human, no ModelRegistry entry
    },
    # MARKER_117_2A: Pipeline agent for Mycelium/Dragon streaming
    "pipeline": {
        "name": "Mycelium Pipeline",
        "icon": "git-branch",  # Lucide: git-branch icon (fractal pipeline)
        "role": "Pipeline",
        "description": "Fractal agent pipeline (Architect → Researcher → Coder)",
        "can_modify": False,
        "capabilities": ["reasoning", "chat", "code"],
        "model_id": None  # Pipeline uses multiple models internally
    },
    # MARKER_117_3: System command agents for UI display
    "dragon": {
        "name": "Dragon",
        "icon": "flame",
        "role": "Orchestrator",
        "description": "Mycelium Dragon — autonomous task executor",
        "can_modify": False,
        "capabilities": ["reasoning", "code", "chat"],
        "model_id": None
    },
    "doctor": {
        "name": "Doctor",
        "icon": "stethoscope",
        "role": "Diagnostic",
        "description": "VETKA diagnostics — health checks and issue detection",
        "can_modify": False,
        "capabilities": ["reasoning", "chat"],
        "model_id": None
    },
}


def log_debug(message: str, category: str = "general", data: Optional[Dict] = None):
    """Add entry to debug log buffer."""
    global _debug_logs
    _debug_logs.append({
        "timestamp": time.time(),
        "message": message,
        "category": category,
        "data": data or {}
    })
    if len(_debug_logs) > _max_logs:
        _debug_logs = _debug_logs[-_max_logs:]


def log_error(error: str, source: str = "unknown", details: Optional[Dict] = None):
    """Add error to recent errors buffer."""
    global _recent_errors
    _recent_errors.append({
        "timestamp": time.time(),
        "error": error,
        "source": source,
        "details": details or {}
    })
    if len(_recent_errors) > _max_errors:
        _recent_errors = _recent_errors[-_max_errors:]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_memory_manager(request: Request):
    """Get memory manager from app state or singleton."""
    memory = getattr(request.app.state, 'memory_manager', None)
    if not memory:
        try:
            from src.initialization.components_init import get_memory_manager
            memory = get_memory_manager()
        except Exception:
            pass
    return memory


def _get_jarvis_traces(limit: int = 20) -> List[Dict[str, Any]]:
    try:
        from src.api.handlers.jarvis_handler import get_jarvis_turn_traces
        return get_jarvis_turn_traces(limit=limit)
    except Exception as e:
        logger.debug(f"[debug_routes] Jarvis traces unavailable: {e}")
        return []


def _get_layout_constants() -> Dict[str, Any]:
    """Get current layout formula constants."""
    try:
        from src.layout.fan_layout import (
            Y_PER_DEPTH,
            BRANCH_LENGTH,
            FAN_ANGLE,
            FILE_SPACING
        )
        return {
            "Y_PER_DEPTH": Y_PER_DEPTH,
            "BRANCH_LENGTH": BRANCH_LENGTH,
            "FAN_ANGLE": FAN_ANGLE,
            "FILE_SPACING": FILE_SPACING
        }
    except ImportError:
        return {"error": "fan_layout module not available"}


# ============================================================
# DEBUG ENDPOINTS
# ============================================================

@router.get("/inspect")
async def debug_inspect(
    keyword: str = Query("", description="Filter results by keyword"),
    request: Request = None
) -> Dict[str, Any]:
    """
    Full tree state inspection for browser agents.

    Returns comprehensive state including:
    - Tree statistics (nodes, edges, files, folders)
    - Active modes and blend values
    - Layout constants
    - Component status
    - Recent activity

    Query params:
    - keyword: Optional filter for specific data (e.g., "blend", "error", "mode")
    """
    memory = _get_memory_manager(request)
    qdrant = memory.qdrant if memory else None

    result = {
        "timestamp": time.time(),
        "vetka_phase": "80",
        "keyword_filter": keyword if keyword else None,

        # Core state
        "qdrant_connected": qdrant is not None,
        "memory_manager_active": memory is not None,

        # Layout formulas
        "layout_constants": _get_layout_constants(),

        # Tree stats (if available)
        "tree_stats": {},

        # Mode states
        "modes": {
            "description": "Mode blend values - check frontend for actual state",
            "available_modes": ["directory", "knowledge", "semantic", "force_directed"]
        },

        # Component availability
        "components": {},

        # Recent activity
        "recent_errors_count": len(_recent_errors),
        "recent_logs_count": len(_debug_logs)
    }

    # Get component status
    if request and hasattr(request.app, 'state'):
        components = [
            'orchestrator', 'memory_manager', 'model_router',
            # 'api_gateway',  # REMOVED: Phase 95
            'eval_agent', 'metrics_engine'
        ]
        for comp in components:
            instance = getattr(request.app.state, comp, None)
            result["components"][comp] = {
                "available": instance is not None,
                "type": type(instance).__name__ if instance else None
            }

    # Get tree stats from Qdrant
    if qdrant:
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Count files
            files_count = qdrant.count(
                collection_name='vetka_elisya',
                count_filter=Filter(
                    must=[FieldCondition(key="type", match=MatchValue(value="scanned_file"))]
                )
            )
            result["tree_stats"]["total_files"] = files_count.count
        except Exception as e:
            result["tree_stats"]["error"] = str(e)

    # Apply keyword filter if provided
    if keyword:
        filtered = {}
        keyword_lower = keyword.lower()
        for key, value in result.items():
            if keyword_lower in key.lower():
                filtered[key] = value
            elif isinstance(value, dict):
                sub_filtered = {k: v for k, v in value.items() if keyword_lower in k.lower()}
                if sub_filtered:
                    filtered[key] = sub_filtered
        if filtered:
            return {"filtered_by": keyword, "results": filtered, "full_keys": list(result.keys())}

    return result


@router.get("/jarvis/traces")
async def get_jarvis_traces(limit: int = Query(20, ge=1, le=200)) -> Dict[str, Any]:
    """
    Phase 157.5.1: return latest Jarvis per-turn traces.
    """
    traces = _get_jarvis_traces(limit=limit)
    return {
        "count": len(traces),
        "limit": limit,
        "items": traces,
    }


@router.get("/formulas")
async def debug_formulas(
    mode: str = Query("directory", description="Layout mode to inspect")
) -> Dict[str, Any]:
    """
    Return current layout formula values for debugging.

    Helps browser agents understand why tree looks a certain way.
    """
    layout_constants = _get_layout_constants()

    # Get mode-specific info
    mode_info = {
        "directory": {
            "description": "Fan layout based on folder hierarchy",
            "key_factors": ["Y_PER_DEPTH", "BRANCH_LENGTH", "FAN_ANGLE"],
            "typical_values": {
                "Y_PER_DEPTH": 100,
                "BRANCH_LENGTH": 50,
                "FAN_ANGLE": 60
            }
        },
        "knowledge": {
            "description": "Tag-based semantic clustering",
            "key_factors": ["similarity_threshold", "min_cluster_size"],
            "typical_values": {
                "similarity_threshold": 0.7,
                "min_cluster_size": 3
            }
        },
        "force_directed": {
            "description": "Physics-based force simulation",
            "key_factors": ["repulsion", "attraction", "damping"],
            "typical_values": {
                "repulsion": 500,
                "attraction": 0.01,
                "damping": 0.9
            }
        }
    }

    return {
        "requested_mode": mode,
        "current_constants": layout_constants,
        "mode_details": mode_info.get(mode, {"error": f"Unknown mode: {mode}"}),
        "all_modes": list(mode_info.keys()),
        "note": "These are server-side values. Frontend may have different blend states."
    }


@router.get("/tree-state")
async def debug_tree_state(request: Request = None) -> Dict[str, Any]:
    """
    Quick tree health check for browser agents.

    Returns condensed tree status suitable for quick debugging.
    """
    memory = _get_memory_manager(request)
    qdrant = memory.qdrant if memory else None

    if not qdrant:
        return {
            "healthy": False,
            "error": "Qdrant not connected",
            "suggestion": "Check if Qdrant is running on port 6333"
        }

    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        # Quick counts
        files_count = qdrant.count(
            collection_name='vetka_elisya',
            count_filter=Filter(
                must=[FieldCondition(key="type", match=MatchValue(value="scanned_file"))]
            )
        )

        # Collection info
        collection_info = qdrant.get_collection('vetka_elisya')

        return {
            "healthy": True,
            "collection": "vetka_elisya",
            "files_count": files_count.count,
            "vectors_count": collection_info.vectors_count,
            "points_count": collection_info.points_count,
            "indexed_percent": round((collection_info.indexed_vectors_count or 0) / max(collection_info.vectors_count or 1, 1) * 100, 1),
            "status": collection_info.status.value if collection_info.status else "unknown"
        }
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "suggestion": "Check Qdrant connection and collection existence"
        }


@router.get("/recent-errors")
async def debug_recent_errors(
    limit: int = Query(20, description="Number of errors to return"),
    source_filter: str = Query("", description="Filter by error source")
) -> Dict[str, Any]:
    """
    Get recent errors for debugging.

    Browser agents can use this to understand what went wrong.
    """
    errors = _recent_errors[-limit:] if _recent_errors else []

    if source_filter:
        errors = [e for e in errors if source_filter.lower() in e.get("source", "").lower()]

    return {
        "total_errors": len(_recent_errors),
        "returned": len(errors),
        "errors": errors,
        "filter_applied": source_filter if source_filter else None
    }


@router.get("/logs")
async def debug_logs(
    limit: int = Query(50, description="Number of log entries to return"),
    category: str = Query("", description="Filter by category")
) -> Dict[str, Any]:
    """
    Get recent debug logs.

    Useful for browser agents to trace execution flow.
    """
    logs = _debug_logs[-limit:] if _debug_logs else []

    if category:
        logs = [l for l in logs if category.lower() in l.get("category", "").lower()]

    return {
        "total_logs": len(_debug_logs),
        "returned": len(logs),
        "logs": logs,
        "filter_applied": category if category else None,
        "available_categories": list(set(l.get("category", "general") for l in _debug_logs))
    }


@router.post("/media-window-snapshot")
async def debug_media_window_snapshot_ingest(
    body: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Store latest detached media geometry snapshot from renderer debug tooling.

    Intended for VETKA/MCC/MCP diagnostics so agents can inspect the latest
    detached media native-vs-DOM geometry without attaching to the renderer console.
    """
    src = str(body.get("src") or "").strip()
    path = str(body.get("path") or "").strip()

    entry = {
        "timestamp": time.time(),
        "src": src or "media",
        "path": path,
        "snapshot": body,
    }

    _media_window_snapshots.append(entry)
    if len(_media_window_snapshots) > _max_media_window_snapshots:
        del _media_window_snapshots[:-_max_media_window_snapshots]

    log_debug(
        f"Detached media snapshot stored for {entry['src']}",
        category="media_window",
        data={
            "path": path,
            "horizontalLetterboxPx": body.get("horizontalLetterboxPx"),
            "nativeInnerLogicalWidth": body.get("nativeInnerLogicalWidth"),
            "nativeInnerLogicalHeight": body.get("nativeInnerLogicalHeight"),
        },
    )

    return {
        "success": True,
        "stored": len(_media_window_snapshots),
        "latest": entry,
    }


@router.get("/media-window-snapshot")
async def debug_media_window_snapshot(
    path: str = Query("", description="Optional exact media path filter"),
    src: str = Query("", description="Optional source/name substring filter"),
) -> Dict[str, Any]:
    """
    Get the latest detached media debug snapshot captured from renderer tooling.
    """
    snapshots = list(_media_window_snapshots)

    if path:
        snapshots = [s for s in snapshots if str(s.get("path") or "") == path]
    if src:
        snapshots = [s for s in snapshots if src.lower() in str(s.get("src") or "").lower()]

    latest = snapshots[-1] if snapshots else None
    return {
        "total_snapshots": len(_media_window_snapshots),
        "returned": len(snapshots),
        "latest": latest,
        "available_sources": sorted({str(s.get("src") or "") for s in _media_window_snapshots if s.get("src")}),
        "filter_applied": {
            "path": path or None,
            "src": src or None,
        },
    }


@router.get("/modes")
async def debug_modes(request: Request = None) -> Dict[str, Any]:
    """
    Get information about available visualization modes.

    Returns mode descriptions and current server-side state.
    Note: Actual blend values are controlled by frontend.
    """
    # Check caches
    from src.api.routes.tree_routes import _semantic_cache, _knowledge_graph_cache

    return {
        "modes": {
            "directory": {
                "name": "Directory Mode",
                "description": "Shows file system hierarchy as a 3D fan tree",
                "layout": "Fan layout with Y_PER_DEPTH vertical spacing",
                "cache_key": "_semantic_cache",
                "cached": _semantic_cache.get('nodes') is not None
            },
            "knowledge": {
                "name": "Knowledge Mode",
                "description": "Groups files by semantic tags into clusters",
                "layout": "Tag-centric with files orbiting tags",
                "cache_key": "_knowledge_graph_cache",
                "cached": _knowledge_graph_cache.get('tags') is not None
            },
            "force_directed": {
                "name": "Force-Directed Mode",
                "description": "Physics simulation with attraction/repulsion",
                "layout": "Dynamic - positions calculated in real-time on frontend",
                "cached": False
            },
            "sugiyama": {
                "name": "Sugiyama (Layered) Mode",
                "description": "Hierarchical DAG layout with layer assignment",
                "layout": "Layers based on dependency depth",
                "status": "experimental"
            }
        },
        "note": "Blend values between modes are controlled by frontend. This endpoint shows server-side cache status.",
        "tip": "Use /api/tree/data?mode=X to fetch specific mode data"
    }


@router.get("/agent-info")
async def debug_agent_info() -> Dict[str, Any]:
    """
    Information for browser-based AI agents about how to use this API.

    This endpoint explains the debug API capabilities to agents.
    """
    return {
        "welcome": "VETKA Debug API for Browser Agents",
        "version": "1.1",
        "phase": "80.1",

        "capabilities": {
            "read_only": False,
            "can_read": True,
            "can_control_camera": True,
            "can_modify_code": False,
            "purpose": "Allow browser-based AI assistants to help debug VETKA and control visualization"
        },

        "endpoints": {
            "/api/debug/inspect": "Full state inspection with optional keyword filter",
            "/api/debug/formulas": "Layout formula values for specific modes",
            "/api/debug/tree-state": "Quick health check of tree data",
            "/api/debug/recent-errors": "Last N errors for debugging",
            "/api/debug/logs": "Debug log entries with category filter",
            "/api/debug/modes": "Information about visualization modes",
            "/api/debug/chat-context": "Get current chat context (same as internal agents)",
            "/api/debug/camera-focus": "POST - Control 3D camera position",
            "/api/debug/agent-info": "This help endpoint"
        },

        "usage_pattern": [
            "1. Call /api/debug/tree-state to check if tree is healthy",
            "2. Call /api/debug/inspect to see full state",
            "3. Call /api/debug/chat-context to see what agents see",
            "4. Call /api/debug/camera-focus to highlight files visually",
            "5. Report findings to Claude Code for actual code fixes"
        ],

        "important": "Code modifications must go through Claude Code with MCP access. Camera and visualization control is allowed.",

        "browser_console": {
            "tip": "You can also call these via window.vetkaAPI if the bridge is loaded",
            "example": "window.vetkaAPI.quickStatus()"
        }
    }


# ============================================================
# CAMERA CONTROL (ACTION ENDPOINT)
# ============================================================

from pydantic import BaseModel

class CameraFocusRequest(BaseModel):
    """Request body for camera focus."""
    target: str  # File path, branch name, or 'overview'
    zoom: str = "medium"  # close, medium, far
    highlight: bool = True
    animate: bool = True


@router.post("/camera-focus")
async def debug_camera_focus(
    request: Request,
    body: CameraFocusRequest
) -> Dict[str, Any]:
    """
    Control 3D camera position from browser agent.

    This allows browser agents to show users specific files or areas
    in the 3D visualization.

    Body params:
    - target: File path (e.g., 'src/main.py'), branch name, or 'overview'
    - zoom: 'close', 'medium', or 'far'
    - highlight: Whether to highlight the target with glow effect
    - animate: Whether to animate the camera movement
    """
    try:
        # Get SocketIO from app state
        socketio = getattr(request.app.state, 'socketio', None)

        if not socketio:
            # Try to get from MCP server
            try:
                from src.mcp.mcp_server import get_mcp_server
                mcp = get_mcp_server()
                if mcp:
                    socketio = mcp.socketio
            except Exception:
                pass

        if socketio:
            # Emit camera control event (await for AsyncServer)
            await socketio.emit('camera_control', {
                'action': 'focus',
                'target': body.target,
                'zoom': body.zoom,
                'highlight': body.highlight,
                'animate': body.animate,
                'source': 'browser_agent'  # Mark source for logging
            }, namespace='/')

            log_debug(
                f"Camera focus: {body.target} (zoom={body.zoom})",
                category="camera",
                data={"target": body.target, "zoom": body.zoom}
            )

            return {
                "success": True,
                "message": f"Camera focusing on '{body.target}'",
                "params": {
                    "target": body.target,
                    "zoom": body.zoom,
                    "highlight": body.highlight,
                    "animate": body.animate
                }
            }
        else:
            return {
                "success": False,
                "error": "SocketIO not available - frontend may not be connected",
                "suggestion": "Make sure VETKA 3D is open in browser"
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# CHAT CONTEXT (SAME DATA AS INTERNAL AGENTS)
# ============================================================

@router.get("/chat-context")
async def debug_chat_context(
    request: Request,
    include_history: bool = Query(False, description="Include recent chat history"),
    history_limit: int = Query(10, description="Number of history messages to include")
) -> Dict[str, Any]:
    """
    Get current chat context - the same summary that internal agents receive.

    This allows browser agents to understand the current state of conversation
    and project context, just like internal VETKA agents do.

    Query params:
    - include_history: Whether to include recent chat messages
    - history_limit: How many messages to include (default 10)
    """
    memory = _get_memory_manager(request)
    orchestrator = getattr(request.app.state, 'orchestrator', None)

    context = {
        "timestamp": time.time(),
        "vetka_phase": "80.1",

        # Project context
        "project": {
            "name": "VETKA",
            "description": "3D Knowledge Graph Visualization System",
            "current_phase": "80.1 - Browser Agent Bridge"
        },

        # Tree summary
        "tree_summary": {},

        # Active components
        "active_components": [],

        # Recent activity summary
        "recent_activity": {
            "errors_count": len(_recent_errors),
            "logs_count": len(_debug_logs),
            "last_error": _recent_errors[-1] if _recent_errors else None
        },

        # Chat history (optional)
        "chat_history": []
    }

    # Get tree summary
    if memory and memory.qdrant:
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            files_count = memory.qdrant.count(
                collection_name='vetka_elisya',
                count_filter=Filter(
                    must=[FieldCondition(key="type", match=MatchValue(value="scanned_file"))]
                )
            )

            context["tree_summary"] = {
                "total_files": files_count.count,
                "collection": "vetka_elisya",
                "indexed": True
            }
        except Exception as e:
            context["tree_summary"] = {"error": str(e)}

    # Get active components
    if request and hasattr(request.app, 'state'):
        components = ['orchestrator', 'memory_manager', 'model_router', 'eval_agent']  # 'api_gateway' removed Phase 95
        for comp in components:
            if getattr(request.app.state, comp, None):
                context["active_components"].append(comp)

    # Get chat history if requested
    if include_history:
        try:
            # Try to get from chat history file
            import json
            chat_history_path = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/chat_history.json"
            if os.path.exists(chat_history_path):
                with open(chat_history_path, 'r') as f:
                    history_data = json.load(f)
                    messages = history_data.get('messages', [])
                    context["chat_history"] = messages[-history_limit:] if messages else []
        except Exception as e:
            context["chat_history"] = [{"error": str(e)}]

    # Build agent-friendly summary
    context["summary_for_agent"] = (
        f"VETKA Phase {context['vetka_phase']}. "
        f"Tree has {context['tree_summary'].get('total_files', '?')} files indexed. "
        f"Active components: {', '.join(context['active_components']) or 'unknown'}. "
        f"Recent errors: {context['recent_activity']['errors_count']}."
    )

    return context


# ============================================================
# PHASE 80.2: AGENT-TO-AGENT TEAM MESSAGING
# ============================================================

class TeamMessageRequest(BaseModel):
    """Request body for sending a team message."""
    message: str  # The message content
    sender: str = "browser_haiku"  # Agent identifier
    to: str = "claude_code"  # Target agent (or 'all')
    priority: str = "normal"  # normal, high, urgent
    context: Optional[Dict[str, Any]] = None  # Additional context data


@router.post("/team-message")
async def send_team_message(
    request: Request,
    body: TeamMessageRequest
) -> Dict[str, Any]:
    """
    Send a message from browser agent to Claude Code (MCP agent).

    This enables cross-agent communication:
    - Browser Haiku can report findings
    - Claude Code can read messages and respond
    - Messages persist in memory buffer

    Phase 80.3: MCP Agents with Lucide icons (monochrome design):
    - browser_haiku (eye) - Tester: QA/Observer in Chrome Console
    - claude_code (terminal) - Executor: Code executor with MCP access
    - vetka_internal (tree-pine) - Orchestrator: Internal agent
    - user (user) - Owner: Human project owner

    Body params:
    - message: The message text
    - sender: Who is sending (default: 'browser_haiku')
    - to: Target agent (default: 'claude_code', or 'all')
    - priority: normal, high, urgent
    - context: Optional dict with additional data (e.g., file paths, error details)
    """
    global _team_messages

    # Get agent display info
    sender_info = KNOWN_AGENTS.get(body.sender, {
        "name": body.sender,
        "icon": "bot",
        "role": "Unknown",
        "description": "Unknown agent"
    })
    to_info = KNOWN_AGENTS.get(body.to, {
        "name": body.to,
        "icon": "bot",
        "role": "Unknown",
        "description": "Unknown agent"
    })

    msg = {
        "id": len(_team_messages) + 1,
        "timestamp": time.time(),
        "sender": body.sender,
        "sender_info": {
            "name": sender_info["name"],
            "icon": sender_info["icon"],
            "role": sender_info.get("role", "")
        },
        "to": body.to,
        "to_info": {
            "name": to_info["name"],
            "icon": to_info["icon"],
            "role": to_info.get("role", "")
        },
        "message": body.message,
        "priority": body.priority,
        "context": body.context or {},
        "read": False
    }

    _team_messages.append(msg)

    # Keep buffer limited
    if len(_team_messages) > _max_team_messages:
        _team_messages = _team_messages[-_max_team_messages:]

    # Log for debugging
    log_debug(
        f"Team message: {body.sender} → {body.to}: {body.message[:50]}...",
        category="team_chat",
        data={"msg_id": msg["id"], "priority": body.priority}
    )

    # Emit via SocketIO for real-time notification
    socketio = getattr(request.app.state, 'socketio', None)
    if socketio:
        try:
            await socketio.emit('team_message', {
                'id': msg["id"],
                'sender': body.sender,
                'to': body.to,
                'preview': body.message[:100],
                'priority': body.priority
            }, namespace='/')
        except Exception:
            pass  # Non-critical if emit fails

    return {
        "success": True,
        "message_id": msg["id"],
        "delivered_to": body.to,
        "timestamp": msg["timestamp"],
        "tip": "Claude Code can read this via /api/debug/team-messages or vetka MCP tools"
    }


@router.get("/team-messages")
async def get_team_messages(
    request: Request,
    limit: int = Query(20, description="Number of messages to return"),
    unread_only: bool = Query(False, description="Only return unread messages"),
    sender_filter: str = Query("", description="Filter by sender"),
    to_filter: str = Query("", description="Filter by recipient"),
    mark_read: bool = Query(False, description="Mark returned messages as read")
) -> Dict[str, Any]:
    """
    Get team messages (for Claude Code to read Browser Haiku's reports).

    Query params:
    - limit: Max messages to return (default 20)
    - unread_only: Only unread messages
    - sender_filter: Filter by sender (e.g., 'browser_haiku')
    - to_filter: Filter by recipient (e.g., 'claude_code')
    - mark_read: Mark returned messages as read

    Returns messages newest first.
    """
    global _team_messages

    # Start with all messages, reversed (newest first)
    messages = list(reversed(_team_messages))

    # Apply filters
    if unread_only:
        messages = [m for m in messages if not m.get("read", False)]

    if sender_filter:
        messages = [m for m in messages if sender_filter.lower() in m.get("sender", "").lower()]

    if to_filter:
        messages = [m for m in messages if to_filter.lower() in m.get("to", "").lower() or m.get("to") == "all"]

    # Limit
    messages = messages[:limit]

    # Mark as read if requested
    if mark_read and messages:
        msg_ids = {m["id"] for m in messages}
        for m in _team_messages:
            if m["id"] in msg_ids:
                m["read"] = True

    # Stats
    total_unread = sum(1 for m in _team_messages if not m.get("read", False))

    return {
        "total_messages": len(_team_messages),
        "unread_count": total_unread,
        "returned": len(messages),
        "messages": messages,
        "filters": {
            "unread_only": unread_only,
            "sender": sender_filter or None,
            "to": to_filter or None
        }
    }


@router.get("/team-agents")
async def get_team_agents() -> Dict[str, Any]:
    """
    Get list of known team agents with their display info.

    Phase 80.3: MCP Agents with monochrome design (white/gray/black).
    Returns agent identities that can be used in team messages.
    Frontend uses Lucide icons for SVG rendering.
    """
    return {
        "agents": KNOWN_AGENTS,
        "usage": {
            "tip": "Use agent keys (e.g., 'browser_haiku', 'claude_code') in sender/to fields",
            "icons": "Icon names from Lucide icon library (https://lucide.dev)",
            "model_registry": "MCP agents also available via GET /api/models/mcp-agents"
        }
    }


# ============================================================
# PHASE 80.3: MCP AGENT ENDPOINTS (for Claude Code / Browser Haiku)
# ============================================================

@router.get("/mcp/pending/{agent_id}")
async def get_pending_for_agent(
    agent_id: str,
    mark_read: bool = Query(True, description="Mark messages as read")
) -> Dict[str, Any]:
    """
    Get pending messages for a specific MCP agent.

    This endpoint is designed for external MCP agents (Claude Code, Browser Haiku)
    to poll for messages addressed to them.

    Path params:
    - agent_id: Agent identifier (e.g., 'claude_code', 'browser_haiku')

    Query params:
    - mark_read: Mark returned messages as read (default True)

    Returns pending messages newest first.
    """
    global _team_messages

    # Get messages for this agent
    pending = [
        m for m in _team_messages
        if (m.get("to") == agent_id or m.get("to") == "all")
        and m.get("pending", False)
        and not m.get("read", False)
    ]

    # Sort newest first
    pending = sorted(pending, key=lambda x: x.get("timestamp", 0), reverse=True)

    # Mark as read if requested
    if mark_read and pending:
        msg_ids = {m.get("id") for m in pending}
        for m in _team_messages:
            if m.get("id") in msg_ids:
                m["read"] = True
                m["pending"] = False

    agent_info = KNOWN_AGENTS.get(agent_id, {"name": agent_id})

    return {
        "agent": agent_id,
        "agent_name": agent_info.get("name", agent_id),
        "pending_count": len(pending),
        "messages": pending,
        "welcome_info": {
            "chat_group_id": "542444da-fcb1-4e26-ac00-f414e2c43591",
            "chat_group_name": "Сугиями рабочая группа 2",
            "send_endpoint": "/api/debug/mcp/groups/{group_id}/send",
            "read_endpoint": "/api/debug/mcp/groups/{group_id}/messages",
            "config_file": ".claude-mcp-config.md",
            "tip": "Используй POST send_endpoint с body: {agent_id, sender, content} для отправки в чат"
        },
        "tip": f"Use POST /api/debug/mcp/respond/{agent_id} to send responses"
    }


class MCPResponseRequest(BaseModel):
    """Request body for MCP agent response."""
    message_id: Optional[str] = None  # Original message ID (optional)
    conversation_id: Optional[str] = None  # Conversation to respond to
    response: str  # Response text
    context: Optional[Dict[str, Any]] = None  # Additional context


@router.post("/mcp/respond/{agent_id}")
async def mcp_agent_respond(
    request: Request,
    agent_id: str,
    body: MCPResponseRequest
) -> Dict[str, Any]:
    """
    Send a response from MCP agent back to the chat.

    This endpoint allows Claude Code / Browser Haiku to respond to
    messages they received through team messaging.

    Path params:
    - agent_id: Agent identifier (e.g., 'claude_code', 'browser_haiku')

    Body params:
    - message_id: ID of message being responded to (optional)
    - conversation_id: Chat conversation to respond to (optional)
    - response: Response text
    - context: Additional context data
    """
    global _team_messages

    agent_info = KNOWN_AGENTS.get(agent_id, {
        "name": agent_id,
        "icon": "bot",
        "role": "MCP Agent"
    })

    import uuid

    # Create response message
    msg = {
        "id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "sender": agent_id,
        "sender_info": {
            "name": agent_info.get("name", agent_id),
            "icon": agent_info.get("icon", "bot"),
            "role": agent_info.get("role", "MCP Agent")
        },
        "to": "user",
        "to_info": KNOWN_AGENTS["user"],
        "message": body.response,
        "in_reply_to": body.message_id,
        "conversation_id": body.conversation_id,
        "context": body.context or {},
        "type": "mcp_response",
        "read": False
    }

    _team_messages.append(msg)

    # Keep buffer limited
    if len(_team_messages) > _max_team_messages:
        _team_messages[:] = _team_messages[-_max_team_messages:]

    # Log for debugging
    log_debug(
        f"MCP response: {agent_id} → user: {body.response[:50]}...",
        category="mcp_response",
        data={"msg_id": msg["id"], "conversation_id": body.conversation_id}
    )

    # Emit via SocketIO for real-time notification
    socketio = getattr(request.app.state, 'socketio', None)
    if socketio:
        try:
            await socketio.emit('mcp_response', {
                'id': msg["id"],
                'agent': agent_id,
                'agent_name': agent_info.get("name"),
                'response': body.response,
                'conversation_id': body.conversation_id
            }, namespace='/')
        except Exception:
            pass  # Non-critical if emit fails

    return {
        "success": True,
        "message_id": msg["id"],
        "agent": agent_id,
        "timestamp": msg["timestamp"],
        "note": "Response delivered to team messages and emitted via SocketIO"
    }


# ============================================================
# PHASE 80.4: MCP AGENTS IN GROUP CHAT
# ============================================================
# MCP agents (Claude Code, Browser Haiku) can read/write to group chats
# They are participants, not called models - they join when online

@router.get("/mcp/groups")
async def list_groups_for_mcp() -> Dict[str, Any]:
    """
    List all group chats for MCP agents to see.

    MCP agents can browse available groups and join conversations.
    """
    from src.services.group_chat_manager import get_group_chat_manager

    manager = get_group_chat_manager()
    groups = []

    for group_id, group in manager._groups.items():
        groups.append({
            "id": group_id,
            "name": group.name,
            "description": group.description,
            "participant_count": len(group.participants),
            "message_count": len(group.messages),
            "last_activity": group.last_activity.isoformat() if group.last_activity else None
        })

    return {
        "groups": groups,
        "count": len(groups),
        "tip": "Use GET /api/debug/mcp/groups/{group_id}/messages to read chat"
    }


@router.get("/mcp/groups/{group_id}/messages")
async def get_group_messages_for_mcp(
    group_id: str,
    limit: int = Query(50, description="Number of messages to return"),
    since_id: Optional[str] = Query(None, description="Get messages after this ID")
) -> Dict[str, Any]:
    """
    Read messages from a group chat.

    MCP agents use this to see the conversation and context.

    Path params:
    - group_id: Group UUID

    Query params:
    - limit: Max messages (default 50)
    - since_id: Only get messages after this ID (for polling)
    """
    from src.services.group_chat_manager import get_group_chat_manager

    manager = get_group_chat_manager()
    group = manager._groups.get(group_id)

    if not group:
        return {"error": f"Group not found: {group_id}", "groups_available": list(manager._groups.keys())}

    # Get messages
    messages = manager.get_messages(group_id, limit=limit)

    # Filter by since_id if provided
    if since_id and messages:
        found_idx = -1
        for i, m in enumerate(messages):
            if m.get("id") == since_id:
                found_idx = i
                break
        if found_idx >= 0:
            messages = messages[found_idx + 1:]

    # Get participants
    participants = []
    for pid, p in group.participants.items():
        participants.append({
            "agent_id": p.agent_id if hasattr(p, 'agent_id') else pid,
            "display_name": p.display_name if hasattr(p, 'display_name') else p.get('display_name', pid),
            "role": p.role.value if hasattr(p, 'role') and hasattr(p.role, 'value') else p.get('role', 'worker'),
            "model_id": p.model_id if hasattr(p, 'model_id') else p.get('model_id', 'unknown')
        })

    return {
        "group_id": group_id,
        "group_name": group.name,
        "participants": participants,
        "messages": messages,
        "message_count": len(messages),
        "tip": "Use POST /api/debug/mcp/groups/{group_id}/send to write"
    }


class MCPGroupMessageRequest(BaseModel):
    """Request for MCP agent to send message to group."""
    agent_id: str  # "claude_code" or "browser_haiku"
    content: str
    message_type: str = "chat"  # chat, response, system


@router.post("/mcp/groups/{group_id}/send")
async def send_group_message_from_mcp(
    request: Request,
    group_id: str,
    body: MCPGroupMessageRequest
) -> Dict[str, Any]:
    """
    Send a message to group chat as MCP agent.

    MCP agents (Claude Code, Browser Haiku) can participate in group chats
    by writing messages. They appear as regular participants.

    Path params:
    - group_id: Group UUID

    Body params:
    - agent_id: MCP agent identifier (claude_code, browser_haiku)
    - content: Message text
    - message_type: chat, response, or system
    """
    from src.services.group_chat_manager import get_group_chat_manager
    # Phase 86: Re-enabled imports - orchestrator exists in components_init
    from src.initialization.components_init import get_orchestrator
    from src.agents.role_prompts import get_agent_prompt
    import uuid
    import asyncio
    import re
    import time
    import traceback

    # Phase 80.16: Outer try/except to prevent Internal Server Error
    try:
        manager = get_group_chat_manager()
        group = manager._groups.get(group_id)

        if not group:
            return {"error": f"Group not found: {group_id}"}

        agent_info = KNOWN_AGENTS.get(body.agent_id, {
            "name": body.agent_id,
            "icon": "bot",
            "role": "MCP Agent"
        })

        # Format sender_id with @ prefix like other agents
        sender_id = f"@{agent_info.get('name', body.agent_id)}"

        # Send message through manager
        message = await manager.send_message(
            group_id=group_id,
            sender_id=sender_id,
            content=body.content,
            message_type=body.message_type,
            metadata={
                "mcp_agent": body.agent_id,
                "icon": agent_info.get("icon"),
                "role": agent_info.get("role")
            }
        )

        if not message:
            return {"error": "Failed to send message"}

        # Phase 80.28: Increment decay for MCP messages (enables smart reply chains)
        # MCP agents get 2 message decay (more generous than user's 1)
        group.last_responder_decay += 1
        print(f"[MCP] Phase 80.28: MCP message, decay now {group.last_responder_decay}")

        # MARKER_108_4: Real-time MCP ↔ VETKA bridge via Socket.IO
        # Phase 80.14: Improved MCP message emit with detailed logging
        # MCP agents (Claude Code, Browser Haiku) send messages via REST API
        # This endpoint broadcasts them to all clients in real-time via Socket.IO
        socketio = getattr(request.app.state, 'socketio', None)
        room = f'group_{group_id}'
        print(f"[MCP] Phase 80.14: Sending message to group {group_id}, socketio={'present' if socketio else 'None'}")

        if socketio:
            try:
                print(f"[MCP] Emitting 'group_message' to room {room}")
                await socketio.emit('group_message', message.to_dict(), room=room)

                # Also emit stream_end for UI consistency
                stream_end_data = {
                    'id': message.id,
                    'group_id': group_id,
                    'agent_id': sender_id,
                    'full_message': body.content,
                    'metadata': {
                        'mcp_agent': body.agent_id,
                        'agent_type': agent_info.get('role', 'MCP')
                    }
                }
                print(f"[MCP] Emitting 'group_stream_end' to room {room}")
                await socketio.emit('group_stream_end', stream_end_data, room=room)
                print(f"[MCP] Phase 80.14: Emit successful for message {message.id}")
            except Exception as e:
                print(f"[MCP] Phase 80.14: SocketIO emit error: {e}")
                traceback.print_exc()
        else:
            print(f"[MCP] Phase 80.14: SocketIO not available - message stored but not broadcast")

        # Phase 80.16: Safe content slicing with fallback
        content_preview = body.content[:50] if body.content else ""
        log_debug(
            f"MCP group message: {body.agent_id} → {group.name}: {content_preview}...",
            category="mcp_group",
            data={"group_id": group_id, "message_id": message.id}
        )

        # Phase 86: Re-enabled agent trigger for @mentions
        # select_responding_agents() will parse @mentions and return agents to call
        # Phase 80.28: Pass group object for smart reply decay (MCP→Agent chains)
        print(f"[MCP_AGENT_TRIGGER] Phase 80.16: Calling select_responding_agents for content: {body.content[:100] if body.content else 'empty'}...")
        participants_to_respond = await manager.select_responding_agents(
            content=body.content,
            participants=group.participants,
            sender_id=sender_id,
            reply_to_agent=None,  # MCP messages don't have reply context
            group=group  # Phase 80.28: Enable smart reply decay for MCP
        )

        print(f"[MCP_AGENT_TRIGGER] Phase 86: select_responding_agents returned {len(participants_to_respond)} agents")

        if participants_to_respond:
            print(f"[MCP_AGENT_TRIGGER] {len(participants_to_respond)} agents to respond: {[getattr(p, 'agent_id', 'unknown') for p in participants_to_respond]}")

            orchestrator = get_orchestrator()
            if not orchestrator:
                # Phase 80.16: Log detailed error when orchestrator is None
                print(f"[MCP_ERROR] Phase 80.16: Orchestrator is None! Cannot call agents.")
                print(f"[MCP_ERROR] This usually means the app was not initialized properly or AGENT_ORCHESTRATOR_CLASS is missing from app config.")
                # Continue without failing - message was already saved
            else:
                # Track previous outputs for chain context
                previous_outputs = {}

                # Process agents sequentially
                for participant in participants_to_respond:
                    # Phase 80.16: Safe participant data extraction with defaults
                    # Phase 80.41: Fix for GroupParticipant objects (not dicts)
                    agent_id = getattr(participant, 'agent_id', 'unknown')
                    model_id = getattr(participant, 'model_id', 'auto')
                    display_name = getattr(participant, 'display_name', 'Agent')
                    role = getattr(participant, 'role', 'worker')

                    # Map group role to orchestrator agent type
                    agent_type_map = {
                        'PM': 'PM', 'pm': 'PM',
                        'Dev': 'Dev', 'dev': 'Dev',
                        'QA': 'QA', 'qa': 'QA',
                        'Architect': 'Architect', 'architect': 'Architect',
                        'Researcher': 'Researcher', 'researcher': 'Researcher',
                        'admin': 'PM', 'worker': 'Dev'
                    }
                    agent_type = agent_type_map.get(display_name, agent_type_map.get(role, 'Dev'))

                    print(f"[MCP_AGENT_TRIGGER] Calling agent {agent_id} ({model_id}) as {agent_type}...")

                    # Emit typing indicator
                    if socketio:
                        await socketio.emit('group_typing', {
                            'group_id': group_id,
                            'agent_id': agent_id
                        }, room=f'group_{group_id}')

                    # Emit stream start
                    msg_id = str(uuid.uuid4())
                    if socketio:
                        await socketio.emit('group_stream_start', {
                            'id': msg_id,
                            'group_id': group_id,
                            'agent_id': agent_id,
                            'model': model_id
                        }, room=f'group_{group_id}')

                    try:
                        # Build role-specific prompt with chain context
                        system_prompt = get_agent_prompt(agent_type)

                        # Build recent messages context
                        recent_messages = manager.get_messages(group_id, limit=5)
                        context_parts = [
                            f"## ROLE\n{system_prompt}\n",
                            f"## GROUP: {group.name}\n",
                        ]

                        # Add chain context if other agents have responded
                        if previous_outputs:
                            context_parts.append("## PREVIOUS AGENT OUTPUTS")
                            for agent_name, output in previous_outputs.items():
                                context_parts.append(f"[{agent_name}]: {output[:400]}...")
                            context_parts.append("")

                        # Add recent conversation
                        context_parts.append("## RECENT CONVERSATION")
                        for msg in recent_messages:
                            msg_content = msg.get('content', '')[:200]
                            context_parts.append(f"[{msg.get('sender_id')}]: {msg_content}")

                        # Current request
                        context_parts.append(f"\n## CURRENT REQUEST\n{body.content}")

                        prompt = "\n".join(context_parts)

                        # Call agent through orchestrator
                        call_start = time.time()

                        try:
                            result = await asyncio.wait_for(
                                orchestrator.call_agent(
                                    agent_type=agent_type,
                                    model_id=model_id,
                                    prompt=prompt,
                                    context={
                                        'group_id': group_id,
                                        'group_name': group.name,
                                        'agent_id': agent_id,
                                        'display_name': display_name
                                    }
                                ),
                                timeout=120.0  # 2 minute timeout
                            )
                        except asyncio.TimeoutError:
                            print(f"[MCP_ERROR] Timeout after 120s calling {agent_type}")
                            result = {'status': 'error', 'error': 'Timeout after 120 seconds'}

                        call_elapsed = time.time() - call_start
                        print(f"[MCP_AGENT_TRIGGER] call_agent returned in {call_elapsed:.2f}s, status={result.get('status')}")

                        if result.get('status') == 'done':
                            response_text = result.get('output', '')
                        else:
                            response_text = f"[Error: {result.get('error', 'Unknown error')}]"

                        # Store for chain context
                        previous_outputs[display_name] = response_text[:500]

                        # Store agent response in group
                        agent_message = await manager.send_message(
                            group_id=group_id,
                            sender_id=agent_id,
                            content=response_text,
                            message_type='response',
                            metadata={'in_reply_to': message.id}
                        )

                        # Emit stream end with full response
                        if socketio:
                            await socketio.emit('group_stream_end', {
                                'id': msg_id,
                                'group_id': group_id,
                                'agent_id': agent_id,
                                'full_message': response_text,
                                'metadata': {
                                    'model': model_id,
                                    'agent_type': agent_type
                                }
                            }, room=f'group_{group_id}')

                        # Broadcast agent response
                        if agent_message and socketio:
                            await socketio.emit('group_message', agent_message.to_dict(), room=f'group_{group_id}')

                        # Phase 80.28: Track last responder for MCP→Agent smart reply chains
                        if result.get('status') == 'done':
                            group.last_responder_id = agent_id
                            group.last_responder_decay = 0  # Reset decay after successful response
                            print(f"[MCP_AGENT_TRIGGER] Phase 80.28: last_responder={agent_id}, decay reset")

                        print(f"[MCP_AGENT_TRIGGER] Agent {agent_id} responded: {len(response_text)} chars")

                        # Check for @mentions in agent response to trigger other agents
                        # MARKER_108_ROUTING_FIX_4: Support hyphenated model names
                        agent_mentions = re.findall(r'@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)', response_text)
                        if agent_mentions:
                            print(f"[MCP_AGENT_TRIGGER] Agent {display_name} mentioned: {agent_mentions}")

                            for mentioned_name in agent_mentions:
                                # Skip self-mentions and already-responded agents
                                if mentioned_name.lower() == display_name.lower():
                                    continue
                                if mentioned_name in previous_outputs:
                                    continue

                                # Find mentioned agent in participants
                                for pid, pdata in group.participants.items():
                                    pname = pdata.get('display_name', '')
                                    if pname.lower() == mentioned_name.lower() and pdata.get('role') != 'observer':
                                        # Check if agent is already in queue
                                        # Phase 80.41: Handle both GroupParticipant objects and dicts
                                        already_queued = any(
                                            (getattr(p, 'agent_id', None) or p.get('agent_id') if isinstance(p, dict) else getattr(p, 'agent_id', None)) == pdata.get('agent_id')
                                            for p in participants_to_respond
                                        )
                                        if not already_queued:
                                            participants_to_respond.append(pdata)
                                            print(f"[MCP_AGENT_TRIGGER] Added {mentioned_name} to responders from agent @mention")
                                        break

                    except Exception as e:
                        # Phase 80.16: Enhanced error logging with traceback
                        print(f"[MCP_ERROR] Phase 80.16: Error calling agent {agent_id}: {e}")
                        traceback.print_exc()
                        # Emit stream end with error
                        if socketio:
                            await socketio.emit('group_stream_end', {
                                'id': msg_id,
                                'group_id': group_id,
                                'agent_id': agent_id,
                                'full_message': '',
                                'error': str(e)[:100]
                            }, room=f'group_{group_id}')

                        error_msg = await manager.send_message(
                            group_id=group_id,
                            sender_id=agent_id,
                            content=f"[Error: {str(e)[:100]}]",
                            message_type='error'
                        )
                        if error_msg and socketio:
                            await socketio.emit('group_message', error_msg.to_dict(), room=f'group_{group_id}')
                        # Phase 80.16: Continue to next agent instead of failing
                        continue

        return {
            "success": True,
            "message_id": message.id,
            "group_id": group_id,
            "sender": sender_id,
            "timestamp": message.created_at.isoformat() if hasattr(message.created_at, 'isoformat') else str(message.created_at)
        }

    except Exception as e:
        # Phase 80.16: Catch all exceptions to prevent Internal Server Error
        print(f"[MCP_ERROR] Phase 80.16: Exception in send_group_message_from_mcp: {e}")
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)[:200],
            "error_type": type(e).__name__,
            "group_id": group_id,
            "agent_id": body.agent_id if body else "unknown"
        }


# ============================================================
# PHASE 80.13: MCP @MENTION NOTIFICATION ENDPOINT
# ============================================================
# Endpoint for MCP agents to check for pending @mentions from group chats

@router.get("/mcp/mentions/{agent_id}")
async def get_mcp_mentions(
    agent_id: str,
    limit: int = Query(20, description="Number of mentions to return"),
    unread_only: bool = Query(True, description="Only return unread mentions"),
    mark_read: bool = Query(False, description="Mark returned mentions as read")
) -> Dict[str, Any]:
    """
    Phase 80.13: Get pending @mentions for an MCP agent.

    When users @mention browser_haiku or claude_code in group chat,
    the mention is stored in team_messages with context type 'group_mention'.

    This endpoint allows MCP agents to poll for their mentions.

    Path params:
    - agent_id: MCP agent identifier (e.g., 'browser_haiku', 'claude_code')

    Query params:
    - limit: Max mentions to return (default 20)
    - unread_only: Only unread mentions (default True)
    - mark_read: Mark returned mentions as read (default False)

    Returns:
    - List of mention notifications with group context
    """
    global _team_messages

    # Validate agent_id
    if agent_id not in KNOWN_AGENTS:
        return {
            "error": f"Unknown MCP agent: {agent_id}",
            "known_agents": list(KNOWN_AGENTS.keys())
        }

    # Filter mentions for this agent
    mentions = [
        m for m in _team_messages
        if (m.get("to") == agent_id or m.get("to") == "all")
        and m.get("context", {}).get("type") == "group_mention"
    ]

    # Filter unread if requested
    if unread_only:
        mentions = [m for m in mentions if not m.get("read", False)]

    # Sort newest first
    mentions = sorted(mentions, key=lambda x: x.get("timestamp", 0), reverse=True)

    # Apply limit
    mentions = mentions[:limit]

    # Mark as read if requested
    if mark_read and mentions:
        msg_ids = {m.get("id") for m in mentions}
        for m in _team_messages:
            if m.get("id") in msg_ids:
                m["read"] = True
                m["pending"] = False

    agent_info = KNOWN_AGENTS.get(agent_id, {"name": agent_id})

    # Count total unread
    total_unread = sum(
        1 for m in _team_messages
        if (m.get("to") == agent_id or m.get("to") == "all")
        and m.get("context", {}).get("type") == "group_mention"
        and not m.get("read", False)
    )

    return {
        "agent": agent_id,
        "agent_name": agent_info.get("name", agent_id),
        "total_unread": total_unread,
        "returned": len(mentions),
        "mentions": mentions,
        "respond_endpoint": f"/api/debug/mcp/groups/{{group_id}}/send",
        "tip": "Use the respond_endpoint with group_id from mention context to reply"
    }


@router.post("/mcp/notify")
async def notify_mcp_agent(
    request: Request,
    body: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Phase 80.13: Manually notify an MCP agent (for testing/debugging).

    Body params:
    - agent_id: Target MCP agent (browser_haiku, claude_code)
    - content: Message content
    - group_id: Optional group context
    - sender: Who is sending (default: 'system')
    """
    global _team_messages

    agent_id = body.get("agent_id")
    content = body.get("content", "")
    group_id = body.get("group_id")
    sender = body.get("sender", "system")

    if not agent_id or agent_id not in KNOWN_AGENTS:
        return {
            "error": "Invalid or missing agent_id",
            "known_agents": list(KNOWN_AGENTS.keys())
        }

    if not content:
        return {"error": "Missing content"}

    agent_info = KNOWN_AGENTS.get(agent_id)

    import uuid

    msg = {
        "id": f"notify_{uuid.uuid4()}",
        "timestamp": time.time(),
        "sender": sender,
        "sender_info": {"name": sender, "icon": "info", "role": "System"},
        "to": agent_id,
        "to_info": {
            "name": agent_info.get("name", agent_id),
            "icon": agent_info.get("icon", "bot"),
            "role": agent_info.get("role", "MCP Agent")
        },
        "message": content,
        "priority": "normal",
        "context": {
            "type": "manual_notify",
            "group_id": group_id
        },
        "pending": True,
        "read": False
    }

    _team_messages.append(msg)

    # Keep buffer limited
    if len(_team_messages) > _max_team_messages:
        _team_messages[:] = _team_messages[-_max_team_messages:]

    # Emit via SocketIO
    socketio = getattr(request.app.state, 'socketio', None)
    if socketio:
        try:
            await socketio.emit('mcp_mention', {
                'type': 'manual_notify',
                'target_agent': agent_id,
                'agent_name': agent_info.get('name'),
                'content': content,
                'group_id': group_id,
                'timestamp': msg["timestamp"]
            }, namespace='/')
        except Exception:
            pass

    log_debug(
        f"MCP notify: {sender} → {agent_id}: {content[:50]}...",
        category="mcp_notify",
        data={"msg_id": msg["id"], "agent": agent_id}
    )

    return {
        "success": True,
        "message_id": msg["id"],
        "agent": agent_id,
        "tip": f"Agent can poll via GET /api/debug/mcp/mentions/{agent_id}"
    }


# ============================================================================
# MARKER_124.2C: TASK BOARD REST API
# ============================================================================
# Phase 124.2C: REST endpoints for Task Board UI (DevPanel).
# Exposes CRUD + dispatch for the TaskBoard backend (Phase 121).


@router.get("/task-board")
async def get_task_board_api() -> Dict[str, Any]:
    """Get all tasks and settings from Task Board."""
    from src.orchestration.task_board import get_task_board

    board = get_task_board()
    tasks = board.get_queue()  # All tasks, sorted by priority
    summary = board.get_board_summary()

    # MARKER_151.12C: Enrich tasks with adjusted_stats (blended verifier + user feedback)
    for task in tasks:
        task_id = task.get("id")
        if task_id and task.get("stats"):
            adjusted = board.compute_adjusted_stats(task_id)
            if adjusted:
                task["adjusted_stats"] = adjusted

    return {
        "success": True,
        "tasks": tasks,
        "settings": board.settings,
        "summary": summary,
    }


# MARKER_137.S1_1_EVENT_DISPATCH: Update task board settings (auto_dispatch toggle)
@router.patch("/task-board/settings")
async def update_task_board_settings(body: Dict[str, Any]) -> Dict[str, Any]:
    """Update TaskBoard settings. Supports: auto_dispatch, max_concurrent, default_preset."""
    from src.orchestration.task_board import get_task_board
    board = get_task_board()
    result = board.update_settings(**body)
    return {"success": True, **result}


# MARKER_127.0A: Pipeline results endpoint for Results Viewer
@router.get("/pipeline-results/{task_id}")
async def get_pipeline_results(task_id: str) -> Dict[str, Any]:
    """Get pipeline results for a completed task.

    First looks up pipeline_task_id from task_board, then reads pipeline_tasks.json.

    Args:
        task_id: Task Board task ID (e.g., "tb_1234_5")

    Returns:
        Pipeline subtasks with their results for display in TaskCard expand view.
    """
    import json
    from pathlib import Path
    from src.orchestration.task_board import get_task_board

    board = get_task_board()
    task = board.tasks.get(task_id)

    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}

    pipeline_task_id = task.get("pipeline_task_id")
    if not pipeline_task_id:
        return {
            "success": True,
            "task_id": task_id,
            "pipeline_task_id": None,
            "status": task.get("status"),
            "subtasks": [],
            "message": "No pipeline results (task not dispatched or still pending)"
        }

    # Read pipeline_tasks.json
    pipeline_file = Path(__file__).parent.parent.parent.parent / "data" / "pipeline_tasks.json"
    if not pipeline_file.exists():
        return {"success": False, "error": "pipeline_tasks.json not found"}

    try:
        pipeline_data = json.loads(pipeline_file.read_text())
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {e}"}

    pipeline_task = pipeline_data.get(pipeline_task_id)
    if not pipeline_task:
        return {
            "success": True,
            "task_id": task_id,
            "pipeline_task_id": pipeline_task_id,
            "status": task.get("status"),
            "subtasks": [],
            "message": f"Pipeline task {pipeline_task_id} not found in pipeline_tasks.json"
        }

    # MARKER_128.4C: Generate diff for each subtask result
    import difflib
    import re

    def extract_file_path_and_code(result: str) -> tuple:
        """Extract file path and code from markdown code block."""
        if not result:
            return None, None
        # Match ```<lang> path/to/file or # file: path/to/file
        match = re.search(r'```\w*\s*(?:#\s*file:\s*)?([^\n`]+\.(?:py|ts|tsx|js|jsx|rs|go|json|yaml|yml|md))', result)
        if match:
            file_path = match.group(1).strip()
            # Extract code between ``` markers
            code_match = re.search(r'```\w*[^\n]*\n(.*?)```', result, re.DOTALL)
            if code_match:
                return file_path, code_match.group(1)
        return None, None

    def generate_diff(file_path: str, new_code: str) -> str:
        """Generate unified diff between original file and new code."""
        if not file_path or not new_code:
            return None
        original_file = Path(__file__).parent.parent.parent.parent / file_path
        if not original_file.exists():
            return None
        try:
            original_lines = original_file.read_text().splitlines(keepends=True)
            new_lines = new_code.splitlines(keepends=True)
            diff = difflib.unified_diff(
                original_lines, new_lines,
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
                lineterm=""
            )
            return "".join(diff)
        except Exception:
            return None

    # Extract subtasks with results
    # MARKER_C23A: Include verifier_feedback for RALF loop display
    subtasks = []
    for s in pipeline_task.get("subtasks", []):
        result = s.get("result")
        file_path, new_code = extract_file_path_and_code(result)
        diff_patch = generate_diff(file_path, new_code) if file_path else None

        # MARKER_C23A: Extract verifier feedback for RALF metrics
        verifier = s.get("verifier_feedback") or s.get("verifier") or {}
        verifier_feedback = None
        if verifier:
            verifier_feedback = {
                "passed": verifier.get("passed", s.get("status") == "done"),
                "confidence": verifier.get("confidence", verifier.get("score", 0.0)),
                "retry_count": verifier.get("retry_count", s.get("retries", 0)),
                "max_retries": verifier.get("max_retries", 3),
                "escalated": verifier.get("escalated", False),
                "feedback": verifier.get("feedback", verifier.get("reason", "")),
            }

        subtasks.append({
            "description": s.get("description", "")[:200],
            "status": s.get("status", "unknown"),
            "result": result,  # May contain code blocks
            "marker": s.get("marker"),
            "needs_research": s.get("needs_research", False),
            "diff_patch": diff_patch,  # MARKER_128.4C
            "original_file": file_path,  # MARKER_128.4C
            "verifier_feedback": verifier_feedback,  # MARKER_C23A
        })

    return {
        "success": True,
        "task_id": task_id,
        "pipeline_task_id": pipeline_task_id,
        "status": pipeline_task.get("status"),
        "phase_type": pipeline_task.get("phase_type"),
        "subtasks": subtasks,
        "results_summary": pipeline_task.get("results", {}),
    }


# MARKER_128.2B: Apply pipeline result — write code to disk
# MARKER_131.C20E: Camera fly-to on approve
@router.post("/pipeline-results/apply")
async def apply_pipeline_result(request: Request, data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a subtask result — extract code blocks and write to disk.

    Parses file path from code comment (// file: path/to/file.ext or # file: path)
    and writes the code to that file.

    Args:
        data: {"task_id": "tb_xxx", "subtask_idx": 0}

    Returns:
        {"success": True, "files_written": ["path/to/file.ext"]}
    """
    import json
    import re
    from pathlib import Path

    task_id = data.get("task_id")
    subtask_idx = data.get("subtask_idx", 0)

    if not task_id:
        return {"success": False, "error": "task_id required"}

    # Get pipeline results
    from src.orchestration.task_board import get_task_board
    board = get_task_board()
    task = board.tasks.get(task_id)

    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}

    pipeline_task_id = task.get("pipeline_task_id")
    if not pipeline_task_id:
        return {"success": False, "error": "No pipeline results for this task"}

    # Read pipeline_tasks.json
    pipeline_file = Path(__file__).parent.parent.parent.parent / "data" / "pipeline_tasks.json"
    if not pipeline_file.exists():
        return {"success": False, "error": "pipeline_tasks.json not found"}

    try:
        pipeline_data = json.loads(pipeline_file.read_text())
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {e}"}

    pipeline_task = pipeline_data.get(pipeline_task_id)
    if not pipeline_task:
        return {"success": False, "error": f"Pipeline task {pipeline_task_id} not found"}

    subtasks = pipeline_task.get("subtasks", [])
    if subtask_idx >= len(subtasks):
        return {"success": False, "error": f"Subtask {subtask_idx} not found (total: {len(subtasks)})"}

    subtask = subtasks[subtask_idx]
    result = subtask.get("result", "")

    if not result:
        return {"success": False, "error": "No result code in this subtask"}

    # Extract code blocks and file paths
    files_written = []
    project_root = Path(__file__).parent.parent.parent.parent

    # Pattern: ```language\n// file: path/to/file\ncode\n```
    # or ```language\n# file: path/to/file\ncode\n```
    code_blocks = re.findall(r'```\w*\n(.*?)```', result, re.DOTALL)

    for block in code_blocks:
        # Find file path comment at start of block
        file_match = re.match(r'^(?://|#)\s*file:\s*([^\n]+)\n', block)
        if file_match:
            file_path = file_match.group(1).strip()
            code = block[file_match.end():]  # Code after the file comment

            # Resolve path relative to project root
            if not file_path.startswith('/'):
                full_path = project_root / file_path
            else:
                full_path = Path(file_path)

            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            full_path.write_text(code)
            files_written.append(str(file_path))
            logger.info(f"[APPLY] Wrote {len(code)} bytes to {file_path}")

    if not files_written:
        return {
            "success": False,
            "error": "No file paths found in code blocks. Expected '// file: path' or '# file: path' comment."
        }

    # MARKER_131.C20E: Camera fly-to the first written file
    if files_written:
        socketio = getattr(request.app.state, 'socketio', None)
        if socketio:
            try:
                first_file = files_written[0]
                await socketio.emit('camera_control', {
                    'action': 'focus',
                    'target': first_file,
                    'zoom': 'close',
                    'highlight': True,
                    'animate': True,
                    'source': 'pipeline_apply'
                }, namespace='/')
                logger.info(f"[APPLY] Camera fly-to: {first_file}")
            except Exception as e:
                logger.warning(f"[APPLY] Camera fly-to failed: {e}")

    return {
        "success": True,
        "files_written": files_written,
        "task_id": task_id,
        "subtask_idx": subtask_idx,
    }


# MARKER_128.3A: Update pipeline result status (applied/rejected/rework)
# MARKER_131.C20E: Camera fly-to on approve
@router.patch("/pipeline-results/{task_id}/status")
async def update_result_status(request: Request, task_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Mark pipeline result as applied/rejected/rework.

    Args:
        task_id: Task Board task ID
        data: {"status": "applied|rejected|rework", "reason": "optional reason"}

    Returns:
        {"success": True}
    """
    from datetime import datetime
    from src.orchestration.task_board import get_task_board

    status = data.get("status")
    reason = data.get("reason", "")

    if status not in ("applied", "rejected", "rework"):
        return {"success": False, "error": f"Invalid status: {status}. Use: applied/rejected/rework"}

    board = get_task_board()
    task = board.tasks.get(task_id)

    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}

    # Update task with result lifecycle fields
    board.update_task(
        task_id,
        result_status=status,
        result_reviewed_at=datetime.now().isoformat(),
        result_review_reason=reason
    )

    # If rework, re-dispatch the task
    if status == "rework":
        board.update_task(task_id, status="pending")
        logger.info(f"[RESULT_STATUS] Task {task_id} marked for rework, status reset to pending")

    logger.info(f"[RESULT_STATUS] Task {task_id} marked as {status}" + (f": {reason}" if reason else ""))

    # MARKER_131.C20E: Camera fly-to on "applied" status
    if status == "applied":
        socketio = getattr(request.app.state, 'socketio', None)
        if socketio:
            try:
                # Try to get a target file from pipeline results
                pipeline_task_id = task.get("pipeline_task_id")
                target_file = None
                if pipeline_task_id:
                    import json
                    from pathlib import Path
                    pipeline_file = Path(__file__).parent.parent.parent.parent / "data" / "pipeline_tasks.json"
                    if pipeline_file.exists():
                        pipeline_data = json.loads(pipeline_file.read_text())
                        pt = pipeline_data.get(pipeline_task_id, {})
                        for s in pt.get("subtasks", []):
                            result = s.get("result", "")
                            # Extract first file path from result
                            import re
                            match = re.search(r'(?://|#)\s*file:\s*([^\n]+)', result)
                            if match:
                                target_file = match.group(1).strip()
                                break

                if target_file:
                    await socketio.emit('camera_control', {
                        'action': 'focus',
                        'target': target_file,
                        'zoom': 'medium',
                        'highlight': True,
                        'animate': True,
                        'source': 'result_applied'
                    }, namespace='/')
                    logger.info(f"[RESULT_STATUS] Camera fly-to: {target_file}")
            except Exception as e:
                logger.warning(f"[RESULT_STATUS] Camera fly-to failed: {e}")

    return {
        "success": True,
        "task_id": task_id,
        "result_status": status,
    }


@router.post("/task-board/add")
async def add_task_api(body: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new task to the board.

    Body params:
    - title: str (required)
    - description: str
    - priority: int (1-5, default 3)
    - phase_type: str (build/fix/research)
    - preset: str (dragon_silver, titan_core, etc.)
    - tags: list[str]
    """
    from src.orchestration.task_board import get_task_board

    title = body.get("title")
    if not title:
        return {"success": False, "error": "Title is required"}

    board = get_task_board()
    task_id = board.add_task(
        title=title,
        description=body.get("description", ""),
        priority=body.get("priority", 3),
        phase_type=body.get("phase_type", "build"),
        preset=body.get("preset"),
        tags=body.get("tags", []),
        source=body.get("source", "api"),
        module=body.get("module"),
        primary_node_id=body.get("primary_node_id"),
        affected_nodes=body.get("affected_nodes"),
        workflow_id=body.get("workflow_id"),
        team_profile=body.get("team_profile"),
        task_origin=body.get("task_origin"),
    )

    return {"success": True, "task_id": task_id}


@router.patch("/task-board/{task_id}")
async def update_task_api(task_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Update a task's fields (priority, status, title, etc.)."""
    from src.orchestration.task_board import get_task_board

    board = get_task_board()

    # Filter allowed update fields
    allowed_fields = {
        "title", "description", "priority", "phase_type", "preset", "status", "tags",
        "module", "primary_node_id", "affected_nodes", "workflow_id", "workflow_bank",
        "workflow_family", "workflow_selection_origin", "team_profile", "task_origin",
    }
    updates = {k: v for k, v in body.items() if k in allowed_fields}

    if not updates:
        return {"success": False, "error": "No valid fields to update"}

    ok = board.update_task(task_id, **updates)
    return {"success": ok, "task_id": task_id}


@router.delete("/task-board/{task_id}")
async def remove_task_api(task_id: str) -> Dict[str, Any]:
    """Remove a task from the board."""
    from src.orchestration.task_board import get_task_board

    board = get_task_board()
    ok = board.remove_task(task_id)
    return {"success": ok, "task_id": task_id}


@router.post("/task-board/dispatch")
async def dispatch_next_task_api(body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Dispatch the highest-priority pending task.

    Body params:
    - chat_id: str (optional, for progress streaming)
    - task_id: str (optional, dispatch specific task instead of next)
    - selected_key: {provider, key_masked} (optional, MARKER_126.9D)
    """
    from src.orchestration.task_board import get_task_board

    body = body or {}
    board = get_task_board()
    chat_id = body.get("chat_id")
    task_id = body.get("task_id")
    # MARKER_126.9D: Selected key for pipeline dispatch
    selected_key = body.get("selected_key")

    if task_id:
        result = await board.dispatch_task(task_id, chat_id=chat_id, selected_key=selected_key)
    else:
        result = await board.dispatch_next(chat_id=chat_id, selected_key=selected_key)

    return result


# MARKER_130.C16C: Agent claim/complete endpoints for coordination
@router.post("/task-board/claim")
async def claim_task_api(body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Claim a task for an agent to work on.

    Body params:
    - task_id: str (required)
    - agent_name: str (required — opus, cursor, dragon, grok)
    - agent_type: str (optional — claude_code, cursor, mycelium, grok, human)
    """
    from src.orchestration.task_board import get_task_board

    body = body or {}
    task_id = body.get("task_id")
    agent_name = body.get("agent_name")
    agent_type = body.get("agent_type", "unknown")

    if not task_id:
        return {"success": False, "error": "task_id is required"}
    if not agent_name:
        return {"success": False, "error": "agent_name is required"}

    board = get_task_board()
    result = board.claim_task(task_id, agent_name, agent_type)
    return result


@router.post("/task-board/complete")
async def complete_task_api(body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Mark a task as completed with optional commit info.

    Body params:
    - task_id: str (required)
    - commit_hash: str (optional — git commit hash)
    - commit_message: str (optional — first line of commit message)
    """
    from src.orchestration.task_board import get_task_board

    body = body or {}
    task_id = body.get("task_id")
    commit_hash = body.get("commit_hash")
    commit_message = body.get("commit_message")

    if not task_id:
        return {"success": False, "error": "task_id is required"}

    board = get_task_board()
    result = board.complete_task(task_id, commit_hash, commit_message)
    return result


@router.get("/task-board/active-agents")
async def get_active_agents_api() -> Dict[str, Any]:
    """Get list of agents with claimed/running tasks.

    Returns agents with their current task and elapsed time.
    """
    from src.orchestration.task_board import get_task_board

    board = get_task_board()
    agents = board.get_active_agents()
    return {"success": True, "agents": agents, "count": len(agents)}


# MARKER_126.5F: Cancel task endpoint for stop button
@router.post("/task-board/cancel")
async def cancel_task_api(body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Cancel a running or pending task.

    Body params:
    - task_id: str (required)
    - reason: str (optional, default "Cancelled by user")
    """
    from src.orchestration.task_board import get_task_board

    body = body or {}
    task_id = body.get("task_id")
    if not task_id:
        return {"success": False, "error": "task_id is required"}

    reason = body.get("reason", "Cancelled by user")
    board = get_task_board()
    ok = board.cancel_task(task_id, reason)
    return {"success": ok, "task_id": task_id}


# MARKER_126.0E: League test endpoint for DevPanel
@router.post("/task-board/test-league")
async def test_league_api(body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Run a pipeline test with specific preset/league.

    Body params:
    - preset: str (required — dragon_bronze, dragon_silver, dragon_gold, titan_core, etc.)
    - task: str (optional test task, defaults to standard benchmark)
    - chat_id: str (optional, for progress streaming)
    """
    from src.orchestration.agent_pipeline import AgentPipeline

    body = body or {}
    preset = body.get("preset")
    if not preset:
        return {"success": False, "error": "preset is required"}

    task = body.get("task", "Add toggleBookmark and getBookmarkedChats to useStore.ts using zustand + immer")
    chat_id = body.get("chat_id")

    try:
        pipeline = AgentPipeline(chat_id=chat_id, preset=preset, auto_write=False)
        result = await pipeline.execute(task, phase_type="build")

        stats = result.get("results", {}).get("stats", {})
        return {
            "success": True,
            "preset": preset,
            "task": task[:100],
            "stats": stats,
            "pipeline_task_id": result.get("task_id"),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "preset": preset}


# MARKER_124.3D: Internal notify endpoint for Task Board SocketIO emission
# MARKER_137.S1_1_EVENT_DISPATCH: Enhanced with auto-dispatch on task added
@router.post("/task-board/notify")
async def notify_task_board_update(request: Request, body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Internal endpoint: emit task_board_updated SocketIO event.

    Called by TaskBoard._notify_board_update() after save.
    MARKER_137.S1_1_EVENT_DISPATCH: When action='added' and auto_dispatch=True,
    automatically dispatches the highest-priority pending task to pipeline.
    """
    body = body or {}
    action = body.get("action", "update")
    sio = getattr(request.app.state, 'socketio', None)
    if not sio:
        try:
            from src.mcp.mcp_server import get_mcp_server
            mcp = get_mcp_server()
            if mcp:
                sio = mcp.socketio
        except Exception:
            pass

    dispatched = False
    if sio:
        await sio.emit("task_board_updated", {
            "action": action,
            "summary": body.get("summary", {}),
        })

        # MARKER_137.S1_1_EVENT_DISPATCH: Auto-dispatch on new task
        if action == "added":
            try:
                from src.orchestration.task_board import TaskBoard
                board = TaskBoard()
                if board.settings.get("auto_dispatch", False):
                    async def _auto_dispatch():
                        try:
                            result = await board.dispatch_next()
                            if result.get("success"):
                                logger.info(f"[AutoDispatch] Task dispatched: {result.get('task_id', '?')}")
                                if sio:
                                    await sio.emit("task_board_updated", {
                                        "action": "auto_dispatched",
                                        "task_id": result.get("task_id"),
                                    })
                            else:
                                logger.debug(f"[AutoDispatch] Skip: {result.get('error', 'no pending')}")
                        except Exception as e:
                            logger.warning(f"[AutoDispatch] Failed: {e}")

                    asyncio.create_task(_auto_dispatch())
                    dispatched = True
            except Exception as e:
                logger.warning(f"[AutoDispatch] Setup error: {e}")

        return {"success": True, "dispatched": dispatched}
    return {"success": False, "error": "No SocketIO instance"}


# ============================================================
# MARKER_146.5_PLAYGROUND_REST: Playground Management Endpoints
# ============================================================


@router.get("/playground")
async def list_playgrounds_api() -> Dict[str, Any]:
    """List all playgrounds (active and inactive).

    Returns:
        {"success": true, "playgrounds": [...], "active_count": N}
    """
    from src.orchestration.playground_manager import list_playgrounds_summary
    playgrounds = list_playgrounds_summary()
    active_count = sum(1 for p in playgrounds if p.get("status") == "active")
    return {
        "success": True,
        "playgrounds": playgrounds,
        "active_count": active_count,
        "total_count": len(playgrounds),
    }


@router.post("/playground/create")
async def create_playground_api(body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a new playground sandbox.

    Body params:
        task: str — what the agent will work on
        preset: str — dragon team preset (default: dragon_silver)
        auto_write: bool — allow file writes (default: true)
    """
    from src.orchestration.playground_manager import create_playground
    body = body or {}
    try:
        result = await create_playground(
            task=body.get("task", ""),
            preset=body.get("preset", "dragon_silver"),
            auto_write=body.get("auto_write", True),
        )
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/playground/{pg_id}/review")
async def review_playground_api(pg_id: str) -> Dict[str, Any]:
    """Review changes in a playground — per-file diffs and stats.

    Returns:
        {"playground_id", "changed_files": [{path, status, diff}], "total_changes"}
    """
    from src.orchestration.playground_manager import review_playground
    result = await review_playground(pg_id)
    return result


@router.post("/playground/{pg_id}/promote")
async def promote_playground_api(pg_id: str, body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Promote playground code to main codebase.

    Body params:
        strategy: "copy" (default) | "cherry-pick" | "merge"
        files: list[str] — specific files to promote (null = all)
        commit_message: str — optional git commit message
        destroy_after: bool — destroy playground after promote (default: true)

    Returns:
        {"success", "promoted_files": [...], "strategy", "errors": [...]}
    """
    from src.orchestration.playground_manager import promote_playground
    body = body or {}
    result = await promote_playground(
        playground_id=pg_id,
        files=body.get("files"),
        strategy=body.get("strategy", "copy"),
        commit_message=body.get("commit_message"),
        destroy_after=body.get("destroy_after", True),
    )
    return result


@router.post("/playground/{pg_id}/reject")
async def reject_playground_api(pg_id: str, body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Reject playground results. Marks as failed, optionally destroys.

    Body params:
        reason: str — why rejected
        destroy: bool — destroy after rejection (default: false)
    """
    from src.orchestration.playground_manager import reject_playground
    body = body or {}
    result = await reject_playground(
        playground_id=pg_id,
        reason=body.get("reason", ""),
        destroy=body.get("destroy", False),
    )
    return result


@router.delete("/playground/{pg_id}")
async def destroy_playground_api(pg_id: str) -> Dict[str, Any]:
    """Destroy a playground and its git worktree."""
    from src.orchestration.playground_manager import destroy_playground
    result = await destroy_playground(pg_id)
    return result


@router.get("/playground/settings")
async def get_playground_settings_api() -> Dict[str, Any]:
    """Get playground configuration settings."""
    from src.orchestration.playground_manager import PlaygroundManager
    settings = PlaygroundManager.load_settings()
    return {"success": True, **settings}


@router.patch("/playground/settings")
async def update_playground_settings_api(body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Update playground settings.

    Body params:
        base_dir: str — directory for worktrees
        max_concurrent: int — max playgrounds (1-10)
        ttl_hours: float — auto-expire hours
        auto_cleanup: bool — enable auto-cleanup
    """
    from src.orchestration.playground_manager import PlaygroundManager
    body = body or {}
    current = PlaygroundManager.load_settings()
    # Merge updates
    if "base_dir" in body:
        current["base_dir"] = body["base_dir"]
    if "max_concurrent" in body:
        current["max_concurrent"] = max(1, min(10, int(body["max_concurrent"])))
    if "ttl_hours" in body:
        current["ttl_hours"] = max(0.5, min(24, float(body["ttl_hours"])))
    if "auto_cleanup" in body:
        current["auto_cleanup"] = bool(body["auto_cleanup"])
    saved = PlaygroundManager.save_settings(current)
    return {"success": True, **saved}


# ============================================================
# MARKER_136.W2A: DISK ARTIFACTS ENDPOINTS
# ============================================================

@router.get("/artifacts")
async def list_disk_artifacts() -> Dict[str, Any]:
    """
    MARKER_136.W2A: List disk artifacts from pipeline output.

    Returns list of artifacts saved to artifacts/ directory by pipelines.
    """
    from src.services.disk_artifact_service import list_artifacts

    try:
        artifacts = await list_artifacts()
        return {
            "success": True,
            "artifacts": artifacts,
            "count": len(artifacts)
        }
    except Exception as e:
        return {"success": False, "error": str(e), "artifacts": []}


@router.get("/artifacts/{filename}")
async def read_disk_artifact(filename: str) -> Dict[str, Any]:
    """
    MARKER_136.W2A: Read artifact content by filename.
    """
    from pathlib import Path
    from src.services.disk_artifact_service import ARTIFACTS_DIR

    filepath = ARTIFACTS_DIR / filename

    if not filepath.exists():
        return {"success": False, "error": "Artifact not found"}

    try:
        content = filepath.read_text(encoding='utf-8')
        stat = filepath.stat()
        return {
            "success": True,
            "artifact": {
                "filename": filename,
                "content": content,
                "size": stat.st_size,
                "extension": filepath.suffix[1:] if filepath.suffix else "txt"
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# MARKER_136.W2B: LLM CALL ENDPOINT FOR ARCHITECT CHAT
# ============================================================

@router.post("/llm-call")
async def llm_call_endpoint(request: Request) -> Dict[str, Any]:
    """
    MARKER_136.W2B: Direct LLM call for ArchitectChat component.

    Expects JSON body:
    - model: str (model ID like 'kimi-k2.5', 'gpt-4o', etc.)
    - messages: list of {role, content}
    - max_tokens: int (optional, default 2000)
    - temperature: float (optional, default 0.3)
    """
    # MARKER_137.ARCHITECT_FIX: Use provider_registry.call_model_v2 directly
    from src.elisya.provider_registry import call_model_v2

    body = await request.json()
    model = body.get("model", "kimi-k2.5")
    messages = body.get("messages", [])
    max_tokens = body.get("max_tokens", 2000)
    temperature = body.get("temperature", 0.3)
    # MARKER_137.ARCHITECT_FIX: Accept model_source from frontend (from /api/models/autodetect)
    # This is how user-selected provider flows through without hardcoding
    model_source = body.get("model_source", "")

    if not messages:
        return {"success": False, "error": "No messages provided"}

    try:
        # Use explicit source if provided (from frontend model selector),
        # otherwise detect from model name
        if model_source:
            provider_name = model_source
        else:
            from src.mcp.tools.llm_call_tool_async import LLMCallToolAsync
            tool = LLMCallToolAsync()
            provider_name = tool._detect_provider(model)

        result = await call_model_v2(
            model=model,
            messages=messages,
            source=provider_name,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # MARKER_137.ARCHITECT_FIX: call_model_v2 returns {"message": {"content": "..."}, ...}
        # Success = has message.content, error = raises exception
        content = result.get("message", {}).get("content", "")
        if content:
            return {
                "success": True,
                "response": content,
                "model": model,
                "provider": provider_name,
                "usage": result.get("usage"),
            }
        else:
            return {
                "success": False,
                "error": "Empty response from LLM",
                "model": model,
                "provider": provider_name,
            }
    except Exception as e:
        logger.error(f"[llm-call] Error: {e}")
        return {"success": False, "error": str(e), "model": model}


# ============================================================
# MARKER_126.5: BALANCE TRACKER ENDPOINTS
# ============================================================

@router.get("/usage/balances")
async def get_usage_balances(refresh_remote: bool = False) -> Dict[str, Any]:
    """
    MARKER_126.5A: Get unified usage and balance data.
    MARKER_126.3E: Sync all keys from KeyManager before returning.
    MARKER_127.3: Reload keys from config on every request (fixes new key visibility bug).

    Returns:
        - records: Per-key usage (tokens, cost, balance where available)
        - totals: Aggregated by provider
        - providers_with_balance: Which providers have remote balance API
    """
    from src.services.balance_tracker import get_balance_tracker
    from src.utils.unified_key_manager import get_key_manager

    # MARKER_127.3: Reload keys from config (picks up newly added keys)
    km = get_key_manager()
    keys_loaded = km.load_from_config()

    tracker = get_balance_tracker()

    # MARKER_126.3E: Sync ALL keys from KeyManager (not just used ones)
    synced_count = tracker.sync_from_key_manager()

    # MARKER_155.PERF.BALANCE_TRIGGER_CACHE:
    # Do not hit remote balance APIs on every poll; only when explicitly requested.
    remote_cache = getattr(get_usage_balances, "_remote_cache", {"ts": 0.0})
    now_ts = time.time()
    ttl_sec = 300.0
    should_refresh_remote = bool(refresh_remote) or (now_ts - float(remote_cache.get("ts", 0.0)) > ttl_sec)
    if should_refresh_remote:
        try:
            for provider in ['openrouter', 'polza']:
                try:
                    await km.fetch_provider_balance(provider)
                except Exception:
                    pass
        except Exception:
            pass
        get_usage_balances._remote_cache = {"ts": now_ts}

    return {
        "success": True,
        "records": tracker.get_all(),
        "totals": tracker.get_totals(),
        "providers_with_balance": ["openrouter", "polza"],
        "keys_loaded": keys_loaded,
        "synced_keys": synced_count,
        "timestamp": time.time()
    }


@router.post("/usage/reset")
async def reset_usage() -> Dict[str, Any]:
    """MARKER_126.5B: Reset daily usage counters."""
    from src.services.balance_tracker import get_balance_tracker

    tracker = get_balance_tracker()
    tracker.reset_daily()
    return {"success": True, "message": "Usage counters reset"}


# MARKER_129.1A: Watcher Status endpoint
@router.get("/watcher-stats")
async def get_watcher_stats() -> Dict[str, Any]:
    """Get watcher health statistics for DevPanel monitoring.

    Returns:
        indexed_today: Files indexed today from changelog
        skip_patterns_count: Number of skip patterns active
        skip_patterns: List of patterns being skipped
        events_last_5min: Event count in last 5 minutes
        recent_events: Last 10 processed events with timestamps
    """
    import json
    from pathlib import Path
    from datetime import datetime

    base_path = Path(__file__).parent.parent.parent.parent / "data"

    # Get skip patterns from file_watcher
    try:
        from src.scanners.file_watcher import SKIP_PATTERNS
        skip_patterns = list(SKIP_PATTERNS)
    except ImportError:
        skip_patterns = []

    # Count indexed files today from changelog
    today = datetime.now().strftime("%Y-%m-%d")
    changelog_file = base_path / "changelog" / f"changelog_{today}.json"
    indexed_today = 0
    if changelog_file.exists():
        try:
            changelog_data = json.loads(changelog_file.read_text())
            indexed_today = len(changelog_data.get("entries", []))
        except Exception:
            pass

    # Get recent events from watcher state
    watcher_state_file = base_path / "watcher_state.json"
    recent_events = []
    events_last_5min = 0
    watched_dirs_count = 0

    if watcher_state_file.exists():
        try:
            watcher_data = json.loads(watcher_state_file.read_text())
            watched_dirs_count = len(watcher_data.get("watched_dirs", []))

            # Get recent events if stored
            recent = watcher_data.get("recent_events", [])
            recent_events = recent[-10:] if recent else []

            # Count events in last 5 minutes
            now = time.time()
            five_min_ago = now - 300
            for evt in recent:
                evt_time = evt.get("timestamp", 0)
                if evt_time > five_min_ago:
                    events_last_5min += 1
        except Exception:
            pass

    return {
        "success": True,
        "indexed_today": indexed_today,
        "skip_patterns_count": len(skip_patterns),
        "skip_patterns": skip_patterns[:20],  # Limit to first 20
        "events_last_5min": events_last_5min,
        "watched_dirs_count": watched_dirs_count,
        "recent_events": recent_events,
        "timestamp": time.time(),
    }


# ============================================================
# MARKER_131.C22: HEARTBEAT SETTINGS
# MARKER_133.C33E: Persist to disk
# ============================================================

# MARKER_133.C33E: Heartbeat config persistence
HEARTBEAT_CONFIG_FILE = Path(__file__).parent.parent.parent.parent / "data" / "heartbeat_config.json"


def _load_heartbeat_config() -> Dict[str, Any]:
    """Load heartbeat config from disk, with env var fallback."""
    if HEARTBEAT_CONFIG_FILE.exists():
        try:
            return json.loads(HEARTBEAT_CONFIG_FILE.read_text())
        except Exception:
            pass
    # Default: OFF to prevent token burn; monitor_all scans all chats
    return {"enabled": False, "interval": 60, "monitor_all": True}


def _save_heartbeat_config(enabled: bool, interval: int, monitor_all: bool = True):
    """Persist heartbeat config to disk."""
    from datetime import datetime
    config = {
        "enabled": enabled,
        "interval": interval,
        "monitor_all": monitor_all,
        "updated_at": datetime.utcnow().isoformat()
    }
    HEARTBEAT_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_CONFIG_FILE.write_text(json.dumps(config, indent=2))
    # Also sync to env for current session
    os.environ["VETKA_HEARTBEAT_ENABLED"] = "true" if enabled else "false"
    os.environ["VETKA_HEARTBEAT_INTERVAL"] = str(interval)


@router.get("/heartbeat/settings")
async def get_heartbeat_settings() -> Dict[str, Any]:
    """Get current heartbeat daemon settings.

    Returns:
        enabled: bool - whether heartbeat is enabled
        interval: int - interval in seconds
        status: str - running/stopped
        last_tick: float - timestamp of last tick
    """
    from pathlib import Path

    # MARKER_133.C33E: Load from disk config first, fallback to env
    config = _load_heartbeat_config()
    enabled = config.get("enabled", False)
    interval = config.get("interval", 60)

    # Read last tick from heartbeat_state.json
    state_file = Path(__file__).parent.parent.parent.parent / "data" / "heartbeat_state.json"
    last_tick = 0
    total_ticks = 0
    tasks_dispatched = 0
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            last_tick = state.get("last_tick", 0)
            total_ticks = state.get("total_ticks", 0)
            tasks_dispatched = state.get("tasks_dispatched", 0)
        except Exception:
            pass

    return {
        "success": True,
        "enabled": enabled,
        "interval": interval,
        "last_tick": last_tick,
        "total_ticks": total_ticks,
        "tasks_dispatched": tasks_dispatched,
        "env_vars": {
            "VETKA_HEARTBEAT_ENABLED": os.getenv("VETKA_HEARTBEAT_ENABLED", "false"),
            "VETKA_HEARTBEAT_INTERVAL": os.getenv("VETKA_HEARTBEAT_INTERVAL", "60"),
        }
    }


@router.post("/heartbeat/settings")
async def update_heartbeat_settings(body: Dict[str, Any]) -> Dict[str, Any]:
    """Update heartbeat daemon settings — PERSISTED TO DISK.

    Body params:
    - enabled: bool
    - interval: int (seconds, 10-604800)
    - monitor_all: bool (MARKER_140: scan all groups + solo chats)

    MARKER_133.C33E: Settings now persist across server restarts.
    MARKER_137.S2: Extended interval cap from 1h to 1 week.
    MARKER_140: Added monitor_all for multi-chat scanning.
    """
    # Load current config
    config = _load_heartbeat_config()
    enabled = config.get("enabled", False)
    interval = config.get("interval", 60)
    monitor_all = config.get("monitor_all", True)

    # Apply updates
    if "enabled" in body:
        enabled = bool(body["enabled"])

    if "interval" in body:
        # MARKER_137.S2: 10s to 1 week (frontend has 6h/12h/1d/1w options)
        interval = max(10, min(body["interval"], 604800))

    if "monitor_all" in body:
        monitor_all = bool(body["monitor_all"])

    # Persist to disk + sync to env
    _save_heartbeat_config(enabled, interval, monitor_all)

    return {
        "success": True,
        "enabled": enabled,
        "interval": interval,
        "monitor_all": monitor_all,
        "message": "Settings saved to disk. Persists across restarts.",
        "config_file": str(HEARTBEAT_CONFIG_FILE),
    }


# MARKER_137.TICK_NOW: Manual heartbeat tick endpoint
@router.post("/heartbeat/tick")
async def trigger_heartbeat_tick(body: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    MARKER_137.TICK_NOW: Manually trigger one heartbeat tick.

    Scans group chat for @dragon/@titan/@doctor tasks and dispatches them.

    Body params (optional):
    - group_id: str (default: MCP Dev group)
    - dry_run: bool (default: false) — parse only, don't execute
    """
    body = body or {}
    group_id = body.get("group_id")  # None = use default
    dry_run = body.get("dry_run", False)

    try:
        from src.orchestration.mycelium_heartbeat import heartbeat_tick
        result = await heartbeat_tick(group_id=group_id, dry_run=dry_run) if group_id else await heartbeat_tick(dry_run=dry_run)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# MARKER_133.C33H: LAYOUT POSITIONS PERSISTENCE
# ============================================================

LAYOUT_POSITIONS_FILE = Path(__file__).parent.parent.parent.parent / "data" / "layout_positions.json"


@router.get("/layout/positions")
async def get_layout_positions() -> Dict[str, Any]:
    """Get saved layout positions for 3D scene objects."""
    if LAYOUT_POSITIONS_FILE.exists():
        try:
            return json.loads(LAYOUT_POSITIONS_FILE.read_text())
        except Exception:
            pass
    return {"positions": {}}


@router.post("/layout/positions")
async def save_layout_positions(body: Dict[str, Any]) -> Dict[str, Any]:
    """Save layout positions for 3D scene objects."""
    LAYOUT_POSITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAYOUT_POSITIONS_FILE.write_text(json.dumps(body, indent=2))
    return {"success": True, "saved": len(body.get("positions", {}))}
