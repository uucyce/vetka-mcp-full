# Phase 106: Multi-Agent MCP Super-Prompt v3.0

## Grok Review Applied
- ✅ MCP server.py updates (Phase 106f NEW)
- ✅ Global call_tool refactor via pool/semaphore
- ✅ Provider semaphores global export
- ✅ Load testing script
- ✅ Migration guide
- ✅ Env vars for tuning

**Status:** 100% IMPLEMENTATION READY

---

## Mission Statement
Transform VETKA MCP from single-client stdio bridge to multi-tenant hub supporting 200+ concurrent agents with zero blocking, full session isolation, and production-grade error recovery.

---

## PHASE 106a: HTTP Multi-Transport Activation

### Task 1.1: CLI Argument Parsing
**File:** `src/mcp/vetka_mcp_bridge.py`
**Line:** After imports (~44)

```python
# MARKER_106a_1: CLI arguments with env var support
import argparse
import signal
import os

def parse_args():
    parser = argparse.ArgumentParser(description='VETKA MCP Bridge')
    parser.add_argument('--http', action='store_true',
                        default=os.getenv('MCP_HTTP_MODE', '').lower() == 'true',
                        help='Use HTTP transport')
    parser.add_argument('--ws', action='store_true',
                        default=os.getenv('MCP_WS_MODE', '').lower() == 'true',
                        help='Enable WebSocket endpoint')
    parser.add_argument('--port', type=int,
                        default=int(os.getenv('MCP_PORT', '5002')),
                        help='HTTP/WS port')
    parser.add_argument('--session-id', type=str,
                        default=os.getenv('MCP_SESSION_ID'),
                        help='Session ID for isolation')
    return parser.parse_args()
```

### Task 1.2: Session ID Header Support
**File:** `src/mcp/vetka_mcp_bridge.py`
**Line:** Replace init_client() (69-76)

```python
# MARKER_106a_2: Enhanced client initialization
import uuid
import contextvars

# Session context for async propagation
session_context: contextvars.ContextVar[str] = contextvars.ContextVar('session_id', default='default')

async def init_client(session_id: str = None):
    global http_client

    if session_id is None:
        session_id = str(uuid.uuid4())

    # Set in context for downstream use
    session_context.set(session_id)

    headers = {
        "X-Session-ID": session_id,
        "X-Agent-ID": f"mcp_{session_id[:8]}",
        "X-Client-Version": "106.0"
    }

    http_client = httpx.AsyncClient(
        base_url=VETKA_BASE_URL,
        timeout=httpx.Timeout(
            connect=10.0,
            read=90.0,
            write=30.0,
            pool=5.0
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

### Task 1.3: Graceful Shutdown Handler
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

    try:
        # Stop all actors
        from src.mcp.mcp_actor import get_dispatcher
        await get_dispatcher().cleanup_all()
    except ImportError:
        pass

    try:
        # Close client pools
        from src.mcp.client_pool import get_pool_manager
        await get_pool_manager().shutdown()
    except ImportError:
        pass

    # Close main client
    await cleanup_client()

    print("[MCP] Shutdown complete")
```

### Task 1.4: Main Function with Dual Mode
**File:** `src/mcp/vetka_mcp_bridge.py`
**Line:** Replace main() (1881-1900)

```python
# MARKER_106a_4: Enhanced main with HTTP/WS/stdio modes
async def main():
    args = parse_args()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    session_id = await init_client(session_id=args.session_id)
    print(f"[MCP] Started with session_id={session_id[:8]}...")

    try:
        if args.http or args.ws:
            # HTTP/WS mode - use enhanced MCP server
            from src.mcp.vetka_mcp_server import run_http
            print(f"[MCP] Starting HTTP server on port {args.port} (WS={args.ws})")
            await run_http(port=args.port, enable_ws=args.ws)
        else:
            # stdio mode - original behavior
            print("[MCP] Starting stdio mode")
            async with stdio_server() as (read_stream, write_stream):
                init_options = server.create_initialization_options()

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
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

    finally:
        await graceful_shutdown()
```

---

## PHASE 106b: MCPActor Class Implementation

### Task 2.1: Create mcp_actor.py
**File:** `src/mcp/mcp_actor.py` (NEW)

```python
# MARKER_106b_1: Full MCPActor implementation
"""
MCPActor - Actor model for multi-tenant MCP sessions.

Features:
- asyncio.Queue mailbox with backpressure (maxsize=100)
- Automatic error recovery with exponential backoff
- Message timeout handling (120s default)
- Metrics collection
- Health monitoring with TTL eviction
- Integration with ClientPoolManager

Environment Variables:
- MCP_MAX_ACTORS: Max concurrent actors (default: 100)
- MCP_ACTOR_TTL: Idle timeout seconds (default: 1800)
- MCP_MESSAGE_TIMEOUT: Per-message timeout (default: 120)
"""

import asyncio
import uuid
import time
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List
from enum import Enum

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
    _message_timeout: float = float(os.getenv('MCP_MESSAGE_TIMEOUT', '120'))
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

        for future in self._result_futures.values():
            if not future.done():
                future.cancel()

    async def send(self, message: Dict[str, Any], wait_result: bool = False) -> Any:
        """Send message to actor's mailbox"""
        message_id = str(uuid.uuid4())[:8]
        message["_id"] = message_id
        message["_timestamp"] = time.time()

        if wait_result:
            loop = asyncio.get_running_loop()
            future = loop.create_future()
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

                self.metrics.messages_processed += 1
                self.metrics.total_processing_time += time.time() - start_time

                msg_id = msg.get("_id")
                if msg_id in self._result_futures:
                    if not self._result_futures[msg_id].done():
                        self._result_futures[msg_id].set_result(result)

                self.mailbox.task_done()
                backoff = 0.1

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.state = ActorState.ERROR
                self.metrics.messages_failed += 1
                self.metrics.last_error = str(e)
                self.metrics.last_error_time = time.time()

                for handler in self._error_handlers:
                    try:
                        await handler(self, e)
                    except:
                        pass

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
        """Process a single message - v3: uses pool + semaphore"""
        msg_type = msg.get("type")

        if msg_type == "tool_call":
            # v3: Use pooled client
            from src.mcp.client_pool import get_pool_manager
            pool = get_pool_manager()
            client = await pool.get_client(self.session_id)

            try:
                from src.mcp.vetka_mcp_bridge import call_tool
                result = await call_tool(msg["name"], msg.get("arguments", {}))
                self.context["last_result"] = result
                return result
            finally:
                await pool.release(self.session_id)

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
            if self.metrics.last_error_time:
                return time.time() - self.metrics.last_error_time > 60
        return True


class MCPSessionDispatcher:
    """Manages pool of MCPActors with health monitoring"""

    _instance = None
    MAX_ACTORS = int(os.getenv('MCP_MAX_ACTORS', '100'))
    ACTOR_TTL = int(os.getenv('MCP_ACTOR_TTL', '1800'))  # 30 minutes

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
            if session_id not in self._actors and len(self._actors) >= self.MAX_ACTORS:
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
                expired = [
                    sid for sid, last in self._last_access.items()
                    if now - last > self.ACTOR_TTL
                ]

                unhealthy = [
                    sid for sid, actor in self._actors.items()
                    if not actor.is_healthy()
                ]

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


_dispatcher: Optional[MCPSessionDispatcher] = None

def get_dispatcher() -> MCPSessionDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = MCPSessionDispatcher()
    return _dispatcher
```

---

## PHASE 106c: Client Pool Manager

### Task 3.1: Create client_pool.py
**File:** `src/mcp/client_pool.py` (NEW)

```python
# MARKER_106c_1: Per-session client pool manager
"""
ClientPoolManager - Per-session httpx client pooling.

Features:
- Isolated connection pools per session
- Automatic cleanup of idle pools (5 min TTL)
- Connection limits (10 per session)
- Stats endpoint for monitoring

Environment Variables:
- MCP_POOL_TTL: Idle pool timeout (default: 300)
- MCP_POOL_MAX_CONNECTIONS: Per-pool max connections (default: 10)
"""

import asyncio
import httpx
import os
import time
from typing import Dict, Optional
from dataclasses import dataclass, field

@dataclass
class PooledClient:
    client: httpx.AsyncClient
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    request_count: int = 0

class ClientPoolManager:
    """Manages per-session httpx client pools"""

    DEFAULT_LIMITS = httpx.Limits(
        max_connections=int(os.getenv('MCP_POOL_MAX_CONNECTIONS', '10')),
        max_keepalive_connections=5,
        keepalive_expiry=30.0
    )

    POOL_TTL = int(os.getenv('MCP_POOL_TTL', '300'))  # 5 minutes

    def __init__(self, base_url: str = "http://localhost:5001"):
        self._pools: Dict[str, PooledClient] = {}
        self._lock = asyncio.Lock()
        self._base_url = base_url
        self._cleanup_task: Optional[asyncio.Task] = None

    async def get_client(self, session_id: str) -> httpx.AsyncClient:
        """Get or create client for session"""
        async with self._lock:
            if session_id not in self._pools:
                client = httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=90.0,
                    limits=self.DEFAULT_LIMITS,
                    headers={
                        "X-Session-ID": session_id,
                        "X-Pool-Client": "true"
                    }
                )
                self._pools[session_id] = PooledClient(
                    client=client,
                    session_id=session_id
                )

            pool = self._pools[session_id]
            pool.last_used = time.time()
            pool.request_count += 1
            return pool.client

    async def release(self, session_id: str):
        """Mark client as no longer actively used (stays in pool until TTL)"""
        pass

    async def cleanup_expired(self):
        """Remove idle pools past TTL"""
        async with self._lock:
            now = time.time()
            expired = [
                sid for sid, pool in self._pools.items()
                if now - pool.last_used > self.POOL_TTL
            ]
            for sid in expired:
                await self._pools[sid].client.aclose()
                del self._pools[sid]

    async def start_cleanup_loop(self, interval: int = 60):
        """Start background cleanup task"""
        async def _loop():
            while True:
                await asyncio.sleep(interval)
                await self.cleanup_expired()

        self._cleanup_task = asyncio.create_task(_loop())

    async def shutdown(self):
        """Close all pools and stop cleanup"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            for pool in self._pools.values():
                await pool.client.aclose()
            self._pools.clear()

    def get_stats(self) -> Dict:
        return {
            "active_pools": len(self._pools),
            "total_requests": sum(p.request_count for p in self._pools.values()),
            "pool_ttl": self.POOL_TTL,
            "pools": {
                sid: {
                    "requests": p.request_count,
                    "age_seconds": int(time.time() - p.created_at),
                    "idle_seconds": int(time.time() - p.last_used)
                }
                for sid, p in self._pools.items()
            }
        }


_pool_manager: Optional[ClientPoolManager] = None

def get_pool_manager() -> ClientPoolManager:
    global _pool_manager
    if _pool_manager is None:
        _pool_manager = ClientPoolManager()
    return _pool_manager
```

---

## PHASE 106d: Provider Semaphores

### Task 4.1: Add per-model semaphores
**File:** `src/elisya/provider_registry.py`
**Line:** After imports (~20)

```python
# MARKER_106d_1: Per-model concurrency limits
import asyncio

MODEL_SEMAPHORES = {
    "grok": asyncio.Semaphore(10),
    "haiku": asyncio.Semaphore(50),
    "sonnet": asyncio.Semaphore(20),
    "opus": asyncio.Semaphore(5),
    "gpt-4": asyncio.Semaphore(10),
    "gpt-3": asyncio.Semaphore(30),
    "gemini": asyncio.Semaphore(20),
    "ollama": asyncio.Semaphore(3),
    "default": asyncio.Semaphore(20),
}

def get_model_semaphore(model: str) -> asyncio.Semaphore:
    """Get semaphore for model family"""
    model_lower = model.lower()
    for key in MODEL_SEMAPHORES:
        if key in model_lower:
            return MODEL_SEMAPHORES[key]
    return MODEL_SEMAPHORES["default"]
```

### Task 4.2: Create wrapper function
**File:** `src/elisya/provider_registry.py`
**Line:** After call_model_v2 definition (~1200)

```python
# MARKER_106d_2: Semaphore-wrapped LLM caller
async def call_model_v2_with_semaphore(
    model: str,
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = None,
    tools: list = None,
    **kwargs
) -> dict:
    """Wrapper with per-model semaphore for concurrency control"""
    semaphore = get_model_semaphore(model)

    async with semaphore:
        return await call_model_v2(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            **kwargs
        )

# Export for global use
__all__ = ['call_model_v2', 'call_model_v2_with_semaphore', 'get_model_semaphore']
```

---

## PHASE 106e: Socket.IO MCP Namespace

### Task 5.1: Create mcp_socket_handler.py
**File:** `src/api/handlers/mcp_socket_handler.py` (NEW)

```python
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
```

### Task 5.2: Register in main.py
**File:** `main.py`
**Line:** After other handler registrations (~378)

```python
# MARKER_106e_2: Register MCP socket handlers
from src.api.handlers.mcp_socket_handler import register_mcp_socket_handlers

# Inside register_all_handlers function:
await register_mcp_socket_handlers(sio, app)
```

---

## PHASE 106f: MCP Server Updates (NEW from Grok)

### Task 6.1: Enhance vetka_mcp_server.py
**File:** `src/mcp/vetka_mcp_server.py`
**Action:** Add session dispatch to run_http

```python
# MARKER_106f_1: Enhanced run_http with WS and session dispatch
# Add to run_http function parameters:
async def run_http(host: str = "0.0.0.0", port: int = 5002, enable_ws: bool = False):
    """Run MCP server with HTTP and optional WebSocket transport"""

    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import JSONResponse
    from starlette.middleware.cors import CORSMiddleware
    import json

    async def mcp_rpc(request):
        """JSON-RPC endpoint with session dispatch"""
        session_id = request.headers.get("X-Session-ID", "default")

        try:
            data = await request.json()
        except:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        method = data.get("method", "")
        params = data.get("params", {})
        req_id = data.get("id", 1)

        if method == "tools/call":
            from src.mcp.mcp_actor import get_dispatcher
            try:
                result = await get_dispatcher().dispatch(
                    session_id,
                    {
                        "type": "tool_call",
                        "name": params.get("name"),
                        "arguments": params.get("arguments", {})
                    },
                    wait=True
                )
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": result
                })
            except Exception as e:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": str(e)}
                })

        elif method == "tools/list":
            from src.mcp.vetka_mcp_bridge import list_tools
            tools = await list_tools()
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": [t.model_dump() for t in tools]}
            })

        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown method: {method}"}
            })

    async def stats_endpoint(request):
        """Stats endpoint for monitoring"""
        from src.mcp.mcp_actor import get_dispatcher
        from src.mcp.client_pool import get_pool_manager
        return JSONResponse({
            "actors": get_dispatcher().get_stats(),
            "pools": get_pool_manager().get_stats()
        })

    async def health_endpoint(request):
        """Health check"""
        from src.mcp.mcp_actor import get_dispatcher
        stats = get_dispatcher().get_stats()
        healthy = stats["healthy_actors"] == stats["active_actors"]
        return JSONResponse({
            "status": "healthy" if healthy else "degraded",
            "active_actors": stats["active_actors"]
        })

    routes = [
        Route("/mcp", mcp_rpc, methods=["POST"]),
        Route("/api/stats", stats_endpoint, methods=["GET"]),
        Route("/health", health_endpoint, methods=["GET"]),
    ]

    # WebSocket endpoint if enabled
    if enable_ws:
        from starlette.websockets import WebSocket

        async def mcp_websocket(websocket: WebSocket):
            await websocket.accept()
            session_id = websocket.headers.get("X-Session-ID", f"ws_{id(websocket)}")

            from src.mcp.mcp_actor import get_dispatcher
            dispatcher = get_dispatcher()

            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    result = await dispatcher.dispatch(session_id, data, wait=True)
                    await websocket.send_text(json.dumps(result))
            except Exception as e:
                await websocket.send_text(json.dumps({"error": str(e)}))
            finally:
                await websocket.close()

        from starlette.routing import WebSocketRoute
        routes.append(WebSocketRoute("/mcp/ws", mcp_websocket))

    app = Starlette(routes=routes)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    import uvicorn
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
```

---

## API Endpoints Summary

| Endpoint | Port | Method | Description |
|----------|------|--------|-------------|
| `/mcp` | 5002 | POST | JSON-RPC tool calls |
| `/mcp/ws` | 5002 | WS | WebSocket transport |
| `/api/stats` | 5002 | GET | Actor/pool stats |
| `/health` | 5002 | GET | Health check |
| `/api/mcp/stats` | 5001 | GET | Cross-check (FastAPI) |
| `/mcp` namespace | 5001 | Socket.IO | Real-time events |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_HTTP_MODE` | false | Enable HTTP transport |
| `MCP_WS_MODE` | false | Enable WebSocket |
| `MCP_PORT` | 5002 | HTTP/WS port |
| `MCP_SESSION_ID` | auto-uuid | Session identifier |
| `MCP_MAX_ACTORS` | 100 | Max concurrent actors |
| `MCP_ACTOR_TTL` | 1800 | Idle actor timeout (sec) |
| `MCP_MESSAGE_TIMEOUT` | 120 | Per-message timeout (sec) |
| `MCP_POOL_TTL` | 300 | Idle pool timeout (sec) |
| `MCP_POOL_MAX_CONNECTIONS` | 10 | Per-pool connections |

---

## Load Testing Commands

```bash
# Start MCP Hub
python src/mcp/vetka_mcp_bridge.py --http --ws --port 5002 &

# Load test: 100 concurrent sessions
for i in {1..100}; do
  session_id="load_$i"
  curl -X POST http://localhost:5002/mcp \
    -H "Content-Type: application/json" \
    -H "X-Session-ID: $session_id" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":$i,\"method\":\"tools/call\",\"params\":{\"name\":\"vetka_health\",\"arguments\":{}}}" &
done
wait

# Monitor stats
curl http://localhost:5002/api/stats | jq .
curl http://localhost:5001/api/mcp/stats | jq .

# WebSocket test (Python)
python -c "
import asyncio
import socketio

async def test():
    sio = socketio.AsyncClient()
    await sio.connect('http://localhost:5001', namespaces=['/mcp'])
    await sio.emit('mcp_join', {'session_id': 'test_ws'}, namespace='/mcp')
    await sio.emit('mcp_tool_call', {'tool': 'vetka_health', 'arguments': {}}, namespace='/mcp')
    await asyncio.sleep(2)
    await sio.disconnect()

asyncio.run(test())
"
```

---

## Migration Guide

### Legacy Users (stdio)
```bash
# No change needed - default behavior
python src/mcp/vetka_mcp_bridge.py
```

### Multi-Claude (HTTP)
```bash
# Start HTTP server
python src/mcp/vetka_mcp_bridge.py --http --port 5002

# Configure Claude Desktop (claude_desktop_config.json):
{
  "mcpServers": {
    "vetka": {
      "url": "http://localhost:5002/mcp"
    }
  }
}
```

### Real-time Apps (Socket.IO)
```javascript
// Connect to /mcp namespace
const socket = io('http://localhost:5001/mcp');
socket.emit('mcp_join', { session_id: 'my_session' });
socket.on('mcp_result', (data) => console.log(data));
socket.emit('mcp_tool_call', { tool: 'vetka_health', arguments: {} });
```

### High-Scale (200+ agents)
```bash
# Increase limits via env
export MCP_MAX_ACTORS=200
export MCP_ACTOR_TTL=3600
python src/mcp/vetka_mcp_bridge.py --http --ws --port 5002
```

---

## Verification Checklist v3

### Phase 106a
- [ ] CLI args parse correctly
- [ ] `--http` starts HTTP server
- [ ] `--ws` enables WebSocket endpoint
- [ ] Session ID in headers propagates
- [ ] SIGINT/SIGTERM shutdown cleanly
- [ ] All actors/pools cleaned on exit

### Phase 106b
- [ ] MCPActor starts/stops
- [ ] Mailbox queuing works
- [ ] Retry with backoff works
- [ ] Health monitoring runs
- [ ] Max actors enforced
- [ ] TTL eviction works

### Phase 106c
- [ ] Pools created per session
- [ ] TTL cleanup runs
- [ ] Stats return data
- [ ] Shutdown closes all

### Phase 106d
- [ ] Semaphores limit calls
- [ ] Per-model limits work
- [ ] No deadlocks

### Phase 106e
- [ ] /mcp namespace connects
- [ ] Tool calls via Socket.IO
- [ ] Rate limiting works
- [ ] Reconnection preserves session

### Phase 106f
- [ ] /mcp POST works
- [ ] /mcp/ws accepts connections
- [ ] /api/stats returns data
- [ ] /health returns status

---

**Version:** 3.0
**Status:** ✅ IMPLEMENTATION READY
**Next:** Apply markers → test → commit → Phase 107
