# Phase 111.18 - Qdrant Batch Manager
# Non-blocking interval-based batch queue for Qdrant operations
# Solves: blocking embedding, per-message upsert, event loop starvation

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Singleton instance
_batch_manager: Optional["QdrantBatchManager"] = None


@dataclass
class QueuedMessage:
    """Message queued for Qdrant persistence."""
    group_id: str
    message_id: str
    sender_id: str
    content: str
    role: str = "user"
    agent: Optional[str] = None
    model: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class QueuedArtifact:
    """Artifact queued for Qdrant indexing."""
    artifact_id: str
    name: str
    content: str
    artifact_type: str
    workflow_id: str
    filepath: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class QdrantBatchManager:
    """
    Manages batched Qdrant operations with interval flush.

    Features:
    - Non-blocking queue operations
    - Batch embedding generation (1 call for N texts)
    - Batch Qdrant upsert (1 operation for N points)
    - Configurable flush interval (default: 30 seconds)
    - Max batch size trigger for immediate flush
    - Runs sync operations in executor to not block event loop

    Usage:
        manager = get_batch_manager()
        await manager.queue_message({...})  # Non-blocking
        # Messages will be flushed every 30 seconds or when batch is full
    """

    def __init__(
        self,
        flush_interval: float = 30.0,  # Phase 111.18: 30 seconds per user request
        max_batch_size: int = 100
    ):
        self._message_queue: List[QueuedMessage] = []
        self._artifact_queue: List[QueuedArtifact] = []
        self._lock = asyncio.Lock()
        self._flush_interval = flush_interval
        self._max_batch_size = max_batch_size
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        self._stats = {
            "messages_queued": 0,
            "messages_flushed": 0,
            "artifacts_queued": 0,
            "artifacts_flushed": 0,
            "flush_count": 0,
            "last_flush": None,
        }
        logger.info(f"[QdrantBatch] Initialized with {flush_interval}s interval, max {max_batch_size} batch")

    async def start(self):
        """Start background flush task."""
        if self._running:
            logger.warning("[QdrantBatch] Already running")
            return

        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("[QdrantBatch] Started background flush loop")

    async def stop(self):
        """Stop and flush remaining items."""
        self._running = False

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self._flush_pending()
        logger.info("[QdrantBatch] Stopped and flushed remaining items")

    async def queue_message(
        self,
        group_id: str,
        message_id: str,
        sender_id: str,
        content: str,
        role: str = "user",
        agent: Optional[str] = None,
        model: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Add message to queue (non-blocking).

        This returns immediately - message will be persisted
        during next flush cycle (every 30 seconds) or when
        batch size is reached.
        """
        msg = QueuedMessage(
            group_id=group_id,
            message_id=message_id,
            sender_id=sender_id,
            content=content,
            role=role,
            agent=agent,
            model=model,
            metadata=metadata or {}
        )

        async with self._lock:
            self._message_queue.append(msg)
            self._stats["messages_queued"] += 1
            queue_len = len(self._message_queue)

        logger.debug(f"[QdrantBatch] Queued message {message_id[:8]}... (queue: {queue_len})")

        # Immediate flush if batch full
        if queue_len >= self._max_batch_size:
            logger.info(f"[QdrantBatch] Batch full ({queue_len}), triggering immediate flush")
            asyncio.create_task(self._flush_messages())

    async def queue_artifact(
        self,
        artifact_id: str,
        name: str,
        content: str,
        artifact_type: str,
        workflow_id: str,
        filepath: str
    ):
        """
        Add artifact to queue for Qdrant indexing (non-blocking).
        """
        artifact = QueuedArtifact(
            artifact_id=artifact_id,
            name=name,
            content=content,
            artifact_type=artifact_type,
            workflow_id=workflow_id,
            filepath=filepath
        )

        async with self._lock:
            self._artifact_queue.append(artifact)
            self._stats["artifacts_queued"] += 1
            queue_len = len(self._artifact_queue)

        logger.debug(f"[QdrantBatch] Queued artifact {artifact_id[:8]}... (queue: {queue_len})")

    async def _flush_loop(self):
        """Periodic flush every interval."""
        while self._running:
            try:
                await asyncio.sleep(self._flush_interval)
                if self._running:  # Check again after sleep
                    await self._flush_pending()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[QdrantBatch] Flush loop error: {e}")

    async def _flush_pending(self):
        """Flush all queued items."""
        self._stats["flush_count"] += 1
        self._stats["last_flush"] = datetime.now().isoformat()

        await self._flush_messages()
        await self._flush_artifacts()

    async def _flush_messages(self):
        """Batch upsert queued messages."""
        async with self._lock:
            if not self._message_queue:
                return
            batch = self._message_queue[:self._max_batch_size]
            self._message_queue = self._message_queue[self._max_batch_size:]

        if not batch:
            return

        logger.info(f"[QdrantBatch] Flushing {len(batch)} messages to Qdrant...")

        # Run sync operations in executor to not block event loop
        try:
            loop = asyncio.get_running_loop()
            count = await loop.run_in_executor(None, self._upsert_messages_sync, batch)
            self._stats["messages_flushed"] += count
            logger.info(f"[QdrantBatch] Flushed {count} messages successfully")
        except Exception as e:
            logger.error(f"[QdrantBatch] Message flush failed: {e}")
            # Re-queue failed messages for retry
            async with self._lock:
                self._message_queue = batch + self._message_queue

    async def _flush_artifacts(self):
        """Batch upsert queued artifacts."""
        async with self._lock:
            if not self._artifact_queue:
                return
            batch = self._artifact_queue[:self._max_batch_size]
            self._artifact_queue = self._artifact_queue[self._max_batch_size:]

        if not batch:
            return

        logger.info(f"[QdrantBatch] Flushing {len(batch)} artifacts to Qdrant...")

        try:
            loop = asyncio.get_running_loop()
            count = await loop.run_in_executor(None, self._upsert_artifacts_sync, batch)
            self._stats["artifacts_flushed"] += count
            logger.info(f"[QdrantBatch] Flushed {count} artifacts successfully")
        except Exception as e:
            logger.error(f"[QdrantBatch] Artifact flush failed: {e}")

    def _upsert_messages_sync(self, messages: List[QueuedMessage]) -> int:
        """
        Sync batch upsert messages (runs in executor).

        This is synchronous but runs in ThreadPoolExecutor
        so it doesn't block the async event loop.
        """
        from src.memory.qdrant_client import get_qdrant_client
        from qdrant_client.models import PointStruct

        client = get_qdrant_client()
        if not client or not client.client:
            logger.warning("[QdrantBatch] Qdrant not available")
            return 0

        # Batch generate embeddings
        try:
            from src.utils.embedding_service import get_embedding_service
            svc = get_embedding_service()

            texts = [m.content[:2000] for m in messages]
            embeddings = svc.get_embedding_batch(texts)

            if not embeddings:
                # Fallback to individual embeddings
                from src.utils.embedding_service import get_embedding
                embeddings = [get_embedding(t) for t in texts]
        except Exception as e:
            logger.error(f"[QdrantBatch] Embedding generation failed: {e}")
            # Fallback to individual
            from src.utils.embedding_service import get_embedding
            embeddings = [get_embedding(m.content[:2000]) for m in messages]

        # Build points
        points = []
        for msg, emb in zip(messages, embeddings):
            if not emb:
                logger.warning(f"[QdrantBatch] No embedding for message {msg.message_id[:8]}")
                continue

            # Deterministic point ID from message_id
            point_id = int(hashlib.md5(msg.message_id.encode()).hexdigest()[:16], 16)

            payload = {
                "group_id": msg.group_id,
                "message_id": msg.message_id,
                "sender_id": msg.sender_id,
                "content": msg.content[:5000],
                "role": msg.role,
                "agent": msg.agent,
                "model": msg.model,
                "timestamp": msg.timestamp,
                "metadata": msg.metadata
            }

            points.append(PointStruct(
                id=point_id,
                vector=emb,
                payload=payload
            ))

        if not points:
            return 0

        # Single batch upsert
        try:
            client.client.upsert(
                collection_name=client.COLLECTION_NAMES.get('chat', 'VetkaGroupChat'),
                points=points
            )
            return len(points)
        except Exception as e:
            logger.error(f"[QdrantBatch] Batch upsert failed: {e}")
            return 0

    def _upsert_artifacts_sync(self, artifacts: List[QueuedArtifact]) -> int:
        """
        Sync batch upsert artifacts (runs in executor).
        """
        from src.memory.qdrant_client import get_qdrant_client
        from qdrant_client.models import PointStruct

        client = get_qdrant_client()
        if not client or not client.client:
            return 0

        # Batch generate embeddings
        try:
            from src.utils.embedding_service import get_embedding_service
            svc = get_embedding_service()

            texts = [a.content[:2000] for a in artifacts]
            embeddings = svc.get_embedding_batch(texts)

            if not embeddings:
                from src.utils.embedding_service import get_embedding
                embeddings = [get_embedding(t) for t in texts]
        except Exception as e:
            logger.error(f"[QdrantBatch] Artifact embedding failed: {e}")
            from src.utils.embedding_service import get_embedding
            embeddings = [get_embedding(a.content[:2000]) for a in artifacts]

        # Build points
        points = []
        for artifact, emb in zip(artifacts, embeddings):
            if not emb:
                continue

            point_id = int(hashlib.md5(artifact.artifact_id.encode()).hexdigest()[:16], 16)

            payload = {
                "artifact_id": artifact.artifact_id,
                "name": artifact.name,
                "content": artifact.content[:5000],
                "artifact_type": artifact.artifact_type,
                "workflow_id": artifact.workflow_id,
                "filepath": artifact.filepath,
                "timestamp": artifact.timestamp
            }

            points.append(PointStruct(
                id=point_id,
                vector=emb,
                payload=payload
            ))

        if not points:
            return 0

        try:
            # Use VetkaArtifacts collection if exists, otherwise default
            collection = client.COLLECTION_NAMES.get('artifacts', 'VetkaArtifacts')
            client.client.upsert(
                collection_name=collection,
                points=points
            )
            return len(points)
        except Exception as e:
            logger.error(f"[QdrantBatch] Artifact batch upsert failed: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            **self._stats,
            "message_queue_size": len(self._message_queue),
            "artifact_queue_size": len(self._artifact_queue),
            "running": self._running,
            "flush_interval": self._flush_interval,
            "max_batch_size": self._max_batch_size
        }

    async def force_flush(self):
        """Manually trigger immediate flush."""
        logger.info("[QdrantBatch] Manual flush triggered")
        await self._flush_pending()


def get_batch_manager() -> QdrantBatchManager:
    """Get singleton batch manager instance."""
    global _batch_manager
    if _batch_manager is None:
        _batch_manager = QdrantBatchManager(
            flush_interval=30.0,  # Phase 111.18: 30 seconds
            max_batch_size=100
        )
    return _batch_manager


async def init_batch_manager():
    """Initialize and start the batch manager. Call from app startup."""
    manager = get_batch_manager()
    await manager.start()
    return manager


async def shutdown_batch_manager():
    """Stop the batch manager gracefully. Call from app shutdown."""
    global _batch_manager
    if _batch_manager:
        await _batch_manager.stop()
        _batch_manager = None
