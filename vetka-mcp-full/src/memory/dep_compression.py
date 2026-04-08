"""
VETKA Phase 77.5 - DEP Graph Compression
Age-based dependency graph compression

@file dep_compression.py
@status ACTIVE
@phase Phase 77.5 - Memory Sync Protocol
@calledBy MemorySyncEngine, CompressionScheduler
@lastAudit 2026-01-20

DEP compression strategy:
- Fresh (<30 days): Full dependencies (all edges)
- Old (30-90 days): Top-3 dependencies only
- Archive (>90 days): Top-1 dependency only
- Ancient (>180 days): No dependencies (lazy recompute on access)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CompressedDEP:
    """
    Compressed dependency information for a node.
    """
    node_path: str
    edges: List[Dict[str, Any]]  # Kept edges with DEP scores
    dep_mode: Literal['full', 'top_3', 'top_1', 'none']
    original_edge_count: int
    compressed_edge_count: int
    compression_ratio: float
    age_days: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'node_path': self.node_path,
            'edges': self.edges,
            'dep_mode': self.dep_mode,
            'original_edge_count': self.original_edge_count,
            'compressed_edge_count': self.compressed_edge_count,
            'compression_ratio': self.compression_ratio,
            'age_days': self.age_days
        }


class DEPCompression:
    """
    Compresses dependency graph based on node age.

    Strategy:
    - Fresh: Keep all dependencies (for accurate layout)
    - Old: Keep only strongest connections (for memory efficiency)
    - Archive: Keep only primary dependency (minimal footprint)
    - Ancient: No stored deps (recompute on demand)

    Usage:
        compressor = DEPCompression()
        compressed = await compressor.compress_dep_graph(node, edges, age_days=45)
    """

    # Age thresholds for dependency compression
    AGE_THRESHOLDS = {
        'full': 30,     # < 30 days: keep all
        'top_3': 90,    # 30-90 days: top 3
        'top_1': 180,   # 90-180 days: top 1
        'none': 365     # > 180 days: none (lazy recompute)
    }

    def __init__(
        self,
        min_dep_score: float = 0.3
    ):
        """
        Initialize DEP compressor.

        Args:
            min_dep_score: Minimum DEP score to keep edge (below this, discard)
        """
        self.min_dep_score = min_dep_score

    async def compress_dep_graph(
        self,
        node_path: str,
        edges: List[Dict[str, Any]],
        age_days: int
    ) -> CompressedDEP:
        """
        Compress dependencies for a node based on age.

        Args:
            node_path: Path of the node
            edges: List of edge dicts with 'source', 'target', 'dep_score'
            age_days: Age of the node in days

        Returns:
            CompressedDEP with filtered edges
        """
        original_count = len(edges)

        # Determine compression mode
        dep_mode = self._get_dep_mode(age_days)

        # Filter and sort edges
        filtered_edges = self._filter_edges(edges, node_path)
        sorted_edges = sorted(
            filtered_edges,
            key=lambda e: e.get('dep_score', 0),
            reverse=True
        )

        # Apply compression
        if dep_mode == 'full':
            kept_edges = sorted_edges
        elif dep_mode == 'top_3':
            kept_edges = sorted_edges[:3]
        elif dep_mode == 'top_1':
            kept_edges = sorted_edges[:1] if sorted_edges else []
        else:  # 'none'
            kept_edges = []

        compressed_count = len(kept_edges)
        ratio = original_count / compressed_count if compressed_count > 0 else float('inf')

        logger.debug(
            f"[DEPCompression] {node_path}: {original_count}→{compressed_count} edges "
            f"(mode={dep_mode}, age={age_days}d)"
        )

        return CompressedDEP(
            node_path=node_path,
            edges=kept_edges,
            dep_mode=dep_mode,
            original_edge_count=original_count,
            compressed_edge_count=compressed_count,
            compression_ratio=ratio,
            age_days=age_days
        )

    async def compress_batch(
        self,
        node_edges: Dict[str, List[Dict[str, Any]]],
        age_func
    ) -> Dict[str, CompressedDEP]:
        """
        Compress dependencies for multiple nodes.

        Args:
            node_edges: Dict mapping node_path to list of edges
            age_func: Function(node_path) → age_days

        Returns:
            Dict mapping node_path to CompressedDEP
        """
        results = {}

        for node_path, edges in node_edges.items():
            age_days = age_func(node_path)
            compressed = await self.compress_dep_graph(node_path, edges, age_days)
            results[node_path] = compressed

        return results

    def _get_dep_mode(self, age_days: int) -> str:
        """
        Determine dependency mode based on age.
        """
        if age_days < self.AGE_THRESHOLDS['full']:
            return 'full'
        elif age_days < self.AGE_THRESHOLDS['top_3']:
            return 'top_3'
        elif age_days < self.AGE_THRESHOLDS['top_1']:
            return 'top_1'
        else:
            return 'none'

    def _filter_edges(
        self,
        edges: List[Dict[str, Any]],
        node_path: str
    ) -> List[Dict[str, Any]]:
        """
        Filter edges by minimum score and relevance.
        """
        filtered = []

        for edge in edges:
            # Check if edge involves this node
            if edge.get('source') != node_path and edge.get('target') != node_path:
                continue

            # Check minimum score
            score = edge.get('dep_score', 0)
            if score < self.min_dep_score:
                continue

            filtered.append(edge)

        return filtered

    async def lazy_recompute_dep(
        self,
        node_path: str,
        all_nodes: List[Any],
        embedding_model=None
    ) -> List[Dict[str, Any]]:
        """
        Recompute dependencies on-demand for archived nodes.

        Called when user accesses an archived node that has
        dep_mode='none'. Performs fast DEP calculation.

        Args:
            node_path: Path of node to recompute deps for
            all_nodes: List of all nodes for comparison
            embedding_model: Model for similarity calculation

        Returns:
            List of recomputed edges
        """
        logger.info(f"[DEPCompression] Lazy recompute for {node_path}")

        # Find the target node
        target_node = None
        for node in all_nodes:
            if hasattr(node, 'path') and node.path == node_path:
                target_node = node
                break

        if not target_node:
            return []

        # Quick DEP calculation (simplified)
        edges = []
        target_embedding = target_node.embedding if hasattr(target_node, 'embedding') else None

        if not target_embedding:
            return []

        import numpy as np

        target_vec = np.array(target_embedding)

        for node in all_nodes:
            if node.path == node_path:
                continue

            if not hasattr(node, 'embedding') or not node.embedding:
                continue

            # Calculate cosine similarity
            other_vec = np.array(node.embedding)

            # Ensure same dimension
            if len(target_vec) != len(other_vec):
                continue

            similarity = np.dot(target_vec, other_vec) / (
                np.linalg.norm(target_vec) * np.linalg.norm(other_vec) + 1e-8
            )

            # Only keep high similarity edges
            if similarity > 0.5:
                edges.append({
                    'source': node.path,
                    'target': node_path,
                    'dep_score': float(similarity),
                    'type': 'semantic_lazy'
                })

        # Sort by score and keep top 3
        edges.sort(key=lambda e: e['dep_score'], reverse=True)
        return edges[:3]


class DEPCompressionStats:
    """
    Tracks DEP compression statistics.
    """

    def __init__(self):
        self.total_original_edges = 0
        self.total_compressed_edges = 0
        self.nodes_by_mode: Dict[str, int] = {
            'full': 0,
            'top_3': 0,
            'top_1': 0,
            'none': 0
        }

    def record(self, compressed: CompressedDEP):
        """Record compression result."""
        self.total_original_edges += compressed.original_edge_count
        self.total_compressed_edges += compressed.compressed_edge_count
        self.nodes_by_mode[compressed.dep_mode] = \
            self.nodes_by_mode.get(compressed.dep_mode, 0) + 1

    def get_report(self) -> Dict[str, Any]:
        """Get compression statistics report."""
        total_nodes = sum(self.nodes_by_mode.values())
        avg_ratio = (
            self.total_original_edges / self.total_compressed_edges
            if self.total_compressed_edges > 0
            else 0
        )

        return {
            'total_nodes': total_nodes,
            'total_original_edges': self.total_original_edges,
            'total_compressed_edges': self.total_compressed_edges,
            'average_compression_ratio': round(avg_ratio, 2),
            'edges_saved': self.total_original_edges - self.total_compressed_edges,
            'nodes_by_mode': self.nodes_by_mode
        }


# ========== FACTORY FUNCTIONS ==========

_dep_compressor_instance: Optional[DEPCompression] = None


def get_dep_compressor(min_dep_score: float = 0.3) -> DEPCompression:
    """Get singleton DEPCompression instance."""
    global _dep_compressor_instance

    if _dep_compressor_instance is None:
        _dep_compressor_instance = DEPCompression(min_dep_score=min_dep_score)

    return _dep_compressor_instance
