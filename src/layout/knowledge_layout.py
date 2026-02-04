# src/layout/knowledge_layout.py
"""
Phase 17.15: Knowledge Graph Layout with UNIFIED SUGIYAMA ENGINE.

This module provides:
1. cluster_files_to_tags() - Group files into semantic clusters/tags using HDBSCAN
2. build_prerequisite_edges() - Create directed edges based on similarity + knowledge_level
3. calculate_knowledge_positions() - Compute Knowledge Mode positions using SUGIYAMA

PHASE 17.15 REFACTORING:
- Tags are now positioned using the SAME Sugiyama engine as Directory Mode
- This ensures consistent hierarchical tree layout between modes
- Files fan out below their parent tags using the same distribution logic

The result is used by the frontend to blend between Directory and Knowledge modes.

MARKER_3D_LAYOUT: Knowledge graph layout system (Sugiyama DAG)
- Engine: Sugiyama algorithm for hierarchical layout (calculate_semantic_sugiyama_layout)
- Coordinates: X (left-right), Y (time/hierarchy), Z (semantic depth)
- Y-axis: Represents depth in tree hierarchy (roots at top, leaves at bottom)
- Edge construction: build_prerequisite_edges() creates directed edges with weights
- Tag colors: generate_cluster_color() provides distinct colors per semantic cluster
- For chats: Can use same layout engine with chat_node.parent_id as hierarchy root
- Integration: Positions from this module feed directly into TreeNode.position

@status: active
@phase: 96
@depends: math, logging, numpy, typing, dataclasses, collections, src.layout.semantic_sugiyama
@used_by: src.visualizer.tree_renderer, knowledge mode frontend, (future: chat_layout)
"""

import math
import logging
import os
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timezone

# Phase 17.15: Import Sugiyama engine functions
# Phase 17.16: Added minimize_crossings and apply_soft_repulsion_semantic
from src.layout.semantic_sugiyama import (
    calculate_semantic_sugiyama_layout,
    distribute_by_similarity,
    distribute_horizontally,
    minimize_crossings,
    apply_soft_repulsion_semantic
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════

@dataclass
class KnowledgeTag:
    """A semantic cluster/tag that groups related files"""
    id: str
    name: str
    files: List[str] = field(default_factory=list)
    centroid: Optional[np.ndarray] = None
    color: str = "#00ff00"
    angle: float = 0.0  # Angular position in layout
    position: Dict[str, float] = field(default_factory=lambda: {'x': 0, 'y': 0, 'z': 0})
    # Phase 17.13: Hierarchical tag tree
    parent_tag_id: Optional[str] = None  # Parent tag ID (None for root)
    depth: int = 0  # Depth in tag hierarchy (0 = root)


@dataclass
class KnowledgeEdge:
    """Edge in knowledge graph"""
    source: str
    target: str
    edge_type: str  # 'prerequisite', 'similarity', 'contains'
    weight: float = 1.0


def generate_cluster_color(cluster_id: int) -> str:
    """Generate a distinct color for each cluster"""
    colors = [
        "#4CAF50",  # Green
        "#2196F3",  # Blue
        "#FF9800",  # Orange
        "#9C27B0",  # Purple
        "#00BCD4",  # Cyan
        "#E91E63",  # Pink
        "#CDDC39",  # Lime
        "#FF5722",  # Deep Orange
        "#3F51B5",  # Indigo
        "#795548",  # Brown
        "#607D8B",  # Blue Grey
        "#009688",  # Teal
    ]
    return colors[cluster_id % len(colors)]


# ═══════════════════════════════════════════════════════════════════
# PHASE 22 v4: INTAKE BRANCH + AUTO-RELOCATION
# Expert consensus: Danila + Kimi K2 + Anonymous Architect
# ═══════════════════════════════════════════════════════════════════

# INTAKE branch constants
INTAKE_TAG_ID = '_intake'
INTAKE_TAG_NAME = 'Intake'
INTAKE_COLOR = '#FFB347'  # Warm orange = "needs attention"
INTAKE_MIN_CONFIDENCE = 0.65  # Threshold to exit intake


def ensure_intake_branch(tags: Dict[str, 'KnowledgeTag']) -> Dict[str, 'KnowledgeTag']:
    """
    Phase 22 v4: Create special intake branch if missing.
    This is where unclassified files live temporarily.

    The intake branch:
    - Acts as staging area for files pending semantic classification
    - Files auto-relocate when confidence threshold is met
    - Visual: warm orange color, bob animation in frontend
    """
    if INTAKE_TAG_ID not in tags:
        tags[INTAKE_TAG_ID] = KnowledgeTag(
            id=INTAKE_TAG_ID,
            name=INTAKE_TAG_NAME,
            files=[],
            color=INTAKE_COLOR,
            depth=0,  # Root level - always visible
            parent_tag_id=None
        )
        logger.info(f"[KnowledgeLayout] Phase 22 v4: Created INTAKE branch for unclassified files")
    return tags


def auto_relocate_from_intake(
    file_id: str,
    file_embedding: np.ndarray,
    current_tags: Dict[str, 'KnowledgeTag'],
    file_metadata: Optional[Dict[str, Dict]] = None,
    similarity_threshold: float = INTAKE_MIN_CONFIDENCE
) -> Tuple[str, float]:
    """
    Phase 22 v4: Semantic scan - which tag should this file move to?

    Factors:
    - Cosine similarity to tag centroid
    - Project overlap (Kimi's contribution)
    - Current position (spatial locality)

    Returns:
    - target_tag_id: Where file should move
    - confidence_score: How sure are we (0-1)

    ALGORITHM (Architect + Kimi consensus):
    1. Compute cosine similarity to all tag centroids
    2. Filter by project overlap (exclude wrong projects)
    3. If top_score > threshold → relocate
    4. Else → stay in intake + emit 'needs_human_review'
    """
    best_tag = INTAKE_TAG_ID
    best_score = 0.0

    # Get file's project from metadata
    file_project = None
    if file_metadata and file_id in file_metadata:
        file_path = file_metadata[file_id].get('path', '')
        # Extract project from path (first 3-4 components)
        parts = file_path.split('/')
        file_project = '/'.join(parts[:min(4, len(parts))])

    for tag_id, tag in current_tags.items():
        if tag_id == INTAKE_TAG_ID:
            continue  # Skip the intake branch itself

        # Factor 1: Semantic similarity (60% weight)
        centroid = tag.centroid
        if centroid is None:
            continue

        # Cosine similarity
        norm_file = np.linalg.norm(file_embedding)
        norm_centroid = np.linalg.norm(centroid)
        if norm_file < 1e-8 or norm_centroid < 1e-8:
            continue
        semantic_sim = float(np.dot(file_embedding, centroid) / (norm_file * norm_centroid))

        # Factor 2: Project overlap (Kimi's strict check)
        project_match = True
        if file_project and tag.files and file_metadata:
            # Check if any file in tag shares the same project
            tag_projects = set()
            for tf in tag.files[:10]:  # Sample first 10 files
                if tf in file_metadata:
                    tp = file_metadata[tf].get('path', '')
                    tp_parts = tp.split('/')
                    tag_projects.add('/'.join(tp_parts[:min(4, len(tp_parts))]))

            if tag_projects and file_project not in tag_projects:
                project_match = False

        # Phase 23 FIX: Much stronger penalty for wrong project
        if not project_match:
            semantic_sim *= 0.05  # Almost complete rejection for wrong project

        # Combined score
        combined = semantic_sim * 0.6 + (0.4 if project_match else 0.0)

        if combined > best_score:
            best_score = combined
            best_tag = tag_id

    # Only relocate if confidence is high enough
    if best_score < similarity_threshold:
        logger.debug(f"[KnowledgeLayout] File {file_id} stays in INTAKE (best_score={best_score:.3f} < {similarity_threshold})")
        return (INTAKE_TAG_ID, best_score)

    logger.info(f"[KnowledgeLayout] File {file_id} auto-relocates to '{current_tags[best_tag].name}' (confidence={best_score:.3f})")
    return (best_tag, best_score)


def compute_knowledge_level_enhanced(
    centrality_score: float,
    rrf_score: float,
    max_centrality: float
) -> float:
    """
    Phase 22 v4: Composite knowledge level formula (KIMI + ARCHITECT consensus).

    KL represents progression from fundamental → advanced.

    Factors:
    - Low centrality → HIGH KL (specialized topics at top)
    - High RRF score → SLIGHTLY higher KL (important gets visible)
    - Normalized for readability (0.1 to 1.0 range)
    """
    # Normalize centrality (invert: low centrality = high KL)
    centrality_normalized = 1.0 - (centrality_score / (max_centrality + 1e-8))

    # Apply sigmoid for better spread
    sigmoid = 1.0 / (1.0 + math.exp(-10 * (centrality_normalized - 0.5)))

    # RRF boost (small effect to avoid distortion)
    rrf_boost = rrf_score * 0.15  # Max +0.15 from RRF

    # Final KL in range [0.1, 1.0]
    kl = 0.1 + (sigmoid * 0.75) + rrf_boost

    return max(0.1, min(1.0, kl))


# ═══════════════════════════════════════════════════════════════════
# PHASE 22 v4: ADAPTIVE SPATIAL FORMULAS
# Expert consensus: Architect's formulas + Danila's visual validation
# ═══════════════════════════════════════════════════════════════════

def compute_file_spacing(
    num_files_in_cluster: int,
    semantic_variance: float,
    knowledge_level_variance: float,
    depth: int,
    max_files_per_cluster: int = 50
) -> Dict[str, float]:
    """
    Phase 22 v4: ARCHITECT'S FORMULA for file spacing.

    File spacing grows with:
    1. Number of files (more files = need more space)
    2. Semantic variance (diverse topics = spread them)
    3. KL variance (if KLs differ a lot, they need visual separation)
    4. Depth (deeper files can be tighter, shallow ones more spread)

    RESULT: No more tight columns. Files breathe.
    """
    # Base spacing (pixels between file centers)
    BASE_FILE_SPACING = 100

    # Factor 1: Count scaling (sqrt to avoid exponential growth)
    count_factor = math.sqrt(num_files_in_cluster / max(1, max_files_per_cluster))
    count_factor = max(1.0, count_factor)  # Don't shrink below 1x

    # Factor 2: Semantic diversity (if all files similar, can pack closer)
    variance_factor = 1.0 + semantic_variance * 0.8  # Up to 1.8x spacing

    # Factor 3: KL diversity (if KLs spread across spectrum, need room)
    kl_factor = 1.0 + knowledge_level_variance * 0.6  # Up to 1.6x spacing

    # Factor 4: Depth reduction (deeper clusters can be tighter)
    depth_factor = 1.0 / (1.0 + depth * 0.1)  # Gradually compress with depth

    # Combined formula
    file_spacing = BASE_FILE_SPACING * count_factor * variance_factor * kl_factor * depth_factor

    # Fan spread (horizontal distance in fan distribution)
    FAN_SPREAD_BASE = 250
    fan_spread = FAN_SPREAD_BASE * variance_factor * kl_factor

    # Radial offset for nested files
    RADIAL_STEP = 60
    radial_offset = RADIAL_STEP * variance_factor

    return {
        'file_spacing': file_spacing,
        'fan_spread': fan_spread,
        'radial_offset': radial_offset,
        'count_factor': count_factor,
        'variance_factor': variance_factor,
    }


def compute_cluster_radius(
    num_children: int,
    semantic_entropy: float,
    depth: int,
    rrf_weight: float = 1.0
) -> Dict[str, float]:
    """
    Phase 22 v4: ARCHITECT'S FORMULA for cluster radius.

    Cluster radius grows to accommodate children.
    Critical: Clusters need MORE separation than internal files.

    Factors:
    - More children = bigger radius
    - High entropy = bigger radius (diverse content spreads more)
    - RRF weight = important clusters get more visual real estate
    """
    BASE_RADIUS = 300  # Pixels from tag center to file orbit

    # Factor 1: Children count (sqrt scaling to avoid huge bubbles)
    children_factor = 1.0 + math.sqrt(num_children) * 0.4

    # Factor 2: Semantic entropy (messy clusters need more room)
    entropy_factor = 1.0 + semantic_entropy * 0.6  # Up to 1.6x

    # Factor 3: RRF importance (important clusters get visibility)
    rrf_factor = 0.8 + rrf_weight * 0.4  # Range [0.8, 1.2]

    # Factor 4: Depth penalty (deeper clusters tighter, shallower bigger)
    depth_factor = 1.0 / (1.0 + depth * 0.15)  # Gradual compression

    # Final radius
    cluster_radius = BASE_RADIUS * children_factor * entropy_factor * rrf_factor * depth_factor

    # Minimum separation between cluster boundaries
    MIN_CLUSTER_SEPARATION = 400  # pixels

    return {
        'radius': cluster_radius,
        'min_separation': MIN_CLUSTER_SEPARATION,
        'children_factor': children_factor,
        'entropy_factor': entropy_factor,
    }


def compute_semantic_variance(embeddings: List[np.ndarray]) -> float:
    """
    Compute semantic variance (entropy) of a set of embeddings.
    High variance = diverse topics = need more visual spread.

    Returns value in range [0, 1].
    """
    if len(embeddings) < 2:
        return 0.0

    # Stack embeddings
    emb_matrix = np.array(embeddings)

    # Compute pairwise cosine similarities
    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    norms = np.where(norms < 1e-8, 1, norms)
    normalized = emb_matrix / norms

    # Similarity matrix
    sim_matrix = np.dot(normalized, normalized.T)

    # Variance = 1 - mean_similarity (more diverse = lower similarity = higher variance)
    mean_sim = np.mean(sim_matrix)
    variance = 1.0 - mean_sim

    # Clamp to [0, 1]
    return max(0.0, min(1.0, variance))


def compute_kl_variance(knowledge_levels: List[float]) -> float:
    """
    Compute variance in knowledge levels within a cluster.
    High variance = files span many difficulty levels = need visual separation.

    Returns value in range [0, 1].
    """
    if len(knowledge_levels) < 2:
        return 0.0

    kl_array = np.array(knowledge_levels)
    variance = np.std(kl_array)  # Standard deviation

    # Normalize to [0, 1] (max std for uniform [0,1] distribution is ~0.29)
    normalized = min(1.0, variance / 0.3)

    return normalized


# ═══════════════════════════════════════════════════════════════════
# PHASE 22 v4: Z-LINK CLASSIFICATION
# Expert consensus: Architect's types + Danila's visual rules
# ═══════════════════════════════════════════════════════════════════

def classify_edge(
    source_id: str,
    target_id: str,
    source_tag: Optional[str],
    target_tag: Optional[str],
    edge_type: str,
    is_chat_history: bool = False,
    temporal_distance_days: int = 0
) -> Dict[str, Any]:
    """
    Phase 22 v4: Classify edges for visual differentiation.

    Types:
    - LOCAL: within same cluster (solid, opaque)
    - CROSS_CLUSTER: between different clusters (dashed, lower opacity)
    - TEMPORAL: long-range dependencies (thin, glow)
    - CHAT_HISTORY: cross-references to chat (special glow, ignores clusters)
    """
    if is_chat_history:
        return {
            'type': 'CHAT_HISTORY',
            'style': 'glow',
            'color': '#FFD700',  # Gold
            'opacity': 0.7,
            'width': 1.5,
            'glow_intensity': 0.8,
            'z_offset': 20,  # Sits in front
            'description': 'Reference from conversation'
        }

    if source_tag == target_tag and source_tag is not None:
        return {
            'type': 'LOCAL',
            'style': 'solid',
            'color': '#888888',  # Gray
            'opacity': 0.8,
            'width': 2.0,
            'z_offset': 0,
            'glow_intensity': 0.0,
            'description': 'Within cluster'
        }

    if source_tag != target_tag:
        # Cross-cluster: apply temporal logic
        if temporal_distance_days > 7:
            return {
                'type': 'TEMPORAL',
                'style': 'dotted',
                'color': '#FF6B6B',  # Red (cross-time)
                'opacity': 0.5,
                'width': 1.0,
                'z_offset': -10,  # Sits behind
                'glow_intensity': 0.4,
                'description': f'Temporal dependency ({temporal_distance_days}d apart)'
            }
        else:
            return {
                'type': 'CROSS_CLUSTER',
                'style': 'dashed',
                'color': '#3B82F6',  # Blue (cross-space)
                'opacity': 0.6,
                'width': 1.5,
                'z_offset': -5,
                'glow_intensity': 0.0,
                'description': 'Between clusters'
            }

    # Default: local edge
    return {
        'type': 'LOCAL',
        'style': 'solid',
        'color': '#888888',
        'opacity': 0.8,
        'width': 2.0,
        'z_offset': 0,
        'glow_intensity': 0.0,
        'description': 'Default edge'
    }


# ═══════════════════════════════════════════════════════════════════
# STEP 1: CLUSTERING FILES INTO TAGS
# ═══════════════════════════════════════════════════════════════════

def cluster_files_to_tags(
    embeddings_dict: Dict[str, np.ndarray],
    file_metadata: Optional[Dict[str, Dict]] = None,
    min_cluster_size: int = 2  # Phase 17.20: Reduced from 3 to 2 for more granular clusters
) -> Dict[str, KnowledgeTag]:
    """
    Group files into clusters (tags) using HDBSCAN on embeddings.

    Args:
        embeddings_dict: {file_id -> embedding vector (768D)}
        file_metadata: Optional {file_id -> {path, name, ...}}
        min_cluster_size: Minimum files per cluster for HDBSCAN

    Returns:
        Dict mapping tag_id -> KnowledgeTag
    """
    if len(embeddings_dict) < min_cluster_size:
        # Too few files - single cluster
        tag = KnowledgeTag(
            id="tag_0",
            name="All Files",
            files=list(embeddings_dict.keys()),
            color=generate_cluster_color(0)
        )
        if embeddings_dict:
            vectors = list(embeddings_dict.values())
            tag.centroid = np.mean(vectors, axis=0)
        return {"tag_0": tag}

    # Try HDBSCAN, fall back to KMeans
    try:
        from sklearn.cluster import HDBSCAN
        return _cluster_hdbscan(embeddings_dict, file_metadata, min_cluster_size)
    except ImportError:
        logger.warning("[KnowledgeLayout] HDBSCAN not available, using KMeans")
        return _cluster_kmeans(embeddings_dict, file_metadata, min_cluster_size)


def _cluster_hdbscan(
    embeddings_dict: Dict[str, np.ndarray],
    file_metadata: Optional[Dict[str, Dict]],
    min_cluster_size: int
) -> Dict[str, KnowledgeTag]:
    """HDBSCAN clustering for variable-size clusters"""
    from sklearn.cluster import HDBSCAN

    file_ids = list(embeddings_dict.keys())
    emb_matrix = np.array([embeddings_dict[fid] for fid in file_ids])

    # Normalize for cosine-like distance
    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    norms = np.where(norms < 1e-8, 1, norms)
    emb_normalized = emb_matrix / norms

    # Phase 17.20: Improved clustering parameters
    # - Lower epsilon for more granular clusters
    # - min_samples controls density requirement
    n_files = len(file_ids)

    # Adaptive parameters based on dataset size
    # Lower epsilon = more granular clusters (files must be more similar to group)
    if n_files > 100:
        epsilon = 0.15  # Very granular for large datasets
        min_samples = 3
    elif n_files > 50:
        epsilon = 0.2
        min_samples = 2
    else:
        epsilon = 0.25  # Reduced from 0.4 for smaller datasets
        min_samples = 2

    logger.info(f"[KnowledgeLayout] HDBSCAN params: n_files={n_files}, epsilon={epsilon}, min_cluster_size={min_cluster_size}")

    clusterer = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric='euclidean',
        cluster_selection_epsilon=epsilon,
        cluster_selection_method='leaf'  # More clusters, less noise
    )
    labels = clusterer.fit_predict(emb_normalized)

    logger.info(f"[KnowledgeLayout] HDBSCAN: {n_files} files, epsilon={epsilon}, found {len(set(labels)) - (1 if -1 in labels else 0)} clusters + {sum(1 for l in labels if l == -1)} noise")

    tags: Dict[str, KnowledgeTag] = {}
    unique_labels = set(labels)

    for label in unique_labels:
        if label == -1:
            # Noise points - create "Uncategorized" tag
            noise_files = [file_ids[i] for i, l in enumerate(labels) if l == -1]
            if noise_files:
                tag_id = "tag_uncategorized"
                noise_vectors = [embeddings_dict[fid] for fid in noise_files]
                tags[tag_id] = KnowledgeTag(
                    id=tag_id,
                    name="Uncategorized",
                    files=noise_files,
                    centroid=np.mean(noise_vectors, axis=0) if noise_vectors else None,
                    color="#888888"  # Grey for uncategorized
                )
            continue

        cluster_files = [file_ids[i] for i, l in enumerate(labels) if l == label]
        tag_id = f"tag_{label}"

        # Calculate centroid
        cluster_vectors = [embeddings_dict[fid] for fid in cluster_files]
        centroid = np.mean(cluster_vectors, axis=0) if cluster_vectors else None

        # Phase 17.3: Generate name from most common parent folder
        name = _generate_tag_name_from_folders(cluster_files, file_metadata, label)

        tags[tag_id] = KnowledgeTag(
            id=tag_id,
            name=name,
            files=cluster_files,
            centroid=centroid,
            color=generate_cluster_color(label)
        )

        logger.info(f"[KnowledgeLayout] Cluster {label}: {len(cluster_files)} files -> '{name}'")

    logger.info(f"[KnowledgeLayout] Created {len(tags)} tags from {len(file_ids)} files")
    return tags


def _cluster_kmeans(
    embeddings_dict: Dict[str, np.ndarray],
    file_metadata: Optional[Dict[str, Dict]],
    min_cluster_size: int
) -> Dict[str, KnowledgeTag]:
    """Fallback: KMeans clustering"""
    try:
        from sklearn.cluster import KMeans
    except ImportError:
        # Ultimate fallback: single cluster
        tag = KnowledgeTag(
            id="tag_0",
            name="All Files",
            files=list(embeddings_dict.keys()),
            color=generate_cluster_color(0)
        )
        return {"tag_0": tag}

    file_ids = list(embeddings_dict.keys())
    emb_matrix = np.array([embeddings_dict[fid] for fid in file_ids])

    # Normalize
    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    norms = np.where(norms < 1e-8, 1, norms)
    emb_normalized = emb_matrix / norms

    # Determine number of clusters
    n_clusters = max(2, min(20, len(file_ids) // 5))

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(emb_normalized)

    tags: Dict[str, KnowledgeTag] = {}

    for k in range(n_clusters):
        cluster_files = [file_ids[i] for i, l in enumerate(labels) if l == k]
        if not cluster_files:
            continue

        tag_id = f"tag_{k}"
        cluster_vectors = [embeddings_dict[fid] for fid in cluster_files]
        centroid = np.mean(cluster_vectors, axis=0)

        # Phase 17.3: Generate name from most common parent folder
        name = _generate_tag_name_from_folders(cluster_files, file_metadata, k)

        tags[tag_id] = KnowledgeTag(
            id=tag_id,
            name=name,
            files=cluster_files,
            centroid=centroid,
            color=generate_cluster_color(k)
        )

        logger.info(f"[KnowledgeLayout] KMeans cluster {k}: {len(cluster_files)} files -> '{name}'")

    return tags


def _find_common_prefix(paths: List[str]) -> str:
    """Find common path prefix among files"""
    if not paths:
        return ""

    parts_list = [p.split('/') for p in paths if p]
    if not parts_list:
        return ""

    min_len = min(len(parts) for parts in parts_list)
    common = []

    for i in range(min_len):
        current = parts_list[0][i]
        if all(parts[i] == current for parts in parts_list):
            common.append(current)
        else:
            break

    return '/'.join(common)


def _check_project_overlap(
    files1: List[str],
    files2: List[str],
    file_metadata: Optional[Dict[str, Dict]] = None
) -> float:
    """
    Phase 22 v2: Check how much two file sets share the same project/path structure.

    Returns overlap score 0.0-1.0:
    - 1.0 = same project (identical path prefixes)
    - 0.5 = related (share some path components)
    - 0.0 = different projects

    This prevents cross-project parenting in hierarchy.
    """
    if not file_metadata or not files1 or not files2:
        return 0.5  # No metadata - neutral

    # Get paths for each file set
    paths1 = [file_metadata.get(f, {}).get('path', '') for f in files1 if f in file_metadata]
    paths2 = [file_metadata.get(f, {}).get('path', '') for f in files2 if f in file_metadata]

    if not paths1 or not paths2:
        return 0.5

    # Find project roots (first 3-4 path components typically identify project)
    def get_project_root(path: str, depth: int = 4) -> str:
        parts = path.split('/')
        return '/'.join(parts[:min(depth, len(parts))])

    roots1 = set(get_project_root(p) for p in paths1 if p)
    roots2 = set(get_project_root(p) for p in paths2 if p)

    if not roots1 or not roots2:
        return 0.5

    # Calculate overlap
    intersection = roots1 & roots2
    union = roots1 | roots2

    if not union:
        return 0.5

    overlap = len(intersection) / len(union)
    return overlap


def _is_bad_root_candidate(tag_name: str) -> bool:
    """
    Phase 22 v2: Check if tag name is a bad root candidate.

    These are typically utility/meta folders that shouldn't be tree roots:
    - chat_history, data, output, cache, logs, etc.
    """
    bad_names = [
        'chat_history', 'chat', 'history', 'data', 'output',
        'cache', 'logs', 'temp', 'tmp', 'backup', 'archive',
        'uncategorized', 'cluster', '__pycache__', 'node_modules',
        'dist', 'build', '.git', 'venv', 'env'
    ]
    name_lower = tag_name.lower().strip()

    for bad in bad_names:
        if bad in name_lower:
            return True

    return False


# Phase 17.20: Semantic tag anchors (imported from SemanticTagger concept)
# Organized by specificity - more specific first for better matching
SEMANTIC_TAG_ANCHORS = {
    # VETKA project-specific
    "elisya": ["elisya", "Elisya", "ELISYA", "api_aggregator", "orchestrator"],
    "orchestration": ["orchestrator", "orchestration", "memory_manager", "context"],
    "sugiyama": ["sugiyama", "Sugiyama", "layout", "crossing", "layer"],
    "tree-render": ["tree_renderer", "TreeRenderer", "three.js", "mesh", "scene"],
    "knowledge-graph": ["knowledge", "KnowledgeTag", "KnowledgeEdge", "semantic"],
    "qdrant": ["Qdrant", "qdrant", "vector", "collection", "embedding"],
    "scanner": ["scanner", "scan", "walk", "directory", "file_scanner"],
    "hostess": ["hostess", "chat", "agent", "dialogue", "conversation"],

    # General categories
    "readme": ["README", "documentation", "overview", "getting started"],
    "3d-viz": ["three.js", "visualization", "3D", "render", "camera"],
    "api": ["endpoint", "route", "REST", "HTTP", "request", "handler"],
    "config": ["configuration", "settings", "environment", "setup", "yaml", "json"],
    "test": ["test", "spec", "unittest", "pytest", "jest", "coverage"],
    "agent": ["agent", "workflow", "PM", "Dev", "QA", "eval"],
    "embedding": ["embedding", "vector", "semantic", "UMAP", "cosine"],
    "phase-docs": ["PHASE", "sprint", "milestone", "session", "status"],
    "frontend": ["frontend", "UI", "interface", "component", "visual"],
    "backend": ["backend", "server", "Flask", "API", "database"],
    "memory": ["memory", "context", "retrieval", "cache"],
    "layout": ["layout", "position", "tree", "hierarchy", "node"],
}


def _generate_tag_name_from_folders(
    cluster_file_ids: List[str],
    file_metadata: Optional[Dict[str, Dict]],
    fallback_label: int,
    cluster_embeddings: Optional[Dict[str, np.ndarray]] = None
) -> str:
    """
    Phase 17.20: Generate semantic tag name from files.

    Strategy (prioritized):
    1. Match cluster content against semantic anchors
    2. Count occurrences of parent folder names
    3. Extract common words from file names
    4. Use common path prefix
    5. Fallback to "Cluster {label}"
    """
    import re

    if not file_metadata:
        return f"Cluster {fallback_label}"

    # Collect all text from cluster for semantic matching
    all_text_parts = []
    folder_counts: Dict[str, int] = {}
    word_counts: Dict[str, int] = {}

    for file_id in cluster_file_ids:
        meta = file_metadata.get(file_id, {})
        file_path = meta.get('path', '')
        file_name = meta.get('name', '') or os.path.basename(file_path)
        content_snippet = meta.get('content', '')[:200] if meta.get('content') else ''

        # Collect text for semantic matching
        all_text_parts.extend([file_path, file_name, content_snippet])

        # Strategy 2: Count folder names
        if file_path:
            parent_dir = os.path.dirname(file_path)
            if parent_dir:
                folder_name = os.path.basename(parent_dir)
                if folder_name and folder_name not in ['.', '..', '', 'src', 'lib', 'app']:
                    folder_counts[folder_name] = folder_counts.get(folder_name, 0) + 1

        # Strategy 3: Extract meaningful words from file names
        if file_name:
            name_no_ext = os.path.splitext(file_name)[0]
            words = re.split(r'[_\-\.\s]+', name_no_ext)
            for word in words:
                word_lower = word.lower()
                if len(word_lower) >= 3 and not word_lower.isdigit():
                    if word_lower not in ['index', 'main', 'test', 'spec', 'init', 'utils', 'helpers']:
                        word_counts[word_lower] = word_counts.get(word_lower, 0) + 1

    # Strategy 1: Match against semantic anchors
    all_text = ' '.join(all_text_parts).lower()
    best_anchor = None
    best_score = 0

    for anchor_name, anchor_words in SEMANTIC_TAG_ANCHORS.items():
        score = sum(1 for w in anchor_words if w.lower() in all_text)
        if score > best_score:
            best_score = score
            best_anchor = anchor_name

    if best_anchor and best_score >= 2:  # At least 2 anchor words matched
        logger.info(f"[KnowledgeLayout] Semantic tag: '{best_anchor}' (score: {best_score})")
        return best_anchor.capitalize()

    # Strategy 2: Use folder name if found
    if folder_counts:
        most_common = max(folder_counts, key=folder_counts.get)
        if folder_counts[most_common] >= 2:
            logger.info(f"[KnowledgeLayout] Tag from folder: '{most_common}' (count: {folder_counts[most_common]})")
            return most_common.capitalize()

    # Strategy 3: Use common word from file names
    if word_counts:
        most_common = max(word_counts, key=word_counts.get)
        if word_counts[most_common] >= 2:
            logger.info(f"[KnowledgeLayout] Tag from word: '{most_common}' (count: {word_counts[most_common]})")
            return most_common.capitalize()

    # Strategy 4: Try common path prefix
    paths = [file_metadata.get(fid, {}).get('path', '') for fid in cluster_file_ids]
    common_prefix = _find_common_prefix(paths)
    if common_prefix:
        last_part = common_prefix.split('/')[-1]
        if last_part and last_part not in ['.', '..', '', 'src', 'lib']:
            return last_part.capitalize()

    # Strategy 5: Use first meaningful folder
    if folder_counts:
        return max(folder_counts, key=folder_counts.get).capitalize()

    # Final fallback
    return f"Cluster {fallback_label}"


# ═══════════════════════════════════════════════════════════════════
# STEP 1.5: BUILD TAG HIERARCHY (Phase 17.13)
# Tags form a tree like folders - not flat!
# ═══════════════════════════════════════════════════════════════════

def build_tag_hierarchy(
    tags: Dict[str, KnowledgeTag],
    embeddings_dict: Dict[str, np.ndarray],
    file_metadata: Optional[Dict[str, Dict]] = None
) -> Dict[str, KnowledgeTag]:
    """
    Build hierarchical tree of tags (like folder structure).

    Algorithm:
    1. Compute tag centroids from file embeddings
    2. Find root tag (closest to global centroid = most general)
    3. For each other tag, find semantic parent (most similar tag with lower depth)

    Phase 22 v2: Added project-aware parent selection and bad root filtering.

    Result: tags with parent_tag_id and depth set
    """
    from sklearn.metrics.pairwise import cosine_similarity

    if len(tags) <= 1:
        # Single tag is root
        for tag in tags.values():
            tag.parent_tag_id = None
            tag.depth = 0
        return tags

    # Step 1: Compute tag centroids
    tag_centroids = {}
    for tag_id, tag in tags.items():
        tag_embeddings = [embeddings_dict[fid] for fid in tag.files if fid in embeddings_dict]
        if tag_embeddings:
            tag_centroids[tag_id] = np.mean(tag_embeddings, axis=0)
            tag.centroid = tag_centroids[tag_id]

    if len(tag_centroids) < 2:
        for tag in tags.values():
            tag.parent_tag_id = None
            tag.depth = 0
        return tags

    # Step 2: Find root tag (closest to global centroid)
    # Phase 17.14: Exclude "uncategorized" from root selection - it's noise
    # Phase 22 v2: Also penalize bad root candidates (chat_history, data, etc.)
    all_centroids = list(tag_centroids.values())
    global_centroid = np.mean(all_centroids, axis=0)

    root_tag_id = None
    min_dist = float('inf')
    fallback_root_id = None  # For case when all tags are bad candidates
    fallback_min_dist = float('inf')

    for tag_id, centroid in tag_centroids.items():
        tag_name = tags[tag_id].name

        # Skip uncategorized tag - it should be leaf, not root
        if tag_id == 'tag_uncategorized' or tag_name.lower() == 'uncategorized':
            continue

        dist = 1 - cosine_similarity([centroid], [global_centroid])[0][0]

        # Phase 22 v2: Penalize bad root candidates but track them as fallback
        if _is_bad_root_candidate(tag_name):
            # Heavy penalty for bad root names
            penalized_dist = dist + 0.5
            if penalized_dist < fallback_min_dist:
                fallback_min_dist = penalized_dist
                fallback_root_id = tag_id
        else:
            # Good candidate - use normal distance
            if dist < min_dist:
                min_dist = dist
                root_tag_id = tag_id

    # Fallback hierarchy: good candidate > bad candidate > first available
    if root_tag_id is None:
        if fallback_root_id is not None:
            root_tag_id = fallback_root_id
            logger.warning(f"[TagHierarchy] Using bad root candidate as fallback: {tags[root_tag_id].name}")
        else:
            root_tag_id = list(tag_centroids.keys())[0]
            logger.warning(f"[TagHierarchy] No good root candidates, using first: {tags[root_tag_id].name}")

    # Set root
    tags[root_tag_id].parent_tag_id = None
    tags[root_tag_id].depth = 0

    # Step 3: Build hierarchy using similarity
    # Process remaining tags, assigning parents based on similarity
    assigned = {root_tag_id}
    max_iterations = len(tags) * 2  # Safety limit
    iteration = 0

    while len(assigned) < len(tags) and iteration < max_iterations:
        iteration += 1

        for tag_id, tag in tags.items():
            if tag_id in assigned:
                continue
            if tag_id not in tag_centroids:
                # No embedding - assign to root
                tag.parent_tag_id = root_tag_id
                tag.depth = 1
                assigned.add(tag_id)
                continue

            # Find best parent among already assigned tags
            best_parent_id = root_tag_id
            best_sim = -1

            for candidate_id in assigned:
                if candidate_id not in tag_centroids:
                    continue

                sim = cosine_similarity(
                    [tag_centroids[tag_id]],
                    [tag_centroids[candidate_id]]
                )[0][0]

                # Phase 22 v2: PROJECT-AWARE hierarchy building
                # Consider both semantic similarity AND path structure
                candidate_depth = tags[candidate_id].depth

                # Get file paths for both tags to check project overlap
                tag_files = tags[tag_id].files
                candidate_files = tags[candidate_id].files

                # Check if tags share common project path
                project_overlap = _check_project_overlap(tag_files, candidate_files, file_metadata)

                # Base similarity
                adjusted_sim = sim

                # Phase 22 v2: Project overlap bonus
                if project_overlap > 0.5:
                    # Strong bonus for same project (share >50% path)
                    adjusted_sim += 0.2
                elif project_overlap > 0.2:
                    # Moderate bonus for related projects
                    adjusted_sim += 0.1
                elif project_overlap < 0.1:
                    # Phase 23 FIX: Strong penalty for different projects
                    adjusted_sim *= 0.3  # Multiplicative penalty instead of additive

                # Depth influence
                if candidate_depth > 0 and sim > 0.7:
                    # Bonus for intermediate parents with good similarity
                    adjusted_sim += 0.05
                elif candidate_depth == 0:
                    # Root penalty to encourage depth
                    adjusted_sim -= 0.05

                if adjusted_sim > best_sim:
                    best_sim = adjusted_sim
                    best_parent_id = candidate_id

            tag.parent_tag_id = best_parent_id
            tag.depth = tags[best_parent_id].depth + 1
            assigned.add(tag_id)

    # Log hierarchy
    depth_counts = defaultdict(int)
    for tag in tags.values():
        depth_counts[tag.depth] += 1

    logger.info(f"[TagHierarchy] Built hierarchy with {len(tags)} tags")
    logger.info(f"[TagHierarchy] Depth distribution: {dict(depth_counts)}")
    logger.info(f"[TagHierarchy] Root tag: {tags[root_tag_id].name}")

    # Phase 23 FIX: Detect and break cycles in tag hierarchy
    cycles_broken = _detect_and_break_cycles(tags)
    if cycles_broken > 0:
        logger.warning(f"[TagHierarchy] Broke {cycles_broken} cycles in tag hierarchy")

    return tags


def _detect_and_break_cycles(tags: Dict[str, KnowledgeTag]) -> int:
    """
    Phase 23 FIX: Detect and break cycles in tag hierarchy.
    Prevents infinite depth and Three.js crashes.
    """
    cycles_broken = 0
    visited = set()
    rec_stack = set()

    def has_cycle(tag_id: str, path: list) -> bool:
        nonlocal cycles_broken
        if tag_id in rec_stack:
            # Cycle detected! Break it by setting parent to None
            logger.warning(f"[TagHierarchy] Cycle detected: {' -> '.join(path)} -> {tag_id}")
            tags[tag_id].parent_tag_id = None
            tags[tag_id].depth = 0
            cycles_broken += 1
            return True

        if tag_id in visited:
            return False

        visited.add(tag_id)
        rec_stack.add(tag_id)
        path.append(tag_id)

        parent_id = tags[tag_id].parent_tag_id
        if parent_id and parent_id in tags:
            has_cycle(parent_id, path)

        path.pop()
        rec_stack.remove(tag_id)
        return False

    for tag_id in tags:
        if tag_id not in visited:
            has_cycle(tag_id, [])

    return cycles_broken


# ═══════════════════════════════════════════════════════════════════
# STEP 2: BUILD PREREQUISITE EDGES
# ═══════════════════════════════════════════════════════════════════

def build_prerequisite_edges(
    file_ids: List[str],
    embeddings_dict: Dict[str, np.ndarray],
    tags: Dict[str, KnowledgeTag],
    similarity_threshold: float = 0.7
) -> Tuple[List[KnowledgeEdge], Dict[str, float]]:
    """
    Create edges between files based on similarity.
    Direction: less advanced (low KL) -> more advanced (high KL)

    Args:
        file_ids: List of file IDs to connect
        embeddings_dict: {file_id -> embedding}
        tags: Clusters from cluster_files_to_tags()
        similarity_threshold: Minimum cosine similarity for edge

    Returns:
        Tuple of (edges list, knowledge_levels dict)
    """
    if len(file_ids) < 2:
        return [], {fid: 0.5 for fid in file_ids}

    # Get embeddings for files
    valid_files = [fid for fid in file_ids if fid in embeddings_dict]
    if len(valid_files) < 2:
        return [], {fid: 0.5 for fid in file_ids}

    # Build embedding matrix
    vectors = np.array([embeddings_dict[fid] for fid in valid_files])

    # Normalize for cosine similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms < 1e-8, 1, norms)
    vectors_normalized = vectors / norms

    # Compute pairwise cosine similarity
    sim_matrix = np.dot(vectors_normalized, vectors_normalized.T)

    # Create undirected edges for similar pairs
    undirected_edges: List[Tuple[str, str, float]] = []

    for i in range(len(valid_files)):
        for j in range(i + 1, len(valid_files)):
            sim = sim_matrix[i][j]
            if sim >= similarity_threshold:
                undirected_edges.append((valid_files[i], valid_files[j], float(sim)))

    logger.info(f"[KnowledgeLayout] Found {len(undirected_edges)} similar pairs (threshold={similarity_threshold})")

    # Calculate in/out degree for knowledge_level
    # For undirected similarity edges, we'll compute degrees after directing them
    # First pass: count how many files each file is similar to
    similarity_count = defaultdict(int)

    for src, tgt, _ in undirected_edges:
        similarity_count[src] += 1
        similarity_count[tgt] += 1

    # CORRECTED knowledge_level formula:
    # Based on prerequisite graph structure:
    # - Many files depend on this one (high in-degree) → FOUNDATIONAL (low kl)
    # - This file depends on many others (high out-degree) → ADVANCED (high kl)
    #
    # For initial assignment, use inverse of similarity count
    # Files with many connections are more "central" = foundational
    # Files with few connections are more "peripheral" = can be advanced
    #
    # Formula: kl = 1 - (similarity_count / max_similarity_count)
    # This gives foundational (many links) LOW kl, advanced (few links) HIGH kl

    knowledge_levels: Dict[str, float] = {}
    max_count = max(similarity_count.values()) if similarity_count else 1

    # Phase 23 FIX: Collect isolated files for distributed assignment
    isolated_files = []

    for fid in file_ids:
        count = similarity_count.get(fid, 0)
        if count == 0:
            isolated_files.append(fid)  # Will distribute later
        else:
            # High count = foundational = low kl
            # Low count = advanced = high kl
            # Normalize and invert
            normalized = count / max_count
            knowledge_levels[fid] = 1.0 - normalized * 0.8  # Range: 0.2 to 1.0

    # Phase 23 FIX: Distribute isolated files across 0.3-0.7 range
    # Sort by file ID for stable ordering (no file_metadata available here)
    if isolated_files:
        isolated_files.sort()  # Sort by ID string for stable ordering
        for idx, fid in enumerate(isolated_files):
            # Spread across 0.3-0.7 range instead of all at 0.5
            if len(isolated_files) > 1:
                knowledge_levels[fid] = 0.3 + (idx / (len(isolated_files) - 1)) * 0.4
            else:
                knowledge_levels[fid] = 0.5
        logger.info(f"[KnowledgeLayout] Distributed {len(isolated_files)} isolated files across KL 0.3-0.7")

    # Now direct edges from low KL to high KL (foundational -> advanced)
    directed_edges: List[KnowledgeEdge] = []

    for src, tgt, weight in undirected_edges:
        kl_src = knowledge_levels.get(src, 0.5)
        kl_tgt = knowledge_levels.get(tgt, 0.5)

        if kl_src <= kl_tgt:
            directed_edges.append(KnowledgeEdge(
                source=src,
                target=tgt,
                edge_type='prerequisite',
                weight=weight
            ))
        else:
            directed_edges.append(KnowledgeEdge(
                source=tgt,
                target=src,
                edge_type='prerequisite',
                weight=weight
            ))

    logger.info(f"[KnowledgeLayout] Created {len(directed_edges)} prerequisite edges")
    logger.info(f"[KnowledgeLayout] KL range: {min(knowledge_levels.values()):.2f} - {max(knowledge_levels.values()):.2f}")

    return directed_edges, knowledge_levels


# ═══════════════════════════════════════════════════════════════════
# STEP 3: BUILD PREREQUISITE CHAINS ("Shashlik on Skewer")
# Files form CHAINS - only the ROOT connects to tag
# ═══════════════════════════════════════════════════════════════════

# Phase 23 FIX: Dynamic max branches based on cluster size
def get_max_branches(cluster_size: int) -> int:
    """Dynamic branch limit: min 5, max 15, scales with sqrt(cluster_size)"""
    return max(5, min(15, int(math.sqrt(cluster_size) * 2)))

MAX_BRANCHES_PER_NODE = 5  # Default fallback (use get_max_branches() instead)

@dataclass
class PrerequisiteChain:
    """A chain of files ordered by knowledge_level"""
    tag_id: str
    chain_index: int  # Index within tag's chains
    files: List[str]  # Ordered from root (lowest KL) to tip (highest KL)
    root_file: str    # The file that connects to tag


def build_prerequisite_chains(
    tag_id: str,
    file_ids: List[str],
    knowledge_levels: Dict[str, float],
    edges: List[KnowledgeEdge]
) -> List[PrerequisiteChain]:
    """
    Build prerequisite chains within a cluster.
    Each chain is a sequence of files connected by prerequisite edges.

    Args:
        tag_id: The tag/cluster these files belong to
        file_ids: Files in this cluster
        knowledge_levels: {file_id -> knowledge_level}
        edges: Prerequisite edges (source=lower KL, target=higher KL)

    Returns:
        List of PrerequisiteChain objects
    """
    if not file_ids:
        return []

    # Build adjacency for this cluster only
    # children[file_id] = list of files that depend on this file
    children: Dict[str, List[str]] = defaultdict(list)
    parents: Dict[str, List[str]] = defaultdict(list)
    file_set = set(file_ids)

    for edge in edges:
        if edge.source in file_set and edge.target in file_set:
            children[edge.source].append(edge.target)
            parents[edge.target].append(edge.source)

    # Find chain roots: files with no parents (in_degree = 0)
    # These are the most foundational files
    roots = [f for f in file_ids if not parents.get(f)]

    # If no explicit roots, use files with lowest KL
    if not roots:
        sorted_by_kl = sorted(file_ids, key=lambda f: knowledge_levels.get(f, 0.5))
        roots = sorted_by_kl[:max(1, len(sorted_by_kl) // 5)]  # Bottom 20%

    # Phase 23 FIX: Dynamic branch limit based on cluster size
    max_branches = get_max_branches(len(file_ids))
    if len(roots) > max_branches:
        # Keep only the most foundational roots
        roots = sorted(roots, key=lambda f: knowledge_levels.get(f, 0.5))[:max_branches]
        logger.debug(f"[KnowledgeLayout] Limited roots to {max_branches} for cluster of {len(file_ids)} files")

    # Build chains starting from each root
    chains = []
    visited = set()

    for chain_idx, root in enumerate(roots):
        chain_files = []
        queue = [root]

        while queue:
            # Sort by KL to process in order
            queue.sort(key=lambda f: knowledge_levels.get(f, 0.5))
            current = queue.pop(0)

            if current in visited:
                continue

            visited.add(current)
            chain_files.append(current)

            # Add unvisited children (files that depend on this one)
            for child in children.get(current, []):
                if child not in visited:
                    queue.append(child)

        if chain_files:
            # Sort by KL ascending (foundational first)
            chain_files.sort(key=lambda f: knowledge_levels.get(f, 0.5))

            chains.append(PrerequisiteChain(
                tag_id=tag_id,
                chain_index=chain_idx,
                files=chain_files,
                root_file=chain_files[0]  # Lowest KL file is root
            ))

    # Handle isolated files (not connected to any chain)
    isolated = [f for f in file_ids if f not in visited]
    if isolated:
        # Create a single chain for isolated files
        isolated.sort(key=lambda f: knowledge_levels.get(f, 0.5))
        chains.append(PrerequisiteChain(
            tag_id=tag_id,
            chain_index=len(chains),
            files=isolated,
            root_file=isolated[0]
        ))

    logger.info(f"[Chains] Tag {tag_id}: {len(chains)} chains from {len(file_ids)} files")
    for i, chain in enumerate(chains):
        logger.info(f"  Chain {i}: {len(chain.files)} files, root KL={knowledge_levels.get(chain.root_file, 0):.2f}")

    return chains


# ═══════════════════════════════════════════════════════════════════
# STEP 3.5: ADAPTIVE SPREAD FORMULA (Phase 17.16)
# Self-regulating spread based on intra-group similarity
# ═══════════════════════════════════════════════════════════════════

def compute_adaptive_spread(
    files: List[str],
    embeddings: Dict[str, np.ndarray],
    base_spread: float = 80
) -> float:
    """
    Phase 17.16: Adaptive spread based on intra-group similarity.

    High similarity (0.9+) → tight spread (files very related)
    Low similarity (0.5)  → wide spread (files diverse)

    Formula: gradient = sum(context) / num(info_objects)

    Args:
        files: List of file IDs
        embeddings: {file_id -> embedding vector}
        base_spread: Base spread value (default 80)

    Returns:
        Adaptive spread value
    """
    if len(files) < 2:
        return base_spread

    from sklearn.metrics.pairwise import cosine_similarity

    # Get embeddings for files
    file_embs = [embeddings[f] for f in files if f in embeddings]
    if len(file_embs) < 2:
        return base_spread

    # Compute similarity matrix
    emb_matrix = np.array(file_embs)
    sim_matrix = cosine_similarity(emb_matrix)
    n = len(file_embs)

    # Average pairwise similarity (upper triangle, excluding diagonal)
    total = 0.0
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += sim_matrix[i][j]
            count += 1

    avg_sim = total / count if count > 0 else 0.5

    # Map similarity to spread factor
    # avg_sim = 0.9+ → spread_factor = 0.3 (tight)
    # avg_sim = 0.5  → spread_factor = 1.0 (wide)
    spread_factor = 1.0 - (avg_sim - 0.5) * 1.4
    spread_factor = max(0.3, min(1.0, spread_factor))

    result = base_spread * spread_factor
    logger.debug(f"[AdaptiveSpread] {len(files)} files, avg_sim={avg_sim:.2f}, factor={spread_factor:.2f}, spread={result:.0f}px")

    return result


# ═══════════════════════════════════════════════════════════════════
# STEP 4: CALCULATE KNOWLEDGE MODE POSITIONS
# Phase 17.16: UNIFIED SUGIYAMA ENGINE with anti-gravity and adaptive spread
# - Tags are positioned using the SAME Sugiyama algorithm as folders
# - Y = depth in tag hierarchy (from DAG/hierarchy)
# - X = semantic similarity within layer (barycenter method)
# - minimize_crossings() for optimal edge layout
# - apply_soft_repulsion() for anti-gravity
# - Files fan out below their parent tags with adaptive spread
# - Z = 0 ALWAYS (flat 2D tree)
# ═══════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════
# PHASE 22: RRF (Reciprocal Rank Fusion) for Hybrid Search
# Grok Research December 2025 - Microsoft GraphRAG optimal k=80
# ═══════════════════════════════════════════════════════════════════

def compute_rrf_scores(
    vector_results: List[Dict],
    keyword_results: Optional[List[Dict]] = None,
    graph_results: Optional[List[Dict]] = None,
    k: int = 80,
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    """
    Phase 22: RRF (Reciprocal Rank Fusion) - Hybrid search scoring.

    Combines multiple ranking sources into a unified score using the RRF formula:
    score_RRF(d) = Σ w_i × 1/(k + rank_i(d))

    Research basis: Microsoft GraphRAG 2025, k=80 optimal for hybrid search.

    Args:
        vector_results: Results from vector/semantic search (Qdrant)
                       Each dict should have 'id' or 'path' field
        keyword_results: Results from BM25/keyword search (optional)
        graph_results: Results from graph-based search (optional)
        k: RRF constant (default 80, optimal for hybrid search)
        weights: Custom weights {'vector': 0.45, 'keyword': 0.35, 'graph': 0.20}

    Returns:
        Dict[str, float]: {doc_id -> rrf_score}
        Higher scores = more relevant across multiple sources

    Example:
        >>> vector_hits = [{'id': 'a', 'score': 0.9}, {'id': 'b', 'score': 0.8}]
        >>> keyword_hits = [{'id': 'b', 'score': 0.95}, {'id': 'a', 'score': 0.7}]
        >>> scores = compute_rrf_scores(vector_hits, keyword_hits)
        >>> # 'b' will score higher (rank 1 in keyword, rank 2 in vector)
    """
    if weights is None:
        weights = {'vector': 0.45, 'keyword': 0.35, 'graph': 0.20}

    scores: Dict[str, float] = defaultdict(float)

    def extract_id(result: Dict) -> str:
        """Extract document ID from result dict"""
        return str(result.get('id') or result.get('path') or result.get('file_id', ''))

    # Vector search scores (primary source - Qdrant)
    if vector_results:
        for rank, result in enumerate(vector_results, 1):
            doc_id = extract_id(result)
            if doc_id:
                scores[doc_id] += weights.get('vector', 0.45) * (1 / (k + rank))

    # Keyword/BM25 scores (secondary source - Weaviate)
    if keyword_results:
        for rank, result in enumerate(keyword_results, 1):
            doc_id = extract_id(result)
            if doc_id:
                scores[doc_id] += weights.get('keyword', 0.35) * (1 / (k + rank))

    # Graph-based scores (tertiary source - graph distance/PageRank)
    if graph_results:
        for rank, result in enumerate(graph_results, 1):
            doc_id = extract_id(result)
            if doc_id:
                scores[doc_id] += weights.get('graph', 0.20) * (1 / (k + rank))

    logger.info(f"[RRF] Computed scores for {len(scores)} documents "
                f"(vector={len(vector_results) if vector_results else 0}, "
                f"keyword={len(keyword_results) if keyword_results else 0}, "
                f"graph={len(graph_results) if graph_results else 0})")

    return dict(scores)


def compute_knowledge_level_rrf(
    node_id: str,
    pagerank_scores: Dict[str, float],
    parent_rrf_scores: Dict[str, float],
    depth: int,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Phase 22: Compute Knowledge Level with RRF-enhanced scoring.

    Formula: Y = 0.6 × PageRank + 0.3 × avg_RRF_parents + 0.2 × 1/(1+depth)

    - Base concepts (low PageRank) → bottom of tree
    - Advanced concepts (high PageRank) → top of tree

    Args:
        node_id: ID of the node
        pagerank_scores: {node_id -> PageRank score (0-1)}
        parent_rrf_scores: {node_id -> average RRF of parent nodes}
        depth: Depth in the tree hierarchy
        weights: Custom weights (default: pagerank=0.6, parent_rrf=0.3, depth=0.2)

    Returns:
        float: Knowledge level score (0-1), higher = more advanced
    """
    if weights is None:
        weights = {'pagerank': 0.6, 'parent_rrf': 0.3, 'depth': 0.2}

    pagerank = pagerank_scores.get(node_id, 0.5)
    parent_rrf = parent_rrf_scores.get(node_id, 0.5)
    depth_factor = 1 / (1 + depth)

    knowledge_level = (
        weights.get('pagerank', 0.6) * pagerank +
        weights.get('parent_rrf', 0.3) * parent_rrf +
        weights.get('depth', 0.2) * depth_factor
    )

    return min(1.0, max(0.0, knowledge_level))


def compute_semantic_spread_rrf(
    node_embedding: np.ndarray,
    parent_embedding: Optional[np.ndarray],
    siblings_count: int,
    rrf_score: float = 0.5
) -> float:
    """
    Phase 22: Compute X-axis spread with semantic similarity and RRF.

    Formula: X-offset = 0.5 × cosine_sim + 0.3 × 1/(1+siblings) + 0.2 × rrf_score

    - Similar to parent → closer to center
    - Many siblings → wider spread
    - Higher RRF → more prominent position

    Args:
        node_embedding: Embedding vector of current node
        parent_embedding: Embedding vector of parent (None for root)
        siblings_count: Number of sibling nodes
        rrf_score: RRF score of this node (0-1)

    Returns:
        float: Spread factor (0-1), used to calculate X position
    """
    # Base spread from siblings
    sibling_factor = 1 / (1 + siblings_count)

    # Semantic similarity to parent
    if parent_embedding is not None and node_embedding is not None:
        try:
            norm_node = np.linalg.norm(node_embedding)
            norm_parent = np.linalg.norm(parent_embedding)
            if norm_node > 0 and norm_parent > 0:
                cosine_sim = np.dot(node_embedding, parent_embedding) / (norm_node * norm_parent)
                cosine_sim = (cosine_sim + 1) / 2  # Normalize to 0-1
            else:
                cosine_sim = 0.5
        except Exception:
            cosine_sim = 0.5
    else:
        cosine_sim = 0.5

    # Combined spread factor
    spread = (
        0.5 * cosine_sim +
        0.3 * sibling_factor +
        0.2 * rrf_score
    )

    return min(1.0, max(0.0, spread))


# Layout Constants (aligned with Sugiyama engine)
MAX_Y = 3000                    # Maximum Y spread for Sugiyama
# Phase 22 v2: ADAPTIVE spreads computed dynamically from node count
# These are BASE values that get multiplied by adaptive factors
BASE_LAYER_WIDTH = 2000         # Base width, scaled by tag count
BASE_TAG_SPACING = 150          # Base spacing between sibling tags
BASE_X_SPREAD = 800             # Base X spread for root tags
Z_OFFSET = 0                    # Z offset (0 for flat tree)

# File positioning under tags - BASE values scaled by file count
BASE_FILE_SPREAD = 200          # Base spread per file group
BASE_FILE_STEP_Y = 40           # Base Y step between rows
BASE_FILE_START_OFFSET = 60     # Base Y offset from tag
BASE_FILES_PER_ROW = 6          # Base files per row

def compute_adaptive_layout_params(num_tags: int, num_files: int) -> dict:
    """
    Phase 22 v2: Compute adaptive layout parameters based on actual data size.

    Args:
        num_tags: Total number of tags/clusters
        num_files: Total number of files

    Returns:
        dict with all adaptive layout parameters
    """
    import math

    # Scale factors based on data size
    tag_scale = math.sqrt(num_tags / 10) if num_tags > 10 else 1.0  # sqrt scaling for tags
    file_scale = math.sqrt(num_files / 100) if num_files > 100 else 1.0  # sqrt scaling for files

    # Compute adaptive values
    max_layer_width = BASE_LAYER_WIDTH * max(1.0, tag_scale * 1.5)
    ideal_tag_spacing = BASE_TAG_SPACING * max(1.0, tag_scale)
    x_spread = BASE_X_SPREAD * max(1.0, tag_scale * 2)  # Double scale for X spread

    # File layout - scale based on average files per tag
    avg_files_per_tag = num_files / max(1, num_tags)
    file_group_scale = math.sqrt(avg_files_per_tag / 10) if avg_files_per_tag > 10 else 1.0

    file_fan_spread = BASE_FILE_SPREAD * max(1.0, file_group_scale * 2)
    file_step_y = BASE_FILE_STEP_Y * max(1.0, file_group_scale * 0.8)
    file_start_offset = BASE_FILE_START_OFFSET * max(1.0, file_group_scale)
    max_files_per_row = int(BASE_FILES_PER_ROW * max(1.0, file_group_scale * 1.5))

    params = {
        'max_layer_width': max_layer_width,
        'ideal_tag_spacing': ideal_tag_spacing,
        'x_spread': x_spread,
        'file_fan_spread': file_fan_spread,
        'file_step_y': file_step_y,
        'file_start_offset': file_start_offset,
        'max_files_per_row': max(4, min(20, max_files_per_row))  # Clamp 4-20
    }

    logger.info(f"[KnowledgeLayout] Adaptive params for {num_tags} tags, {num_files} files:")
    logger.info(f"  max_layer_width={params['max_layer_width']:.0f}, x_spread={params['x_spread']:.0f}")
    logger.info(f"  file_fan_spread={params['file_fan_spread']:.0f}, max_files_per_row={params['max_files_per_row']}")

    return params


def calculate_knowledge_positions(
    tags: Dict[str, KnowledgeTag],
    knowledge_levels: Dict[str, float],
    edges: List[KnowledgeEdge],
    file_directory_positions: Optional[Dict[str, Dict[str, float]]] = None,
    embeddings_dict: Optional[Dict[str, np.ndarray]] = None,
    rrf_scores: Optional[Dict[str, float]] = None,  # Phase 22: RRF scores
    file_metadata: Optional[Dict[str, Dict[str, str]]] = None  # Phase 22: For temporal Z
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Phase 17.15 + Phase 22: UNIFIED SUGIYAMA ENGINE layout with RRF integration.

    Uses the SAME Sugiyama algorithm as Directory Mode for tag positioning,
    then distributes files below their parent tags using similarity-based X spread.

    Phase 22 additions:
    - RRF scores influence node prominence (higher RRF = more central position)
    - Knowledge levels enhanced with RRF-based parent influence

    Structure:
    - Tags form a TREE (parent-child hierarchy based on semantic similarity)
    - Y = depth from Sugiyama DAG layout (buckets 0-10 mapped to 100-3000)
    - X = semantic similarity within layer (barycenter method + MDS + RRF)
    - Files fan out BELOW their parent tag with similarity-based clustering
    - Z = 0 ALWAYS (flat 2D tree)

    Args:
        tags: Tag clusters from clustering
        knowledge_levels: {file_id -> kl (0-1)}
        edges: Prerequisite edges (used for file chains)
        file_directory_positions: Not used in Phase 17.15
        embeddings_dict: Optional {file_id -> embedding} for similarity-based file placement
        rrf_scores: Phase 22 - Optional {node_id -> rrf_score} for hybrid ranking

    Returns:
        Tuple of:
        - positions: {node_id -> position data}
        - chain_edges: [{source, target, type}, ...] for rendering stems
    """
    positions: Dict[str, Dict[str, Any]] = {}
    chain_edges: List[Dict[str, Any]] = []

    num_tags = len(tags)
    if num_tags == 0:
        return positions, chain_edges

    # Phase 22 v2: Count total files for adaptive layout
    total_files = sum(len(tag.files) for tag in tags.values())

    # Phase 22 v2: Compute ADAPTIVE layout parameters
    layout_params = compute_adaptive_layout_params(num_tags, total_files)
    MAX_LAYER_WIDTH = layout_params['max_layer_width']
    IDEAL_TAG_SPACING = layout_params['ideal_tag_spacing']
    X_SPREAD = layout_params['x_spread']
    FILE_FAN_SPREAD = layout_params['file_fan_spread']
    FILE_STEP_Y = layout_params['file_step_y']
    FILE_START_OFFSET = layout_params['file_start_offset']
    MAX_FILES_PER_ROW = layout_params['max_files_per_row']

    # Phase 22: Initialize RRF scores if not provided
    if rrf_scores is None:
        rrf_scores = {}

    # Log RRF integration status
    rrf_count = len(rrf_scores)
    if rrf_count > 0:
        logger.info(f"[KnowledgeLayout] Phase 22: RRF scores available for {rrf_count} nodes")

    logger.info(f"[KnowledgeLayout] Phase 22 v2: ADAPTIVE SUGIYAMA for {num_tags} tags, {total_files} files")

    # ═══════════════════════════════════════════════════════════════
    # STEP 1: Convert tags to Sugiyama node format
    # Treat tags like semantic nodes - use their centroids as embeddings
    # ═══════════════════════════════════════════════════════════════

    tag_nodes: Dict[str, Any] = {}
    for tag_id, tag in tags.items():
        tag_nodes[tag_id] = {
            'id': tag_id,
            'type': 'concept',  # Sugiyama uses 'concept' for non-file nodes
            'embedding': tag.centroid,
            'name': tag.name,
            'depth': tag.depth
        }

    # ═══════════════════════════════════════════════════════════════
    # STEP 2: Build prerequisite edges between tags (parent->child)
    # This creates the DAG structure for Sugiyama
    # ═══════════════════════════════════════════════════════════════

    tag_edges: List[Dict[str, Any]] = []
    for tag_id, tag in tags.items():
        if tag.parent_tag_id and tag.parent_tag_id in tags:
            tag_edges.append({
                'source': tag.parent_tag_id,
                'target': tag_id,
                'type': 'prerequisite'  # Sugiyama uses 'prerequisite' for hierarchy
            })

    logger.info(f"[KnowledgeLayout] Built {len(tag_edges)} tag hierarchy edges")

    # ═══════════════════════════════════════════════════════════════
    # STEP 3: Position tags using Sugiyama-style layout
    # Use pre-computed depths for Y, similarity-based distribution for X
    # ═══════════════════════════════════════════════════════════════

    # Phase 17.15: Use direct depth-based positioning for tags
    # (Sugiyama's DAG-based knowledge_level calculation doesn't work well
    # for our tag hierarchy because we already have explicit parent-child)

    # Group tags by depth (like Sugiyama layers)
    layers: Dict[int, List[str]] = {}
    max_depth = 0
    for tag_id, tag in tags.items():
        depth = tag.depth
        max_depth = max(max_depth, depth)
        if depth not in layers:
            layers[depth] = []
        layers[depth].append(tag_id)

    logger.info(f"[KnowledgeLayout] Tag layer distribution: {[(d, len(n)) for d, n in sorted(layers.items())]}")

    # Calculate X positions using similarity-based distribution (from Sugiyama)
    tag_embeddings = {tag_id: tag.centroid for tag_id, tag in tags.items()
                      if tag.centroid is not None}

    # Position tags layer by layer
    # Phase 17.20 FIX: Children should be positioned relative to their parent!
    # This creates tree structure like Directory Mode
    tag_positions: Dict[str, Dict[str, float]] = {}

    # Constants for tag layout (Phase 17.20: closer to Directory Mode)
    TAG_Y_BASE = 100
    TAG_LAYER_HEIGHT = 150  # Reduced from 250 to be closer to Directory Mode's 80 * ~2
    CHILD_SPREAD = 300  # Fallback X spread for children under a parent

    # First, position root layer (depth 0)
    root_tags = layers.get(0, [])
    if root_tags:
        if len(root_tags) > 1 and len(tag_embeddings) >= 2:
            root_x_positions = distribute_by_similarity(root_tags, tag_embeddings, X_SPREAD)
        else:
            root_x_positions = distribute_horizontally(len(root_tags), X_SPREAD)

        for i, tag_id in enumerate(root_tags):
            tag_positions[tag_id] = {
                'x': float(root_x_positions[i]) if i < len(root_x_positions) else 0.0,
                'y': float(TAG_Y_BASE),
                'z': 0.0,
                'layer': 0
            }

    # Then position each subsequent layer - children relative to parents!
    for depth in sorted(layers.keys()):
        if depth == 0:
            continue  # Already positioned

        layer_tags = layers[depth]
        y = TAG_Y_BASE + depth * TAG_LAYER_HEIGHT

        # Group children by parent
        children_by_parent: Dict[str, List[str]] = {}
        orphans = []

        for tag_id in layer_tags:
            parent_id = tags[tag_id].parent_tag_id
            if parent_id and parent_id in tag_positions:
                if parent_id not in children_by_parent:
                    children_by_parent[parent_id] = []
                children_by_parent[parent_id].append(tag_id)
            else:
                orphans.append(tag_id)

        # Position children under each parent
        for parent_id, children in children_by_parent.items():
            parent_x = tag_positions[parent_id]['x']
            n_children = len(children)

            # Phase 17.20: Adaptive spacing like Directory Mode
            # If too many children, reduce spacing to fit MAX_LAYER_WIDTH
            ideal_width = (n_children - 1) * IDEAL_TAG_SPACING if n_children > 1 else 0
            max_group_width = MAX_LAYER_WIDTH / 2  # Each group gets half max width

            if ideal_width > max_group_width and n_children > 1:
                effective_spacing = max_group_width / (n_children - 1)
                logger.info(f"[KnowledgeLayout] Children under '{tags[parent_id].name}': {n_children} tags, spacing reduced {IDEAL_TAG_SPACING}→{effective_spacing:.0f}")
            else:
                effective_spacing = IDEAL_TAG_SPACING

            # Compute X positions - use similarity if available, otherwise even distribution
            child_embeddings = {c: tag_embeddings[c] for c in children if c in tag_embeddings}
            spread = effective_spacing * (n_children - 1) if n_children > 1 else CHILD_SPREAD

            if len(child_embeddings) >= 2:
                # Semantic spread adjusted by effective spacing
                semantic_spread = compute_adaptive_spread(children, child_embeddings, spread)
                child_x_offsets = distribute_by_similarity(children, child_embeddings, semantic_spread)
            else:
                child_x_offsets = distribute_horizontally(n_children, spread)

            for i, child_id in enumerate(children):
                offset_x = child_x_offsets[i] if i < len(child_x_offsets) else 0
                tag_positions[child_id] = {
                    'x': parent_x + offset_x,  # RELATIVE to parent!
                    'y': float(y),
                    'z': 0.0,
                    'layer': depth
                }
                logger.debug(f"[KnowledgeLayout] Tag '{tags[child_id].name}' under parent '{tags[parent_id].name}': x={parent_x + offset_x:.0f}")

        # Position orphans (no valid parent) using similarity
        if orphans:
            if len(orphans) > 1 and len(tag_embeddings) >= 2:
                orphan_x_positions = distribute_by_similarity(orphans, tag_embeddings, X_SPREAD)
            else:
                orphan_x_positions = distribute_horizontally(len(orphans), X_SPREAD)

            for i, tag_id in enumerate(orphans):
                tag_positions[tag_id] = {
                    'x': float(orphan_x_positions[i]) if i < len(orphan_x_positions) else 0.0,
                    'y': float(y),
                    'z': 0.0,
                    'layer': depth
                }

    logger.info(f"[KnowledgeLayout] Phase 17.20: Positioned {len(tag_positions)} tags with parent-relative X")

    # ═══════════════════════════════════════════════════════════════
    # Phase 17.16: Apply minimize_crossings and soft_repulsion
    # Same as Directory Mode for consistent tree visualization
    # ═══════════════════════════════════════════════════════════════

    # Build tag edges for minimize_crossings
    tag_hierarchy_edges = []
    for tag_id, tag in tags.items():
        if tag.parent_tag_id and tag.parent_tag_id in tags:
            tag_hierarchy_edges.append({
                'source': tag.parent_tag_id,
                'target': tag_id,
                'type': 'prerequisite'
            })

    # Phase 17.20: DISABLED minimize_crossings for Knowledge Mode
    # Reason: It destroys semantic X positioning from distribute_by_similarity()
    # The Phase 17.19 fix preserves spacing but loses node↔position correspondence
    # For Knowledge Mode, semantic similarity is MORE important than crossing reduction
    #
    # if len(tag_hierarchy_edges) > 0 and len(layers) > 1:
    #     minimize_crossings(tag_positions, layers, tag_hierarchy_edges, iterations=5, x_spread=X_SPREAD)
    #     logger.info("[KnowledgeLayout] Applied minimize_crossings (barycenter method)")
    logger.info("[KnowledgeLayout] Phase 17.20: Skipped minimize_crossings to preserve semantic X")

    # Apply soft repulsion to avoid overlap (anti-gravity)
    apply_soft_repulsion_semantic(tag_positions, layers, iterations=3, min_distance=120, repulsion_strength=0.4)
    logger.info("[KnowledgeLayout] Applied soft_repulsion (anti-gravity)")

    # Store tag positions and update tag objects
    for tag_id, tag in tags.items():
        if tag_id in tag_positions:
            pos = tag_positions[tag_id]
            tag_x = pos['x']
            tag_y = pos['y']
            tag_z = pos.get('z', 0)
            depth = pos.get('layer', tag.depth)
        else:
            # Fallback if tag not in Sugiyama result
            tag_x = 0
            tag_y = 100 + tag.depth * 300
            tag_z = 0
            depth = tag.depth

        tag.position = {'x': tag_x, 'y': tag_y, 'z': tag_z}

        # Phase 22: Compute aggregate RRF score for tag (average of files' RRF)
        tag_rrf = 0.0
        if rrf_scores and tag.files:
            file_rrf_values = [rrf_scores.get(f, 0.0) for f in tag.files]
            tag_rrf = sum(file_rrf_values) / len(file_rrf_values) if file_rrf_values else 0.0

        positions[tag_id] = {
            'x': tag_x,
            'y': tag_y,
            'z': tag_z,
            'type': 'tag',
            'depth': depth,
            'parent_tag': tag.parent_tag_id,
            'name': tag.name,
            'color': tag.color,
            'file_count': len(tag.files),
            'rrf_score': tag_rrf  # Phase 22: RRF score for hybrid ranking
        }

        logger.info(f"[KnowledgeLayout] Tag '{tag.name}' depth={depth} at ({tag_x:.0f}, {tag_y:.0f}) - {len(tag.files)} files")

    # ═══════════════════════════════════════════════════════════════
    # Phase 17.20: Add tag→tag hierarchy edges for tree visualization
    # ═══════════════════════════════════════════════════════════════

    for tag_id, tag in tags.items():
        if tag.parent_tag_id and tag.parent_tag_id in positions:
            chain_edges.append({
                'source': tag.parent_tag_id,
                'target': tag_id,
                'type': 'tag_to_tag',
                'chain_index': 0
            })
            logger.debug(f"[KnowledgeLayout] Tag edge: {tag.parent_tag_id} → {tag_id}")

    logger.info(f"[KnowledgeLayout] Added {sum(1 for e in chain_edges if e['type'] == 'tag_to_tag')} tag→tag hierarchy edges")

    # ═══════════════════════════════════════════════════════════════
    # STEP 4: Build chains for each tag (optional, for prerequisite ordering)
    # ═══════════════════════════════════════════════════════════════

    all_chains: List[PrerequisiteChain] = []
    for tag_id, tag in tags.items():
        tag_chains = build_prerequisite_chains(
            tag_id=tag_id,
            file_ids=tag.files,
            knowledge_levels=knowledge_levels,
            edges=edges
        )
        all_chains.extend(tag_chains)

    # ═══════════════════════════════════════════════════════════════
    # STEP 5: Position files below their parent tags
    # Phase 17.16: Use adaptive spread based on intra-group similarity
    # ═══════════════════════════════════════════════════════════════

    for tag_id, tag in tags.items():
        tag_pos = positions[tag_id]
        tag_y = tag_pos['y']
        tag_x = tag_pos['x']
        tag_depth = tag_pos.get('depth', tag.depth)

        # Get files for this tag
        file_ids = tag.files
        num_files = len(file_ids)

        if num_files == 0:
            continue

        # Phase 22: Sort files by COMBINED score (knowledge_level + RRF)
        # High RRF + high knowledge → center of cluster, more prominent
        def combined_score(f):
            kl = knowledge_levels.get(f, 0.5)
            rrf = rrf_scores.get(f, 0.0) if rrf_scores else 0.0
            # Combined: 60% knowledge level + 40% RRF
            return 0.6 * kl + 0.4 * rrf

        sorted_files = sorted(file_ids, key=combined_score)

        # Phase 23 FIX: Collect modification times for Z distribution
        all_file_mtimes = []
        if file_metadata:
            for fid in sorted_files:
                if fid in file_metadata:
                    meta = file_metadata.get(fid, {})
                    mtime = meta.get('mtime', meta.get('modified_time', meta.get('ctime', 0)))
                    if mtime > 0:
                        all_file_mtimes.append(mtime)

        # Get file embeddings for similarity-based X distribution
        file_embeddings = {}
        if embeddings_dict:
            file_embeddings = {f: embeddings_dict[f] for f in sorted_files if f in embeddings_dict}

        # Phase 22 v4: Compute semantic variance and KL variance for adaptive spacing
        file_emb_list = [file_embeddings[f] for f in sorted_files if f in file_embeddings]
        file_kl_list = [knowledge_levels.get(f, 0.5) for f in sorted_files]

        sem_variance = compute_semantic_variance(file_emb_list) if file_emb_list else 0.0
        kl_variance = compute_kl_variance(file_kl_list)

        # Phase 22 v4: Use ARCHITECT'S adaptive spacing formula
        spacing_params = compute_file_spacing(
            num_files_in_cluster=num_files,
            semantic_variance=sem_variance,
            knowledge_level_variance=kl_variance,
            depth=tag_depth
        )

        # Use Phase 22 v4 adaptive values instead of static constants
        adaptive_spread = spacing_params['fan_spread']

        # Phase 22: Adjust spread based on RRF variance (more important files spread wider)
        if rrf_scores:
            file_rrf_values = [rrf_scores.get(f, 0.0) for f in sorted_files]
            if len(file_rrf_values) > 1:
                rrf_variance = max(file_rrf_values) - min(file_rrf_values)
                # Higher RRF variance → wider spread (1.0 to 1.5x)
                rrf_spread_factor = 1.0 + 0.5 * rrf_variance
                adaptive_spread *= rrf_spread_factor

        logger.info(f"[KnowledgeLayout] Tag '{tag.name}': {num_files} files, sem_var={sem_variance:.2f}, kl_var={kl_variance:.2f}, spread={adaptive_spread:.0f}px")

        # Calculate X positions using Sugiyama's similarity distribution with adaptive spread
        if len(file_embeddings) >= 2:
            x_positions = distribute_by_similarity(sorted_files, file_embeddings, adaptive_spread)
        else:
            x_positions = distribute_horizontally(num_files, adaptive_spread)

        # Position files in grid layout below tag
        # Phase 22 v4: Use adaptive spacing from ARCHITECT'S formula
        tag_centroid = tag.centroid if hasattr(tag, 'centroid') and tag.centroid is not None else None

        # Phase 22 v4: Use adaptive file_spacing for Y step and radial_offset
        adaptive_file_spacing = spacing_params['file_spacing']
        adaptive_radial_offset = spacing_params['radial_offset']

        for i, file_id in enumerate(sorted_files):
            kl = knowledge_levels.get(file_id, 0.5)
            file_rrf = rrf_scores.get(file_id, 0.0) if rrf_scores else 0.0

            # Grid layout: N columns per row
            row = i // MAX_FILES_PER_ROW
            col = i % MAX_FILES_PER_ROW

            # Phase 22 v4: Y = tag_y + offset + row * adaptive_step + RRF bonus
            # Higher RRF files get slight Y boost (more prominent)
            # Use adaptive_file_spacing instead of static FILE_STEP_Y
            rrf_y_bonus = file_rrf * 20  # Up to 20px bonus for high RRF
            y = tag_y + adaptive_radial_offset + (row * adaptive_file_spacing) + rrf_y_bonus

            # Phase 22: X = similarity-based offset with RRF influence
            # High RRF files gravitate toward center
            file_embedding = embeddings_dict.get(file_id) if embeddings_dict else None

            if i < len(x_positions):
                base_x = x_positions[i]
                # RRF pull toward center: higher RRF → closer to tag_x
                rrf_center_pull = file_rrf * 0.3  # 0-30% pull toward center
                x = tag_x + base_x * (1 - rrf_center_pull)
            else:
                # Fallback: centered grid with adaptive spacing
                cols_in_row = min(MAX_FILES_PER_ROW, num_files - row * MAX_FILES_PER_ROW)
                col_offset = (col - (cols_in_row - 1) / 2) * (adaptive_file_spacing * 0.5)
                x = tag_x + col_offset

            # ═══════════════════════════════════════════════════════════════════
            # Phase 23 REFACTOR: New coordinate system
            # Y = Knowledge Level + TIME BONUS (newer files slightly higher in layer)
            # Z = ACTUALITY (surprise + interactions + highlight)
            # ═══════════════════════════════════════════════════════════════════

            # Add time bonus to Y (newer files = slightly higher within their layer)
            time_bonus = 0.0
            if file_metadata and file_id in file_metadata:
                meta = file_metadata.get(file_id, {})
                mtime = meta.get('mtime', meta.get('modified_time', meta.get('ctime', 0)))

                if mtime > 0 and all_file_mtimes:
                    min_t = min(all_file_mtimes)
                    max_t = max(all_file_mtimes)
                    if max_t > min_t and (max_t - min_t) > 60:
                        norm_mtime = (mtime - min_t) / (max_t - min_t)
                        time_bonus = norm_mtime * 30  # 0-30 pixels bonus

            y = y + time_bonus  # Add time bonus to existing Y

            # Z = ACTUALITY (not time!)
            # Components:
            # 1. surprise_metric: how unusual the file is (0-1)
            # 2. agent_interactions: how many times agents worked with it
            # 3. highlighted: agent wants to show this file
            z = 0.0
            file_surprise = 0.5  # Default middle value
            file_interactions = 0
            file_highlighted = False

            if file_metadata and file_id in file_metadata:
                meta = file_metadata.get(file_id, {})
                file_surprise = meta.get('surprise_metric', 0.5)
                file_interactions = meta.get('agent_interactions', 0)
                file_highlighted = meta.get('highlighted', False)

            z += file_surprise * 30  # 0-30 pixels based on surprise
            z += min(file_interactions * 5, 20)  # 0-20 pixels (capped)
            if file_highlighted:
                z += 50  # Temporarily boost highlighted files

            # Minimal jitter to prevent overlap (deterministic, not random)
            z += (i % 5) * 3  # 0, 3, 6, 9, 12 pattern

            z = max(0, min(100, z))  # Clamp to 0-100 range

            # Find chain info for this file
            chain_index = 0
            is_chain_root = True
            prev_in_chain = None

            for chain in all_chains:
                if chain.tag_id == tag_id and file_id in chain.files:
                    chain_index = chain.chain_index
                    is_chain_root = file_id == chain.root_file
                    file_idx_in_chain = chain.files.index(file_id)
                    if file_idx_in_chain > 0:
                        prev_in_chain = chain.files[file_idx_in_chain - 1]
                    break

            # Phase 22: Get RRF score for this file
            file_rrf = rrf_scores.get(file_id, 0.0) if rrf_scores else 0.0

            positions[file_id] = {
                'x': x,
                'y': y,
                'z': z,
                'type': 'file',
                'knowledge_level': kl,
                'parent_tag': tag_id,
                'chain_index': chain_index,
                'is_chain_root': is_chain_root,
                'prev_in_chain': prev_in_chain,
                'rrf_score': file_rrf  # Phase 22: RRF score for hybrid ranking
            }

            # Create edge from tag to file (for rendering stems)
            chain_edges.append({
                'source': tag_id,
                'target': file_id,
                'type': 'tag_to_file',
                'chain_index': chain_index
            })

    # Log stats (accept both "file" and "leaf" types)
    files_positioned = len([p for p in positions.values() if p['type'] in ['file', 'leaf']])
    logger.info(f"[KnowledgeLayout] Positioned {files_positioned} files under {num_tags} tags")
    logger.info(f"[KnowledgeLayout] Created {len(chain_edges)} chain edges")

    # Log position ranges for debugging
    if positions:
        file_positions = [(fid, p) for fid, p in positions.items() if p['type'] in ['file', 'leaf']]
        tag_positions_list = [(tid, p) for tid, p in positions.items() if p['type'] == 'tag']

        if tag_positions_list:
            tag_x_vals = [p['x'] for _, p in tag_positions_list]
            tag_y_vals = [p['y'] for _, p in tag_positions_list]
            logger.info(f"[KnowledgeLayout] Tag X range: {min(tag_x_vals):.0f} to {max(tag_x_vals):.0f}")
            logger.info(f"[KnowledgeLayout] Tag Y range: {min(tag_y_vals):.0f} to {max(tag_y_vals):.0f}")

        if file_positions:
            y_vals = [p['y'] for _, p in file_positions]
            x_vals = [p['x'] for _, p in file_positions]
            logger.info(f"[KnowledgeLayout] File X range: {min(x_vals):.0f} to {max(x_vals):.0f}")
            logger.info(f"[KnowledgeLayout] File Y range: {min(y_vals):.0f} to {max(y_vals):.0f}")

            # Phase 17.15: Log first 5 files with EXACT coordinates for debugging
            for i, (fid, p) in enumerate(file_positions[:5]):
                logger.info(f"[KnowledgeLayout] FILE[{i}] id={fid} x={p['x']:.1f} y={p['y']:.1f} z={p['z']:.1f} tag={p.get('parent_tag', '?')}")

    return positions, chain_edges


# ═══════════════════════════════════════════════════════════════════
# PHASE 108.2: CHAT NODE POSITIONING
# ═══════════════════════════════════════════════════════════════════

def calculate_decay_factor(last_activity: datetime) -> float:
    """
    Calculate decay factor for chat node opacity based on recency.

    MARKER_108_CHAT_DECAY: Phase 108.2 - Chat node temporal decay

    Args:
        last_activity: Timestamp of last chat activity

    Returns:
        float: Decay factor in range [0, 1] where 1 = most recent, 0 = oldest
               Formula: max(0, 1 - hours_since_activity / 168)
               168 hours = 1 week, so chats older than 1 week have 0 decay
    """
    now = datetime.now(timezone.utc)

    # Ensure last_activity is timezone-aware
    if last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=timezone.utc)

    delta = now - last_activity
    hours_since = delta.total_seconds() / 3600

    # Decay over 1 week (168 hours)
    decay = max(0.0, 1.0 - (hours_since / 168.0))

    return decay


def calculate_chat_positions(
    chats: List[Dict],
    file_positions: Dict[str, Dict],
    time_range: Optional[Tuple[datetime, datetime]] = None,
    y_min: float = 0,
    y_max: float = 500
) -> List[Dict]:
    """
    Calculate 3D positions for chat nodes relative to their parent files.

    MARKER_108_CHAT_POSITION: Phase 108.2 - Chat node positioning

    Positioning rules:
    - X: offset from parent file (+8-12 units to the right, staggered if multiple chats)
    - Y: temporal axis (older chats at bottom, newer at top)
      Formula: base_y + (normalized_time * height_range)
      normalized_time = (chat_timestamp - min_timestamp) / (max_timestamp - min_timestamp)
    - Z: same as parent file (keep in same "depth plane")
    - decay_factor: affects opacity (recent chats = brighter)

    Args:
        chats: List of chat dicts with keys:
               - id (str): chat UUID
               - parentId (str): file_id this chat is associated with
               - lastActivity (datetime): timestamp of last activity
               - name (str, optional): chat title
        file_positions: Dict mapping file_id to position dict with keys {x, y, z}
        time_range: Optional (min_time, max_time) for Y normalization
                    If None, will be computed from chat timestamps
        y_min: Minimum Y coordinate for timeline (default: 0)
        y_max: Maximum Y coordinate for timeline (default: 500)

    Returns:
        List of chat dicts with added 'position' key containing:
        {
            'x': float,
            'y': float,
            'z': float,
            'decay_factor': float  # 0-1, for opacity
        }
    """
    if not chats:
        logger.info("[ChatLayout] No chats to position")
        return []

    # Group chats by parent file
    chats_by_parent: Dict[str, List[Dict]] = defaultdict(list)
    for chat in chats:
        parent_id = chat.get('parentId')
        if parent_id:
            chats_by_parent[parent_id].append(chat)

    # Determine time range for Y-axis normalization
    if time_range is None:
        all_timestamps = [
            chat['lastActivity']
            for chat in chats
            if 'lastActivity' in chat and chat['lastActivity'] is not None
        ]

        if not all_timestamps:
            logger.warning("[ChatLayout] No valid timestamps found in chats")
            min_time = datetime.now(timezone.utc)
            max_time = min_time
        else:
            min_time = min(all_timestamps)
            max_time = max(all_timestamps)
    else:
        min_time, max_time = time_range

    # Ensure timezone-aware
    if min_time.tzinfo is None:
        min_time = min_time.replace(tzinfo=timezone.utc)
    if max_time.tzinfo is None:
        max_time = max_time.replace(tzinfo=timezone.utc)

    time_span = (max_time - min_time).total_seconds()
    if time_span == 0:
        time_span = 1  # Avoid division by zero

    height_range = y_max - y_min

    logger.info(f"[ChatLayout] Processing {len(chats)} chats across {len(chats_by_parent)} parent files")
    logger.info(f"[ChatLayout] Time range: {min_time} to {max_time} (span: {time_span/3600:.1f} hours)")

    # Position each chat
    positioned_chats = []

    for parent_id, parent_chats in chats_by_parent.items():
        # Get parent file position
        parent_pos = file_positions.get(parent_id)

        if parent_pos is None:
            logger.warning(f"[ChatLayout] Parent file {parent_id} not found in positions, skipping {len(parent_chats)} chats")
            continue

        # Sort chats by timestamp (oldest first)
        sorted_chats = sorted(
            parent_chats,
            key=lambda c: c.get('lastActivity', datetime.min.replace(tzinfo=timezone.utc))
        )

        # Calculate positions for each chat under this parent
        for idx, chat in enumerate(sorted_chats):
            last_activity = chat.get('lastActivity')

            if last_activity is None:
                logger.warning(f"[ChatLayout] Chat {chat.get('id', '?')} has no lastActivity, using current time")
                last_activity = datetime.now(timezone.utc)

            # Ensure timezone-aware
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)

            # MARKER_111_5: Fix "blue bars" - chats positioned in grid, not stacked
            # Calculate X/Y with proper stagger so chats don't overlap

            # Grid layout: 5 chats per row, then wrap to next row
            base_x_offset = 30   # Увеличено с 10 до 30
            stagger_x = (idx % 5) * 12  # 5 чатов в ряду: 0, 12, 24, 36, 48
            stagger_y = (idx // 5) * 25  # Новый ряд каждые 5 чатов

            x_pos = parent_pos['x'] + base_x_offset + stagger_x
            # Чаты ВЫШЕ родительского файла (не по глобальному времени)
            y_pos = parent_pos.get('y', 0) + 20 + stagger_y

            # Z stays same as parent (same depth plane)
            z_pos = parent_pos.get('z', 0.0)

            # Calculate decay factor for opacity
            decay = calculate_decay_factor(last_activity)

            # Add position to chat dict
            chat['position'] = {
                'x': float(x_pos),
                'y': float(y_pos),
                'z': float(z_pos),
                'decay_factor': float(decay)
            }

            positioned_chats.append(chat)

            logger.debug(
                f"[ChatLayout] Chat {chat.get('id', '?')[:8]} "
                f"pos=({x_pos:.1f}, {y_pos:.1f}, {z_pos:.1f}) "
                f"decay={decay:.2f} parent={parent_id[:8]}"
            )

    logger.info(f"[ChatLayout] Successfully positioned {len(positioned_chats)}/{len(chats)} chats")

    return positioned_chats


# ═══════════════════════════════════════════════════════════════════
# MAIN API FUNCTION
# ═══════════════════════════════════════════════════════════════════

def build_knowledge_graph_from_qdrant(
    qdrant_client,
    collection_name: str = "vetka_elisya",
    min_cluster_size: int = 2,  # Phase 17.20: Reduced from 3 for more clusters
    similarity_threshold: float = 0.7,
    file_directory_positions: Optional[Dict[str, Dict[str, float]]] = None,
    rrf_scores: Optional[Dict[str, float]] = None  # Phase 22: RRF scores for hybrid ranking
) -> Dict[str, Any]:
    """
    Build complete Knowledge Graph data from Qdrant collection.

    Phase 17.3 FIXED: Now accepts file directory positions so tags can
    inherit folder positions instead of clustering at Y=0.

    Phase 22: Added RRF (Reciprocal Rank Fusion) scores for hybrid search ranking.
    RRF scores influence node prominence in the visualization.

    Args:
        qdrant_client: Qdrant client instance
        collection_name: Name of Qdrant collection
        min_cluster_size: Minimum files per cluster
        similarity_threshold: Minimum similarity for edges
        file_directory_positions: {file_id -> {x, y, z}} from Directory Mode
        rrf_scores: Phase 22 - {file_id -> rrf_score} from hybrid search

    Returns:
        Dict with:
        - tags: {tag_id -> tag data}
        - edges: list of edge dicts
        - chain_edges: list of chain edge dicts
        - positions: {node_id -> position data}
        - knowledge_levels: {file_id -> knowledge_level}
        - rrf_stats: Phase 22 - {count, min, max, avg} RRF statistics
    """
    if not qdrant_client:
        logger.error("[KnowledgeLayout] No Qdrant client provided")
        return {'tags': {}, 'edges': [], 'chain_edges': [], 'positions': {}, 'knowledge_levels': {}}

    # 1. Fetch embeddings from Qdrant
    embeddings_dict: Dict[str, np.ndarray] = {}
    file_metadata: Dict[str, Dict] = {}
    offset = None

    logger.info("[KnowledgeLayout] Fetching embeddings from Qdrant...")

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

            payload = point.payload or {}
            file_metadata[file_id] = {
                'path': payload.get('path', ''),
                'name': payload.get('name', ''),
                'extension': payload.get('extension', ''),
                'type': payload.get('type', 'file')
            }

        if offset is None:
            break

    logger.info(f"[KnowledgeLayout] Loaded {len(embeddings_dict)} embeddings from Qdrant")

    # Phase 22 FIX: SAVE ORIGINAL DATA before filtering for fallback
    original_embeddings_dict = embeddings_dict.copy()
    original_file_metadata = file_metadata.copy()

    # Phase 17.21: CRITICAL FIX - Filter to only files that exist in 3D scene!
    # Qdrant may contain more files than current directory scan
    # We must only use files that the 3D scene knows about
    if file_directory_positions:
        scene_file_paths = set(file_directory_positions.keys())
        original_count = len(embeddings_dict)
        qdrant_ids = set(embeddings_dict.keys())

        # Phase 22 FIX: Create path → qdrant_id mapping
        # Frontend sends paths, Qdrant uses string IDs - need to bridge them
        path_to_qdrant_id = {}
        for qdrant_id, metadata in file_metadata.items():
            path = metadata.get('path', '')
            if path:
                path_to_qdrant_id[path] = qdrant_id

        # Debug: Show sample IDs from both sources
        logger.info(f"[KnowledgeLayout] Phase 22 ID Mapping DEBUG:")
        logger.info(f"  Qdrant sample IDs: {list(qdrant_ids)[:3]}")
        logger.info(f"  Scene sample paths: {list(scene_file_paths)[:3]}")
        logger.info(f"  Path→ID mapping size: {len(path_to_qdrant_id)}")
        if path_to_qdrant_id:
            sample_mapping = list(path_to_qdrant_id.items())[:2]
            logger.info(f"  Sample path→id mapping: {sample_mapping}")

        # Phase 23 FIX: Improved path matching with normalization + backslash handling
        scene_file_paths_normalized = {
            os.path.normpath(p.replace('\\', '/')): p for p in scene_file_paths
        }

        scene_file_ids = set()
        for qdrant_id, meta in file_metadata.items():
            file_path = meta.get('path', meta.get('file_path', ''))
            if not file_path:
                continue

            # Phase 23 FIX: Handle Windows backslashes
            normalized_path = os.path.normpath(file_path.replace('\\', '/'))

            # Check 1: Exact normalized match
            if normalized_path in scene_file_paths_normalized:
                scene_file_ids.add(qdrant_id)
                continue

            # Check 2: Match by relative path suffix
            for scene_norm, scene_orig in scene_file_paths_normalized.items():
                if normalized_path.endswith(scene_norm) or scene_norm.endswith(normalized_path):
                    scene_file_ids.add(qdrant_id)
                    break
            else:
                # Check 3: Match by filename only (last resort)
                filename = os.path.basename(normalized_path)
                for scene_norm in scene_file_paths_normalized:
                    if os.path.basename(scene_norm) == filename:
                        scene_file_ids.add(qdrant_id)
                        break

        if not scene_file_ids and file_metadata:
            logger.warning(f"[KnowledgeLayout] No files matched! scene_paths={len(scene_file_paths_normalized)}, qdrant_files={len(file_metadata)}")
            # Fallback: use all Qdrant files
            scene_file_ids = set(file_metadata.keys())
            logger.warning(f"[KnowledgeLayout] FALLBACK: Using all {len(scene_file_ids)} Qdrant files")

        # Check intersection
        matching_ids = qdrant_ids & scene_file_ids
        logger.info(f"  Matching IDs after mapping: {len(matching_ids)} (Qdrant: {len(qdrant_ids)}, Scene: {len(scene_file_ids)})")

        # Filter embeddings to only scene files
        embeddings_dict = {fid: emb for fid, emb in embeddings_dict.items()
                          if fid in scene_file_ids}
        file_metadata = {fid: meta for fid, meta in file_metadata.items()
                         if fid in scene_file_ids}

        filtered_count = len(embeddings_dict)
        logger.info(f"[KnowledgeLayout] Phase 17.21: Filtered to {filtered_count} files "
                    f"(from {original_count} in Qdrant, {len(scene_file_ids)} in 3D scene)")

        if original_count != filtered_count:
            logger.warning(f"[KnowledgeLayout] Removed {original_count - filtered_count} files "
                           f"not present in 3D scene!")

        # If NO matches, IDs are incompatible - USE FALLBACK!
        if filtered_count == 0 and original_count > 0:
            logger.error(f"[KnowledgeLayout] NO MATCHING IDs! ID formats incompatible!")
            logger.error(f"  First Qdrant ID: {list(qdrant_ids)[0] if qdrant_ids else 'none'}")
            logger.error(f"  First Scene ID: {list(scene_file_ids)[0] if scene_file_ids else 'none'}")
            # Phase 22 FIX: RESTORE original data from saved copies
            logger.warning("[KnowledgeLayout] FALLBACK: Restoring ALL Qdrant files due to ID mismatch!")
            embeddings_dict = original_embeddings_dict
            file_metadata = original_file_metadata
            logger.info(f"[KnowledgeLayout] Restored {len(embeddings_dict)} embeddings for fallback processing")
    else:
        logger.warning("[KnowledgeLayout] No file_directory_positions provided - using ALL Qdrant files!")

    if not embeddings_dict:
        return {'tags': {}, 'edges': [], 'positions': {}, 'knowledge_levels': {}}

    # 2. Cluster files into tags
    tags = cluster_files_to_tags(embeddings_dict, file_metadata, min_cluster_size)

    # 2.1 Phase 22 v4: Ensure INTAKE branch exists for unclassified files
    tags = ensure_intake_branch(tags)

    # 2.5 Phase 17.13: Build tag hierarchy (parent-child relationships)
    # Phase 22 v2: Pass file_metadata for project-aware parent selection
    tags = build_tag_hierarchy(tags, embeddings_dict, file_metadata)
    logger.info(f"[KnowledgeLayout] Tag hierarchy built with {len(tags)} tags")

    # 3. Build prerequisite edges
    file_ids = list(embeddings_dict.keys())
    edges, knowledge_levels = build_prerequisite_edges(
        file_ids, embeddings_dict, tags, similarity_threshold
    )

    # Phase 23 FIX: Simplified RRF fallback when not provided
    # Instead of computing similarity (which is uniform within clusters),
    # use stable path-based ranking for consistent ordering
    if rrf_scores is None:
        logger.warning("[KnowledgeLayout] Phase 23: RRF scores not provided, using path-based ranking")

        # Sort files by path for stable, deterministic ranking
        sorted_file_ids = sorted(
            file_ids,
            key=lambda fid: file_metadata.get(fid, {}).get('path', fid) if file_metadata else fid
        )

        # Assign RRF scores based on position (1/(rank+k) formula)
        rrf_scores = {}
        for i, fid in enumerate(sorted_file_ids):
            rrf_scores[fid] = 1.0 / (i + 60)  # k=60 is standard RRF constant

        logger.info(f"[KnowledgeLayout] Phase 23: Generated path-based RRF for {len(rrf_scores)} files")

    # Phase 22: Log RRF scores
    if rrf_scores:
        rrf_values = list(rrf_scores.values())
        logger.info(f"[KnowledgeLayout] Phase 22: RRF scores for {len(rrf_scores)} files")
        if rrf_values:
            logger.info(f"  RRF range: {min(rrf_values):.4f} to {max(rrf_values):.4f}")
            logger.info(f"  RRF mean: {sum(rrf_values) / len(rrf_values):.4f}")

    # 4. Calculate positions and chain edges
    # Phase 17.15: Pass embeddings for similarity-based file placement
    # Phase 22: Pass RRF scores for hybrid ranking + file_metadata for temporal Z
    positions, chain_edges = calculate_knowledge_positions(
        tags, knowledge_levels, edges,
        file_directory_positions=file_directory_positions,
        embeddings_dict=embeddings_dict,  # Phase 17.15: For similarity-based X distribution
        rrf_scores=rrf_scores,  # Phase 22: For hybrid ranking
        file_metadata=file_metadata  # Phase 22: For temporal Z distribution
    )

    # Phase 22: Compute RRF statistics for response
    rrf_stats = {}
    if rrf_scores:
        rrf_values = list(rrf_scores.values())
        rrf_stats = {
            'count': len(rrf_values),
            'min': min(rrf_values) if rrf_values else 0,
            'max': max(rrf_values) if rrf_values else 0,
            'avg': sum(rrf_values) / len(rrf_values) if rrf_values else 0
        }

    # 5. Convert to serializable format
    result = {
        'tags': {
            tag_id: {
                'id': tag.id,
                'name': tag.name,
                'files': tag.files,
                'color': tag.color,
                'angle': tag.angle,
                'position': tag.position,
                # Phase 17.13: Hierarchical tag tree data
                'parent_tag_id': tag.parent_tag_id,
                'depth': tag.depth
            }
            for tag_id, tag in tags.items()
        },
        'edges': [
            {
                'source': edge.source,
                'target': edge.target,
                'type': edge.edge_type,
                'weight': edge.weight
            }
            for edge in edges
        ],
        'positions': positions,
        'knowledge_levels': knowledge_levels,
        'chain_edges': chain_edges,  # Chain edges for stem rendering
        'rrf_stats': rrf_stats  # Phase 22: RRF statistics
    }

    logger.info(f"[KnowledgeLayout] Knowledge graph complete:")
    logger.info(f"  Tags: {len(tags)}")
    logger.info(f"  Edges: {len(edges)}")
    logger.info(f"  Chain edges: {len(chain_edges)}")
    logger.info(f"  Positions: {len(positions)}")
    if rrf_stats:
        logger.info(f"  RRF stats: {rrf_stats}")

    return result
