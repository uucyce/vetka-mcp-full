# src/orchestration/semantic_dag_builder.py
"""
Phase 17.2 FINAL: Semantic DAG Builder with Multi-Criteria Prerequisite Inference.

Builds REAL branching DAG (not hub/spiral) using:
1. HDBSCAN clustering for concept discovery
2. Multi-criteria voting for prerequisite edge inference
3. DAG depth-based knowledge level calculation

References:
- EduKG (2025): Prerequisite inference for educational KG
- Multi-criteria voting (2025): 10+ metrics for edge prediction
- Sugiyama (1981): Layered graph drawing algorithm

@status: active
@phase: 96
@depends: numpy, sklearn, collections
@used_by: src.orchestration.cam_engine
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import logging
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class SemanticNode:
    """Node in semantic tree (concept/cluster or file)"""
    id: str
    type: str  # 'concept' or 'file'
    label: str
    embedding: Optional[np.ndarray] = None
    children: List[str] = field(default_factory=list)  # file IDs if concept
    knowledge_level: float = 0.5  # 0.0 (foundational) -> 1.0 (advanced)

    # New fields for multi-criteria inference
    complexity_score: float = 0.5  # Embedding L2 norm normalized
    frequency_score: float = 0.5   # Token frequency (if available)
    depth_hint: int = 0            # Directory depth hint

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'type': self.type,
            'label': self.label,
            'knowledge_level': float(self.knowledge_level),
            'children': self.children
        }


@dataclass
class SemanticEdge:
    """Edge in semantic DAG"""
    source: str  # concept_id or file_id
    target: str  # concept_id or file_id
    type: str  # 'prerequisite', 'similarity', 'contains'
    weight: float = 1.0
    confidence: float = 0.0  # Multi-criteria confidence score

    def to_dict(self) -> Dict:
        return {
            'source': self.source,
            'target': self.target,
            'type': self.type,
            'weight': float(self.weight),
            'confidence': float(self.confidence)
        }


class SemanticDAGBuilder:
    """
    Build semantic DAG from embeddings using:
    1. Clustering for concept discovery
    2. Multi-criteria voting for prerequisite edges (NOT just similarity)
    3. DAG depth for knowledge levels (NOT hub-score)
    """

    def __init__(
        self,
        embeddings_dict: Dict[str, np.ndarray],
        file_metadata: Optional[Dict[str, Dict]] = None,
        min_cluster_size: int = 3
    ):
        """
        Args:
            embeddings_dict: {file_id -> embedding (768D)}
            file_metadata: {file_id -> {path, depth, name, extension, ...}}
            min_cluster_size: minimum files per cluster (default 3)
        """
        self.embeddings = embeddings_dict
        self.file_metadata = file_metadata or {}
        self.min_cluster_size = min_cluster_size
        self.semantic_nodes: Dict[str, SemanticNode] = {}
        self.semantic_edges: List[SemanticEdge] = []
        self.concept_map: Dict[str, List[str]] = {}  # concept_id -> list of file_ids

    def build_semantic_tree(self) -> Tuple[Dict[str, SemanticNode], List[SemanticEdge]]:
        """
        Full pipeline (REORDERED for proper DAG):
        1. Cluster embeddings into concepts
        2. Create concept nodes with complexity scores
        3. Create file leaf nodes
        4. Infer prerequisite edges (MULTI-CRITERIA)
        5. Calculate knowledge levels FROM DAG DEPTH
        6. Return nodes + edges
        """

        logger.info("[SemanticDAG] Step 0: Hydrating multimodal embeddings (JEPA)...")
        self._hydrate_multimodal_embeddings_from_jepa()

        logger.info("[SemanticDAG] Step 1: Clustering embeddings...")
        self._cluster_embeddings()

        logger.info("[SemanticDAG] Step 2: Creating concept nodes with complexity scores...")
        self._create_concept_nodes_with_scores()

        logger.info("[SemanticDAG] Step 3: Creating file leaf nodes...")
        self._create_file_nodes()

        logger.info("[SemanticDAG] Step 4: Inferring prerequisite edges (MULTI-CRITERIA)...")
        self._infer_prerequisite_edges_multicriteria()

        logger.info("[SemanticDAG] Step 5: Calculating knowledge levels FROM DAG...")
        self._calculate_knowledge_levels_from_dag()

        logger.info(f"[SemanticDAG] Complete: {len(self.semantic_nodes)} nodes, {len(self.semantic_edges)} edges")

        return self.semantic_nodes, self.semantic_edges

    def _run_coro_sync(self, coro):
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                alt = asyncio.new_event_loop()
                try:
                    return alt.run_until_complete(coro)
                finally:
                    alt.close()
        except RuntimeError:
            pass
        return asyncio.run(coro)

    def _hydrate_multimodal_embeddings_from_jepa(self):
        """
        MARKER_2026_JEPA_INTEGRATION_FULL:
        Fill missing embeddings for audio/video nodes using JEPA integrator.
        Only runs for metadata entries explicitly marked as media.
        """
        try:
            from src.knowledge_graph.jepa_integrator import jepa
        except Exception as e:
            logger.info(f"[SemanticDAG] JEPA integrator unavailable: {e.__class__.__name__}")
            return

        hydrated = 0
        for file_id, meta in (self.file_metadata or {}).items():
            if file_id in self.embeddings and self.embeddings[file_id] is not None:
                continue
            mtype = str(meta.get("type") or "").lower()
            path = str(meta.get("path") or "")
            if mtype not in {"video", "audio"} or not path:
                continue
            try:
                if mtype == "video":
                    emb = self._run_coro_sync(jepa.get_video_embedding(path))
                else:
                    emb, _info = self._run_coro_sync(jepa.get_audio_embedding(path))
                if emb is not None:
                    self.embeddings[file_id] = np.array(emb, dtype=np.float32)
                    hydrated += 1
                    meta["jepa_extracted"] = True
            except Exception as e:
                logger.warning(f"[SemanticDAG] JEPA hydrate failed for {file_id}: {e.__class__.__name__}")
                continue

        if hydrated > 0:
            logger.info(f"[SemanticDAG] Hydrated multimodal embeddings via JEPA: {hydrated}")

    def _cluster_embeddings(self):
        """Use HDBSCAN to cluster file embeddings into concepts"""
        if len(self.embeddings) < self.min_cluster_size:
            self.concept_map["concept_0"] = list(self.embeddings.keys())
            logger.info(f"[SemanticDAG] Too few files ({len(self.embeddings)}), using single cluster")
            return

        try:
            from sklearn.cluster import HDBSCAN
            has_hdbscan = True
        except ImportError:
            has_hdbscan = False
            logger.info("[SemanticDAG] HDBSCAN not available, using KMeans fallback")

        if has_hdbscan:
            self._cluster_hdbscan()
        else:
            self._cluster_kmeans()

    def _cluster_hdbscan(self):
        """HDBSCAN clustering for variable-size clusters"""
        from sklearn.cluster import HDBSCAN

        file_ids = list(self.embeddings.keys())
        emb_matrix = np.array([self.embeddings[fid] for fid in file_ids])

        # Normalize for cosine distance
        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
        norms = np.where(norms < 1e-8, 1, norms)
        emb_normalized = emb_matrix / norms

        clusterer = HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            metric='euclidean',
            cluster_selection_epsilon=0.5
        )
        labels = clusterer.fit_predict(emb_normalized)

        unique_labels = set(labels)
        noise_count = 0

        for label in unique_labels:
            if label == -1:
                noise_count = sum(1 for l in labels if l == -1)
                continue

            cluster_files = [file_ids[i] for i, l in enumerate(labels) if l == label]
            concept_id = f"concept_{label}"
            self.concept_map[concept_id] = cluster_files
            logger.info(f"[SemanticDAG] Cluster {label}: {len(cluster_files)} files")

        # Handle noise files - create individual concepts for them (not one big misc)
        if noise_count > 0:
            noise_files = [file_ids[i] for i, l in enumerate(labels) if l == -1]
            # Group noise by directory depth to create smaller clusters
            depth_groups = defaultdict(list)
            for fid in noise_files:
                meta = self.file_metadata.get(fid, {})
                depth = meta.get('depth', 0)
                depth_groups[depth].append(fid)

            # Create concept for each depth group
            for depth, files in depth_groups.items():
                if len(files) >= 2:
                    concept_id = f"concept_depth_{depth}"
                    self.concept_map[concept_id] = files
                    logger.info(f"[SemanticDAG] Depth {depth} cluster: {len(files)} files")
                else:
                    # Single orphan file - assign to closest cluster
                    self._assign_to_nearest_cluster(files[0])

    def _assign_to_nearest_cluster(self, file_id: str):
        """Assign a lone file to the nearest existing cluster by embedding similarity"""
        if file_id not in self.embeddings:
            return

        file_emb = self.embeddings[file_id]
        best_cluster = None
        best_sim = -1

        for concept_id, cluster_files in self.concept_map.items():
            # Calculate cluster centroid
            cluster_embs = [self.embeddings[fid] for fid in cluster_files if fid in self.embeddings]
            if not cluster_embs:
                continue
            centroid = np.mean(cluster_embs, axis=0)

            # Cosine similarity
            norm_f = np.linalg.norm(file_emb)
            norm_c = np.linalg.norm(centroid)
            if norm_f > 1e-8 and norm_c > 1e-8:
                sim = np.dot(file_emb, centroid) / (norm_f * norm_c)
                if sim > best_sim:
                    best_sim = sim
                    best_cluster = concept_id

        if best_cluster:
            self.concept_map[best_cluster].append(file_id)

    def _cluster_kmeans(self):
        """Fallback: simple k-means if HDBSCAN unavailable"""
        try:
            from sklearn.cluster import KMeans
        except ImportError:
            logger.error("[SemanticDAG] sklearn required. Using single cluster fallback.")
            self.concept_map["concept_0"] = list(self.embeddings.keys())
            return

        file_ids = list(self.embeddings.keys())
        emb_matrix = np.array([self.embeddings[fid] for fid in file_ids])

        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
        norms = np.where(norms < 1e-8, 1, norms)
        emb_normalized = emb_matrix / norms

        n_clusters = max(2, min(20, len(file_ids) // 5))

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(emb_normalized)

        for k in range(n_clusters):
            cluster_files = [file_ids[i] for i, l in enumerate(labels) if l == k]
            if len(cluster_files) >= 1:
                concept_id = f"concept_{k}"
                self.concept_map[concept_id] = cluster_files
                logger.info(f"[SemanticDAG] KMeans cluster {k}: {len(cluster_files)} files")

    def _create_concept_nodes_with_scores(self):
        """Create SemanticNode for each concept with complexity/depth scores"""
        for concept_id, file_ids in self.concept_map.items():
            # Average embedding for concept
            valid_embeddings = [self.embeddings[fid] for fid in file_ids if fid in self.embeddings]
            if valid_embeddings:
                emb = np.mean(valid_embeddings, axis=0)
            else:
                emb = np.zeros(768)

            # Calculate complexity score (L2 norm of embedding)
            complexity = np.linalg.norm(emb) / 100.0  # normalize
            complexity = min(1.0, max(0.0, complexity))

            # Calculate average depth hint from file metadata
            depths = [self.file_metadata.get(fid, {}).get('depth', 0) for fid in file_ids]
            avg_depth = sum(depths) / len(depths) if depths else 0

            # Generate label
            label = f"Topic_{concept_id.split('_')[-1]}"

            node = SemanticNode(
                id=concept_id,
                type='concept',
                label=label,
                embedding=emb,
                children=file_ids,
                knowledge_level=0.5,  # Will be calculated from DAG later
                complexity_score=complexity,
                depth_hint=int(avg_depth)
            )

            self.semantic_nodes[concept_id] = node

            # Add "contains" edges from concept to files
            for file_id in file_ids:
                self.semantic_edges.append(SemanticEdge(
                    source=concept_id,
                    target=file_id,
                    type='contains'
                ))

    def _create_file_nodes(self):
        """Create SemanticNode for each file (as leaf)"""
        for file_id, embedding in self.embeddings.items():
            if '_' in file_id:
                label = file_id.split('_')[-1][:20]
            else:
                label = file_id[:20]

            meta = self.file_metadata.get(file_id, {})
            depth = meta.get('depth', 0)

            node = SemanticNode(
                id=file_id,
                type='file',
                label=label,
                embedding=embedding,
                children=[],
                knowledge_level=0.5,
                depth_hint=depth
            )

            self.semantic_nodes[file_id] = node

    def _infer_prerequisite_edges_multicriteria(self):
        """
        Infer prerequisite edges using MULTI-CRITERIA voting (not just similarity).

        Criteria:
        1. Embedding similarity (cosine > threshold)
        2. Complexity asymmetry (simpler -> more complex)
        3. Depth hint (shallower -> deeper suggests foundation -> advanced)
        4. Cluster size (larger clusters = more foundational)

        Direction: source is PREREQUISITE for target (study source BEFORE target)
        """
        concepts = [n for n in self.semantic_nodes.values() if n.type == 'concept']

        if len(concepts) < 2:
            logger.info("[SemanticDAG] Less than 2 concepts, no prerequisite edges needed")
            return

        # Thresholds
        similarity_threshold = 0.4  # Lowered for more connectivity
        min_confidence = 0.3  # Minimum confidence for edge

        edges_added = 0

        for i, concept_a in enumerate(concepts):
            for concept_b in concepts[i+1:]:
                if concept_a.embedding is None or concept_b.embedding is None:
                    continue

                # Criterion 1: Cosine similarity (must be related)
                norm_a = np.linalg.norm(concept_a.embedding)
                norm_b = np.linalg.norm(concept_b.embedding)

                if norm_a < 1e-8 or norm_b < 1e-8:
                    continue

                similarity = np.dot(concept_a.embedding, concept_b.embedding) / (norm_a * norm_b)

                if similarity < similarity_threshold:
                    continue  # Not related enough

                # Multi-criteria voting for direction
                votes_a_before_b = 0.0  # Votes for A -> B (A prerequisite of B)
                votes_b_before_a = 0.0  # Votes for B -> A (B prerequisite of A)

                # Criterion 2: Complexity (simpler = foundational)
                complexity_diff = concept_b.complexity_score - concept_a.complexity_score
                if complexity_diff > 0.05:  # B more complex -> A before B
                    votes_a_before_b += 0.3
                elif complexity_diff < -0.05:  # A more complex -> B before A
                    votes_b_before_a += 0.3

                # Criterion 3: Depth hint (shallower = foundational)
                depth_diff = concept_b.depth_hint - concept_a.depth_hint
                if depth_diff > 0:  # B deeper -> A before B
                    votes_a_before_b += 0.2
                elif depth_diff < 0:  # A deeper -> B before A
                    votes_b_before_a += 0.2

                # Criterion 4: Cluster size (larger = more foundational)
                size_a = len(concept_a.children)
                size_b = len(concept_b.children)
                if size_a > size_b * 1.5:  # A much larger -> A before B
                    votes_a_before_b += 0.25
                elif size_b > size_a * 1.5:  # B much larger -> B before A
                    votes_b_before_a += 0.25

                # Criterion 5: Embedding norm (lower = simpler = foundational)
                if norm_a < norm_b * 0.9:  # A simpler -> A before B
                    votes_a_before_b += 0.15
                elif norm_b < norm_a * 0.9:  # B simpler -> B before A
                    votes_b_before_a += 0.15

                # Criterion 6: Label alphabetical (tiebreaker)
                if concept_a.id < concept_b.id:
                    votes_a_before_b += 0.05
                else:
                    votes_b_before_a += 0.05

                # Determine direction and confidence
                confidence = abs(votes_a_before_b - votes_b_before_a)

                if confidence < min_confidence:
                    # Too close to call - skip or use similarity as tiebreaker
                    if similarity > 0.7:
                        # Strong similarity - create edge in direction of smaller ID
                        if concept_a.id < concept_b.id:
                            source, target = concept_a.id, concept_b.id
                        else:
                            source, target = concept_b.id, concept_a.id
                        confidence = 0.3
                    else:
                        continue
                elif votes_a_before_b > votes_b_before_a:
                    source, target = concept_a.id, concept_b.id
                else:
                    source, target = concept_b.id, concept_a.id

                # Add prerequisite edge
                self.semantic_edges.append(SemanticEdge(
                    source=source,
                    target=target,
                    type='prerequisite',
                    weight=float(similarity),
                    confidence=confidence
                ))
                edges_added += 1

        logger.info(f"[SemanticDAG] Added {edges_added} prerequisite edges via multi-criteria voting")

    def _calculate_knowledge_levels_from_dag(self):
        """
        Calculate knowledge_level FROM DAG DEPTH using BFS.

        NOT from hub-score or embedding complexity!

        Depth 0 (roots, no incoming edges) -> knowledge_level 0.1 (foundational)
        Depth N (max depth) -> knowledge_level 1.0 (advanced)
        """

        # Build adjacency for prerequisite edges only
        concept_ids = [n.id for n in self.semantic_nodes.values() if n.type == 'concept']
        in_degree = {cid: 0 for cid in concept_ids}
        adjacency = {cid: [] for cid in concept_ids}

        for edge in self.semantic_edges:
            if edge.type == 'prerequisite':
                if edge.source in concept_ids and edge.target in concept_ids:
                    in_degree[edge.target] = in_degree.get(edge.target, 0) + 1
                    if edge.source in adjacency:
                        adjacency[edge.source].append(edge.target)

        # Find root concepts (no incoming prerequisite edges)
        roots = [cid for cid in concept_ids if in_degree[cid] == 0]

        if not roots:
            logger.warning("[SemanticDAG] No root concepts found, using all as roots")
            roots = concept_ids[:1] if concept_ids else []

        logger.info(f"[SemanticDAG] DAG roots: {roots}")

        # BFS to calculate depth
        depths = {cid: float('inf') for cid in concept_ids}
        queue = deque()

        for root in roots:
            depths[root] = 0
            queue.append((root, 0))

        while queue:
            node_id, depth = queue.popleft()
            for target in adjacency.get(node_id, []):
                if depths[target] > depth + 1:
                    depths[target] = depth + 1
                    queue.append((target, depth + 1))

        # Handle unreachable concepts (set to max depth + 1)
        max_depth = max(d for d in depths.values() if d != float('inf'))
        if max_depth == float('inf'):
            max_depth = 0

        for cid in concept_ids:
            if depths[cid] == float('inf'):
                depths[cid] = max_depth + 1
                max_depth = depths[cid]

        # Normalize depths to knowledge_level [0.1, 1.0]
        if max_depth == 0:
            # Single level - all at 0.5
            for cid in concept_ids:
                self.semantic_nodes[cid].knowledge_level = 0.5
        else:
            for cid in concept_ids:
                normalized = depths[cid] / max_depth  # 0.0 to 1.0
                knowledge_level = 0.1 + normalized * 0.9  # 0.1 to 1.0
                self.semantic_nodes[cid].knowledge_level = knowledge_level

        logger.info(f"[SemanticDAG] DAG max depth: {max_depth}, knowledge levels calculated")

        # Update file knowledge levels based on parent concept (accept both "file" and "leaf")
        for node_id, node in self.semantic_nodes.items():
            if node.type in ['file', 'leaf']:
                for edge in self.semantic_edges:
                    if edge.target == node_id and edge.type == 'contains':
                        parent = self.semantic_nodes.get(edge.source)
                        if parent:
                            offset = np.random.uniform(-0.02, 0.02)
                            node.knowledge_level = max(0.0, min(1.0, parent.knowledge_level + offset))
                        break

    def get_stats(self) -> Dict[str, Any]:
        """Return statistics about the semantic DAG"""
        concept_count = sum(1 for n in self.semantic_nodes.values() if n.type == 'concept')
        file_count = sum(1 for n in self.semantic_nodes.values() if n.type in ['file', 'leaf'])

        edge_types = {}
        for e in self.semantic_edges:
            edge_types[e.type] = edge_types.get(e.type, 0) + 1

        knowledge_levels = [n.knowledge_level for n in self.semantic_nodes.values() if n.type == 'concept']

        # Calculate DAG depth
        prereq_edges = [e for e in self.semantic_edges if e.type == 'prerequisite']
        in_degrees = defaultdict(int)
        for e in prereq_edges:
            in_degrees[e.target] += 1

        roots = [n.id for n in self.semantic_nodes.values()
                 if n.type == 'concept' and in_degrees[n.id] == 0]

        return {
            'total_nodes': len(self.semantic_nodes),
            'concept_count': concept_count,
            'file_count': file_count,
            'total_edges': len(self.semantic_edges),
            'edge_types': edge_types,
            'dag_roots': len(roots),
            'prerequisite_edges': len(prereq_edges),
            'knowledge_level_distribution': {
                'min': min(knowledge_levels) if knowledge_levels else 0,
                'max': max(knowledge_levels) if knowledge_levels else 1,
                'mean': float(np.mean(knowledge_levels)) if knowledge_levels else 0.5
            }
        }


def export_semantic_dag_json(nodes: Dict[str, SemanticNode], edges: List[SemanticEdge], filepath: str):
    """Export semantic DAG to JSON for API/debugging"""
    data = {
        'nodes': [n.to_dict() for n in nodes.values()],
        'edges': [e.to_dict() for e in edges]
    }

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    logger.info(f"[SemanticDAG] Exported to {filepath}")


def build_semantic_dag_from_qdrant(
    qdrant_client,
    collection_name: str = "vetka_elisya",
    min_cluster_size: int = 3
) -> Tuple[Dict[str, SemanticNode], List[SemanticEdge], Dict[str, Any]]:
    """
    Convenience function to build semantic DAG directly from Qdrant.

    Args:
        qdrant_client: Qdrant client instance
        collection_name: Name of Qdrant collection
        min_cluster_size: Minimum files per cluster

    Returns:
        Tuple of (nodes, edges, stats)
    """
    if not qdrant_client:
        logger.error("[SemanticDAG] No Qdrant client provided")
        return {}, [], {}

    def _safe_float(value: Any) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _resolve_times(payload: Dict[str, Any]) -> Tuple[float, float]:
        created = _safe_float(payload.get('created_time'))
        modified = _safe_float(payload.get('modified_time'))
        updated = _safe_float(payload.get('updated_at'))
        created_resolved = created or modified or updated or 0.0
        modified_resolved = modified or created_resolved or updated or 0.0
        return created_resolved, modified_resolved

    # Fetch all embeddings AND metadata from Qdrant
    embeddings_dict = {}
    file_metadata = {}
    offset = None
    metadata_stats = {
        'total': 0,
        'with_created_time': 0,
        'with_modified_time': 0,
        'with_updated_at': 0,
        'with_parent_folder': 0,
        'with_modality': 0,
        'with_mime_type': 0,
        'with_size_bytes': 0,
        'with_content_hash': 0,
        'with_source': 0,
        'with_depth': 0,
        'created_from_created': 0,
        'created_from_modified': 0,
        'created_from_updated': 0,
        'created_missing': 0,
    }

    logger.info("[SemanticDAG] Fetching embeddings from Qdrant...")

    while True:
        points, offset = qdrant_client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=True
        )

        for point in points:
            file_id = str(point.id)
            if point.vector:
                embeddings_dict[file_id] = np.array(point.vector)

            # Extract metadata for multi-criteria inference
            payload = point.payload or {}
            path = payload.get('path', '')
            depth = int(payload.get('depth') or (path.count('/') if path else 0))
            created_time, modified_time = _resolve_times(payload)
            parent_folder = payload.get('parent_folder', '')
            modality = payload.get('modality', '')

            file_metadata[file_id] = {
                'path': path,
                'depth': depth,
                'name': payload.get('name', ''),
                'extension': payload.get('extension', ''),
                'type': payload.get('type', 'file'),
                'parent_folder': parent_folder,
                'mime_type': payload.get('mime_type', ''),
                'modality': modality,
                'size_bytes': int(payload.get('size_bytes') or 0),
                'content_hash': payload.get('content_hash', ''),
                'source': payload.get('source', ''),
                'created_time': created_time,
                'modified_time': modified_time,
                'updated_at': _safe_float(payload.get('updated_at')),
            }
            raw_created = _safe_float(payload.get('created_time'))
            raw_modified = _safe_float(payload.get('modified_time'))
            raw_updated = _safe_float(payload.get('updated_at'))

            metadata_stats['total'] += 1
            if created_time > 0:
                metadata_stats['with_created_time'] += 1
            if modified_time > 0:
                metadata_stats['with_modified_time'] += 1
            if raw_updated > 0:
                metadata_stats['with_updated_at'] += 1
            if parent_folder:
                metadata_stats['with_parent_folder'] += 1
            if modality:
                metadata_stats['with_modality'] += 1
            if payload.get('mime_type'):
                metadata_stats['with_mime_type'] += 1
            if int(payload.get('size_bytes') or 0) > 0:
                metadata_stats['with_size_bytes'] += 1
            if payload.get('content_hash'):
                metadata_stats['with_content_hash'] += 1
            if payload.get('source'):
                metadata_stats['with_source'] += 1
            if depth > 0 or path:
                metadata_stats['with_depth'] += 1

            if raw_created > 0:
                metadata_stats['created_from_created'] += 1
            elif raw_modified > 0:
                metadata_stats['created_from_modified'] += 1
            elif raw_updated > 0:
                metadata_stats['created_from_updated'] += 1
            else:
                metadata_stats['created_missing'] += 1

        if offset is None:
            break

    logger.info(f"[SemanticDAG] Loaded {len(embeddings_dict)} embeddings with metadata")
    total = max(1, metadata_stats['total'])
    metadata_completeness = {
        'total': metadata_stats['total'],
        'percent': {
            'created_time': round(100.0 * metadata_stats['with_created_time'] / total, 1),
            'modified_time': round(100.0 * metadata_stats['with_modified_time'] / total, 1),
            'updated_at': round(100.0 * metadata_stats['with_updated_at'] / total, 1),
            'parent_folder': round(100.0 * metadata_stats['with_parent_folder'] / total, 1),
            'modality': round(100.0 * metadata_stats['with_modality'] / total, 1),
            'mime_type': round(100.0 * metadata_stats['with_mime_type'] / total, 1),
            'size_bytes': round(100.0 * metadata_stats['with_size_bytes'] / total, 1),
            'content_hash': round(100.0 * metadata_stats['with_content_hash'] / total, 1),
            'source': round(100.0 * metadata_stats['with_source'] / total, 1),
            'depth': round(100.0 * metadata_stats['with_depth'] / total, 1),
        },
        'time_fallback': {
            'from_created': metadata_stats['created_from_created'],
            'from_modified': metadata_stats['created_from_modified'],
            'from_updated_at': metadata_stats['created_from_updated'],
            'missing': metadata_stats['created_missing'],
        },
    }
    logger.info(
        "[SemanticDAG] Metadata completeness: created=%s%% modified=%s%% updated=%s%% parent=%s%% modality=%s%% mime=%s%% source=%s%%",
        metadata_completeness['percent']['created_time'],
        metadata_completeness['percent']['modified_time'],
        metadata_completeness['percent']['updated_at'],
        metadata_completeness['percent']['parent_folder'],
        metadata_completeness['percent']['modality'],
        metadata_completeness['percent']['mime_type'],
        metadata_completeness['percent']['source'],
    )
    if metadata_completeness['percent']['created_time'] < 90.0:
        logger.warning(
            "[SemanticDAG] Low created_time completeness: %.1f%% (fallback modified=%d updated=%d missing=%d)",
            metadata_completeness['percent']['created_time'],
            metadata_completeness['time_fallback']['from_modified'],
            metadata_completeness['time_fallback']['from_updated_at'],
            metadata_completeness['time_fallback']['missing'],
        )

    if len(embeddings_dict) == 0:
        logger.warning("[SemanticDAG] No embeddings found!")
        return {}, [], {}

    # Build semantic DAG with multi-criteria inference
    builder = SemanticDAGBuilder(
        embeddings_dict,
        file_metadata=file_metadata,
        min_cluster_size=min_cluster_size
    )
    nodes, edges = builder.build_semantic_tree()
    stats = builder.get_stats()
    stats['metadata_completeness'] = metadata_completeness

    return nodes, edges, stats
