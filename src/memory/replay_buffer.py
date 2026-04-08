"""
VETKA Phase 76.1 - Replay Buffer
Storage for high-value learning examples for LoRA fine-tuning

@file replay_buffer.py
@status ACTIVE
@phase Phase 76.1 - Learning System Integration
@calledBy langgraph_nodes.py (approval_node)
@lastAudit 2026-01-20

Strategy (from Grok #1 Research):
- Storage: Qdrant collection "vetka_replay"
- Size: 500-1000 examples optimal for 7B models
- Sampling: 80% recent + 20% hard (highest difficulty)
- Hardness metric: retry_count * (1 - eval_score) + surprise
- Deduplication: Cosine similarity >0.95 → discard
"""

import logging
import math
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Import Qdrant client
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        PointStruct,
        Distance,
        VectorParams,
        Filter,
        FieldCondition,
        Range,
        ScrollRequest
    )
    QDRANT_AVAILABLE = True
except ImportError:
    logger.warning("qdrant-client not installed for ReplayBuffer")
    QDRANT_AVAILABLE = False
    QdrantClient = None


@dataclass
class ReplayExample:
    """
    High-value learning example for LoRA training.

    Stored in Qdrant for semantic retrieval and training.
    """
    workflow_id: str
    task: str
    enhanced_prompt: str  # From LearnerAgent
    eval_score: float
    retry_count: int
    difficulty: float  # Computed: retry_count * (1-score) + surprise
    category: str  # 'failure' / 'success' / 'hard'
    surprise_score: float  # From CAM
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReplayExample':
        return cls(**data)


class ReplayBuffer:
    """
    Storage for high-value learning examples.

    Strategy (from Grok #1):
    - 80% recent failures (last N workflows)
    - 20% hard examples (highest difficulty score)

    Optimal size: 500-1000 examples for 7B models.

    Usage:
        buffer = ReplayBuffer(qdrant_client, max_size=1000)
        buffer.add(example_dict)
        samples = buffer.sample(n=50)  # For LoRA training
    """

    COLLECTION_NAME = "vetka_replay"
    VECTOR_SIZE = 768  # Gemma embeddings

    def __init__(
        self,
        qdrant_client: Optional[QdrantClient] = None,
        max_size: int = 1000,
        dedup_threshold: float = 0.95
    ):
        """
        Initialize Replay Buffer.

        Args:
            qdrant_client: Qdrant client instance (or None for lazy init)
            max_size: Maximum examples to store (500-1000 optimal)
            dedup_threshold: Cosine similarity threshold for deduplication
        """
        self.qdrant = qdrant_client
        self.max_size = max_size
        self.dedup_threshold = dedup_threshold
        self._initialized = False

        if self.qdrant and QDRANT_AVAILABLE:
            self._ensure_collection()
            self._initialized = True
            logger.info(f"[ReplayBuffer] Initialized with max_size={max_size}")

    def _ensure_collection(self) -> bool:
        """Create Qdrant collection if not exists."""
        if not self.qdrant or not QDRANT_AVAILABLE:
            return False

        try:
            collections = self.qdrant.get_collections()
            existing = {c.name for c in collections.collections}

            if self.COLLECTION_NAME not in existing:
                self.qdrant.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"[ReplayBuffer] Created collection: {self.COLLECTION_NAME}")

            return True

        except Exception as e:
            logger.error(f"[ReplayBuffer] Collection initialization failed: {e}")
            return False

    def add(self, example: Dict[str, Any]) -> bool:
        """
        Add example to buffer with deduplication.

        Deduplication: Cosine similarity >0.95 → discard

        Args:
            example: Dict with keys:
                - workflow_id: str
                - task: str
                - enhanced_prompt: str
                - eval_score: float
                - retry_count: int
                - surprise_score: float (optional, default 0.5)
                - embeddings: List[float] (768D vector)

        Returns:
            True if added, False if duplicate or error
        """
        if not self.qdrant or not QDRANT_AVAILABLE:
            logger.warning("[ReplayBuffer] Qdrant not available, skipping add")
            return False

        embeddings = example.get('embeddings', [])
        if not embeddings or len(embeddings) != self.VECTOR_SIZE:
            logger.warning(f"[ReplayBuffer] Invalid embeddings: expected {self.VECTOR_SIZE}D")
            return False

        try:
            # Check for duplicates (semantic similarity > threshold)
            if self._is_duplicate(embeddings):
                logger.debug(f"[ReplayBuffer] Duplicate detected, skipping: {example.get('workflow_id')}")
                return False

            # Compute difficulty score
            difficulty = self._compute_difficulty(
                retry_count=example.get('retry_count', 0),
                eval_score=example.get('eval_score', 0.5),
                surprise=example.get('surprise_score', 0.5)
            )

            # Categorize
            category = self._categorize(difficulty, example.get('eval_score', 0.5))

            # Generate unique point ID
            point_id = uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"replay_{example.get('workflow_id', 'unknown')}_{datetime.now().isoformat()}"
            ).int & 0x7FFFFFFFFFFFFFFF

            # Create payload (exclude embeddings - stored as vector)
            payload = {
                'workflow_id': example.get('workflow_id', 'unknown'),
                'task': example.get('task', '')[:1000],  # Truncate for storage
                'enhanced_prompt': example.get('enhanced_prompt', '')[:2000],
                'eval_score': example.get('eval_score', 0.5),
                'retry_count': example.get('retry_count', 0),
                'difficulty': difficulty,
                'category': category,
                'surprise_score': example.get('surprise_score', 0.5),
                'timestamp': datetime.now().isoformat()
            }

            # Create point
            point = PointStruct(
                id=point_id,
                vector=embeddings,
                payload=payload
            )

            # Upsert to Qdrant
            self.qdrant.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[point]
            )

            logger.debug(f"[ReplayBuffer] Added example: {example.get('workflow_id')}, difficulty={difficulty:.3f}")

            # Cleanup if over max_size
            self._cleanup_old()

            return True

        except Exception as e:
            logger.error(f"[ReplayBuffer] Add failed: {e}")
            return False

    def sample(self, n: int = 50) -> List[Dict[str, Any]]:
        """
        Sample examples for LoRA training.

        Strategy (from Grok #1):
        - 80% recent (40 examples if n=50)
        - 20% hard (10 examples if n=50)

        Args:
            n: Number of examples to sample

        Returns:
            List of example dicts ready for training
        """
        if not self.qdrant or not QDRANT_AVAILABLE:
            logger.warning("[ReplayBuffer] Qdrant not available, returning empty sample")
            return []

        try:
            recent_n = int(n * 0.8)
            hard_n = n - recent_n

            examples = []

            # Get recent examples (scroll, newest first)
            recent_points, _ = self.qdrant.scroll(
                collection_name=self.COLLECTION_NAME,
                limit=recent_n,
                with_payload=True,
                with_vectors=False
            )

            for point in recent_points:
                examples.append(point.payload)

            # Get hard examples (difficulty >= 0.6)
            try:
                hard_filter = Filter(
                    must=[
                        FieldCondition(
                            key='difficulty',
                            range=Range(gte=0.6)
                        )
                    ]
                )

                hard_points, _ = self.qdrant.scroll(
                    collection_name=self.COLLECTION_NAME,
                    scroll_filter=hard_filter,
                    limit=hard_n,
                    with_payload=True,
                    with_vectors=False
                )

                for point in hard_points:
                    # Avoid duplicates from recent
                    if point.payload.get('workflow_id') not in [e.get('workflow_id') for e in examples]:
                        examples.append(point.payload)

            except Exception as e:
                logger.warning(f"[ReplayBuffer] Hard examples filter failed: {e}")

            logger.info(f"[ReplayBuffer] Sampled {len(examples)} examples (target: {n})")
            return examples[:n]

        except Exception as e:
            logger.error(f"[ReplayBuffer] Sample failed: {e}")
            return []

    def _compute_difficulty(
        self,
        retry_count: int,
        eval_score: float,
        surprise: float
    ) -> float:
        """
        Hardness metric from Grok #1:
        difficulty = retry_count * (1 - eval_score) + surprise

        Normalized to [0, 1]

        Args:
            retry_count: Number of retry attempts (0-3 typically)
            eval_score: Final evaluation score (0-1)
            surprise: CAM surprise score (0-1)

        Returns:
            Normalized difficulty score (0-1)
        """
        raw = retry_count * (1 - eval_score) + surprise
        # Normalize (assume max_retry=3, max_surprise=1, max raw ~4)
        normalized = min(1.0, raw / 4.0)
        return round(normalized, 3)

    def _categorize(self, difficulty: float, eval_score: float) -> str:
        """
        Categorize example for training strategy.

        Categories:
        - 'hard': difficulty >= 0.6 (priority for training)
        - 'failure': eval_score < 0.7 (learn from mistakes)
        - 'success': otherwise (positive examples)
        """
        if difficulty >= 0.6:
            return "hard"
        elif eval_score < 0.7:
            return "failure"
        else:
            return "success"

    def _is_duplicate(self, embedding: List[float]) -> bool:
        """
        Check semantic similarity > threshold.

        Args:
            embedding: 768D vector to check

        Returns:
            True if duplicate exists (similarity > 0.95)
        """
        if not self.qdrant:
            return False

        try:
            results = self.qdrant.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=embedding,
                limit=1,
                score_threshold=self.dedup_threshold
            )
            return len(results) > 0

        except Exception as e:
            logger.warning(f"[ReplayBuffer] Duplicate check failed: {e}")
            return False

    def _cleanup_old(self):
        """
        Remove oldest examples if over max_size.

        Strategy: Delete oldest by timestamp, keep hard examples longer.
        """
        if not self.qdrant:
            return

        try:
            # Get collection info
            info = self.qdrant.get_collection(self.COLLECTION_NAME)
            current_count = info.points_count

            if current_count <= self.max_size:
                return

            # Calculate how many to delete
            to_delete = current_count - self.max_size

            # Get oldest non-hard examples
            try:
                non_hard_filter = Filter(
                    must_not=[
                        FieldCondition(
                            key='category',
                            match={'value': 'hard'}
                        )
                    ]
                )

                oldest_points, _ = self.qdrant.scroll(
                    collection_name=self.COLLECTION_NAME,
                    scroll_filter=non_hard_filter,
                    limit=to_delete,
                    with_payload=False,
                    with_vectors=False
                )

                if oldest_points:
                    ids_to_delete = [point.id for point in oldest_points]
                    self.qdrant.delete(
                        collection_name=self.COLLECTION_NAME,
                        points_selector={'points': ids_to_delete}
                    )
                    logger.info(f"[ReplayBuffer] Cleaned up {len(ids_to_delete)} old examples")

            except Exception as e:
                logger.warning(f"[ReplayBuffer] Cleanup filter failed: {e}")

        except Exception as e:
            logger.warning(f"[ReplayBuffer] Cleanup failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get buffer statistics.

        Returns:
            Dict with count, category distribution, avg difficulty
        """
        if not self.qdrant or not QDRANT_AVAILABLE:
            return {'available': False}

        try:
            info = self.qdrant.get_collection(self.COLLECTION_NAME)

            # Get all points for category stats
            all_points, _ = self.qdrant.scroll(
                collection_name=self.COLLECTION_NAME,
                limit=self.max_size,
                with_payload=True,
                with_vectors=False
            )

            categories = {'hard': 0, 'failure': 0, 'success': 0}
            difficulties = []

            for point in all_points:
                cat = point.payload.get('category', 'unknown')
                if cat in categories:
                    categories[cat] += 1
                difficulties.append(point.payload.get('difficulty', 0))

            avg_difficulty = sum(difficulties) / len(difficulties) if difficulties else 0

            return {
                'available': True,
                'total_count': info.points_count,
                'max_size': self.max_size,
                'categories': categories,
                'avg_difficulty': round(avg_difficulty, 3),
                'collection': self.COLLECTION_NAME
            }

        except Exception as e:
            logger.error(f"[ReplayBuffer] Stats failed: {e}")
            return {'available': False, 'error': str(e)}

    def clear(self):
        """Clear all examples from buffer (use with caution!)."""
        if not self.qdrant or not QDRANT_AVAILABLE:
            return

        try:
            self.qdrant.delete_collection(self.COLLECTION_NAME)
            self._ensure_collection()
            logger.info("[ReplayBuffer] Buffer cleared")
        except Exception as e:
            logger.error(f"[ReplayBuffer] Clear failed: {e}")


# ============ FACTORY FUNCTION ============

_replay_buffer_instance: Optional[ReplayBuffer] = None


def get_replay_buffer(
    qdrant_client: Optional[QdrantClient] = None,
    max_size: int = 1000
) -> ReplayBuffer:
    """
    Factory function - returns singleton ReplayBuffer.

    Args:
        qdrant_client: Qdrant client (uses global if None)
        max_size: Maximum examples (500-1000 optimal)

    Returns:
        ReplayBuffer singleton instance
    """
    global _replay_buffer_instance

    if _replay_buffer_instance is None:
        # Try to get global Qdrant client if not provided
        if qdrant_client is None:
            try:
                from src.memory.qdrant_client import get_qdrant_client
                qdrant_vetka = get_qdrant_client()
                if qdrant_vetka and qdrant_vetka.client:
                    qdrant_client = qdrant_vetka.client
            except ImportError:
                pass

        _replay_buffer_instance = ReplayBuffer(
            qdrant_client=qdrant_client,
            max_size=max_size
        )

    return _replay_buffer_instance
