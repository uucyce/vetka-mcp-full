"""MYCELIUM WebSocket Server — DevPanel direct connection.

Lightweight WebSocket server on port 8082 for DevPanel.
Broadcasts pipeline activity, task board updates, and stats.
Uses `websockets` library (no FastAPI/SocketIO needed).

MARKER_129.5: Phase 129 — DevPanel direct WebSocket

@status: active
@phase: 129
@depends: websockets, asyncio, json
@used_by: mycelium_mcp_server.py, agent_pipeline.py (ws_broadcaster)
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)

MYCELIUM_WS_PORT = int(os.environ.get("MYCELIUM_WS_PORT", "8082"))
MYCELIUM_WS_HOST = os.environ.get("MYCELIUM_WS_HOST", "localhost")


# MARKER_129.5_START: MyceliumWSBroadcaster — WebSocket for DevPanel
class MyceliumWSBroadcaster:
    """WebSocket server for DevPanel direct connection.

    Events streamed to DevPanel:
    - pipeline_activity: role, message, model, subtask progress
    - task_board_updated: action, task data
    - pipeline_stats: per-pipeline metrics (LLM calls, tokens, duration)
    - pipeline_complete: task_id, final result
    - pipeline_failed: task_id, error
    - pong: heartbeat response
    """

    def __init__(self, host: str = None, port: int = None):
        self.host = host or MYCELIUM_WS_HOST
        self.port = port or MYCELIUM_WS_PORT
        self.clients: Set = set()
        self._server = None
        self._start_time = time.time()
        self._messages_sent = 0

    async def start(self):
        """Start WebSocket server."""
        try:
            import websockets
            self._server = await websockets.serve(
                self._handler, self.host, self.port
            )
            logger.info(f"[MYCELIUM WS] Listening on ws://{self.host}:{self.port}")
        except ImportError:
            logger.warning("[MYCELIUM WS] websockets not installed — DevPanel direct connection disabled")
            logger.warning("[MYCELIUM WS] Install with: pip install websockets>=12.0")
        except OSError as e:
            logger.error(f"[MYCELIUM WS] Port {self.port} in use: {e}")
            logger.error("[MYCELIUM WS] Set MYCELIUM_WS_PORT to use different port")

    async def stop(self):
        """Stop WebSocket server and close all connections."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            logger.info("[MYCELIUM WS] Server stopped")

    @property
    def is_running(self) -> bool:
        return self._server is not None

    @property
    def client_count(self) -> int:
        return len(self.clients)

    async def _handler(self, websocket, path=None):
        """Handle individual WebSocket connection."""
        self.clients.add(websocket)
        client_id = id(websocket)
        logger.info(f"[MYCELIUM WS] Client {client_id} connected ({self.client_count} total)")

        # Send welcome message
        try:
            await websocket.send(json.dumps({
                "type": "connected",
                "server": "mycelium",
                "uptime": int(time.time() - self._start_time),
                "clients": self.client_count,
            }))
        except Exception:
            pass

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_client_message(data, websocket)
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass  # Connection closed
        finally:
            self.clients.discard(websocket)
            logger.info(f"[MYCELIUM WS] Client {client_id} disconnected ({self.client_count} total)")

    async def _handle_client_message(self, data: dict, ws):
        """Handle incoming messages from DevPanel."""
        msg_type = data.get("type")

        if msg_type == "ping":
            try:
                await ws.send(json.dumps({"type": "pong", "timestamp": time.time()}))
            except Exception:
                pass

    async def broadcast(self, data: dict):
        """Broadcast event to all connected DevPanel clients.

        Fire-and-forget — never blocks pipeline on WebSocket errors.
        Automatically removes disconnected clients.
        """
        if not self.clients:
            return

        message = json.dumps(data, default=str)
        disconnected = set()

        for client in list(self.clients):
            try:
                await client.send(message)
                self._messages_sent += 1
            except Exception:
                disconnected.add(client)

        if disconnected:
            self.clients -= disconnected

    async def broadcast_pipeline_activity(
        self, role: str, message: str, model: str = "system",
        subtask_idx: int = 0, total: int = 0,
        task_id: str = None, preset: str = None
    ):
        """Broadcast pipeline activity event (convenience method)."""
        await self.broadcast({
            "type": "pipeline_activity",
            "role": role,
            "message": message,
            "model": model,
            "subtask_idx": subtask_idx,
            "total": total,
            "task_id": task_id,
            "preset": preset,
            "timestamp": time.time(),
        })

    async def broadcast_board_update(self, action: str, task_data: dict = None):
        """Broadcast task board update event."""
        await self.broadcast({
            "type": "task_board_updated",
            "action": action,
            "task": task_data,
            "timestamp": time.time(),
        })

    async def broadcast_pipeline_stats(self, stats: dict):
        """Broadcast pipeline statistics."""
        await self.broadcast({
            "type": "pipeline_stats",
            "stats": stats,
            "timestamp": time.time(),
        })

    def get_status(self) -> dict:
        """Get WebSocket server status for health check."""
        return {
            "running": self.is_running,
            "host": self.host,
            "port": self.port,
            "clients": self.client_count,
            "messages_sent": self._messages_sent,
            "uptime": int(time.time() - self._start_time),
        }


# Singleton
_ws_broadcaster: Optional[MyceliumWSBroadcaster] = None


def get_ws_broadcaster() -> MyceliumWSBroadcaster:
    """Get or create singleton MyceliumWSBroadcaster."""
    global _ws_broadcaster
    if _ws_broadcaster is None:
        _ws_broadcaster = MyceliumWSBroadcaster()
    return _ws_broadcaster
# MARKER_129.5_END
