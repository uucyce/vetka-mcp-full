"""
Camera Control Tool for VETKA MCP.

Allows agents to control the 3D camera - focus on files, branches, or overview.
Uses SocketIO to emit events to frontend.

@status: active
@phase: 96
@depends: base_tool, mcp_server
@used_by: mcp_server
"""

from typing import Any, Dict
from .base_tool import BaseMCPTool


class CameraControlTool(BaseMCPTool):
    """Control 3D camera position - agents can show user specific files/branches"""

    @property
    def name(self) -> str:
        return "vetka_camera_focus"

    @property
    def description(self) -> str:
        return (
            "Move 3D camera to focus on specific file, branch, or tree overview. "
            "Use when you want to show the user something important in the visualization. "
            "Examples: focus on a file you just modified, show the branch structure, "
            "or zoom out to see the full tree."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "File path (e.g., 'src/main.py'), branch name, or 'overview' for full tree view"
                },
                "zoom": {
                    "type": "string",
                    "enum": ["close", "medium", "far"],
                    "description": "Zoom level: 'close' for detail, 'medium' for context, 'far' for overview",
                    "default": "medium"
                },
                "highlight": {
                    "type": "boolean",
                    "description": "Highlight the target node with a glow effect",
                    "default": True
                },
                "animate": {
                    "type": "boolean",
                    "description": "Animate camera movement (smooth transition)",
                    "default": True
                }
            },
            "required": ["target"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        target = arguments.get("target", "overview")
        zoom = arguments.get("zoom", "medium")
        highlight = arguments.get("highlight", True)
        animate = arguments.get("animate", True)

        # Get SocketIO from global MCP server
        from src.mcp.mcp_server import get_mcp_server
        mcp = get_mcp_server()

        if mcp and mcp.socketio:
            # Emit camera control event to all connected clients
            mcp.socketio.emit('camera_control', {
                'action': 'focus',
                'target': target,
                'zoom': zoom,
                'highlight': highlight,
                'animate': animate
            }, namespace='/')

            return {
                "success": True,
                "message": f"Camera focusing on '{target}' (zoom={zoom}, highlight={highlight})"
            }
        else:
            return {
                "success": False,
                "error": "SocketIO not available - cannot control camera"
            }
