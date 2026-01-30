"""
VETKA Phase 77.6 - Trash Memory Management
Soft delete with recovery capability

@file trash.py
@status ACTIVE
@phase Phase 77.6 - Memory Sync Protocol
@calledBy MemorySyncEngine, DiffApplier
@lastAudit 2026-01-20

MARKER-77-06: Cleanup interval settings

Key principle: deleted ≠ permanent delete
Deleted files go to Trash Memory (recoverable) with TTL.
User can restore within TTL period.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# Check Qdrant availability
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        PointStruct,
        Distance,
        VectorParams,
        Filter,
        FieldCondition,
        Range,
        MatchValue
    )
    QDRANT_AVAILABLE = True
except ImportError:
    logger.warning("qdrant-client not available for TrashMemory")
    QDRANT_AVAILABLE = False
    QdrantClient = None


@dataclass
class TrashItem:
    """
    Item in trash memory.
    """
    original_path: str
    node_data: Dict[str, Any]  # Original NodeState as dict
    embedding: List[float]
    moved_at: datetime
    ttl_days: int
    restore_until: datetime
    reason: str = "filesystem_deletion"
    restored: bool = False

    def to_payload(self) -> Dict[str, Any]:
        """Convert to Qdrant payload."""
        return {
            'original_path': self.original_path,
            'node_data': self.node_data,
            'moved_at': self.moved_at.isoformat(),
            'ttl_days': self.ttl_days,
            'restore_until': self.restore_until.isoformat(),
            'reason': self.reason,
            'restored': self.restored
        }

    @classmethod
    def from_payload(cls, payload: Dict, embedding: List[float]) -> 'TrashItem':
        """Create from Qdrant payload."""
        return cls(
            original_path=payload.get('original_path', ''),
            node_data=payload.get('node_data', {}),
            embedding=embedding,
            moved_at=datetime.fromisoformat(payload.get('moved_at', datetime.now().isoformat())),
            ttl_days=payload.get('ttl_days', 90),
            restore_until=datetime.fromisoformat(payload.get('restore_until', datetime.now().isoformat())),
            reason=payload.get('reason', 'unknown'),
            restored=payload.get('restored', False)
        )


class TrashMemory:
    """
    Trash memory for soft-deleted nodes.

    Nodes moved to trash:
    - Can be restored within TTL period
    - Are automatically cleaned up after TTL
    - Preserve original embedding for search

    MARKER-77-06: Cleanup settings
    - TRASH_CLEANUP_INTERVAL = 86400 (24 hours)
    - TRASH_TTL_DEFAULT = 90 days

    Usage:
        trash = TrashMemory(qdrant_client)
        await trash.move_to_trash(node, ttl_days=90)
        # Later...
        await trash.restore_from_trash(path)
    """

    # MARKER-77-06: Cleanup configuration
    TRASH_CLEANUP_INTERVAL = 86400  # 24 hours in seconds
    TRASH_TTL_DEFAULT = 90  # days
    TRASH_COLLECTION = "VetkaTrash"  # Matches MARKER-77-02 in qdrant_client.py

    VECTOR_SIZE = 768

    def __init__(
        self,
        qdrant_client=None,
        ttl_days: int = None
    ):
        """
        Initialize trash memory.

        Args:
            qdrant_client: QdrantVetkaClient or raw QdrantClient
            ttl_days: Default TTL (days until permanent deletion)
        """
        self.qdrant = qdrant_client
        self.ttl_days = ttl_days or self.TRASH_TTL_DEFAULT
        self._initialized = False
        self._last_cleanup: Optional[datetime] = None

        if self.qdrant and QDRANT_AVAILABLE:
            self._ensure_collection()
            self._initialized = True
            logger.info(f"[TrashMemory] Initialized (TTL={self.ttl_days}d)")

    def _ensure_collection(self) -> bool:
        """Create trash collection if not exists."""
        if not self.qdrant or not QDRANT_AVAILABLE:
            return False

        try:
            client = getattr(self.qdrant, 'client', self.qdrant)
            if not client:
                return False

            collections = client.get_collections()
            existing = {c.name for c in collections.collections}

            if self.TRASH_COLLECTION not in existing:
                client.create_collection(
                    collection_name=self.TRASH_COLLECTION,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"[TrashMemory] Created collection: {self.TRASH_COLLECTION}")

            return True

        except Exception as e:
            logger.error(f"[TrashMemory] Collection init failed: {e}")
            return False

    async def move_to_trash(
        self,
        node: Any,
        ttl_days: int = None,
        reason: str = "filesystem_deletion"
    ) -> bool:
        """
        Move node to trash (soft delete).

        Args:
            node: NodeState to trash
            ttl_days: Days until permanent deletion (default: 90)
            reason: Reason for deletion

        Returns:
            True if successfully moved to trash
        """
        if not self.qdrant or not QDRANT_AVAILABLE:
            logger.warning("[TrashMemory] Qdrant not available")
            return False

        ttl = ttl_days or self.ttl_days
        now = datetime.now()

        # Extract data from node
        path = node.path if hasattr(node, 'path') else str(id(node))
        embedding = node.embedding if hasattr(node, 'embedding') else []

        if not embedding or len(embedding) == 0:
            # Use zero vector if no embedding
            embedding = [0.0] * self.VECTOR_SIZE

        # Ensure correct vector size
        if len(embedding) != self.VECTOR_SIZE:
            # Pad or truncate
            if len(embedding) < self.VECTOR_SIZE:
                embedding = embedding + [0.0] * (self.VECTOR_SIZE - len(embedding))
            else:
                embedding = embedding[:self.VECTOR_SIZE]

        # Create trash item
        trash_item = TrashItem(
            original_path=path,
            node_data=node.to_dict() if hasattr(node, 'to_dict') else {'path': path},
            embedding=embedding,
            moved_at=now,
            ttl_days=ttl,
            restore_until=now + timedelta(days=ttl),
            reason=reason
        )

        try:
            client = getattr(self.qdrant, 'client', self.qdrant)

            # Generate point ID from path
            point_id = uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"trash_{path}_{now.isoformat()}"
            ).int & 0x7FFFFFFFFFFFFFFF

            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=trash_item.to_payload()
            )

            client.upsert(
                collection_name=self.TRASH_COLLECTION,
                points=[point]
            )

            logger.info(f"[TrashMemory] Moved to trash: {path} (TTL={ttl}d)")
            return True

        except Exception as e:
            logger.error(f"[TrashMemory] Move to trash failed: {e}")
            return False

    async def restore_from_trash(
        self,
        path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Restore node from trash.

        Args:
            path: Original path of the node

        Returns:
            Original node data dict, or None if not found
        """
        if not self.qdrant or not QDRANT_AVAILABLE:
            return None

        try:
            client = getattr(self.qdrant, 'client', self.qdrant)

            # Search for the item by path
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key='original_path',
                        match=MatchValue(value=path)
                    ),
                    FieldCondition(
                        key='restored',
                        match=MatchValue(value=False)
                    )
                ]
            )

            results, _ = client.scroll(
                collection_name=self.TRASH_COLLECTION,
                scroll_filter=search_filter,
                limit=1,
                with_payload=True,
                with_vectors=True
            )

            if not results:
                logger.warning(f"[TrashMemory] Not found in trash: {path}")
                return None

            point = results[0]
            payload = point.payload

            # Check if TTL expired
            restore_until = datetime.fromisoformat(payload.get('restore_until', ''))
            if datetime.now() > restore_until:
                logger.warning(f"[TrashMemory] TTL expired for: {path}")
                return None

            # Mark as restored (don't delete, keep for audit)
            client.set_payload(
                collection_name=self.TRASH_COLLECTION,
                payload={'restored': True},
                points=[point.id]
            )

            logger.info(f"[TrashMemory] Restored from trash: {path}")

            # Return original node data
            node_data = payload.get('node_data', {})
            node_data['embedding'] = point.vector
            return node_data

        except Exception as e:
            logger.error(f"[TrashMemory] Restore failed: {e}")
            return None

    async def cleanup_expired(self) -> int:
        """
        Delete items past their TTL.

        MARKER-77-06: Respects TRASH_CLEANUP_INTERVAL.

        Returns:
            Number of items deleted
        """
        if not self.qdrant or not QDRANT_AVAILABLE:
            return 0

        # Check cleanup interval
        now = datetime.now()
        if self._last_cleanup:
            elapsed = (now - self._last_cleanup).total_seconds()
            if elapsed < self.TRASH_CLEANUP_INTERVAL:
                logger.debug(f"[TrashMemory] Cleanup skipped (last: {elapsed:.0f}s ago)")
                return 0

        self._last_cleanup = now

        try:
            client = getattr(self.qdrant, 'client', self.qdrant)

            # Find expired items
            # Note: Qdrant doesn't support datetime comparison directly
            # So we scroll all and check in Python
            all_points, _ = client.scroll(
                collection_name=self.TRASH_COLLECTION,
                limit=10000,
                with_payload=True,
                with_vectors=False
            )

            expired_ids = []
            for point in all_points:
                restore_until_str = point.payload.get('restore_until', '')
                if not restore_until_str:
                    continue

                restore_until = datetime.fromisoformat(restore_until_str)
                if now > restore_until:
                    expired_ids.append(point.id)

            if expired_ids:
                client.delete(
                    collection_name=self.TRASH_COLLECTION,
                    points_selector={'points': expired_ids}
                )
                logger.info(f"[TrashMemory] Cleaned up {len(expired_ids)} expired items")

            return len(expired_ids)

        except Exception as e:
            logger.error(f"[TrashMemory] Cleanup failed: {e}")
            return 0

    async def list_trash(
        self,
        limit: int = 100,
        include_restored: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List items in trash.

        Args:
            limit: Maximum items to return
            include_restored: Include already-restored items

        Returns:
            List of trash item summaries
        """
        if not self.qdrant or not QDRANT_AVAILABLE:
            return []

        try:
            client = getattr(self.qdrant, 'client', self.qdrant)

            search_filter = None
            if not include_restored:
                search_filter = Filter(
                    must=[
                        FieldCondition(
                            key='restored',
                            match=MatchValue(value=False)
                        )
                    ]
                )

            points, _ = client.scroll(
                collection_name=self.TRASH_COLLECTION,
                scroll_filter=search_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )

            items = []
            for point in points:
                payload = point.payload
                items.append({
                    'id': point.id,
                    'path': payload.get('original_path', ''),
                    'moved_at': payload.get('moved_at', ''),
                    'restore_until': payload.get('restore_until', ''),
                    'reason': payload.get('reason', ''),
                    'restored': payload.get('restored', False)
                })

            # Sort by moved_at (newest first)
            items.sort(key=lambda x: x['moved_at'], reverse=True)

            return items

        except Exception as e:
            logger.error(f"[TrashMemory] List failed: {e}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get trash statistics."""
        if not self.qdrant or not QDRANT_AVAILABLE:
            return {'available': False}

        try:
            client = getattr(self.qdrant, 'client', self.qdrant)
            info = client.get_collection(self.TRASH_COLLECTION)

            items = await self.list_trash(limit=10000, include_restored=True)
            restored_count = len([i for i in items if i.get('restored')])
            active_count = len([i for i in items if not i.get('restored')])

            return {
                'available': True,
                'collection': self.TRASH_COLLECTION,
                'total_points': info.points_count,
                'active_in_trash': active_count,
                'restored': restored_count,
                'ttl_days': self.ttl_days,
                'cleanup_interval_hours': self.TRASH_CLEANUP_INTERVAL / 3600,
                'last_cleanup': self._last_cleanup.isoformat() if self._last_cleanup else None
            }

        except Exception as e:
            logger.error(f"[TrashMemory] Stats failed: {e}")
            return {'available': False, 'error': str(e)}

    async def empty_trash(self, confirm: bool = False) -> int:
        """
        Permanently delete all items in trash.

        DANGER: This is irreversible!

        Args:
            confirm: Must be True to proceed

        Returns:
            Number of items deleted
        """
        if not confirm:
            logger.warning("[TrashMemory] empty_trash requires confirm=True")
            return 0

        if not self.qdrant or not QDRANT_AVAILABLE:
            return 0

        try:
            client = getattr(self.qdrant, 'client', self.qdrant)

            # Get count before
            info = client.get_collection(self.TRASH_COLLECTION)
            count = info.points_count

            # Delete and recreate collection
            client.delete_collection(self.TRASH_COLLECTION)
            self._ensure_collection()

            logger.warning(f"[TrashMemory] EMPTIED TRASH: {count} items deleted")
            return count

        except Exception as e:
            logger.error(f"[TrashMemory] Empty trash failed: {e}")
            return 0


# ========== FACTORY FUNCTION ==========

_trash_instance: Optional[TrashMemory] = None


def get_trash_memory(
    qdrant_client=None,
    ttl_days: int = None
) -> TrashMemory:
    """
    Factory function - returns singleton TrashMemory.

    Args:
        qdrant_client: Qdrant client (uses global if None)
        ttl_days: Default TTL in days

    Returns:
        TrashMemory singleton instance
    """
    global _trash_instance

    if _trash_instance is None:
        # Try to get global Qdrant client if not provided
        if qdrant_client is None:
            try:
                from src.memory.qdrant_client import get_qdrant_client
                qdrant_client = get_qdrant_client()
            except ImportError:
                pass

        _trash_instance = TrashMemory(
            qdrant_client=qdrant_client,
            ttl_days=ttl_days
        )

    return _trash_instance
