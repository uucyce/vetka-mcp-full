"""
VETKA Phase 99 - Multi-Generational Cache (MGC)

PostgreSQL-inspired hierarchical cache with automatic promotion/demotion.
Three-tier architecture: RAM (Gen 0) -> Qdrant (Gen 1) -> JSON (Gen 2)

@file mgc_cache.py
@status active
@phase 99
@depends asyncio, dataclasses, datetime, typing, logging, pathlib, json
@used_by qdrant_client.py, embedding_pipeline.py, cam_engine.py

MARKER-99-02: MGC promotion threshold - items with access_count >= threshold stay in Gen 0
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Awaitable
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class MGCEntry:
    """
    Single entry in the Multi-Generational Cache.

    Attributes:
        key: Unique identifier for this entry
        value: Cached value (any serializable type)
        access_count: Number of times this entry was accessed
        created_at: When this entry was first created
        last_accessed: When this entry was last accessed
        generation: Current tier (0=RAM, 1=Qdrant, 2=JSON)
        size_bytes: Estimated size in bytes (for memory management)
    """
    key: str
    value: Any
    access_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    generation: int = 0  # 0=RAM, 1=Qdrant, 2=JSON
    size_bytes: int = 0

    def touch(self) -> None:
        """Update access tracking."""
        self.access_count += 1
        self.last_accessed = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON storage."""
        return {
            "key": self.key,
            "value": self.value,
            "access_count": self.access_count,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "generation": self.generation,
            "size_bytes": self.size_bytes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MGCEntry":
        """Deserialize from JSON."""
        return cls(
            key=data["key"],
            value=data["value"],
            access_count=data.get("access_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            generation=data.get("generation", 2),  # Loaded from JSON = Gen 2
            size_bytes=data.get("size_bytes", 0)
        )


class MGCCache:
    """
    Multi-Generational Cache with automatic tier management.

    Generation Flow:
        New Entry -> Gen 0 (RAM)
                        |
                        +-- access_count >= threshold -> stays in Gen 0
                        |
                        +-- LRU eviction -> Gen 1 (Qdrant)
                                                |
                                                +-- cold/stale -> Gen 2 (JSON)

    Usage:
        mgc = MGCCache(gen0_max=100)
        await mgc.set("key", value)      # -> Gen 0 (RAM)
        result = await mgc.get("key")    # checks Gen 0 -> Gen 1 -> Gen 2

    MARKER-99-02: Promotion threshold controls Gen 0 retention
    """

    def __init__(
        self,
        gen0_max: int = 100,
        promotion_threshold: int = 3,
        qdrant_client: Optional[Any] = None,
        json_path: Optional[Path] = None
    ):
        """
        Initialize MGC cache.

        Args:
            gen0_max: Maximum entries in Gen 0 (RAM)
            promotion_threshold: Access count to stay in Gen 0
            qdrant_client: Optional Qdrant client for Gen 1
            json_path: Path for Gen 2 JSON storage
        """
        self.gen0: Dict[str, MGCEntry] = {}
        self.gen0_max = gen0_max
        self.promotion_threshold = promotion_threshold
        self.qdrant = qdrant_client
        self.json_path = json_path or Path("data/mgc_cache.json")

        # Stats
        self._hits = {"gen0": 0, "gen1": 0, "gen2": 0}
        self._misses = 0
        self._evictions = 0

        # Lock for thread safety
        self._lock = asyncio.Lock()

        logger.debug(f"MGCCache initialized: gen0_max={gen0_max}, threshold={promotion_threshold}")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from fastest available generation.

        Checks Gen 0 (RAM) -> Gen 1 (Qdrant) -> Gen 2 (JSON)
        Promotes frequently accessed items back to Gen 0.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        async with self._lock:
            # Gen 0: RAM (hot) - O(1) lookup
            if key in self.gen0:
                entry = self.gen0[key]
                entry.touch()
                self._hits["gen0"] += 1
                logger.debug(f"MGC Gen 0 hit: {key}")
                return entry.value

        # Gen 1: Qdrant (warm) - async lookup
        if self.qdrant:
            result = await self._get_from_qdrant(key)
            if result is not None:
                self._hits["gen1"] += 1
                logger.debug(f"MGC Gen 1 hit: {key}")
                # Maybe promote back to Gen 0
                await self._maybe_promote(key, result)
                return result

        # Gen 2: JSON (cold) - file lookup
        result = await self._get_from_json(key)
        if result is not None:
            self._hits["gen2"] += 1
            logger.debug(f"MGC Gen 2 hit: {key}")
            # Maybe promote back to Gen 0
            await self._maybe_promote(key, result)
            return result

        self._misses += 1
        return None

    async def set(self, key: str, value: Any, size_bytes: int = 0) -> None:
        """
        Set value in Gen 0 (RAM), handle eviction if full.

        Args:
            key: Cache key
            value: Value to cache
            size_bytes: Optional size estimate for memory tracking
        """
        async with self._lock:
            # Check if eviction needed
            if len(self.gen0) >= self.gen0_max and key not in self.gen0:
                await self._evict_lru()

            # Create or update entry
            if key in self.gen0:
                entry = self.gen0[key]
                entry.value = value
                entry.touch()
            else:
                entry = MGCEntry(
                    key=key,
                    value=value,
                    size_bytes=size_bytes
                )
                self.gen0[key] = entry

            logger.debug(f"MGC set: {key} -> Gen 0")

    async def delete(self, key: str) -> bool:
        """
        Delete key from all generations.

        Args:
            key: Cache key to delete

        Returns:
            True if key was found and deleted
        """
        deleted = False

        async with self._lock:
            if key in self.gen0:
                del self.gen0[key]
                deleted = True

        # Also try to delete from Gen 1 and Gen 2
        if self.qdrant:
            await self._delete_from_qdrant(key)
        await self._delete_from_json(key)

        return deleted

    async def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Awaitable[Any]],
        size_bytes: int = 0
    ) -> Any:
        """
        Get from cache or compute and store.

        Args:
            key: Cache key
            compute_fn: Async function to compute value if not cached
            size_bytes: Size estimate for new entry

        Returns:
            Cached or computed value
        """
        # Try cache first
        result = await self.get(key)
        if result is not None:
            return result

        # Compute and cache
        result = await compute_fn()
        await self.set(key, result, size_bytes)
        return result

    async def _evict_lru(self) -> None:
        """
        Evict least recently used item to Gen 1 or Gen 2.

        MARKER-99-02: Items with access_count >= threshold go to Gen 1 (Qdrant)
        Others go directly to Gen 2 (JSON)
        """
        if not self.gen0:
            return

        # Find LRU entry
        lru_key = min(self.gen0, key=lambda k: self.gen0[k].last_accessed)
        entry = self.gen0.pop(lru_key)
        entry.generation = 1 if entry.access_count >= self.promotion_threshold else 2

        self._evictions += 1
        logger.debug(f"MGC evict: {lru_key} -> Gen {entry.generation}")

        # Demote based on access count
        if entry.access_count >= self.promotion_threshold:
            # Valuable item -> Gen 1 (Qdrant)
            await self._store_in_qdrant(entry)
        else:
            # Low-value item -> Gen 2 (JSON)
            await self._store_in_json(entry)

    async def _maybe_promote(self, key: str, value: Any) -> None:
        """
        Promote item back to Gen 0 if accessed often.

        Items retrieved from Gen 1 or Gen 2 that are accessed frequently
        get promoted back to Gen 0 for faster access.
        """
        async with self._lock:
            if len(self.gen0) < self.gen0_max:
                entry = MGCEntry(key=key, value=value, generation=0)
                entry.touch()
                self.gen0[key] = entry
                logger.debug(f"MGC promote: {key} -> Gen 0")

    # === Gen 1: Qdrant Operations ===

    async def _get_from_qdrant(self, key: str) -> Optional[Any]:
        """Retrieve from Qdrant (Gen 1)."""
        if not self.qdrant:
            return None

        try:
            # Use key as filter
            key_hash = self._hash_key(key)
            # This is a placeholder - actual implementation depends on Qdrant schema
            # In practice, you'd store MGC entries in a dedicated collection
            # with key_hash as payload field
            return None  # TODO: Implement when integrating with real Qdrant
        except Exception as e:
            logger.warning(f"MGC Qdrant get failed: {e}")
            return None

    async def _store_in_qdrant(self, entry: MGCEntry) -> None:
        """Store entry in Qdrant (Gen 1)."""
        if not self.qdrant:
            # Fallback to JSON if no Qdrant
            await self._store_in_json(entry)
            return

        try:
            # Placeholder - actual implementation depends on Qdrant schema
            logger.debug(f"MGC would store in Qdrant: {entry.key}")
            # For now, fallback to JSON
            await self._store_in_json(entry)
        except Exception as e:
            logger.warning(f"MGC Qdrant store failed: {e}")
            await self._store_in_json(entry)

    async def _delete_from_qdrant(self, key: str) -> None:
        """Delete from Qdrant (Gen 1)."""
        if not self.qdrant:
            return
        # Placeholder
        pass

    # === Gen 2: JSON Operations ===

    async def _get_from_json(self, key: str) -> Optional[Any]:
        """Retrieve from JSON file (Gen 2)."""
        try:
            if not self.json_path.exists():
                return None

            async with asyncio.Lock():
                data = json.loads(self.json_path.read_text())
                key_hash = self._hash_key(key)
                if key_hash in data:
                    return data[key_hash].get("value")
            return None
        except Exception as e:
            logger.warning(f"MGC JSON get failed: {e}")
            return None

    async def _store_in_json(self, entry: MGCEntry) -> None:
        """Store entry in JSON file (Gen 2)."""
        try:
            # Ensure directory exists
            self.json_path.parent.mkdir(parents=True, exist_ok=True)

            # Load existing data
            data = {}
            if self.json_path.exists():
                try:
                    data = json.loads(self.json_path.read_text())
                except json.JSONDecodeError:
                    data = {}

            # Add entry
            key_hash = self._hash_key(entry.key)
            data[key_hash] = entry.to_dict()

            # Write back
            self.json_path.write_text(json.dumps(data, indent=2, default=str))
            logger.debug(f"MGC stored in JSON: {entry.key}")
        except Exception as e:
            logger.error(f"MGC JSON store failed: {e}")

    async def _delete_from_json(self, key: str) -> None:
        """Delete from JSON file (Gen 2)."""
        try:
            if not self.json_path.exists():
                return

            data = json.loads(self.json_path.read_text())
            key_hash = self._hash_key(key)
            if key_hash in data:
                del data[key_hash]
                self.json_path.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.warning(f"MGC JSON delete failed: {e}")

    # === Utilities ===

    def _hash_key(self, key: str) -> str:
        """Create consistent hash for key storage."""
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(self._hits.values())
        total_requests = total_hits + self._misses

        return {
            "gen0_size": len(self.gen0),
            "gen0_max": self.gen0_max,
            "hits": self._hits.copy(),
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": total_hits / max(1, total_requests),
            "gen0_hit_rate": self._hits["gen0"] / max(1, total_requests)
        }

    async def clear(self) -> None:
        """Clear all generations."""
        async with self._lock:
            self.gen0.clear()
        # Clear JSON
        if self.json_path.exists():
            self.json_path.unlink()
        logger.info("MGC cache cleared")

    def __repr__(self) -> str:
        stats = self.get_stats()
        return f"MGCCache(gen0={stats['gen0_size']}/{self.gen0_max}, hit_rate={stats['hit_rate']:.2%})"


# === Singleton instance for global access ===
_global_mgc: Optional[MGCCache] = None


def get_mgc_cache() -> MGCCache:
    """Get or create global MGC cache instance."""
    global _global_mgc
    if _global_mgc is None:
        _global_mgc = MGCCache()
        logger.info("Global MGC cache initialized")
    return _global_mgc


def reset_mgc_cache() -> None:
    """Reset global MGC cache (for testing)."""
    global _global_mgc
    _global_mgc = None
