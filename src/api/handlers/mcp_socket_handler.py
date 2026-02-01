# MARKER_106e_1: MCP Socket.IO namespace handler
"""
MCP Socket.IO namespace for real-time agent communication.

Events (Client → Server):
- mcp_join: Join session with optional reconnect
- mcp_tool_call: Execute tool via WebSocket
- mcp_broadcast: Broadcast to session room
- mcp_ping: Health check

Events (Server → Client):
- mcp_status: Connection/session status
- mcp_result: Tool execution result
- mcp_error: Error notification
- mcp_progress: Execution progress
- mcp_pong: Health response with stats
"""

from socketio import AsyncServer
from typing import Dict, Any, Set
import asyncio
import time
from collections import defaultdict

MCP_NAMESPACE = "/mcp"

MESSAGE_LIMIT = 100
MESSAGE_WINDOW = 60

class MCPSocketManager:
    def __init__(self):
        self.client_sessions: Dict[str, str] = {}
        self.session_clients: Dict[str, Set[str]] = defaultdict(set)
        self.message_counts: Dict[str, list] = defaultdict(list)

    def associate(self, sid: str, session_id: str):
        self.client_sessions[sid] = session_id
        self.session_clients[session_id].add(sid)

    def disassociate(self, sid: str):
        session_id = self.client_sessions.pop(sid, None)
        if session_id:
            self.session_clients[session_id].discard(sid)
            if not self.session_clients[session_id]:
                del self.session_clients[session_id]
        self.message_counts.pop(sid, None)

    def check_rate_limit(self, sid: str) -> bool:
        now = time.time()
        timestamps = self.message_counts[sid]
        timestamps[:] = [t for t in timestamps if now - t < MESSAGE_WINDOW]
        if len(timestamps) >= MESSAGE_LIMIT:
            return False
        timestamps.append(now)
        return True

    def get_session_sids(self, session_id: str) -> Set[str]:
        return self.session_clients.get(session_id, set())

_manager = MCPSocketManager()

async def register_mcp_socket_handlers(sio: AsyncServer, app):
    """Register MCP namespace event handlers"""

    @sio.on("connect", namespace=MCP_NAMESPACE)
    async def handle_connect(sid, environ):
        print(f"[MCP:WS] Client connected: {sid}")
        await sio.emit("mcp_status", {
            "status": "connected",
            "sid": sid,
            "timestamp": time.time()
        }, to=sid, namespace=MCP_NAMESPACE)

    @sio.on("disconnect", namespace=MCP_NAMESPACE)
    async def handle_disconnect(sid):
        print(f"[MCP:WS] Client disconnected: {sid}")
        session_id = _manager.client_sessions.get(sid)
        _manager.disassociate(sid)

        if session_id and not _manager.get_session_sids(session_id):
            async def delayed_cleanup():
                await asyncio.sleep(30)
                if not _manager.get_session_sids(session_id):
                    from src.mcp.mcp_actor import get_dispatcher
                    await get_dispatcher().cleanup(session_id)
            asyncio.create_task(delayed_cleanup())

    @sio.on("mcp_join", namespace=MCP_NAMESPACE)
    async def handle_join(sid, data: Dict[str, Any]):
        session_id = data.get("session_id") or sid
        reconnect = data.get("reconnect", False)

        _manager.associate(sid, session_id)

        from src.mcp.mcp_actor import get_dispatcher
        dispatcher = get_dispatcher()
        actor = await dispatcher.get_or_create(session_id)

        await sio.enter_room(sid, f"mcp_{session_id}", namespace=MCP_NAMESPACE)

        response = {
            "status": "joined" if not reconnect else "rejoined",
            "session_id": session_id,
            "actor_stats": actor.get_stats()
        }

        if reconnect:
            response["context"] = actor.context

        await sio.emit("mcp_status", response, to=sid, namespace=MCP_NAMESPACE)

    @sio.on("mcp_tool_call", namespace=MCP_NAMESPACE)
    async def handle_tool_call(sid, data: Dict[str, Any]):
        if not _manager.check_rate_limit(sid):
            await sio.emit("mcp_error", {
                "error": "Rate limit exceeded",
                "retry_after": MESSAGE_WINDOW
            }, to=sid, namespace=MCP_NAMESPACE)
            return

        session_id = _manager.client_sessions.get(sid, sid)
        tool_name = data.get("tool")
        arguments = data.get("arguments", {})
        request_id = data.get("request_id", str(time.time()))

        try:
            await sio.emit("mcp_progress", {
                "request_id": request_id,
                "tool": tool_name,
                "status": "started"
            }, to=sid, namespace=MCP_NAMESPACE)

            from src.mcp.mcp_actor import get_dispatcher
            result = await get_dispatcher().dispatch(
                session_id,
                {"type": "tool_call", "name": tool_name, "arguments": arguments},
                wait=True
            )

            await sio.emit("mcp_result", {
                "request_id": request_id,
                "tool": tool_name,
                "result": result,
                "session_id": session_id
            }, to=sid, namespace=MCP_NAMESPACE)

        except asyncio.TimeoutError:
            await sio.emit("mcp_error", {
                "request_id": request_id,
                "tool": tool_name,
                "error": "Request timed out"
            }, to=sid, namespace=MCP_NAMESPACE)

        except Exception as e:
            await sio.emit("mcp_error", {
                "request_id": request_id,
                "tool": tool_name,
                "error": str(e)
            }, to=sid, namespace=MCP_NAMESPACE)

    @sio.on("mcp_ping", namespace=MCP_NAMESPACE)
    async def handle_ping(sid, data: Dict[str, Any]):
        from src.mcp.mcp_actor import get_dispatcher
        from src.mcp.client_pool import get_pool_manager

        stats = {
            "dispatcher": get_dispatcher().get_stats(),
            "pool": get_pool_manager().get_stats(),
            "socket_manager": {
                "total_clients": len(_manager.client_sessions),
                "total_sessions": len(_manager.session_clients)
            }
        }

        await sio.emit("mcp_pong", {
            "timestamp": time.time(),
            "stats": stats
        }, to=sid, namespace=MCP_NAMESPACE)
