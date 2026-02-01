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
