"""Viewport Detail Tool for VETKA MCP.

MARKER_109_2_VIEWPORT_TOOL: Phase 109.1 Dynamic Context Injection

Retrieves detailed viewport state including:
- Camera position and zoom level
- Focused nodes (pinned and visible)
- Visible file count and statistics
- Integration with CAM engine viewport patterns

This tool enables AI agents to understand what the user is currently viewing
in the 3D visualization, allowing for context-aware responses.

@status: active
@phase: 109.1
@depends: base_tool, mcp_server, engram_user_memory, cam_engine
@used_by: session_tools, mcp_bridge
"""

from typing import Dict, Any, Optional
from .base_tool import BaseMCPTool


class ViewportDetailTool(BaseMCPTool):
    """Get detailed viewport state for context injection."""

    @property
    def name(self) -> str:
        return "vetka_get_viewport_detail"

    @property
    def description(self) -> str:
        return (
            "Get current 3D viewport detail including camera position, zoom level, focused nodes, and visible file count. "
            "Returns viewport state with camera coordinates, focus path, visible/pinned node counts, and optional statistics. "
            "Use to understand what the user is currently viewing in the 3D visualization for context-aware responses."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Optional session ID to filter viewport by session context"
                },
                "include_stats": {
                    "type": "boolean",
                    "description": "Include detailed viewport statistics (default: true)",
                    "default": True
                },
                "include_pinned": {
                    "type": "boolean",
                    "description": "Include pinned nodes information (default: true)",
                    "default": True
                },
                "include_lod": {
                    "type": "boolean",
                    "description": "Include LOD (Level of Detail) information for visible nodes (default: false)",
                    "default": False
                }
            },
            "required": []
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute viewport detail retrieval."""
        session_id = arguments.get("session_id")
        include_stats = arguments.get("include_stats", True)
        include_pinned = arguments.get("include_pinned", True)
        include_lod = arguments.get("include_lod", False)

        try:
            # Get viewport state from MCP server's socketio context
            viewport_data = self._get_viewport_state(session_id)

            if not viewport_data:
                return {
                    "success": True,
                    "result": {
                        "viewport": None,
                        "summary": "[→ viewport] No active viewport session",
                        "available": False
                    }
                }

            # Build response based on requested details
            result = {
                "viewport": {
                    "camera": viewport_data.get("camera", {"x": 0, "y": 0, "z": 100, "zoom": 1.0}),
                    "focus": viewport_data.get("focus", "/"),
                    "visible_count": viewport_data.get("visible_count", 0),
                }
            }

            # Add pinned nodes if requested
            if include_pinned:
                result["viewport"]["pinned_count"] = viewport_data.get("pinned_count", 0)
                result["viewport"]["pinned_nodes"] = viewport_data.get("pinned_nodes", [])

            # Add detailed statistics if requested
            if include_stats:
                result["statistics"] = {
                    "total_nodes": viewport_data.get("total_nodes", 0),
                    "viewport_nodes": viewport_data.get("viewport_nodes", 0),
                    "zoom_level": viewport_data.get("zoom_level", 1.0),
                    "camera_target": viewport_data.get("camera_target", {"x": 0, "y": 0, "z": 0}),
                    "avg_distance": viewport_data.get("avg_distance", 100.0)
                }

            # Add LOD information if requested
            if include_lod:
                result["lod_distribution"] = viewport_data.get("lod_distribution", {})

            # Generate human-readable summary
            camera = result["viewport"]["camera"]
            zoom = camera.get("zoom", 1.0)
            focus = result["viewport"]["focus"]
            visible = result["viewport"]["visible_count"]
            pinned = result["viewport"].get("pinned_count", 0)

            summary_parts = [
                f"[→ viewport] {visible} nodes visible"
            ]

            if zoom != 1.0:
                summary_parts.append(f"(zoom~{zoom:.1f})")

            if focus != "/":
                summary_parts.append(f"focus: {focus}")

            if include_pinned and pinned > 0:
                summary_parts.append(f"{pinned} pinned")

            result["summary"] = " ".join(summary_parts)
            result["available"] = True

            return {
                "success": True,
                "result": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to retrieve viewport details: {str(e)}",
                "result": {
                    "viewport": None,
                    "summary": "[→ viewport] Error retrieving viewport state",
                    "available": False
                }
            }

    def _get_viewport_state(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve viewport state from the MCP server's SocketIO context.

        The viewport state is maintained by the frontend and synchronized
        via SocketIO events. This method attempts to retrieve the latest
        known viewport state.

        Args:
            session_id: Optional session ID to filter by

        Returns:
            Dictionary containing viewport state, or None if not available
        """
        try:
            # Try to get viewport state from MCP server global state
            from src.mcp.mcp_server import get_mcp_server
            mcp = get_mcp_server()

            if not mcp:
                return None

            # Check if viewport state is cached in MCP server
            # The frontend should be sending viewport updates via SocketIO
            if hasattr(mcp, 'viewport_state') and mcp.viewport_state:
                state = mcp.viewport_state

                # Filter by session if provided
                if session_id and state.get("session_id") != session_id:
                    return None

                return state

            # Fallback: Try to get from user preferences (CAM engine viewport patterns)
            return self._get_viewport_from_preferences(session_id)

        except Exception as e:
            print(f"[ViewportDetailTool] Error getting viewport state: {e}")
            return None

    def _get_viewport_from_preferences(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fallback: Get viewport information from user preferences.

        This uses the Engram user memory system to retrieve viewport patterns
        that the CAM engine has learned about the user's viewing habits.

        Args:
            session_id: Optional session ID (used to derive user_id)

        Returns:
            Synthetic viewport state based on user preferences, or None
        """
        try:
            from src.memory.engram_user_memory import get_engram_user_memory

            # Derive user_id from session_id or use default
            user_id = "default"
            if session_id and "_" in session_id:
                parts = session_id.split("_")
                if len(parts) > 1:
                    user_id = parts[1]

            engram = get_engram_user_memory()

            # Try to get viewport patterns from Engram
            zoom_pref = engram.get_preference(user_id, "viewport_patterns", "zoom_levels")
            focus_pref = engram.get_preference(user_id, "viewport_patterns", "focus_areas")

            # Build synthetic viewport state from preferences
            return {
                "camera": {
                    "x": 0,
                    "y": 0,
                    "z": 100,
                    "zoom": zoom_pref[0] if zoom_pref and isinstance(zoom_pref, list) else 1.0
                },
                "focus": focus_pref[0] if focus_pref and isinstance(focus_pref, list) else "/",
                "visible_count": 0,
                "pinned_count": 0,
                "source": "preferences"
            }

        except Exception as e:
            print(f"[ViewportDetailTool] Error getting viewport from preferences: {e}")
            return None


def register_viewport_tool(tool_list: list):
    """
    Register viewport tool with a tool registry list.

    Args:
        tool_list: List to append tool instance to
    """
    tool_list.append(ViewportDetailTool())


# Convenience function for direct import
def vetka_get_viewport_detail(
    session_id: Optional[str] = None,
    include_stats: bool = True,
    include_pinned: bool = True,
    include_lod: bool = False
) -> Dict[str, Any]:
    """
    Get viewport detail.

    Convenience wrapper for ViewportDetailTool.

    Args:
        session_id: Optional session ID to filter by
        include_stats: Include detailed statistics
        include_pinned: Include pinned nodes
        include_lod: Include LOD distribution

    Returns:
        Dictionary with viewport details
    """
    tool = ViewportDetailTool()
    return tool.execute({
        "session_id": session_id,
        "include_stats": include_stats,
        "include_pinned": include_pinned,
        "include_lod": include_lod
    })
