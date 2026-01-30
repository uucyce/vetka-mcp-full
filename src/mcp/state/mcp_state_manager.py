"""MCP State Manager - Agent workflow state with Qdrant persistence + LRU cache.

Provides persistent state management for MCP sessions and multi-agent workflows.
Uses a tiered storage approach: LRU cache for hot data, Qdrant for persistence.

Features:
- save_state(agent_id, data, ttl): Persist state with TTL
- get_state(agent_id): Retrieve state (cache-first)
- update_state(agent_id, updates): Merge updates into existing state
- delete_state(agent_id): Remove state from cache and Qdrant
- get_all_states(prefix): List states by workflow prefix
- delete_expired_states(): Cleanup TTL-expired entries

Architecture:
- LRU cache: OrderedDict with max 100 entries
- Qdrant collection: vetka_mcp_states (768-dim vectors for future embeddings)
- Point IDs: UUID5 hash of agent_id for collision-free storage

@status: active
@phase: 96
@depends: qdrant_client, src/memory/qdrant_client.py, dataclasses, collections.OrderedDict
@used_by: src/mcp/state/__init__.py, src/mcp/tools/session_tools.py, src/mcp/tools/workflow_tools.py
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
import time
import asyncio
import hashlib
from collections import OrderedDict

# Qdrant imports
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

@dataclass
class MCPStateEntry:
    """Single state entry for an agent."""
    agent_id: str
    workflow_id: str
    data: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    ttl_seconds: int = 3600  # 1 hour default
    access_count: int = 0

class MCPStateManager:
    """
    MCP State Manager with Qdrant + LRU Cache.

    Features:
    - save_state(agent_id, data, ttl): Persist state
    - get_state(agent_id): Retrieve state (cache first)
    - update_state(agent_id, updates): Merge updates
    - delete_state(agent_id): Remove state
    - get_all_states(prefix): List states by workflow
    - delete_expired_states(): Cleanup TTL expired
    """

    COLLECTION_NAME = "vetka_mcp_states"
    VECTOR_SIZE = 768
    CACHE_MAX_SIZE = 100

    def __init__(self, collection_name: str = None):
        self.collection_name = collection_name or self.COLLECTION_NAME
        self._cache: OrderedDict[str, MCPStateEntry] = OrderedDict()
        self._qdrant: Optional[QdrantClient] = None
        self._init_qdrant()
        print(f"   • MCPStateManager: initialized (collection={self.collection_name})")

    def _init_qdrant(self):
        """Initialize Qdrant client and collection."""
        if not QDRANT_AVAILABLE:
            print("   ⚠️ Qdrant not available - using cache only")
            return
        try:
            from src.memory.qdrant_client import get_qdrant_client
            vetka_client = get_qdrant_client()
            # Use the underlying QdrantClient for direct API access
            self._qdrant = vetka_client.client if vetka_client else None
            if self._qdrant:
                self._ensure_collection()
        except Exception as e:
            print(f"   ⚠️ Qdrant init failed: {e}")

    def _ensure_collection(self):
        """Create MCP states collection if it doesn't exist."""
        if not self._qdrant:
            return
        try:
            collections = self._qdrant.get_collections()
            existing = {c.name for c in collections.collections}
            if self.collection_name not in existing:
                self._qdrant.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
                print(f"   ✅ Created MCP states collection: {self.collection_name}")
        except Exception as e:
            print(f"   ⚠️ Collection creation failed: {e}")

    def _generate_point_id(self, agent_id: str) -> int:
        """Generate collision-free Qdrant point ID."""
        import uuid
        return uuid.uuid5(uuid.NAMESPACE_DNS, agent_id).int & 0x7FFFFFFFFFFFFFFF

    async def save_state(self, agent_id: str, data: Dict[str, Any],
                         ttl_seconds: int = 3600, workflow_id: str = None) -> bool:
        """Save agent state to cache and Qdrant."""
        entry = MCPStateEntry(
            agent_id=agent_id,
            workflow_id=workflow_id or agent_id.split("_")[0],
            data=data,
            ttl_seconds=ttl_seconds
        )

        # Update cache (LRU)
        if agent_id in self._cache:
            del self._cache[agent_id]
        self._cache[agent_id] = entry

        # Evict oldest if over limit
        while len(self._cache) > self.CACHE_MAX_SIZE:
            self._cache.popitem(last=False)

        # Persist to Qdrant
        if self._qdrant:
            try:
                point_id = self._generate_point_id(agent_id)
                vector = [0.0] * self.VECTOR_SIZE
                point = PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "agent_id": agent_id,
                        "workflow_id": entry.workflow_id,
                        "data": data,
                        "created_at": entry.created_at,
                        "updated_at": entry.updated_at,
                        "ttl_seconds": ttl_seconds,
                        "expires_at": entry.created_at + ttl_seconds
                    }
                )
                self._qdrant.upsert(
                    collection_name=self.collection_name,
                    points=[point]
                )
            except Exception as e:
                print(f"   ⚠️ Qdrant save failed: {e}")
                return False

        return True

    async def get_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get state from cache or Qdrant."""
        # Check cache first (O(1))
        if agent_id in self._cache:
            entry = self._cache[agent_id]
            if time.time() < entry.created_at + entry.ttl_seconds:
                entry.access_count += 1
                self._cache.move_to_end(agent_id)
                return entry.data
            else:
                del self._cache[agent_id]

        # Fallback to Qdrant - use scroll with filter (retrieve needs with_payload=True)
        if self._qdrant:
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                scroll_filter = Filter(
                    must=[FieldCondition(
                        key="agent_id",
                        match=MatchValue(value=agent_id)
                    )]
                )
                points, _ = self._qdrant.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=scroll_filter,
                    limit=1,
                    with_payload=True
                )
                if points:
                    payload = points[0].payload
                    if time.time() < payload.get("expires_at", 0):
                        entry = MCPStateEntry(
                            agent_id=agent_id,
                            workflow_id=payload.get("workflow_id", ""),
                            data=payload.get("data", {}),
                            created_at=payload.get("created_at", time.time()),
                            ttl_seconds=payload.get("ttl_seconds", 3600)
                        )
                        self._cache[agent_id] = entry
                        return entry.data
            except Exception as e:
                print(f"   ⚠️ Qdrant get failed: {e}")

        return None

    async def update_state(self, agent_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Merge updates into existing state."""
        current = await self.get_state(agent_id)
        if current is None:
            current = {}

        merged = {**current, **updates}

        ttl = 3600
        workflow_id = None
        if agent_id in self._cache:
            ttl = self._cache[agent_id].ttl_seconds
            workflow_id = self._cache[agent_id].workflow_id

        await self.save_state(agent_id, merged, ttl, workflow_id)
        return merged

    async def delete_state(self, agent_id: str) -> bool:
        """Delete state from cache and Qdrant."""
        if agent_id in self._cache:
            del self._cache[agent_id]

        if self._qdrant:
            try:
                point_id = self._generate_point_id(agent_id)
                self._qdrant.delete(
                    collection_name=self.collection_name,
                    points_selector=[point_id]
                )
            except Exception as e:
                print(f"   ⚠️ Qdrant delete failed: {e}")
                return False

        return True

    async def get_all_states(self, prefix: str = None, limit: int = 100) -> Dict[str, Dict[str, Any]]:
        """Get all states, optionally filtered by prefix."""
        result = {}

        for agent_id, entry in self._cache.items():
            if prefix is None or agent_id.startswith(prefix):
                if time.time() < entry.created_at + entry.ttl_seconds:
                    result[agent_id] = entry.data

        if self._qdrant and len(result) < limit:
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                scroll_filter = None
                if prefix:
                    scroll_filter = Filter(
                        must=[FieldCondition(
                            key="workflow_id",
                            match=MatchValue(value=prefix)
                        )]
                    )
                points, _ = self._qdrant.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=scroll_filter,
                    limit=limit
                )
                for point in points:
                    agent_id = point.payload.get("agent_id")
                    if agent_id and agent_id not in result:
                        if time.time() < point.payload.get("expires_at", 0):
                            result[agent_id] = point.payload.get("data", {})
            except Exception as e:
                print(f"   ⚠️ Qdrant scroll failed: {e}")

        return result

    async def delete_expired_states(self) -> int:
        """Delete all expired states. Returns count deleted."""
        deleted = 0
        now = time.time()

        expired_keys = [
            k for k, v in self._cache.items()
            if now >= v.created_at + v.ttl_seconds
        ]
        for k in expired_keys:
            del self._cache[k]
            deleted += 1

        if self._qdrant:
            try:
                from qdrant_client.models import Filter, FieldCondition, Range
                expired_filter = Filter(
                    must=[FieldCondition(
                        key="expires_at",
                        range=Range(lt=now)
                    )]
                )
                points, _ = self._qdrant.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=expired_filter,
                    limit=1000
                )
                if points:
                    ids = [p.id for p in points]
                    self._qdrant.delete(
                        collection_name=self.collection_name,
                        points_selector=ids
                    )
                    deleted += len(ids)
            except Exception as e:
                print(f"   ⚠️ Qdrant cleanup failed: {e}")

        print(f"   🧹 MCPStateManager: deleted {deleted} expired states")
        return deleted


# Singleton
_mcp_state_manager: Optional[MCPStateManager] = None

def get_mcp_state_manager() -> MCPStateManager:
    """Get singleton MCPStateManager instance."""
    global _mcp_state_manager
    if _mcp_state_manager is None:
        _mcp_state_manager = MCPStateManager()
    return _mcp_state_manager
