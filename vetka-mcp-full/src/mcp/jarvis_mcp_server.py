#!/usr/bin/env python3
# MARKER_138.S2_2_JARVIS_MCP_SERVER
"""Jarvis MCP server (standalone, async, non-blocking)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

logger = logging.getLogger("JARVIS_MCP")
logging.basicConfig(level=logging.INFO, format="[JARVIS MCP] %(message)s")

MCP_AVAILABLE = True
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except Exception:  # pragma: no cover - fallback for test/import environments
    MCP_AVAILABLE = False
    Server = None
    stdio_server = None

    class TextContent:  # type: ignore[override]
        def __init__(self, type: str, text: str):
            self.type = type
            self.text = text

    class Tool:  # type: ignore[override]
        def __init__(self, name: str, description: str, inputSchema: Dict[str, Any]):
            self.name = name
            self.description = description
            self.inputSchema = inputSchema

from src.jarvis.workflow_router import JarvisWorkflowRouter
from src.jarvis.engram_bridge import get_jarvis_engram_bridge


JARVIS_TOOLS = [
    Tool(
        name="jarvis_health",
        description="Health status for Jarvis MCP server.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="jarvis_workflow_route",
        description="Route request to Jarvis workflow plan.",
        inputSchema={
            "type": "object",
            "properties": {
                "request": {"type": "string"},
                "voice_mode": {"type": "boolean"},
            },
            "required": ["request"],
        },
    ),
    Tool(
        name="jarvis_context",
        description="Fetch Engram-based user context for request.",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "request": {"type": "string"},
            },
            "required": ["user_id", "request"],
        },
    ),
    Tool(
        name="jarvis_chat",
        description="Non-blocking Jarvis chat response via voice subsystem.",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "request": {"type": "string"},
                "timeout": {"type": "integer"},
            },
            "required": ["request"],
        },
    ),
    Tool(
        name="jarvis_unified_search",
        description="Proxy search to VETKA unified search endpoint.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
                "sources": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["query"],
        },
    ),
]

_start_time = time.time()
_router = JarvisWorkflowRouter()


def _get_jarvis_respond():
    from src.voice.jarvis_llm import jarvis_respond

    return jarvis_respond


async def _handle_health() -> Dict[str, Any]:
    return {
        "success": True,
        "server": "jarvis",
        "status": "healthy",
        "uptime_s": int(time.time() - _start_time),
        "mcp_available": MCP_AVAILABLE,
    }


async def _handle_workflow_route(arguments: Dict[str, Any]) -> Dict[str, Any]:
    request = (arguments.get("request") or "").strip()
    voice_mode = bool(arguments.get("voice_mode", False))
    if not request:
        return {"success": False, "error": "request is required"}

    plan = _router.route(request=request, voice_mode=voice_mode)
    return {"success": True, "plan": plan.to_dict()}


async def _handle_context(arguments: Dict[str, Any]) -> Dict[str, Any]:
    user_id = (arguments.get("user_id") or "default_user").strip()
    request = (arguments.get("request") or "").strip()
    if not request:
        return {"success": False, "error": "request is required"}

    bridge = get_jarvis_engram_bridge()
    payload = await bridge.build_context(user_id=user_id, request=request)
    return {"success": True, "context": payload}


async def _handle_chat(arguments: Dict[str, Any]) -> Dict[str, Any]:
    request = (arguments.get("request") or "").strip()
    user_id = (arguments.get("user_id") or "default_user").strip()
    timeout_s = int(arguments.get("timeout", 30))

    if not request:
        return {"success": False, "error": "request is required"}

    # Non-blocking path: timeout-bounded async call to voice subsystem.
    try:
        jarvis_respond = _get_jarvis_respond()
        response = await asyncio.wait_for(
            jarvis_respond(transcript=request, user_id=user_id),
            timeout=max(2, min(timeout_s, 120)),
        )
        return {"success": True, "response": response, "user_id": user_id}
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": f"Jarvis response timeout after {timeout_s}s",
            "user_id": user_id,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "user_id": user_id}


async def _handle_unified_search(arguments: Dict[str, Any]) -> Dict[str, Any]:
    query = (arguments.get("query") or "").strip()
    if not query:
        return {"success": False, "error": "query is required"}

    limit = max(1, min(int(arguments.get("limit", 20)), 100))
    sources = arguments.get("sources")

    try:
        import httpx

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "http://localhost:5001/api/search/unified",
                json={"query": query, "limit": limit, "sources": sources},
            )
        if resp.status_code != 200:
            return {"success": False, "error": f"HTTP {resp.status_code}", "query": query}
        data = resp.json()
        return {"success": True, "query": query, "result": data}
    except Exception as e:
        return {"success": False, "error": str(e), "query": query}


if MCP_AVAILABLE:
    server = Server("jarvis")

    @server.list_tools()  # type: ignore[misc]
    async def _list_tools() -> List[Tool]:
        return JARVIS_TOOLS

    @server.call_tool()  # type: ignore[misc]
    async def _call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        if name == "jarvis_health":
            result = await _handle_health()
        elif name == "jarvis_workflow_route":
            result = await _handle_workflow_route(arguments)
        elif name == "jarvis_context":
            result = await _handle_context(arguments)
        elif name == "jarvis_chat":
            result = await _handle_chat(arguments)
        elif name == "jarvis_unified_search":
            result = await _handle_unified_search(arguments)
        else:
            result = {"success": False, "error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


async def main() -> None:
    if not MCP_AVAILABLE:
        raise RuntimeError("MCP package not available for jarvis_mcp_server")

    logger.info("Starting Jarvis MCP server")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
