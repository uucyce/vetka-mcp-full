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
