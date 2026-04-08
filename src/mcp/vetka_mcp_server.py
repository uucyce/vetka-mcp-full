#!/usr/bin/env python3
"""
VETKA Universal MCP Server - Multi-Transport Support + Multi-Agent Hub

@file vetka_mcp_server.py
@status PRODUCTION (Phase 106f)
@phase Phase 106f - Multi-Agent MCP Enhancements
@lastAudit 2026-02-02

Multi-transport MCP server supporting:
- stdio (Claude Desktop/Code) ✅
- HTTP (VS Code, Cursor, Gemini) ✅ + Session Dispatch
- SSE (JetBrains) ✅
- WebSocket (Real-time) ✅ NEW

Phase 106f Features:
- Session-based actor isolation (X-Session-ID header)
- Multi-agent support via MCPActor dispatcher
- WebSocket endpoint for real-time communication
- Enhanced monitoring with /api/stats
- Health checks with actor status

Usage:
  # stdio mode (Claude Desktop/Code) - default
  python vetka_mcp_server.py

  # HTTP mode with session dispatch (VS Code, Cursor, Gemini)
  python vetka_mcp_server.py --http --port 5002

  # HTTP + WebSocket mode (multi-agent support)
  python vetka_mcp_server.py --http --ws --port 5002

  # SSE mode (JetBrains)
  python vetka_mcp_server.py --sse --port 5003
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import AsyncGenerator

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import Phase 65.1 bridge as base (all tools and implementations)
from src.mcp.vetka_mcp_bridge import (
    server,
    init_client,
    cleanup_client,
    VETKA_BASE_URL,
    list_tools as bridge_list_tools,
)
from src.mcp import vetka_mcp_bridge

MCP_VERSION = "2.0.0"
MCP_PROTOCOL_VERSION = "2024-11-05"


# ============================================================================
# STDIO TRANSPORT (from Phase 65.1)
# ============================================================================

async def run_stdio():
    """
    Run MCP server with stdio transport.
    Supports Claude Desktop, Claude Code, and other stdio-based MCP clients.
    """
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"  VETKA MCP stdio Server (Phase 65.2)", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)
    print(f"  Reading from: stdin", file=sys.stderr)
    print(f"  Writing to: stdout", file=sys.stderr)
    print(f"  VETKA API: {VETKA_BASE_URL}", file=sys.stderr)
    print(f"  Tools: 13 (8 read + 5 write)", file=sys.stderr)
    print(f"{'=' * 60}\n", file=sys.stderr)

    # Initialize HTTP client to VETKA
    await init_client()

    try:
        from mcp.server.stdio import stdio_server
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    finally:
        await cleanup_client()


# ============================================================================
# HTTP TRANSPORT (Phase 106f - Multi-Agent Enhanced)
# ============================================================================

async def run_http(port: int = 5002, enable_ws: bool = False):
    """
    Run MCP server with HTTP transport and optional WebSocket.
    Supports VS Code, Cursor, Gemini CLI, and other HTTP-based MCP clients.

    Endpoints:
      POST /mcp - JSON-RPC 2.0 with session dispatch
      GET /health - Health check
      GET /api/stats - Actor and pool statistics
      WS /mcp/ws - WebSocket transport (if enable_ws=True)
    """
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import JSONResponse, PlainTextResponse
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware
    import uvicorn

    print(f"\n{'=' * 60}")
    print(f"  VETKA MCP HTTP Server (Phase 106f)")
    print(f"{'=' * 60}")
    print(f"  Listening on: http://0.0.0.0:{port}")
    print(f"  Endpoint: POST http://localhost:{port}/mcp")
    print(f"  Health: GET http://localhost:{port}/health")
    print(f"  Stats: GET http://localhost:{port}/api/stats")
    if enable_ws:
        print(f"  WebSocket: ws://localhost:{port}/mcp/ws")
    print(f"  VETKA API: {VETKA_BASE_URL}")
    print(f"  Tools: 13 (8 read + 5 write)")
    print(f"  Multi-Agent: Session dispatch enabled")
    print(f"{'=' * 60}\n")

    # Initialize HTTP client to VETKA
    await init_client()

    async def health_check(request):
        """Enhanced health check endpoint with actor status (Phase 106f)"""
        try:
            from src.mcp.mcp_actor import get_dispatcher
            stats = get_dispatcher().get_stats()
            healthy = stats["healthy_actors"] == stats["active_actors"] if stats["active_actors"] > 0 else True
            status_text = "healthy" if healthy else "degraded"
        except ImportError:
            # Actor system not available, basic health check
            stats = None
            status_text = "healthy"
            healthy = True

        response = {
            "status": status_text,
            "transport": "http",
            "server": "vetka-mcp",
            "version": MCP_VERSION,
            "protocol": MCP_PROTOCOL_VERSION,
            "vetka_api": VETKA_BASE_URL,
            "tools_count": 13
        }

        if stats:
            response["active_actors"] = stats["active_actors"]
            response["healthy_actors"] = stats["healthy_actors"]

        return JSONResponse(response)

    async def stats_endpoint(request):
        """Stats endpoint for monitoring actor and pool metrics (Phase 106f)"""
        try:
            from src.mcp.mcp_actor import get_dispatcher
            from src.mcp.client_pool import get_pool_manager

            return JSONResponse({
                "actors": get_dispatcher().get_stats(),
                "pools": get_pool_manager().get_stats(),
                "timestamp": asyncio.get_event_loop().time()
            })
        except ImportError:
            return JSONResponse({
                "error": "Actor system not available",
                "fallback": True,
                "message": "Multi-agent features require Phase 106 components"
            }, status_code=503)

    async def handle_mcp(request):
        """Handle MCP JSON-RPC requests with session dispatch (Phase 106f)"""
        # Extract session ID from header for session isolation
        session_id = request.headers.get("X-Session-ID", "default")

        try:
            body = await request.json()
        except Exception as e:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error",
                    "data": str(e)
                }
            }, status_code=400)

        method = body.get("method", "")
        params = body.get("params", {})
        req_id = body.get("id")

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "serverInfo": {
                        "name": "vetka",
                        "version": MCP_VERSION
                    },
                    "capabilities": {
                        "tools": {},
                        "multiSession": True  # Phase 106 feature
                    },
                    "sessionInfo": {
                        "sessionId": session_id
                    }
                }

            elif method == "tools/list":
                tools = await bridge_list_tools()
                result = {
                    "tools": [
                        {
                            "name": t.name,
                            "description": t.description,
                            "inputSchema": t.inputSchema
                        }
                        for t in tools
                    ]
                }

            elif method == "tools/call":
                # Phase 106f: Use MCPActor dispatcher for session isolation
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})

                try:
                    from src.mcp.mcp_actor import get_dispatcher
                    result = await get_dispatcher().dispatch(
                        session_id,
                        {
                            "type": "tool_call",
                            "name": tool_name,
                            "arguments": tool_args
                        },
                        wait=True
                    )

                    # Format result for MCP protocol - convert TextContent to dict
                    def to_dict(item):
                        if hasattr(item, 'type') and hasattr(item, 'text'):
                            return {"type": item.type, "text": item.text}
                        elif isinstance(item, dict):
                            return item
                        else:
                            return {"type": "text", "text": str(item)}

                    if isinstance(result, list):
                        # Convert list of TextContent to dicts
                        result = {"content": [to_dict(c) for c in result]}
                    elif hasattr(result, '__iter__') and not isinstance(result, (str, dict)):
                        # Convert iterable to MCP format
                        result = {"content": [to_dict(c) for c in result]}
                    elif not isinstance(result, dict) or "content" not in result:
                        # Wrap raw result
                        result = {"content": [{"type": "text", "text": str(result)}]}

                except ImportError:
                    # Fallback to direct call if actor system not available
                    content_list = await vetka_mcp_bridge.call_tool(tool_name, tool_args)
                    result = {
                        "content": [
                            {"type": c.type, "text": c.text}
                            for c in content_list
                        ]
                    }

            else:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }, status_code=404)

            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result
            })

        except Exception as e:
            import traceback
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": {
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }
                }
            }, status_code=500)

    async def handle_options(request):
        """Handle CORS preflight"""
        return PlainTextResponse("", status_code=204)

    # Build routes list
    routes = [
        Route("/health", health_check, methods=["GET"]),
        Route("/api/stats", stats_endpoint, methods=["GET"]),
        Route("/mcp", handle_mcp, methods=["POST"]),
        Route("/mcp", handle_options, methods=["OPTIONS"]),
        Route("/", lambda r: PlainTextResponse(
            "VETKA MCP HTTP Server (Phase 106f)\n"
            "POST /mcp for JSON-RPC\n"
            "GET /health for health check\n"
            "GET /api/stats for monitoring\n" +
            ("WS /mcp/ws for WebSocket\n" if enable_ws else "")
        ))
    ]

    # Add WebSocket endpoint if enabled (Phase 106f)
    if enable_ws:
        from starlette.websockets import WebSocket
        from starlette.routing import WebSocketRoute
        import json as json_lib

        async def mcp_websocket(websocket: WebSocket):
            """WebSocket endpoint for real-time MCP communication"""
            await websocket.accept()
            session_id = websocket.headers.get("X-Session-ID", f"ws_{id(websocket)}")
            print(f"[MCP:WS] WebSocket connected: session={session_id}")

            try:
                from src.mcp.mcp_actor import get_dispatcher
                dispatcher = get_dispatcher()

                async for message_text in websocket.iter_text():
                    try:
                        data = json_lib.loads(message_text)
                        result = await dispatcher.dispatch(session_id, data, wait=True)
                        await websocket.send_text(json_lib.dumps({
                            "status": "success",
                            "result": result
                        }))
                    except json_lib.JSONDecodeError as e:
                        await websocket.send_text(json_lib.dumps({
                            "status": "error",
                            "error": f"Invalid JSON: {str(e)}"
                        }))
                    except Exception as e:
                        await websocket.send_text(json_lib.dumps({
                            "status": "error",
                            "error": str(e)
                        }))

            except Exception as e:
                print(f"[MCP:WS] Error: {e}")
            finally:
                print(f"[MCP:WS] WebSocket disconnected: session={session_id}")
                await websocket.close()

        routes.append(WebSocketRoute("/mcp/ws", mcp_websocket))

    # Create Starlette app with CORS middleware
    app = Starlette(
        routes=routes,
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"],
            )
        ]
    )

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )

    server_instance = uvicorn.Server(config)

    try:
        await server_instance.serve()
    finally:
        await cleanup_client()


# ============================================================================
# SSE TRANSPORT (Phase 65.2)
# ============================================================================

async def run_sse(port: int = 5003):
    """
    Run MCP server with SSE (Server-Sent Events) transport.
    Supports JetBrains IDEs and other SSE-based MCP clients.

    Endpoints:
      GET /sse - SSE event stream
      POST /mcp - JSON-RPC requests
    """
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import JSONResponse, PlainTextResponse
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware
    from sse_starlette.sse import EventSourceResponse
    import uvicorn

    print(f"\n{'=' * 60}")
    print(f"  VETKA MCP SSE Server (Phase 65.2)")
    print(f"{'=' * 60}")
    print(f"  Listening on: http://0.0.0.0:{port}")
    print(f"  SSE Stream: GET http://localhost:{port}/sse")
    print(f"  JSON-RPC: POST http://localhost:{port}/mcp")
    print(f"  VETKA API: {VETKA_BASE_URL}")
    print(f"  Tools: 13 (8 read + 5 write)")
    print(f"{'=' * 60}\n")

    # Initialize HTTP client to VETKA
    await init_client()

    # Store for pending requests (SSE clients send requests, get responses via events)
    pending_responses: dict[str, asyncio.Event] = {}
    response_data: dict[str, dict] = {}

    async def sse_event_generator(request) -> AsyncGenerator:
        """Generate SSE events for connected clients"""
        # Send initial connection event
        yield {
            "event": "connected",
            "data": json.dumps({
                "server": "vetka-mcp",
                "version": MCP_VERSION,
                "protocol": MCP_PROTOCOL_VERSION
            })
        }

        # Send server capabilities
        tools = await bridge_list_tools()
        yield {
            "event": "capabilities",
            "data": json.dumps({
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.inputSchema
                    }
                    for t in tools
                ]
            })
        }

        # Keep connection alive with heartbeat
        while True:
            await asyncio.sleep(30)
            yield {"event": "ping", "data": ""}

    async def handle_sse(request):
        """Handle SSE connection"""
        return EventSourceResponse(sse_event_generator(request))

    async def handle_mcp(request):
        """Handle MCP JSON-RPC requests (same as HTTP)"""
        try:
            body = await request.json()
        except Exception as e:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error", "data": str(e)}
            }, status_code=400)

        method = body.get("method", "")
        params = body.get("params", {})
        req_id = body.get("id")

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "serverInfo": {"name": "vetka", "version": MCP_VERSION},
                    "capabilities": {"tools": {}}
                }

            elif method == "tools/list":
                tools = await bridge_list_tools()
                result = {
                    "tools": [
                        {"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
                        for t in tools
                    ]
                }

            elif method == "tools/call":
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})
                content_list = await vetka_mcp_bridge.call_tool(tool_name, tool_args)
                result = {
                    "content": [{"type": c.type, "text": c.text} for c in content_list]
                }

            else:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }, status_code=404)

            return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": result})

        except Exception as e:
            import traceback
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": {"error": str(e), "traceback": traceback.format_exc()}
                }
            }, status_code=500)

    async def health_check(request):
        """Health check endpoint"""
        return JSONResponse({
            "status": "healthy",
            "transport": "sse",
            "server": "vetka-mcp",
            "version": MCP_VERSION
        })

    # Create app
    app = Starlette(
        routes=[
            Route("/sse", handle_sse, methods=["GET"]),
            Route("/mcp", handle_mcp, methods=["POST"]),
            Route("/health", health_check, methods=["GET"]),
            Route("/", lambda r: PlainTextResponse(
                "VETKA MCP SSE Server\n"
                "GET /sse for event stream\n"
                "POST /mcp for JSON-RPC"
            ))
        ],
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"],
            )
        ]
    )

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )

    server_instance = uvicorn.Server(config)

    try:
        await server_instance.serve()
    finally:
        await cleanup_client()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Parse arguments and run appropriate transport"""
    parser = argparse.ArgumentParser(
        description="VETKA Universal MCP Server (Phase 65.2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Transports:
  stdio (default)  - Claude Desktop/Code, Xcode
  HTTP             - VS Code, Cursor, Gemini CLI, GitHub Copilot
  SSE              - JetBrains IDEs

Examples:
  # stdio mode (Claude Desktop/Code)
  python vetka_mcp_server.py

  # HTTP mode (VS Code, Cursor, Gemini)
  python vetka_mcp_server.py --http --port 5002

  # SSE mode (JetBrains)
  python vetka_mcp_server.py --sse --port 5003

  # Test HTTP server
  curl http://localhost:5002/health
  curl -X POST http://localhost:5002/mcp \\
    -H "Content-Type: application/json" \\
    -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
"""
    )

    parser.add_argument(
        "--http",
        action="store_true",
        help="Run HTTP server (VS Code, Cursor, Gemini)"
    )

    parser.add_argument(
        "--sse",
        action="store_true",
        help="Run SSE server (JetBrains)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=5002,
        help="Port for HTTP/SSE server (default: 5002)"
    )

    args = parser.parse_args()

    try:
        if args.http:
            asyncio.run(run_http(args.port))
        elif args.sse:
            asyncio.run(run_sse(args.port))
        else:
            # stdio mode (default)
            asyncio.run(run_stdio())

    except KeyboardInterrupt:
        print("\n\nShutting down...", file=sys.stderr)
        sys.exit(0)

    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
