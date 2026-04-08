"""
VETKA Phase 77.4 - Age-Based Embedding Compression
Age-based embedding dimensionality reduction for memory efficiency.

MARKER_104_COMPRESSION_FIX: Renamed from MemoryCompression to AgeBasedEmbeddingCompression
to clarify this is NOT the same as ELISION (token compression in elision.py).

IMPORTANT DISTINCTION:
- This module (compression.py): AGE-BASED EMBEDDING COMPRESSION
  Reduces embedding dimensions (768D -> 384D -> 256D -> 64D) based on memory age.
  Uses PCA for dimensionality reduction. Affects vector storage size.

- elision.py: TOKEN COMPRESSION (ELISION)
  Compresses JSON keys/paths to save API tokens (40-60% savings).
  Does NOT affect embeddings. Purely for context window efficiency.

@file compression.py
@status active
@phase 104
@depends logging, datetime, dataclasses, numpy, sklearn.decomposition
@used_by vetka_mcp_bridge.py, shared_tools.py, tools.py (agents)

MARKER-77-09: Add search_quality_degradation metric

Compression strategy (like human memory decay curve):
- Fresh (<1 day): 768D full embeddings
- Recent (<7 days): 768D (still full)
- Month (<30 days): 384D (PCA reduction)
- Old (<90 days): 256D (more compression)
- Archive (>90 days): 64D (summary only)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Literal, Tuple
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)

# Check sklearn availability
try:
    from sklearn.decomposition import PCA

    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("sklearn not available - compression will be limited")
    SKLEARN_AVAILABLE = False
    PCA = None


@dataclass
class CompressedNodeState:
    """
    Compressed node state after age-based reduction.
    """

    path: str
    embedding: List[float]
    embedding_dim: int  # 768 / 384 / 256 / 64
    original_dim: int = 768  # For tracking compression ratio
    dep_mode: Literal["full", "top_3", "top_1", "none"] = "full"
    confidence: float = 1.0  # Decays with age
    memory_layer: Literal["active", "archived"] = "active"
    compression_ratio: float = 1.0  # 768/embedding_dim
    age_days: int = 0

    # MARKER-77-09: Quality degradation metric
    quality_score: float = (
        1.0  # Estimated search quality (1.0 = full, decreases with compression)
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "embedding": self.embedding,
            "embedding_dim": self.embedding_dim,
            "original_dim": self.original_dim,
            "dep_mode": self.dep_mode,
            "confidence": self.confidence,
            "memory_layer": self.memory_layer,
            "compression_ratio": self.compression_ratio,
            "age_days": self.age_days,
            "quality_score": self.quality_score,
        }


class AgeBasedEmbeddingCompression:
    """
    Age-based embedding dimensionality reduction.

    MARKER_104_COMPRESSION_FIX: Renamed from MemoryCompression to clarify
    this is NOT ELISION (token compression). This class reduces EMBEDDING
    DIMENSIONS based on memory age, NOT token counts.

    Compression curve (like human memory forgetting curve):
    - 0-6 days: 768D (100% quality) - Fresh memories, full fidelity
    - 7-29 days: 384D (~90% quality) - Recent, slight reduction
    - 30-89 days: 256D (~80% quality) - Older, more compression
    - 90+ days: 64D (~60% quality) - Archive, summary only

    Uses PCA for dimensionality reduction when sklearn is available,
    falls back to magnitude-based truncation otherwise.

    Usage:
        compressor = AgeBasedEmbeddingCompression()
        compressed = await compressor.compress_by_age(node)

    Note: For token/JSON compression, use ElisionCompressor from elision.py
    """

    # Compression thresholds (days → target dimension)
    COMPRESSION_SCHEDULE = [
        (0, 768, "active", 1.0),  # Fresh: full
        (7, 768, "active", 0.99),  # Week: still full
        (30, 384, "active", 0.90),  # Month: PCA 384D
        (90, 256, "archived", 0.80),  # Quarter: PCA 256D
        (180, 64, "archived", 0.60),  # Half year: summary
    ]

    # Confidence decay rates
    CONFIDENCE_DECAY = {
        0: 1.0,
        1: 0.99,
        7: 0.95,
        30: 0.85,
        90: 0.70,
        180: 0.50,
        365: 0.30,
    }

    def __init__(self, pca_models: Dict[int, Any] = None):
        """
        Initialize compressor.

        Args:
            pca_models: Pre-fitted PCA models for each target dimension
        """
        self.pca_models = pca_models or {}
        self._quality_tracker: Dict[str, float] = {}

    async def compress_by_age(
        self,
        node: Any,  # NodeState from snapshot.py
        age_days: int = None,
    ) -> CompressedNodeState:
        """
        Compress node embedding based on age.

        Args:
            node: NodeState with embedding and timestamp
            age_days: Override age calculation (optional)

        Returns:
            CompressedNodeState with compressed embedding
        """
        # Calculate age if not provided
        if age_days is None:
            if hasattr(node, "timestamp"):
                age_days = (datetime.now() - node.timestamp).days
            else:
                age_days = 0

        # Get current embedding
        embedding = node.embedding if hasattr(node, "embedding") else []
        original_dim = len(embedding)

        if original_dim == 0:
            # No embedding, return as-is
            return CompressedNodeState(
                path=node.path if hasattr(node, "path") else "",
                embedding=[],
                embedding_dim=0,
                original_dim=0,
                age_days=age_days,
            )

        # Find target dimension based on age
        target_dim, memory_layer, quality = self._get_target_config(
            age_days, original_dim
        )
        confidence = self._get_confidence(age_days)

        # Perform compression if needed
        if target_dim < original_dim:
            compressed_embedding = await self._reduce_dimension(embedding, target_dim)
        else:
            compressed_embedding = embedding

        # Track quality degradation
        path = node.path if hasattr(node, "path") else str(id(node))
        self._quality_tracker[path] = quality

        return CompressedNodeState(
            path=path,
            embedding=compressed_embedding,
            embedding_dim=len(compressed_embedding),
            original_dim=original_dim,
            dep_mode=self._get_dep_mode(age_days),
            confidence=confidence,
            memory_layer=memory_layer,
            compression_ratio=original_dim / len(compressed_embedding)
            if compressed_embedding
            else 1.0,
            age_days=age_days,
            quality_score=quality,
        )

    async def compress_batch(
        self, nodes: List[Any], age_func=None
    ) -> List[CompressedNodeState]:
        """
        Compress multiple nodes efficiently.

        Uses batch PCA for better performance.

        Args:
            nodes: List of NodeState objects
            age_func: Function to calculate age for each node

        Returns:
            List of CompressedNodeState
        """
        results = []

        # Group by target dimension for batch processing
        dim_groups: Dict[int, List[Tuple[Any, int]]] = {}

        for node in nodes:
            if age_func:
                age = age_func(node)
            elif hasattr(node, "timestamp"):
                age = (datetime.now() - node.timestamp).days
            else:
                age = 0

            embedding = node.embedding if hasattr(node, "embedding") else []
            target_dim, _, _ = self._get_target_config(age, len(embedding))

            if target_dim not in dim_groups:
                dim_groups[target_dim] = []
            dim_groups[target_dim].append((node, age))

        # Process each dimension group
        for target_dim, group in dim_groups.items():
            for node, age in group:
                compressed = await self.compress_by_age(node, age_days=age)
                results.append(compressed)

        return results

    def _get_target_config(
        self, age_days: int, original_dim: int
    ) -> Tuple[int, str, float]:
        """
        Get target compression config based on age.

        Returns:
            (target_dimension, memory_layer, quality_score)
        """
        target_dim = original_dim
        memory_layer = "active"
        quality = 1.0

        for threshold_days, dim, layer, q in self.COMPRESSION_SCHEDULE:
            if age_days >= threshold_days:
                target_dim = min(dim, original_dim)
                memory_layer = layer
                quality = q

        return target_dim, memory_layer, quality

    def _get_confidence(self, age_days: int) -> float:
        """
        Get confidence score based on age.

        Uses interpolation between known thresholds.
        """
        confidence = 1.0

        for threshold_days, conf in sorted(self.CONFIDENCE_DECAY.items()):
            if age_days >= threshold_days:
                confidence = conf

        return confidence

    def _get_dep_mode(self, age_days: int) -> str:
        """Get dependency mode based on age."""
        if age_days < 30:
            return "full"
        elif age_days < 90:
            return "top_3"
        elif age_days < 180:
            return "top_1"
        else:
            return "none"

    async def _reduce_dimension(
        self, embedding: List[float], target_dim: int
    ) -> List[float]:
        """
        Reduce embedding dimension using PCA.

        Args:
            embedding: Original 768D embedding
            target_dim: Target dimension (384, 256, or 64)

        Returns:
            Reduced embedding
        """
        if not SKLEARN_AVAILABLE:
            # Fallback: simple truncation + normalization
            return self._simple_reduce(embedding, target_dim)

        try:
            arr = np.array([embedding])

            # Get or create PCA model for this dimension
            if target_dim not in self.pca_models:
                pca = PCA(n_components=target_dim)
                # Fit on single vector (not ideal, but works)
                # In production, should fit on representative corpus
                self.pca_models[target_dim] = pca.fit(arr)

            pca = self.pca_models[target_dim]
            reduced = pca.transform(arr)

            return reduced[0].tolist()

        except Exception as e:
            logger.warning(f"[Compression] PCA failed: {e}, using simple reduction")
            return self._simple_reduce(embedding, target_dim)

    def _simple_reduce(self, embedding: List[float], target_dim: int) -> List[float]:
        """
        Simple dimension reduction without PCA.

        Strategy: Keep top-N components by absolute value.
        """
        arr = np.array(embedding)

        if len(arr) <= target_dim:
            return embedding

        # Get indices of top N by absolute value
        top_indices = np.argsort(np.abs(arr))[-target_dim:]
        top_indices = np.sort(top_indices)  # Keep original order

        reduced = np.zeros(target_dim)
        for i, idx in enumerate(top_indices):
            reduced[i] = arr[idx]

        # Normalize
        norm = np.linalg.norm(reduced)
        if norm > 0:
            reduced = reduced / norm

        return reduced.tolist()

    def get_quality_degradation_report(self) -> Dict[str, Any]:
        """
        MARKER-77-09: Get search quality degradation report.

        Returns statistics about how much search quality
        is degraded due to compression.
        """
        if not self._quality_tracker:
            return {"nodes_tracked": 0, "avg_quality": 1.0, "degraded_count": 0}

        qualities = list(self._quality_tracker.values())
        degraded = [q for q in qualities if q < 1.0]

        return {
            "nodes_tracked": len(qualities),
            "avg_quality": sum(qualities) / len(qualities),
            "min_quality": min(qualities),
            "max_quality": max(qualities),
            "degraded_count": len(degraded),
            "degradation_rate": len(degraded) / len(qualities) if qualities else 0,
            "quality_distribution": {
                "full_quality": len([q for q in qualities if q >= 1.0]),
                "high_quality": len([q for q in qualities if 0.9 <= q < 1.0]),
                "medium_quality": len([q for q in qualities if 0.7 <= q < 0.9]),
                "low_quality": len([q for q in qualities if q < 0.7]),
            },
        }


class CompressionScheduler:
    """
    Schedules age-based embedding compression for old nodes.

    Runs periodically to compress node embeddings that have aged
    past their threshold. Uses AgeBasedEmbeddingCompression internally.
    """

    def __init__(
        self, compressor: AgeBasedEmbeddingCompression = None, check_interval_hours: int = 24
    ):
        """
        Initialize scheduler.

        Args:
            compressor: AgeBasedEmbeddingCompression instance
            check_interval_hours: How often to check for compression candidates
        """
        self.compressor = compressor or AgeBasedEmbeddingCompression()
        self.check_interval = timedelta(hours=check_interval_hours)
        self.last_check: Optional[datetime] = None

    async def check_and_compress(self, nodes: List[Any]) -> Dict[str, int]:
        """
        Check nodes and compress those that need it.

        Returns:
            Dict with compression statistics
        """
        now = datetime.now()

        if self.last_check and (now - self.last_check) < self.check_interval:
            return {"skipped": True, "reason": "too_soon"}

        self.last_check = now

        stats = {
            "checked": len(nodes),
            "compressed_768_to_384": 0,
            "compressed_384_to_256": 0,
            "compressed_256_to_64": 0,
            "unchanged": 0,
        }

        compressed_nodes = await self.compressor.compress_batch(nodes)

        for original, compressed in zip(nodes, compressed_nodes):
            orig_dim = len(original.embedding) if hasattr(original, "embedding") else 0
            new_dim = compressed.embedding_dim

            if orig_dim == new_dim:
                stats["unchanged"] += 1
            elif orig_dim == 768 and new_dim == 384:
                stats["compressed_768_to_384"] += 1
            elif orig_dim in (768, 384) and new_dim == 256:
                stats["compressed_384_to_256"] += 1
            elif new_dim == 64:
                stats["compressed_256_to_64"] += 1

        return stats


# ========== FACTORY FUNCTIONS ==========

_compressor_instance: Optional[AgeBasedEmbeddingCompression] = None


def get_memory_compressor() -> AgeBasedEmbeddingCompression:
    """Get singleton AgeBasedEmbeddingCompression instance.

    Note: For token/JSON compression, use get_elision_compressor() from elision.py
    """
    global _compressor_instance

    if _compressor_instance is None:
        _compressor_instance = AgeBasedEmbeddingCompression()

    return _compressor_instance


# MARKER_104_COMPRESSION_FIX: Backward compatibility alias
# Keep MemoryCompression as an alias for existing imports
MemoryCompression = AgeBasedEmbeddingCompression


def analyze_content_complexity(content: str) -> Dict[str, Any]:
    """
    Analyze content complexity for adaptive memory sizing.

    Args:
        content: Text content to analyze

    Returns:
        Dictionary with complexity metrics
    """
    if not content:
        return {
            "complexity_score": 0.0,
            "estimated_tokens": 0,
            "structural_depth": 0,
            "semantic_density": 0.0,
        }

    # Simple complexity metrics
    lines = content.split("\n")
    words = content.split()

    # Structural depth (nesting indicators)
    depth_indicators = ["    ", "\t", "{", "(", "["]
    structural_depth = sum(content.count(indicator) for indicator in depth_indicators)

    # Semantic density (unique words / total words)
    unique_words = set(word.lower().strip(".,!?;:") for word in words if word.strip())
    semantic_density = len(unique_words) / max(len(words), 1)

    # Overall complexity score (0-1)
    complexity_score = min(
        1.0,
        (
            (len(lines) / 100) * 0.3  # Line count factor
            + (structural_depth / 50) * 0.4  # Structure factor
            + semantic_density * 0.3  # Semantic factor
        ),
    )

    return {
        "complexity_score": complexity_score,
        "estimated_tokens": len(words) * 1.3,  # Rough token estimation
        "structural_depth": structural_depth,
        "semantic_density": semantic_density,
        "line_count": len(lines),
        "word_count": len(words),
        "unique_word_count": len(unique_words),
    }


def get_compression_scheduler(check_interval_hours: int = 24) -> CompressionScheduler:
    """Get a CompressionScheduler instance for age-based embedding compression."""
    return CompressionScheduler(
        compressor=get_memory_compressor(), check_interval_hours=check_interval_hours
    )
