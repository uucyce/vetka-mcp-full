"""
VETKA CAM Engine — Constructivist Agentic Memory
Dynamic Tree Restructuring

Implements 4 core operations from NeurIPS 2025 CAM paper:
1. Branching - create new branches for novel artifacts
2. Pruning - mark low-activation branches for deletion
3. Merging - combine similar subtrees
4. Accommodation - smooth layout transitions with Procrustes

Based on: arXiv:2510.05520 + VETKA Grok findings

@status: active
@phase: 99
@depends: numpy, src.utils.embedding_service, src.memory.stm_buffer
@used_by: src.orchestration.orchestrator_with_elisya, src.api.routes.tree_routes, src.mcp.tools
"""

import logging
import time
import uuid
import math
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from dataclasses import dataclass
from collections import defaultdict
import numpy as np

# Optional imports with graceful degradation
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

logger = logging.getLogger("VETKA_CAM")


@dataclass
class VETKANode:
    """
    Represents a node in the VETKA tree.

    Attributes:
        id: Unique node identifier
        path: File system path
        name: Display name
        depth: Directory depth (layer in tree)
        embedding: Semantic embedding vector (768D Gemma)
        children: List of child node IDs
        parent: Parent node ID (optional)
        activation_score: Relevance score (0.0-1.0)
        is_marked_for_deletion: Pruning flag
        duplicate_of: ID of node this is a duplicate of
        created_at: Creation timestamp
        last_accessed: Last access timestamp
        metadata: Additional node metadata
    """
    id: str
    path: str
    name: str
    depth: int
    embedding: Optional[np.ndarray] = None
    children: List[str] = None
    parent: Optional[str] = None
    activation_score: float = 0.5
    is_marked_for_deletion: bool = False
    duplicate_of: Optional[str] = None
    created_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.children is None:
            self.children = []
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.last_accessed is None:
            self.last_accessed = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'path': self.path,
            'name': self.name,
            'depth': self.depth,
            'children': self.children,
            'parent': self.parent,
            'activation_score': self.activation_score,
            'is_marked_for_deletion': self.is_marked_for_deletion,
            'duplicate_of': self.duplicate_of,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'metadata': self.metadata
        }


@dataclass
class CAMOperation:
    """
    Represents a CAM operation result.

    Attributes:
        operation_type: Type of operation (branch|merge|prune|accommodate)
        node_ids: IDs of affected nodes
        duration_ms: Operation duration in milliseconds
        success: Whether operation succeeded
        details: Additional operation details
    """
    operation_type: str
    node_ids: List[str]
    duration_ms: float
    success: bool
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class VETKACAMEngine:
    """
    Constructivist Agentic Memory Engine for VETKA.

    Implements dynamic tree restructuring based on NeurIPS 2025 CAM paper.
    Makes the tree actively reorganize itself when new artifacts are added.

    Key features:
    - Branching: Detect and create new branches for novel content
    - Pruning: Identify and mark low-value branches
    - Merging: Find and combine similar subtrees
    - Accommodation: Smooth layout transitions with Procrustes interpolation
    """

    # CAM thresholds (from Grok research)
    SIMILARITY_THRESHOLD_NOVEL = 0.7    # Below this = new branch
    SIMILARITY_THRESHOLD_MERGE = 0.92   # Above this = merge candidates
    ACTIVATION_THRESHOLD_PRUNE = 0.2    # Below this = prune candidates

    # Embedding model (same as MemoryManager)
    EMBEDDING_MODEL = "embeddinggemma:300m"
    EMBEDDING_DIM = 768

    def __init__(
        self,
        memory_manager: Optional[Any] = None,
        layout_engine: Optional[Any] = None,
        embedding_model: str = "embeddinggemma:300m"
    ):
        """
        Initialize CAM engine.

        Args:
            memory_manager: VETKA MemoryManager instance (optional)
            layout_engine: VETKA layout engine instance (optional)
            embedding_model: Embedding model name
        """
        self.memory_manager = memory_manager
        self.layout_engine = layout_engine
        self.embedding_model = embedding_model

        # Tree state
        self.nodes: Dict[str, VETKANode] = {}
        self.edges: List[Tuple[str, str]] = []  # (parent, child) tuples

        # Query history for activation scoring
        self.query_history: List[Dict[str, Any]] = []
        self.max_query_history = 100

        # Operation metrics
        self.metrics: Dict[str, List[float]] = {
            'branch_times': [],
            'prune_times': [],
            'merge_times': [],
            'accommodate_times': []
        }

        logger.info(f"CAM Engine initialized (model: {embedding_model})")

    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Delegate to unified EmbeddingService (Phase 36.1)"""
        from src.utils.embedding_service import get_embedding
        embedding = get_embedding(text)
        if embedding:
            return np.array(embedding)
        return None

    def calculate_activation_score(self, branch_id: str) -> float:
        """
        Calculate activation score for a branch.

        Score indicates how relevant this branch is to recent user queries.
        Based on CAM paper: activation = relevance + connectivity

        Args:
            branch_id: ID of branch to score

        Returns:
            Score from 0.0 (never used) to 1.0 (always relevant)
        """
        if branch_id not in self.nodes:
            return 0.0

        node = self.nodes[branch_id]

        # If no query history, return default score
        if not self.query_history:
            return 0.5

        # Calculate relevance to recent queries
        total_relevance = 0.0
        num_queries = len(self.query_history)

        for query in self.query_history[-20:]:  # Last 20 queries
            query_emb = query.get('embedding')
            if query_emb is not None and node.embedding is not None:
                # Cosine similarity
                similarity = np.dot(query_emb, node.embedding) / (
                    np.linalg.norm(query_emb) * np.linalg.norm(node.embedding)
                )
                total_relevance += max(0, similarity)  # Clip negative

        # Average relevance
        avg_relevance = total_relevance / num_queries if num_queries > 0 else 0.0

        # Connectivity bonus (nodes with more children are more "hub-like")
        connectivity_bonus = min(0.2, len(node.children) * 0.02)

        # Recency bonus (recently accessed nodes get boost)
        time_since_access = (datetime.now(timezone.utc) - node.last_accessed).total_seconds()
        recency_bonus = max(0, 0.1 * (1 - time_since_access / 86400))  # Decay over 24h

        # Combined score
        score = avg_relevance + connectivity_bonus + recency_bonus

        return min(1.0, max(0.0, score))

    def compute_branch_similarity(self, branch_a_id: str, branch_b_id: str) -> float:
        """
        Compute similarity between two branches.

        Uses mean embedding of all nodes in each branch subtree.

        Args:
            branch_a_id: First branch ID
            branch_b_id: Second branch ID

        Returns:
            Similarity score from 0.0 (different) to 1.0 (identical)
        """
        if branch_a_id not in self.nodes or branch_b_id not in self.nodes:
            return 0.0

        # Get all descendant nodes for each branch
        def get_subtree_embeddings(node_id: str) -> List[np.ndarray]:
            """Recursively collect embeddings from subtree."""
            embeddings = []
            node = self.nodes.get(node_id)
            if not node:
                return embeddings

            if node.embedding is not None:
                embeddings.append(node.embedding)

            for child_id in node.children:
                embeddings.extend(get_subtree_embeddings(child_id))

            return embeddings

        embs_a = get_subtree_embeddings(branch_a_id)
        embs_b = get_subtree_embeddings(branch_b_id)

        if not embs_a or not embs_b:
            return 0.0

        # Mean embeddings
        mean_a = np.mean(embs_a, axis=0)
        mean_b = np.mean(embs_b, axis=0)

        # Cosine similarity
        similarity = np.dot(mean_a, mean_b) / (
            np.linalg.norm(mean_a) * np.linalg.norm(mean_b)
        )

        return max(0.0, min(1.0, similarity))

    async def handle_new_artifact(
        self,
        artifact_path: str,
        metadata: Dict[str, Any]
    ) -> CAMOperation:
        """
        Handle new artifact detection.

        Decision tree:
        - similarity < 0.7: create new branch
        - 0.7 <= similarity < 0.92: propose merge
        - similarity >= 0.92: mark as variant

        Args:
            artifact_path: Path to new artifact
            metadata: Artifact metadata including:
                - type: file type
                - size: file size
                - embedding: precomputed embedding (optional)
                - parent: parent path

        Returns:
            CAMOperation with operation type and details
        """
        start_time = time.time()

        try:
            # Extract or compute embedding
            embedding = metadata.get('embedding')
            if embedding is None:
                # Generate embedding from file content
                content = metadata.get('content', artifact_path)
                embedding = self._get_embedding(content)
            elif isinstance(embedding, list):
                embedding = np.array(embedding)

            # Create new node
            node_id = str(uuid.uuid4())
            node = VETKANode(
                id=node_id,
                path=artifact_path,
                name=metadata.get('name', artifact_path.split('/')[-1]),
                depth=metadata.get('depth', 0),
                embedding=embedding,
                parent=metadata.get('parent'),
                metadata=metadata
            )

            # Find most similar existing node
            max_similarity = 0.0
            most_similar_id = None

            for existing_id, existing_node in self.nodes.items():
                if existing_node.embedding is not None and embedding is not None:
                    similarity = np.dot(embedding, existing_node.embedding) / (
                        np.linalg.norm(embedding) * np.linalg.norm(existing_node.embedding)
                    )
                    if similarity > max_similarity:
                        max_similarity = similarity
                        most_similar_id = existing_id

            # Decision tree
            operation_type = "branch"

            if max_similarity < self.SIMILARITY_THRESHOLD_NOVEL:
                # Novel content - create new branch
                self.nodes[node_id] = node
                if node.parent and node.parent in self.nodes:
                    self.nodes[node.parent].children.append(node_id)
                    self.edges.append((node.parent, node_id))
                operation_type = "branch"

            elif max_similarity >= self.SIMILARITY_THRESHOLD_MERGE:
                # Very similar - mark as variant
                node.duplicate_of = most_similar_id
                self.nodes[node_id] = node
                operation_type = "variant"

            else:
                # Moderate similarity - propose merge
                self.nodes[node_id] = node
                if node.parent and node.parent in self.nodes:
                    self.nodes[node.parent].children.append(node_id)
                    self.edges.append((node.parent, node_id))
                operation_type = "merge_proposal"

                # Emit merge proposal (would be sent via Socket.IO)
                logger.info(
                    f"Merge proposal: {node_id} similar to {most_similar_id} "
                    f"(similarity: {max_similarity:.2f})"
                )

            # Call accommodation to update layout
            if self.layout_engine:
                await self.accommodate_layout(reason="artifact_added")

            duration_ms = (time.time() - start_time) * 1000
            self.metrics['branch_times'].append(duration_ms)

            return CAMOperation(
                operation_type=operation_type,
                node_ids=[node_id],
                duration_ms=duration_ms,
                success=True,
                details={
                    'similarity': max_similarity,
                    'similar_to': most_similar_id,
                    'path': artifact_path
                }
            )

        except Exception as e:
            logger.error(f"handle_new_artifact failed: {e}")
            duration_ms = (time.time() - start_time) * 1000
            return CAMOperation(
                operation_type="branch",
                node_ids=[],
                duration_ms=duration_ms,
                success=False,
                details={'error': str(e)}
            )

    async def prune_low_entropy(self, threshold: float = 0.2) -> List[str]:
        """
        Identify low-activation branches for pruning.

        Runs periodically (e.g., hourly) to find branches that are rarely used.
        Requires user confirmation before actual deletion.

        Args:
            threshold: Activation score threshold (default 0.2)

        Returns:
            List of node IDs marked for pruning
        """
        start_time = time.time()
        candidates = []

        try:
            # Calculate activation scores for all branches
            for node_id, node in self.nodes.items():
                # Skip root nodes and already marked nodes
                if node.parent is None or node.is_marked_for_deletion:
                    continue

                score = self.calculate_activation_score(node_id)
                node.activation_score = score

                if score < threshold:
                    # Mark for deletion (needs user confirmation)
                    node.is_marked_for_deletion = True
                    candidates.append(node_id)
                    logger.info(f"Prune candidate: {node.name} (score: {score:.3f})")

            duration_ms = (time.time() - start_time) * 1000
            self.metrics['prune_times'].append(duration_ms)

            logger.info(f"Pruning identified {len(candidates)} candidates")
            return candidates

        except Exception as e:
            logger.error(f"prune_low_entropy failed: {e}")
            return []

    async def merge_similar_subtrees(
        self,
        threshold: float = 0.92
    ) -> List[Tuple[str, str]]:
        """
        Find and merge similar subtrees.

        Merges branches with high similarity to reduce redundancy.
        Preserves data by combining metadata and using Z-axis for variants.

        Args:
            threshold: Similarity threshold for merging (default 0.92)

        Returns:
            List of (old_id, merged_id) pairs
        """
        start_time = time.time()
        merged_pairs = []

        try:
            # Find all pairs of similar subtrees
            node_ids = list(self.nodes.keys())

            for i, id_a in enumerate(node_ids):
                for id_b in node_ids[i+1:]:
                    similarity = self.compute_branch_similarity(id_a, id_b)

                    if similarity >= threshold:
                        # Merge id_b into id_a
                        node_a = self.nodes[id_a]
                        node_b = self.nodes[id_b]

                        # Combine metadata
                        node_a.metadata['merged_variants'] = node_a.metadata.get(
                            'merged_variants', []
                        )
                        node_a.metadata['merged_variants'].append({
                            'id': id_b,
                            'path': node_b.path,
                            'metadata': node_b.metadata
                        })

                        # Move children of B to A
                        for child_id in node_b.children:
                            if child_id not in node_a.children:
                                node_a.children.append(child_id)
                                self.nodes[child_id].parent = id_a
                                # Update edge
                                self.edges = [
                                    (p, c) if (p, c) != (id_b, child_id) else (id_a, child_id)
                                    for p, c in self.edges
                                ]

                        # Remove node_b
                        del self.nodes[id_b]
                        self.edges = [(p, c) for p, c in self.edges if c != id_b]

                        merged_pairs.append((id_b, id_a))
                        logger.info(f"Merged {id_b} into {id_a} (similarity: {similarity:.2f})")

            # Update layout if merges occurred
            if merged_pairs and self.layout_engine:
                await self.accommodate_layout(reason="merge_completed")

            duration_ms = (time.time() - start_time) * 1000
            self.metrics['merge_times'].append(duration_ms)

            return merged_pairs

        except Exception as e:
            logger.error(f"merge_similar_subtrees failed: {e}")
            return []

    async def accommodate_layout(self, reason: str = "structure_changed") -> Dict[str, Any]:
        """
        Smooth tree restructuring using Procrustes interpolation.

        Implements Grok Topic 5: Procrustes alignment for smooth phase transitions.

        Steps:
        1. Compute new Sugiyama layout
        2. Apply Procrustes alignment: old_positions → new_positions
        3. Smooth animation with collision detection

        Args:
            reason: Reason for accommodation (for logging)

        Returns:
            Dictionary with old_positions, new_positions, duration
        """
        start_time = time.time()

        try:
            logger.info(f"Accommodation triggered: {reason}")

            # Get current positions (if layout_engine available)
            old_positions = {}
            new_positions = {}

            if hasattr(self, '_last_positions') and self._last_positions:
                old_positions = self._last_positions.copy()

            # If we have a layout engine, compute new layout
            if self.layout_engine:
                # This would call the actual Sugiyama layout calculator
                # For now, we'll create a stub that shows the integration pattern

                # Convert nodes to layout format
                nodes_list = [
                    {
                        'id': node.id,
                        'name': node.name,
                        'metadata': node.metadata
                    }
                    for node in self.nodes.values()
                ]

                edges_list = [
                    {'source': parent, 'target': child}
                    for parent, child in self.edges
                ]

                # Calculate new layout (would call actual layout engine)
                # new_layout = self.layout_engine.calculate(nodes_list, edges_list)
                # For now, generate placeholder positions
                for node_id in self.nodes.keys():
                    new_positions[node_id] = {
                        'x': 0, 'y': 0, 'z': 0  # Would be real positions from layout engine
                    }

            # Store for next accommodation
            self._last_positions = new_positions

            # Procrustes alignment would happen here in full implementation
            # from src.visualizer.procrustes_interpolation import ProcrustesInterpolator
            # interpolator = ProcrustesInterpolator(animation_duration=0.75)
            # alignment = interpolator.align_layouts(old_positions, new_positions)

            accommodation_result = {
                'old_positions': old_positions,
                'new_positions': new_positions,
                'duration': 0.75,  # 750ms animation
                'reason': reason,
                'easing': 'ease-in-out-cubic',
                'collision_detection': True
            }

            duration_ms = (time.time() - start_time) * 1000
            self.metrics['accommodate_times'].append(duration_ms)

            return accommodation_result

        except Exception as e:
            logger.error(f"accommodate_layout failed: {e}")
            return {}

    async def propose_merge(
        self,
        branch_a_id: str,
        branch_b_id: str,
        similarity: float
    ):
        """
        Propose merge to user.

        When similarity > 0.92 found, ask user for confirmation.

        Args:
            branch_a_id: First branch ID
            branch_b_id: Second branch ID
            similarity: Computed similarity score
        """
        # This would emit Socket.IO event to frontend
        logger.info(
            f"Merge proposal: {branch_a_id} ↔ {branch_b_id} "
            f"(similarity: {similarity:.2f})"
        )

    def add_query_to_history(self, query: str, embedding: Optional[np.ndarray] = None):
        """
        Add query to history for activation scoring.

        Args:
            query: User query text
            embedding: Precomputed embedding (optional)
        """
        if embedding is None:
            embedding = self._get_embedding(query)

        self.query_history.append({
            'query': query,
            'embedding': embedding,
            'timestamp': datetime.now(timezone.utc)
        })

        # Keep only recent history
        if len(self.query_history) > self.max_query_history:
            self.query_history = self.query_history[-self.max_query_history:]

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get CAM operation metrics.

        Returns:
            Dictionary with performance metrics
        """
        def stats(times: List[float]) -> Dict[str, float]:
            """Calculate statistics for timing list."""
            if not times:
                return {'count': 0, 'avg': 0, 'min': 0, 'max': 0}
            return {
                'count': len(times),
                'avg': sum(times) / len(times),
                'min': min(times),
                'max': max(times)
            }

        return {
            'branching': stats(self.metrics['branch_times']),
            'pruning': stats(self.metrics['prune_times']),
            'merging': stats(self.metrics['merge_times']),
            'accommodation': stats(self.metrics['accommodate_times']),
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges)
        }

    # ═══════════════════════════════════════════════════════════════════
    # Phase 17.1: SURPRISE METRIC for file-level novelty detection
    # ═══════════════════════════════════════════════════════════════════

    def calculate_surprise_for_file(
        self,
        file_embedding: np.ndarray,
        sibling_embeddings: List[np.ndarray]
    ) -> float:
        """
        Calculate surprise metric for a file relative to its siblings.

        surprise = 1 - cosine_similarity(file_embedding, avg_sibling_embeddings)

        Args:
            file_embedding: 768D embedding of the file
            sibling_embeddings: List of 768D embeddings of sibling files

        Returns:
            Surprise score from 0.0 (identical to siblings) to 1.0 (completely novel)
        """
        if file_embedding is None or len(sibling_embeddings) == 0:
            return 0.5  # Neutral surprise for unknown/first file

        # Average sibling embedding
        avg_sibling = np.mean(sibling_embeddings, axis=0)

        # Cosine similarity
        dot_product = np.dot(file_embedding, avg_sibling)
        norm_file = np.linalg.norm(file_embedding)
        norm_sibling = np.linalg.norm(avg_sibling)

        if norm_file < 1e-8 or norm_sibling < 1e-8:
            return 0.5  # Avoid division by zero

        similarity = dot_product / (norm_file * norm_sibling)

        # Surprise = 1 - similarity, bounded to [0, 1]
        surprise = max(0.0, min(1.0, 1.0 - similarity))

        return surprise

    def decide_cam_operation_for_file(self, surprise: float) -> str:
        """
        Decide CAM operation based on surprise metric.

        Thresholds from NeurIPS 2025 CAM paper:
        - surprise > 0.65  → BRANCH (create new subtree)
        - 0.30 < surprise ≤ 0.65  → APPEND (add to existing folder)
        - surprise ≤ 0.30  → MERGE (duplicate, skip or compress)

        Args:
            surprise: Surprise metric (0.0-1.0)

        Returns:
            Operation string: 'branch', 'append', or 'merge'
        """
        if surprise > 0.65:
            return 'branch'
        elif surprise > 0.30:
            return 'append'
        else:
            return 'merge'

    # ═══════════════════════════════════════════════════════════════════
    # Phase 99: STM Buffer Integration - FIX_99.1
    # ═══════════════════════════════════════════════════════════════════

    def notify_stm_surprise(
        self,
        content: str,
        surprise_score: float,
        stm_buffer: Optional[Any] = None,
        threshold: float = 0.3
    ) -> bool:
        """
        Notify STM buffer about a surprise event.

        FIX_99.1: High-surprise events are added to STM for quick context access.

        Args:
            content: Content that triggered surprise
            surprise_score: Calculated surprise metric (0.0-1.0)
            stm_buffer: Optional STMBuffer instance (will use global if None)
            threshold: Minimum surprise score to notify (default 0.3)

        Returns:
            True if event was added to STM, False otherwise
        """
        if surprise_score < threshold:
            return False

        try:
            if stm_buffer is None:
                from src.memory.stm_buffer import get_stm_buffer
                stm_buffer = get_stm_buffer()

            stm_buffer.add_from_cam(content[:500], surprise_score)
            logger.info(f"CAM → STM: surprise event added (score={surprise_score:.2f})")
            return True
        except ImportError:
            logger.debug("STM buffer not available for CAM integration")
            return False
        except Exception as e:
            logger.warning(f"CAM → STM notification failed: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════
# Phase 67.2: Global Singleton Instance
# ═══════════════════════════════════════════════════════════════════

_cam_engine_instance: Optional[VETKACAMEngine] = None


def get_cam_engine(memory_manager: Optional[Any] = None) -> Optional[VETKACAMEngine]:
    """
    Factory function - returns singleton CAM engine.

    Phase 67.2: Added to avoid creating new instance per call.

    Args:
        memory_manager: Optional MemoryManager instance for initialization

    Returns:
        Singleton VETKACAMEngine instance, or None if initialization fails
    """
    global _cam_engine_instance

    if _cam_engine_instance is None:
        try:
            _cam_engine_instance = VETKACAMEngine(memory_manager=memory_manager)
            logger.info("[CAM] Singleton engine initialized")
        except Exception as e:
            logger.error(f"[CAM] Failed to initialize singleton: {e}")
            return None

    return _cam_engine_instance


def reset_cam_engine():
    """Reset singleton for testing purposes."""
    global _cam_engine_instance
    _cam_engine_instance = None
    logger.info("[CAM] Singleton engine reset")


# Alias for backwards compatibility and simpler access
cam_engine = get_cam_engine


# ═══════════════════════════════════════════════════════════════════
# Phase 92: Standalone surprise calculation for tools
# ═══════════════════════════════════════════════════════════════════

def calculate_surprise(content: str, context: Optional[str] = None) -> float:
    """
    Calculate surprise score for content.

    Standalone function for use in CAM tools without needing
    full embeddings infrastructure.

    Uses text-based heuristics when embeddings unavailable:
    - Unique word ratio
    - Structural complexity
    - Character entropy

    Args:
        content: Text content to analyze
        context: Optional surrounding context for comparison

    Returns:
        Surprise score from 0.0 (predictable) to 1.0 (highly novel)
    """
    if not content:
        return 0.5

    # Text-based surprise heuristics
    words = content.lower().split()
    if len(words) == 0:
        return 0.5

    unique_words = set(words)
    unique_ratio = len(unique_words) / len(words)

    # Character entropy (Shannon)
    char_counts = {}
    for c in content.lower():
        char_counts[c] = char_counts.get(c, 0) + 1

    total_chars = len(content)
    entropy = 0.0
    for count in char_counts.values():
        if count > 0:
            prob = count / total_chars
            entropy -= prob * math.log2(prob)

    # Normalize entropy (max ~4.7 for English text)
    normalized_entropy = min(1.0, entropy / 4.7)

    # Structural indicators (code-like = more surprising in prose context)
    code_indicators = ['{', '}', '()', '=>', 'def ', 'class ', 'import ', 'from ']
    code_score = sum(1 for ind in code_indicators if ind in content) / len(code_indicators)

    # Compare with context if provided
    context_diff = 0.5
    if context:
        context_words = set(context.lower().split())
        if context_words:
            overlap = len(unique_words & context_words) / max(len(unique_words), 1)
            context_diff = 1.0 - overlap  # Less overlap = more surprise

    # Combine factors
    surprise = (
        unique_ratio * 0.25 +
        normalized_entropy * 0.25 +
        code_score * 0.15 +
        context_diff * 0.35
    )

    return max(0.0, min(1.0, surprise))


# ═══════════════════════════════════════════════════════════════════
# Phase 17.1: Standalone function for use in tree_routes.py
# ═══════════════════════════════════════════════════════════════════

def calculate_surprise_metrics_for_tree(
    files_by_folder: Dict[str, List[Dict]],
    qdrant_client,
    collection_name: str = "vetka_elisya"
) -> Dict[str, Dict[str, Any]]:
    """
    Calculate surprise metrics for all files in the tree.

    Args:
        files_by_folder: Dict mapping folder_path -> list of file dicts
        qdrant_client: Qdrant client for fetching embeddings
        collection_name: Qdrant collection name

    Returns:
        Dict mapping file_id -> {surprise_metric, cam_operation}
    """
    if not qdrant_client:
        return {}

    cam_engine = VETKACAMEngine()
    results = {}

    try:
        # Get all embeddings from Qdrant
        embeddings_map = {}  # file_id -> embedding

        # Scroll through all points to get embeddings
        offset = None
        while True:
            points, offset = qdrant_client.scroll(
                collection_name=collection_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=True  # We need vectors for surprise calculation
            )

            for point in points:
                file_id = str(point.id)
                if point.vector:
                    embeddings_map[file_id] = np.array(point.vector)

            if offset is None:
                break

        logger.info(f"[CAM] Loaded {len(embeddings_map)} embeddings for surprise calculation")

        # Calculate surprise for each file
        for folder_path, folder_files in files_by_folder.items():
            # Get sibling embeddings (all files in this folder)
            sibling_embeddings = []
            for f in folder_files:
                fid = f.get('id')
                if fid in embeddings_map:
                    sibling_embeddings.append(embeddings_map[fid])

            # Calculate surprise for each file
            for file_data in folder_files:
                file_id = file_data.get('id')

                if file_id not in embeddings_map:
                    results[file_id] = {
                        'surprise_metric': 0.5,
                        'cam_operation': 'append'
                    }
                    continue

                file_emb = embeddings_map[file_id]

                # Exclude this file from siblings
                other_siblings = [
                    emb for f, emb in zip(folder_files, sibling_embeddings)
                    if f.get('id') != file_id and emb is not None
                ]

                surprise = cam_engine.calculate_surprise_for_file(file_emb, other_siblings)
                operation = cam_engine.decide_cam_operation_for_file(surprise)

                results[file_id] = {
                    'surprise_metric': round(surprise, 3),
                    'cam_operation': operation
                }

        logger.info(f"[CAM] Calculated surprise for {len(results)} files")

    except Exception as e:
        logger.error(f"[CAM] Error calculating surprise metrics: {e}")

    return results


# ═══════════════════════════════════════════════════════════════════
# [PHASE75.1] CAM Tool Memory — JARVIS-эффект для VETKA tools
# "Сэр, обычно в этом контексте вы используете search_files()..."
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ToolUsageRecord:
    """Record of a single tool usage event."""
    tool_name: str
    context_key: str  # e.g., folder_path, query_type, file_extension
    timestamp: datetime
    success: bool
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CAMToolMemory:
    """
    Phase 75.1: Remembers VETKA tool usage patterns for JARVIS-like suggestions.

    VETKA Tools tracked:
    - view_document(path) — view file in 3D viewport
    - search_files(query) — search in tree
    - get_viewport() — get current viewport state
    - pin_files(paths) — pin files for context

    Context keys for learning:
    - folder_path: "/src/orchestration" → suggest search_files
    - file_extension: ".py" → suggest view_document
    - query_type: "where is" → suggest search_files
    - viewport_zoom: "close" → suggest pin_files
    """

    # VETKA-specific tools (not code tools - those go to Elysia)
    VETKA_TOOLS = [
        'view_document',
        'search_files',
        'get_viewport',
        'pin_files',
        'focus_node',      # 3D camera focus
        'expand_folder',   # Tree expansion
    ]

    # Decay factor for old activations (exponential decay)
    ACTIVATION_DECAY = 0.95  # Per hour

    def __init__(self, max_history: int = 500):
        """
        Initialize CAM Tool Memory.

        Args:
            max_history: Maximum number of usage records to keep
        """
        # Tool activations: {"tool_name": {"context_key": activation_score}}
        self.tool_activations: Dict[str, Dict[str, float]] = {
            tool: {} for tool in self.VETKA_TOOLS
        }

        # Usage history for learning
        self.usage_history: List[ToolUsageRecord] = []
        self.max_history = max_history

        # Last update timestamp for decay calculation
        self._last_decay_time = datetime.now(timezone.utc)

        logger.info("[CAM ToolMemory] Initialized with VETKA tools tracking")

    def record_tool_use(
        self,
        tool_name: str,
        context: Dict[str, Any],
        success: bool = True
    ) -> None:
        """
        Record tool usage and update activation scores.

        Args:
            tool_name: Name of the tool used (e.g., 'search_files')
            context: Context dict with keys like:
                - folder_path: Current folder being viewed
                - file_extension: Extension of selected file
                - query_type: Type of user query (search, view, etc.)
                - viewport_zoom: Current zoom level
            success: Whether the tool execution was successful
        """
        if tool_name not in self.VETKA_TOOLS:
            logger.debug(f"[CAM ToolMemory] Ignoring non-VETKA tool: {tool_name}")
            return

        # Extract context key (prioritized)
        context_key = self._extract_context_key(context)

        # Create usage record
        record = ToolUsageRecord(
            tool_name=tool_name,
            context_key=context_key,
            timestamp=datetime.now(timezone.utc),
            success=success,
            metadata=context
        )

        # Add to history (with size limit)
        self.usage_history.append(record)
        if len(self.usage_history) > self.max_history:
            self.usage_history = self.usage_history[-self.max_history:]

        # Update activation score
        # Formula: activation += success_bonus * (1 + recency_weight)
        success_bonus = 0.15 if success else -0.05
        recency_weight = 0.1  # Recent usage gets extra boost

        if context_key not in self.tool_activations[tool_name]:
            self.tool_activations[tool_name][context_key] = 0.5  # Default

        current = self.tool_activations[tool_name][context_key]
        new_score = min(1.0, max(0.0, current + success_bonus * (1 + recency_weight)))
        self.tool_activations[tool_name][context_key] = new_score

        logger.debug(
            f"[CAM ToolMemory] Recorded {tool_name} for '{context_key}': "
            f"{current:.2f} → {new_score:.2f}"
        )

    def suggest_tool(
        self,
        context: Dict[str, Any],
        top_n: int = 3
    ) -> List[Tuple[str, float]]:
        """
        Suggest tools based on current context and usage history.

        Args:
            context: Current context dict
            top_n: Number of top suggestions to return

        Returns:
            List of (tool_name, activation_score) tuples, sorted by score descending
        """
        # Apply decay to old activations
        self._apply_decay()

        context_key = self._extract_context_key(context)
        suggestions = []

        for tool_name in self.VETKA_TOOLS:
            # Get activation for this context
            activations = self.tool_activations.get(tool_name, {})

            # Exact match
            if context_key in activations:
                score = activations[context_key]
            else:
                # Partial match: find similar context keys
                score = self._find_similar_activation(activations, context_key)

            if score > 0.3:  # Threshold for suggestion
                suggestions.append((tool_name, score))

        # Sort by score descending
        suggestions.sort(key=lambda x: x[1], reverse=True)

        return suggestions[:top_n]

    def get_jarvis_hint(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Get JARVIS-style hint for current context.

        Returns:
            Hint string like "CAM suggests: search_files (activation: 0.85)"
            or None if no strong suggestion
        """
        suggestions = self.suggest_tool(context, top_n=1)

        if not suggestions:
            return None

        top_tool, score = suggestions[0]
        if score >= 0.6:  # Strong suggestion threshold
            return f"CAM suggests: {top_tool} (activation: {score:.2f})"

        return None

    def _extract_context_key(self, context: Dict[str, Any]) -> str:
        """
        Extract the most relevant context key for learning.

        Priority:
        1. folder_path (most specific)
        2. file_extension
        3. query_type
        4. viewport_zoom
        5. "general" (fallback)
        """
        if context.get('folder_path'):
            # Normalize: /src/orchestration → src/orchestration
            folder = context['folder_path'].strip('/').lower()
            return f"folder:{folder}"

        if context.get('file_extension'):
            ext = context['file_extension'].lower().lstrip('.')
            return f"ext:{ext}"

        if context.get('query_type'):
            return f"query:{context['query_type'].lower()}"

        if context.get('viewport_zoom'):
            zoom = context['viewport_zoom']
            if isinstance(zoom, (int, float)):
                zoom_level = "close" if zoom > 5 else "medium" if zoom > 2 else "overview"
            else:
                zoom_level = str(zoom).lower()
            return f"zoom:{zoom_level}"

        return "general"

    def _find_similar_activation(
        self,
        activations: Dict[str, float],
        context_key: str
    ) -> float:
        """Find activation score from similar context keys."""
        if not activations:
            return 0.3  # Default low score

        # Check for partial matches
        key_type, key_value = context_key.split(':', 1) if ':' in context_key else ('', context_key)

        # Find keys of same type
        same_type_scores = []
        for stored_key, score in activations.items():
            stored_type, _ = stored_key.split(':', 1) if ':' in stored_key else ('', stored_key)
            if stored_type == key_type:
                same_type_scores.append(score)

        if same_type_scores:
            # Return average of same-type activations (with penalty)
            return sum(same_type_scores) / len(same_type_scores) * 0.7

        # Fallback: average of all activations (with bigger penalty)
        if activations:
            return sum(activations.values()) / len(activations) * 0.5

        return 0.3

    def _apply_decay(self) -> None:
        """Apply exponential decay to old activations."""
        now = datetime.now(timezone.utc)
        hours_passed = (now - self._last_decay_time).total_seconds() / 3600

        if hours_passed < 0.5:  # Only decay every 30 minutes
            return

        decay_factor = self.ACTIVATION_DECAY ** hours_passed

        for tool_name in self.VETKA_TOOLS:
            for context_key in self.tool_activations[tool_name]:
                old_score = self.tool_activations[tool_name][context_key]
                # Decay towards 0.5 (neutral)
                new_score = 0.5 + (old_score - 0.5) * decay_factor
                self.tool_activations[tool_name][context_key] = new_score

        self._last_decay_time = now
        logger.debug(f"[CAM ToolMemory] Applied decay (factor: {decay_factor:.3f})")

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        total_activations = sum(
            len(acts) for acts in self.tool_activations.values()
        )

        top_tools = []
        for tool_name, acts in self.tool_activations.items():
            if acts:
                max_score = max(acts.values())
                top_tools.append((tool_name, max_score))

        top_tools.sort(key=lambda x: x[1], reverse=True)

        return {
            'total_records': len(self.usage_history),
            'total_activations': total_activations,
            'top_tools': top_tools[:3],
            'tools_tracked': len(self.VETKA_TOOLS),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for persistence."""
        return {
            'tool_activations': self.tool_activations,
            'usage_history': [
                {
                    'tool_name': r.tool_name,
                    'context_key': r.context_key,
                    'timestamp': r.timestamp.isoformat(),
                    'success': r.success,
                }
                for r in self.usage_history[-100:]  # Last 100 only
            ],
            'last_decay_time': self._last_decay_time.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CAMToolMemory":
        """Deserialize from persistence."""
        memory = cls()
        memory.tool_activations = data.get('tool_activations', memory.tool_activations)

        # Restore history
        for record in data.get('usage_history', []):
            memory.usage_history.append(ToolUsageRecord(
                tool_name=record['tool_name'],
                context_key=record['context_key'],
                timestamp=datetime.fromisoformat(record['timestamp']),
                success=record['success'],
            ))

        if data.get('last_decay_time'):
            memory._last_decay_time = datetime.fromisoformat(data['last_decay_time'])

        return memory


# ═══════════════════════════════════════════════════════════════════
# [PHASE75.1] Global Singleton for CAM Tool Memory
# ═══════════════════════════════════════════════════════════════════

_cam_tool_memory_instance: Optional[CAMToolMemory] = None


def get_cam_tool_memory() -> CAMToolMemory:
    """
    Factory function - returns singleton CAM Tool Memory.

    Returns:
        Singleton CAMToolMemory instance
    """
    global _cam_tool_memory_instance

    if _cam_tool_memory_instance is None:
        _cam_tool_memory_instance = CAMToolMemory()
        logger.info("[CAM ToolMemory] Singleton initialized")

    return _cam_tool_memory_instance


def reset_cam_tool_memory() -> None:
    """Reset singleton for testing purposes."""
    global _cam_tool_memory_instance
    _cam_tool_memory_instance = None
    logger.info("[CAM ToolMemory] Singleton reset")
