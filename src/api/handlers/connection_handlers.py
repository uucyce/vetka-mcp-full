"""
VETKA Connection Handlers - FastAPI/ASGI Version

@file connection_handlers.py
@status ACTIVE
@phase Phase 39.7
@lastAudit 2026-01-05

Connection Socket.IO handlers for python-socketio AsyncServer.
Migrated from src/server/handlers/connection_handlers.py (Flask-SocketIO)

Changes from Flask version:
- @socketio.on('connect') -> @sio.event async def connect()
- emit() -> await sio.emit()
- request.sid -> sid parameter
- def -> async def
"""

import time
import asyncio

# Connection rate-limiting state
_CONNECTION_LOG_TIMES = {}
_CONNECTION_LOG_INTERVAL = 5.0
_CONNECTION_LOG_LOCK = asyncio.Lock()
_TOTAL_CONNECTIONS = 0
_TOTAL_DISCONNECTIONS = 0


async def _should_log_connection(client_id: str, event_type: str = "connect") -> bool:
    """
    Rate-limit connection/disconnection logging to prevent spam.
    Returns True if this event should be logged.
    """
    global _TOTAL_CONNECTIONS, _TOTAL_DISCONNECTIONS

    async with _CONNECTION_LOG_LOCK:
        if event_type == "connect":
            _TOTAL_CONNECTIONS += 1
        else:
            _TOTAL_DISCONNECTIONS += 1

        key = f"{client_id}:{event_type}"
        now = time.time()
        last_log = _CONNECTION_LOG_TIMES.get(key, 0)

        if now - last_log >= _CONNECTION_LOG_INTERVAL:
            _CONNECTION_LOG_TIMES[key] = now
            return True
        return False


def register_connection_handlers(sio, app=None):
    """Register connection-related Socket.IO handlers."""

    # Phase 53: Import ChatRegistry for session cleanup
    from src.chat.chat_registry import ChatRegistry

    @sio.event
    async def connect(sid, environ):
        """Handle client connection (rate-limited logging)"""
        client_id = sid[:8]
        if await _should_log_connection(client_id, "connect"):
            print(f"  Client connected: {client_id} (total: {_TOTAL_CONNECTIONS})")

        await sio.emit('connect_response', {
            'data': 'Connected to VETKA Phase 53',
            'timestamp': time.time()
        }, to=sid)

    @sio.event
    async def disconnect(sid):
        """Handle client disconnection (rate-limited logging)"""
        client_id = sid[:8]

        # Phase 53: Clean up per-session chat manager
        ChatRegistry.remove_manager(sid)

        if await _should_log_connection(client_id, "disconnect"):
            print(f"  Client disconnected: {client_id} (total: {_TOTAL_DISCONNECTIONS})")
