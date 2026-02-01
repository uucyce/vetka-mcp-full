# Phase 106: Multi-Agent MCP Super-Prompt v2.0

## Changes from v1.0
- Added graceful shutdown handling
- Added health check endpoints
- Added metrics collection
- Added error recovery patterns
- Added session timeout handling
- Added WebSocket reconnection logic

---

## PHASE 106a: HTTP Multi-Transport Activation

### Task 1.1: CLI Argument Parsing (UNCHANGED)
**File:** `src/mcp/vetka_mcp_bridge.py`
**Line:** After imports (~44)

```python
# MARKER_106a_1: CLI arguments
import argparse
import signal

def parse_args():
    parser = argparse.ArgumentParser(description='VETKA MCP Bridge')
    parser.add_argument('--http', action='store_true', help='Use HTTP transport')
    parser.add_argument('--port', type=int, default=5002, help='HTTP port')
    parser.add_argument('--session-id', type=str, help='Session ID for isolation')
    parser.add_argument('--ws', action='store_true', help='Enable WebSocket mode')
    return parser.parse_args()
```

### Task 1.2: Session ID Header Support (ENHANCED)
**File:** `src/mcp/vetka_mcp_bridge.py`
**Line:** Replace init_client() (69-76)

```python
# MARKER_106a_2: Enhanced client initialization with retry
import uuid

async def init_client(session_id: str = None):
    global http_client

    if session_id is None:
        session_id = str(uuid.uuid4())

    headers = {
        "X-Session-ID": session_id,
        "X-Agent-ID": f"mcp_{session_id[:8]}",
        "X-Client-Version": "106.0"
    }

    http_client = httpx.AsyncClient(
        base_url=VETKA_BASE_URL,
        timeout=httpx.Timeout(
            connect=10.0,    # Connection timeout
            read=90.0,       # Read timeout (LLM calls)
            write=30.0,      # Write timeout
            pool=5.0         # Pool acquisition timeout
        ),
        follow_redirects=True,
        headers=headers,
        limits=httpx.Limits(
            max_connections=50,
            max_keepalive_connections=10,
            keepalive_expiry=30.0
        )
    )

    return session_id
```

### Task 1.3: Graceful Shutdown (NEW)
**File:** `src/mcp/vetka_mcp_bridge.py`
**Line:** Add before main()

```python
# MARKER_106a_3: Graceful shutdown handler
_shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    print(f"[MCP] Received signal {signum}, initiating shutdown...")
    _shutdown_event.set()

async def graceful_shutdown():
    """Cleanup all resources on shutdown"""
    print("[MCP] Shutting down...")

    # Stop all actors
    from src.mcp.mcp_actor import get_dispatcher
    await get_dispatcher().cleanup_all()

    # Close client pools
    from src.mcp.client_pool import get_pool_manager
    await get_pool_manager().shutdown()

    # Close main client
    await cleanup_client()

    print("[MCP] Shutdown complete")
```

### Task 1.4: Main Function with Shutdown (ENHANCED)
**File:** `src/mcp/vetka_mcp_bridge.py`
**Line:** Replace main() (1881-1900)

```python
# MARKER_106a_4: Enhanced main with graceful shutdown
async def main():
    args = parse_args()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    session_id = await init_client(session_id=args.session_id)
    print(f"[MCP] Started with session_id={session_id[:8]}...")

    try:
        if args.http or args.ws:
            from src.mcp.vetka_mcp_server import run_http
            await run_http(port=args.port, enable_ws=args.ws)
        else:
            async with stdio_server() as (read_stream, write_stream):
                init_options = server.create_initialization_options()

                # Run with shutdown monitoring
                server_task = asyncio.create_task(
                    server.run(read_stream, write_stream, init_options)
                )
                shutdown_task = asyncio.create_task(_shutdown_event.wait())

                done, pending = await asyncio.wait(
                    [server_task, shutdown_task],
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in pending:
                    task.cancel()

    finally:
        await graceful_shutdown()
```

---

## PHASE 106b: MCPActor Class Implementation

### Task 2.1: MCPActor with Error Recovery (ENHANCED)
**File:** `src/mcp/mcp_actor.py` (NEW)

```python
# MARKER_106b_1: Full MCPActor with error recovery
"""
MCPActor - Actor model for multi-tenant MCP sessions.

Features:
- Automatic error recovery with exponential backoff
- Message timeout handling
- Metrics collection
- Health monitoring
"""

import asyncio
import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from collections import deque

class ActorState(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING = "waiting"
    ERROR = "error"
    STOPPED = "stopped"

@dataclass
class ActorMetrics:
    messages_processed: int = 0
    messages_failed: int = 0
    total_processing_time: float = 0.0
    last_error: Optional[str] = None
    last_error_time: Optional[float] = None
    created_at: float = field(default_factory=time.time)

@dataclass
class MCPActor:
    session_id: str
    mailbox: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=100))
    state: ActorState = ActorState.IDLE
    context: Dict[str, Any] = field(default_factory=dict)
    metrics: ActorMetrics = field(default_factory=ActorMetrics)
    _task: Optional[asyncio.Task] = None
    _semaphore: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(5))
    _message_timeout: float = 120.0  # 2 minutes per message
    _max_retries: int = 3
    _error_handlers: List[Callable] = field(default_factory=list)
    _result_futures: Dict[str, asyncio.Future] = field(default_factory=dict)

    async def start(self):
        """Start the actor's autonomous loop"""
        self._task = asyncio.create_task(self._loop())
        return self

    async def stop(self, timeout: float = 5.0):
        """Stop the actor gracefully with timeout"""
        await self.mailbox.put({"type": "stop"})

        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except asyncio.TimeoutError:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

        self.state = ActorState.STOPPED

        # Cancel pending result futures
        for future in self._result_futures.values():
            if not future.done():
                future.cancel()

    async def send(self, message: Dict[str, Any], wait_result: bool = False) -> Any:
        """Send message to actor's mailbox"""
        message_id = str(uuid.uuid4())[:8]
        message["_id"] = message_id
        message["_timestamp"] = time.time()

        if wait_result:
            future = asyncio.get_event_loop().create_future()
            self._result_futures[message_id] = future
            await self.mailbox.put(message)
            try:
                return await asyncio.wait_for(future, timeout=self._message_timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Message {message_id} timed out")
            finally:
                self._result_futures.pop(message_id, None)
        else:
            await self.mailbox.put(message)
            return message_id

    async def _loop(self):
        """Autonomous processing loop with error recovery"""
        backoff = 0.1
        max_backoff = 30.0

        while True:
            try:
                self.state = ActorState.WAITING
                msg = await self.mailbox.get()

                if msg.get("type") == "stop":
                    break

                self.state = ActorState.PROCESSING
                start_time = time.time()

                async with self._semaphore:
                    result = await self._process_with_retry(msg)

                # Update metrics
                self.metrics.messages_processed += 1
                self.metrics.total_processing_time += time.time() - start_time

                # Resolve future if waiting
                msg_id = msg.get("_id")
                if msg_id in self._result_futures:
                    self._result_futures[msg_id].set_result(result)

                self.mailbox.task_done()
                backoff = 0.1  # Reset backoff on success

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.state = ActorState.ERROR
                self.metrics.messages_failed += 1
                self.metrics.last_error = str(e)
                self.metrics.last_error_time = time.time()

                # Call error handlers
                for handler in self._error_handlers:
                    try:
                        await handler(self, e)
                    except:
                        pass

                # Exponential backoff
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

    async def _process_with_retry(self, msg: Dict[str, Any]) -> Any:
        """Process message with retry logic"""
        last_error = None

        for attempt in range(self._max_retries):
            try:
                return await asyncio.wait_for(
                    self._process(msg),
                    timeout=self._message_timeout
                )
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Attempt {attempt + 1} timed out")
            except Exception as e:
                last_error = e

            if attempt < self._max_retries - 1:
                await asyncio.sleep(0.5 * (attempt + 1))

        raise last_error

    async def _process(self, msg: Dict[str, Any]) -> Any:
        """Process a single message"""
        msg_type = msg.get("type")

        if msg_type == "tool_call":
            from src.mcp.vetka_mcp_bridge import call_tool
            result = await call_tool(msg["name"], msg.get("arguments", {}))
            self.context["last_result"] = result
            return result

        elif msg_type == "state_update":
            self.context.update(msg.get("data", {}))
            return {"status": "updated"}

        elif msg_type == "ping":
            return {"status": "pong", "session_id": self.session_id}

        else:
            return {"status": "unknown_type", "type": msg_type}

    def add_error_handler(self, handler: Callable):
        """Add custom error handler"""
        self._error_handlers.append(handler)

    def get_stats(self) -> Dict[str, Any]:
        """Return actor statistics"""
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "queue_size": self.mailbox.qsize(),
            "messages_processed": self.metrics.messages_processed,
            "messages_failed": self.metrics.messages_failed,
            "avg_processing_time": (
                self.metrics.total_processing_time / max(1, self.metrics.messages_processed)
            ),
            "uptime_seconds": time.time() - self.metrics.created_at,
            "last_error": self.metrics.last_error
        }

    def is_healthy(self) -> bool:
        """Health check"""
        if self.state == ActorState.STOPPED:
            return False
        if self.state == ActorState.ERROR:
            # Unhealthy if error within last 60 seconds
            if self.metrics.last_error_time:
                return time.time() - self.metrics.last_error_time > 60
        return True
```

### Task 2.2: Session Dispatcher with Health Monitoring (ENHANCED)
**File:** `src/mcp/mcp_actor.py` (append)

```python
# MARKER_106b_2: Enhanced dispatcher with health monitoring

class MCPSessionDispatcher:
    """Manages pool of MCPActors with health monitoring"""

    _instance = None
    MAX_ACTORS = 100
    ACTOR_TTL = 1800  # 30 minutes idle

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._actors: Dict[str, MCPActor] = {}
            cls._instance._lock = asyncio.Lock()
            cls._instance._last_access: Dict[str, float] = {}
            cls._instance._health_task: Optional[asyncio.Task] = None
        return cls._instance

    async def get_or_create(self, session_id: str) -> MCPActor:
        """Get existing actor or create new one"""
        async with self._lock:
            # Enforce max actors limit
            if session_id not in self._actors and len(self._actors) >= self.MAX_ACTORS:
                # Evict oldest idle actor
                await self._evict_oldest()

            if session_id not in self._actors:
                actor = MCPActor(session_id=session_id)
                await actor.start()
                self._actors[session_id] = actor

            self._last_access[session_id] = time.time()
            return self._actors[session_id]

    async def dispatch(self, session_id: str, message: Dict[str, Any], wait: bool = False) -> Any:
        """Send message to session's actor"""
        actor = await self.get_or_create(session_id)
        return await actor.send(message, wait_result=wait)

    async def cleanup(self, session_id: str):
        """Stop and remove actor"""
        async with self._lock:
            if session_id in self._actors:
                await self._actors[session_id].stop()
                del self._actors[session_id]
                self._last_access.pop(session_id, None)

    async def cleanup_all(self):
        """Stop all actors"""
        async with self._lock:
            for actor in self._actors.values():
                await actor.stop(timeout=2.0)
            self._actors.clear()
            self._last_access.clear()

    async def _evict_oldest(self):
        """Evict oldest idle actor to make room"""
        if not self._last_access:
            return

        oldest_sid = min(self._last_access, key=self._last_access.get)
        await self._actors[oldest_sid].stop(timeout=1.0)
        del self._actors[oldest_sid]
        del self._last_access[oldest_sid]

    async def _health_check_loop(self, interval: int = 60):
        """Periodic health check and cleanup"""
        while True:
            await asyncio.sleep(interval)
            now = time.time()

            async with self._lock:
                # Find idle actors past TTL
                expired = [
                    sid for sid, last in self._last_access.items()
                    if now - last > self.ACTOR_TTL
                ]

                # Find unhealthy actors
                unhealthy = [
                    sid for sid, actor in self._actors.items()
                    if not actor.is_healthy()
                ]

                # Cleanup
                for sid in set(expired + unhealthy):
                    if sid in self._actors:
                        await self._actors[sid].stop(timeout=1.0)
                        del self._actors[sid]
                        self._last_access.pop(sid, None)

    async def start_health_monitoring(self):
        """Start background health monitoring"""
        if self._health_task is None:
            self._health_task = asyncio.create_task(self._health_check_loop())

    def get_stats(self) -> Dict[str, Any]:
        """Return dispatcher statistics"""
        healthy = sum(1 for a in self._actors.values() if a.is_healthy())
        return {
            "active_actors": len(self._actors),
            "healthy_actors": healthy,
            "unhealthy_actors": len(self._actors) - healthy,
            "max_actors": self.MAX_ACTORS,
            "actor_ttl_seconds": self.ACTOR_TTL,
            "actors": {
                sid: actor.get_stats()
                for sid, actor in self._actors.items()
            }
        }

# Global dispatcher
_dispatcher: Optional[MCPSessionDispatcher] = None

def get_dispatcher() -> MCPSessionDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = MCPSessionDispatcher()
    return _dispatcher
```

---

## PHASE 106c: Client Pool Manager (UNCHANGED from v1)
See v1.0 for full implementation.

---

## PHASE 106d: Provider Semaphores (UNCHANGED from v1)
See v1.0 for full implementation.

---

## PHASE 106e: Socket.IO MCP Namespace

### Task 5.1: MCP Socket Handler with Reconnection (ENHANCED)
**File:** `src/api/handlers/mcp_socket_handler.py` (NEW)

```python
# MARKER_106e_1: Enhanced MCP namespace handler
"""
MCP Socket.IO namespace handler with reconnection support.

Features:
- Automatic session recovery on reconnect
- Rate limiting per client
- Metrics collection
- Error broadcasting
"""

from socketio import AsyncServer
from typing import Dict, Any, Set
import asyncio
import time
from collections import defaultdict

MCP_NAMESPACE = "/mcp"

# Rate limiting: max 100 messages per minute per client
MESSAGE_LIMIT = 100
MESSAGE_WINDOW = 60

class MCPSocketManager:
    def __init__(self):
        self.client_sessions: Dict[str, str] = {}  # sid -> session_id
        self.session_clients: Dict[str, Set[str]] = defaultdict(set)  # session_id -> sids
        self.message_counts: Dict[str, list] = defaultdict(list)  # sid -> timestamps

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
        # Clean old timestamps
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

        # Only cleanup actor if no more clients for this session
        if session_id and not _manager.get_session_sids(session_id):
            from src.mcp.mcp_actor import get_dispatcher
            # Give 30 seconds grace period for reconnect
            await asyncio.sleep(30)
            if not _manager.get_session_sids(session_id):
                await get_dispatcher().cleanup(session_id)

    @sio.on("mcp_join", namespace=MCP_NAMESPACE)
    async def handle_join(sid, data: Dict[str, Any]):
        """Join or rejoin MCP session"""
        session_id = data.get("session_id") or sid
        reconnect = data.get("reconnect", False)

        # Associate client with session
        _manager.associate(sid, session_id)

        # Get or create actor
        from src.mcp.mcp_actor import get_dispatcher
        dispatcher = get_dispatcher()
        actor = await dispatcher.get_or_create(session_id)

        # Join room
        await sio.enter_room(sid, f"mcp_{session_id}", namespace=MCP_NAMESPACE)

        # Send session state on reconnect
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
        """Execute MCP tool via WebSocket with rate limiting"""
        # Rate limit check
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
            # Emit progress start
            await sio.emit("mcp_progress", {
                "request_id": request_id,
                "tool": tool_name,
                "status": "started"
            }, to=sid, namespace=MCP_NAMESPACE)

            # Execute via actor
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
                "error": "Request timed out",
                "session_id": session_id
            }, to=sid, namespace=MCP_NAMESPACE)

        except Exception as e:
            await sio.emit("mcp_error", {
                "request_id": request_id,
                "tool": tool_name,
                "error": str(e),
                "session_id": session_id
            }, to=sid, namespace=MCP_NAMESPACE)

    @sio.on("mcp_broadcast", namespace=MCP_NAMESPACE)
    async def handle_broadcast(sid, data: Dict[str, Any]):
        """Broadcast message to all clients in session"""
        session_id = _manager.client_sessions.get(sid)
        if session_id:
            await sio.emit(
                "mcp_message",
                {"from": sid, "data": data.get("message")},
                room=f"mcp_{session_id}",
                namespace=MCP_NAMESPACE
            )

    @sio.on("mcp_ping", namespace=MCP_NAMESPACE)
    async def handle_ping(sid, data: Dict[str, Any]):
        """Health check with stats"""
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
```

### Task 5.2: API Endpoints for Stats (NEW)
**File:** `main.py`
**Action:** Add MCP stats endpoints

```python
# MARKER_106e_2: Add MCP stats API endpoint

@app.get("/api/mcp/stats")
async def get_mcp_stats():
    """Get MCP subsystem statistics"""
    from src.mcp.mcp_actor import get_dispatcher
    from src.mcp.client_pool import get_pool_manager

    return {
        "dispatcher": get_dispatcher().get_stats(),
        "pool": get_pool_manager().get_stats(),
        "status": "healthy"
    }

@app.get("/api/mcp/health")
async def get_mcp_health():
    """MCP health check"""
    from src.mcp.mcp_actor import get_dispatcher

    dispatcher = get_dispatcher()
    stats = dispatcher.get_stats()

    healthy = stats["healthy_actors"] == stats["active_actors"]

    return {
        "status": "healthy" if healthy else "degraded",
        "active_actors": stats["active_actors"],
        "healthy_actors": stats["healthy_actors"]
    }
```

---

## Verification Checklist v2.0

### Phase 106a
- [ ] CLI args parsing works
- [ ] `--http --port 5002` starts HTTP server
- [ ] `--ws` enables WebSocket endpoint
- [ ] Session ID propagates in headers
- [ ] SIGINT/SIGTERM handled gracefully
- [ ] All resources cleaned up on shutdown

### Phase 106b
- [ ] MCPActor starts/stops correctly
- [ ] Mailbox queuing with timeout works
- [ ] Retry logic with backoff works
- [ ] Error handlers called on failure
- [ ] Health monitoring removes unhealthy actors
- [ ] Max actors limit enforced (100)
- [ ] Idle actors evicted after TTL (30 min)

### Phase 106c
- [ ] Pool creates clients per session
- [ ] TTL cleanup works
- [ ] Stats endpoint returns data
- [ ] Shutdown closes all connections

### Phase 106d
- [ ] Semaphores limit concurrent calls
- [ ] Different limits per model family
- [ ] No deadlocks under load

### Phase 106e
- [ ] /mcp namespace accepts connections
- [ ] Tool calls execute via WebSocket
- [ ] Rate limiting works (100/min)
- [ ] Reconnection preserves session
- [ ] Room-based broadcast works
- [ ] Stats API endpoints respond
- [ ] Health endpoint returns status

---

**Version:** 2.0
**Changes:** Added error recovery, health monitoring, rate limiting, graceful shutdown
**Ready for Implementation:** YES
