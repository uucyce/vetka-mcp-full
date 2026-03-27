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
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Awaitable
import hashlib

# MARKER_198.P1.3: Gen1 SQLite path — worktree-safe absolute path
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_GEN1_DB_PATH = _PROJECT_ROOT / "data" / "mgc_gen1.db"

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
        self._json_lock = asyncio.Lock()

        # MARKER_198.P1.3: Initialize Gen1 SQLite
        self._gen1_enabled = False
        self._gen1_db_path = _GEN1_DB_PATH
        self._init_gen1_db()

        logger.debug(f"MGCCache initialized: gen0_max={gen0_max}, threshold={promotion_threshold}")

    def _init_gen1_db(self):
        """MARKER_198.P1.3: Initialize Gen1 SQLite database with WAL mode.

        MARKER_199.DDL_FAST: sqlite_master fast path — skip DDL if table exists.
        """
        try:
            self._gen1_db_path = _GEN1_DB_PATH
            self._gen1_db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self._gen1_db_path))
            conn.execute("PRAGMA journal_mode=WAL")
            # Fast path: skip DDL if table already exists
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='mgc_gen1'"
            ).fetchone()
            if not exists:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS mgc_gen1 (
                        key_hash TEXT PRIMARY KEY,
                        key TEXT NOT NULL,
                        value_json TEXT NOT NULL,
                        access_count INTEGER DEFAULT 0,
                        created_at TEXT,
                        last_accessed TEXT
                    )
                """)
                conn.commit()
            conn.close()
            self._gen1_enabled = True
            logger.info(f"[MGC] Gen1 SQLite initialized: {self._gen1_db_path}")
        except Exception as e:
            logger.warning(f"[MGC] Gen1 SQLite init failed: {e}")
            self._gen1_enabled = False

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

        # Gen 1: SQLite (warm) - async lookup
        if self._gen1_enabled or self.qdrant:
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
        if self._gen1_enabled or self.qdrant:
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

    # === Gen 1: SQLite Operations (MARKER_198.P1.3) ===

    async def _get_from_qdrant(self, key: str) -> Optional[Any]:
        """MARKER_198.P1.3: Gen1 SQLite lookup (was Qdrant stub)."""
        if not self._gen1_enabled:
            return None
        try:
            key_hash = hashlib.md5(key.encode()).hexdigest()

            def _db_get():
                conn = sqlite3.connect(str(self._gen1_db_path))
                row = conn.execute(
                    "SELECT value_json, access_count FROM mgc_gen1 WHERE key_hash = ?",
                    (key_hash,)
                ).fetchone()
                if row:
                    # Update access count and last_accessed
                    import time
                    conn.execute(
                        "UPDATE mgc_gen1 SET access_count = access_count + 1, last_accessed = ? WHERE key_hash = ?",
                        (time.strftime("%Y-%m-%d %H:%M:%S"), key_hash)
                    )
                    conn.commit()
                conn.close()
                return row

            row = await asyncio.to_thread(_db_get)
            if row:
                value = json.loads(row[0])
                logger.debug(f"[MGC] Gen1 HIT: {key[:40]} (access_count={row[1]+1})")
                return value
            return None
        except Exception as e:
            logger.debug(f"[MGC] Gen1 get failed: {e}")
            return None

    async def _store_in_qdrant(self, entry: 'MGCEntry') -> None:
        """MARKER_198.P1.3: Gen1 SQLite store (was Qdrant stub)."""
        if not self._gen1_enabled:
            await self._store_in_json(entry)
            return
        try:
            key_hash = hashlib.md5(entry.key.encode()).hexdigest()
            value_json = json.dumps(entry.value, default=str)

            def _db_store():
                conn = sqlite3.connect(str(self._gen1_db_path))
                conn.execute(
                    """INSERT OR REPLACE INTO mgc_gen1
                       (key_hash, key, value_json, access_count, created_at, last_accessed)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (key_hash, entry.key, value_json, entry.access_count,
                     entry.created_at.isoformat() if hasattr(entry.created_at, 'isoformat') else str(entry.created_at),
                     entry.last_accessed.isoformat() if hasattr(entry.last_accessed, 'isoformat') else str(entry.last_accessed))
                )
                conn.commit()
                conn.close()

            await asyncio.to_thread(_db_store)
            logger.debug(f"[MGC] Gen1 STORE: {entry.key[:40]}")
        except Exception as e:
            logger.debug(f"[MGC] Gen1 store failed, falling back to JSON: {e}")
            await self._store_in_json(entry)

    async def _delete_from_qdrant(self, key: str) -> None:
        """MARKER_198.P1.3: Gen1 SQLite delete."""
        if not self._gen1_enabled:
            return
        try:
            key_hash = hashlib.md5(key.encode()).hexdigest()

            def _db_delete():
                conn = sqlite3.connect(str(self._gen1_db_path))
                conn.execute("DELETE FROM mgc_gen1 WHERE key_hash = ?", (key_hash,))
                conn.commit()
                conn.close()

            await asyncio.to_thread(_db_delete)
        except Exception:
            pass

    # === Gen 2: JSON Operations ===

    async def _get_from_json(self, key: str) -> Optional[Any]:
        """Retrieve from JSON file (Gen 2)."""
        try:
            if not self.json_path.exists():
                return None

            async with self._json_lock:
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

        gen1_count = 0
        if self._gen1_enabled:
            try:
                conn = sqlite3.connect(str(self._gen1_db_path))
                gen1_count = conn.execute("SELECT COUNT(*) FROM mgc_gen1").fetchone()[0]
                conn.close()
            except Exception:
                pass

        return {
            "gen0_size": len(self.gen0),
            "gen0_max": self.gen0_max,
            "gen1_count": gen1_count,
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

    # MARKER_119.1: Sync Gen0-only access for sync callers
    # (SpiralContextGenerator, ARCSolverAgent — both sync methods)
    def get_sync(self, key: str) -> Optional[Any]:
        """Sync Gen0-only get. Returns None if not in Gen0.

        For use by sync callers that only need RAM-speed cache hits.
        Does NOT check Gen1 (Qdrant) or Gen2 (JSON).
        """
        if key in self.gen0:
            entry = self.gen0[key]
            entry.touch()
            self._hits["gen0"] += 1
            return entry.value
        self._misses += 1
        return None

    def set_sync(self, key: str, value: Any, size_bytes: int = 0) -> None:
        """Sync Gen0-only set. LRU evicts oldest if Gen0 is full."""
        if len(self.gen0) >= self.gen0_max and key not in self.gen0:
            self._evict_lru_sync()
        if key in self.gen0:
            self.gen0[key].value = value
            self.gen0[key].touch()
        else:
            self.gen0[key] = MGCEntry(key=key, value=value, size_bytes=size_bytes)

    def _evict_lru_sync(self) -> None:
        """Sync LRU eviction — drop oldest from Gen0."""
        if not self.gen0:
            return
        lru_key = min(self.gen0, key=lambda k: self.gen0[k].last_accessed)
        self.gen0.pop(lru_key)
        self._evictions += 1
    # MARKER_119.1_END

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
