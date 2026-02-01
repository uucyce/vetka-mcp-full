# Phase 106: Multi-Agent MCP Super-Prompt v1.0

## Mission Statement
Transform VETKA MCP from single-client stdio bridge to multi-tenant hub supporting 100+ concurrent agents with zero blocking.

---

## PHASE 106a: HTTP Multi-Transport Activation

### Task 1.1: Enable HTTP Transport Flag
**File:** `src/mcp/vetka_mcp_bridge.py`
**Action:** Add CLI argument parsing

```python
# MARKER_106a_1: Add after imports (line ~44)
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='VETKA MCP Bridge')
    parser.add_argument('--http', action='store_true', help='Use HTTP transport')
    parser.add_argument('--port', type=int, default=5002, help='HTTP port')
    parser.add_argument('--session-id', type=str, help='Session ID for isolation')
    return parser.parse_args()
```

### Task 1.2: Session ID Header Support
**File:** `src/mcp/vetka_mcp_bridge.py`
**Action:** Modify http_client initialization

```python
# MARKER_106a_2: Replace init_client() (line 69-76)
async def init_client(session_id: str = None):
    global http_client
    headers = {}
    if session_id:
        headers["X-Session-ID"] = session_id
        headers["X-Agent-ID"] = f"mcp_{session_id[:8]}"

    http_client = httpx.AsyncClient(
        base_url=VETKA_BASE_URL,
        timeout=VETKA_TIMEOUT,
        follow_redirects=True,
        headers=headers,
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=10)
    )
```

### Task 1.3: Main Function Update
**File:** `src/mcp/vetka_mcp_bridge.py`
**Action:** Support both stdio and HTTP modes

```python
# MARKER_106a_3: Replace main() (line 1881-1900)
async def main():
    args = parse_args()

    await init_client(session_id=args.session_id)

    try:
        if args.http:
            # HTTP mode - use vetka_mcp_server
            from src.mcp.vetka_mcp_server import run_http
            await run_http(port=args.port)
        else:
            # stdio mode - original behavior
            async with stdio_server() as (read_stream, write_stream):
                init_options = server.create_initialization_options()
                await server.run(read_stream, write_stream, init_options)
    finally:
        await cleanup_client()
```

---

## PHASE 106b: MCPActor Class Implementation

### Task 2.1: Create MCPActor Base
**File:** `src/mcp/mcp_actor.py` (NEW)

```python
# MARKER_106b_1: Full MCPActor implementation
"""
MCPActor - Actor model for multi-tenant MCP sessions.

Each MCPActor has:
- Unique session_id
- Private asyncio.Queue mailbox
- Isolated state dictionary
- Autonomous loop for processing messages

Usage:
    actor = MCPActor(session_id="user_123")
    await actor.start()
    await actor.send({"type": "tool_call", "name": "vetka_search", ...})
    await actor.stop()
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum

class ActorState(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING = "waiting"
    STOPPED = "stopped"

@dataclass
class MCPActor:
    session_id: str
    mailbox: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=100))
    state: ActorState = ActorState.IDLE
    context: Dict[str, Any] = field(default_factory=dict)
    _task: Optional[asyncio.Task] = None
    _semaphore: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(5))

    async def start(self):
        """Start the actor's autonomous loop"""
        self._task = asyncio.create_task(self._loop())
        return self

    async def stop(self):
        """Stop the actor gracefully"""
        await self.mailbox.put({"type": "stop"})
        if self._task:
            await self._task
        self.state = ActorState.STOPPED

    async def send(self, message: Dict[str, Any]) -> str:
        """Send message to actor's mailbox, returns message_id"""
        message_id = str(uuid.uuid4())[:8]
        message["_id"] = message_id
        await self.mailbox.put(message)
        return message_id

    async def _loop(self):
        """Autonomous processing loop"""
        while True:
            try:
                self.state = ActorState.WAITING
                msg = await self.mailbox.get()

                if msg.get("type") == "stop":
                    break

                self.state = ActorState.PROCESSING
                async with self._semaphore:
                    await self._process(msg)

                self.mailbox.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log but don't crash the actor
                print(f"[MCPActor:{self.session_id}] Error: {e}")

    async def _process(self, msg: Dict[str, Any]):
        """Process a single message - override in subclass"""
        msg_type = msg.get("type")

        if msg_type == "tool_call":
            # Import here to avoid circular deps
            from src.mcp.vetka_mcp_bridge import call_tool
            result = await call_tool(msg["name"], msg.get("arguments", {}))
            self.context["last_result"] = result

        elif msg_type == "state_update":
            self.context.update(msg.get("data", {}))
```

### Task 2.2: Session Dispatcher
**File:** `src/mcp/mcp_actor.py` (append)

```python
# MARKER_106b_2: Session dispatcher singleton

class MCPSessionDispatcher:
    """Manages pool of MCPActors, one per session"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._actors: Dict[str, MCPActor] = {}
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    async def get_or_create(self, session_id: str) -> MCPActor:
        """Get existing actor or create new one"""
        async with self._lock:
            if session_id not in self._actors:
                actor = MCPActor(session_id=session_id)
                await actor.start()
                self._actors[session_id] = actor
            return self._actors[session_id]

    async def dispatch(self, session_id: str, message: Dict[str, Any]) -> str:
        """Send message to session's actor"""
        actor = await self.get_or_create(session_id)
        return await actor.send(message)

    async def cleanup(self, session_id: str):
        """Stop and remove actor"""
        async with self._lock:
            if session_id in self._actors:
                await self._actors[session_id].stop()
                del self._actors[session_id]

    async def cleanup_all(self):
        """Stop all actors - call on shutdown"""
        async with self._lock:
            for actor in self._actors.values():
                await actor.stop()
            self._actors.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Return actor pool statistics"""
        return {
            "active_actors": len(self._actors),
            "session_ids": list(self._actors.keys()),
            "states": {sid: a.state.value for sid, a in self._actors.items()}
        }

# Global dispatcher instance
def get_dispatcher() -> MCPSessionDispatcher:
    return MCPSessionDispatcher()
```

---

## PHASE 106c: Client Pool Manager

### Task 3.1: Per-Tenant Client Pool
**File:** `src/mcp/client_pool.py` (NEW)

```python
# MARKER_106c_1: Client pool implementation
"""
ClientPoolManager - Per-session httpx client pooling.

Provides isolated connection pools for multi-tenant MCP.
Automatic cleanup of idle pools after TTL expiration.
"""

import asyncio
import httpx
from typing import Dict, Optional
from dataclasses import dataclass, field
import time

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
        max_connections=10,
        max_keepalive_connections=5,
        keepalive_expiry=30.0
    )

    POOL_TTL = 300  # 5 minutes idle before cleanup

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
        """Mark client as no longer actively used"""
        # Clients stay in pool until TTL expires
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

        async with self._lock:
            for pool in self._pools.values():
                await pool.client.aclose()
            self._pools.clear()

    def get_stats(self) -> Dict:
        return {
            "active_pools": len(self._pools),
            "total_requests": sum(p.request_count for p in self._pools.values()),
            "pools": {
                sid: {
                    "requests": p.request_count,
                    "age_seconds": int(time.time() - p.created_at),
                    "idle_seconds": int(time.time() - p.last_used)
                }
                for sid, p in self._pools.items()
            }
        }

# Global pool manager
_pool_manager: Optional[ClientPoolManager] = None

def get_pool_manager() -> ClientPoolManager:
    global _pool_manager
    if _pool_manager is None:
        _pool_manager = ClientPoolManager()
    return _pool_manager
```

---

## PHASE 106d: Provider Semaphores

### Task 4.1: Per-Model Semaphores
**File:** `src/elisya/provider_registry.py`
**Action:** Add semaphores after imports

```python
# MARKER_106d_1: Add after imports (around line 20)
import asyncio

# Per-model concurrency limits
MODEL_SEMAPHORES = {
    "grok": asyncio.Semaphore(10),      # Grok: 10 concurrent
    "haiku": asyncio.Semaphore(50),     # Haiku: fast, 50 concurrent
    "sonnet": asyncio.Semaphore(20),    # Sonnet: 20 concurrent
    "opus": asyncio.Semaphore(5),       # Opus: expensive, 5 concurrent
    "gpt-4": asyncio.Semaphore(10),     # GPT-4: 10 concurrent
    "gemini": asyncio.Semaphore(20),    # Gemini: 20 concurrent
    "ollama": asyncio.Semaphore(3),     # Ollama: local, 3 concurrent
    "default": asyncio.Semaphore(20),   # Fallback
}

def get_model_semaphore(model: str) -> asyncio.Semaphore:
    """Get semaphore for model family"""
    model_lower = model.lower()
    for key in MODEL_SEMAPHORES:
        if key in model_lower:
            return MODEL_SEMAPHORES[key]
    return MODEL_SEMAPHORES["default"]
```

### Task 4.2: Wrap LLM Calls with Semaphore
**File:** `src/elisya/provider_registry.py`
**Action:** Modify call_model_v2 function

```python
# MARKER_106d_2: Wrap the main call function (around line 1066)
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
```

---

## PHASE 106e: Socket.IO MCP Namespace

### Task 5.1: MCP Socket Handler
**File:** `src/api/handlers/mcp_socket_handler.py` (NEW)

```python
# MARKER_106e_1: MCP namespace handler
"""
MCP Socket.IO namespace handler for real-time agent communication.

Events:
- mcp_join: Join MCP session room
- mcp_leave: Leave session room
- mcp_tool_call: Execute tool via WebSocket
- mcp_progress: Receive progress updates

Server-side events:
- mcp_result: Tool execution result
- mcp_error: Error notification
- mcp_status: Session status update
"""

from socketio import AsyncServer
from typing import Dict, Any
import asyncio

MCP_NAMESPACE = "/mcp"

async def register_mcp_socket_handlers(sio: AsyncServer, app):
    """Register MCP namespace event handlers"""

    @sio.on("connect", namespace=MCP_NAMESPACE)
    async def handle_connect(sid, environ):
        print(f"[MCP:WS] Client connected: {sid}")
        await sio.emit("mcp_status", {"status": "connected"}, to=sid, namespace=MCP_NAMESPACE)

    @sio.on("disconnect", namespace=MCP_NAMESPACE)
    async def handle_disconnect(sid):
        print(f"[MCP:WS] Client disconnected: {sid}")
        # Cleanup actor if exists
        from src.mcp.mcp_actor import get_dispatcher
        dispatcher = get_dispatcher()
        await dispatcher.cleanup(sid)

    @sio.on("mcp_join", namespace=MCP_NAMESPACE)
    async def handle_join(sid, data: Dict[str, Any]):
        """Join MCP session room"""
        session_id = data.get("session_id", sid)

        # Create actor for this session
        from src.mcp.mcp_actor import get_dispatcher
        dispatcher = get_dispatcher()
        await dispatcher.get_or_create(session_id)

        # Join room for targeted broadcasts
        await sio.enter_room(sid, f"mcp_{session_id}", namespace=MCP_NAMESPACE)

        await sio.emit("mcp_status", {
            "status": "joined",
            "session_id": session_id
        }, to=sid, namespace=MCP_NAMESPACE)

    @sio.on("mcp_tool_call", namespace=MCP_NAMESPACE)
    async def handle_tool_call(sid, data: Dict[str, Any]):
        """Execute MCP tool via WebSocket"""
        session_id = data.get("session_id", sid)
        tool_name = data.get("tool")
        arguments = data.get("arguments", {})

        try:
            from src.mcp.vetka_mcp_bridge import call_tool
            result = await call_tool(tool_name, arguments)

            await sio.emit("mcp_result", {
                "tool": tool_name,
                "result": result,
                "session_id": session_id
            }, to=sid, namespace=MCP_NAMESPACE)

        except Exception as e:
            await sio.emit("mcp_error", {
                "tool": tool_name,
                "error": str(e),
                "session_id": session_id
            }, to=sid, namespace=MCP_NAMESPACE)

    @sio.on("mcp_ping", namespace=MCP_NAMESPACE)
    async def handle_ping(sid, data: Dict[str, Any]):
        """Health check"""
        from src.mcp.mcp_actor import get_dispatcher
        stats = get_dispatcher().get_stats()
        await sio.emit("mcp_pong", {"stats": stats}, to=sid, namespace=MCP_NAMESPACE)
```

### Task 5.2: Register Handler in main.py
**File:** `main.py`
**Action:** Add after other handler registrations

```python
# MARKER_106e_2: Add to register_all_handlers (around line 378)
from src.api.handlers.mcp_socket_handler import register_mcp_socket_handlers

# In register_all_handlers function:
await register_mcp_socket_handlers(sio, app)
```

---

## Verification Checklist

### Phase 106a
- [ ] CLI args parsing works
- [ ] `--http --port 5002` starts HTTP server
- [ ] Session ID propagates in headers
- [ ] Multiple Claude instances can connect

### Phase 106b
- [ ] MCPActor starts/stops correctly
- [ ] Mailbox queuing works
- [ ] Dispatcher creates actors on demand
- [ ] Cleanup removes actors

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
- [ ] Results emit back to client
- [ ] Room isolation works

---

## Testing Commands

```bash
# Test HTTP transport
python src/mcp/vetka_mcp_bridge.py --http --port 5002

# Spawn multiple sessions
for i in {1..5}; do
  curl -X POST http://localhost:5002/mcp \
    -H "Content-Type: application/json" \
    -H "X-Session-ID: session_$i" \
    -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"vetka_health","arguments":{}}}' &
done

# Check actor pool stats
curl http://localhost:5001/api/mcp/stats

# WebSocket test (via Python)
import socketio
sio = socketio.AsyncClient()
await sio.connect('http://localhost:5001', namespaces=['/mcp'])
await sio.emit('mcp_join', {'session_id': 'test_123'}, namespace='/mcp')
await sio.emit('mcp_tool_call', {'tool': 'vetka_health', 'arguments': {}}, namespace='/mcp')
```

---

**Version:** 1.0
**Next:** Review with Grok for iteration 2
