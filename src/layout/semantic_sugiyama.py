# src/layout/semantic_sugiyama.py
"""
Phase 17.2 FINAL: Semantic Sugiyama Layout with DAG hierarchy + X-axis similarity.

Layout:
- Y = knowledge_level from DAG depth (foundational at bottom, advanced at top)
- X = semantic similarity within layer (similar nodes cluster together)
- Z = slight depth variation for visual separation

This creates a REAL branching tree structure, not spiral or hub.

@status: active
@phase: 96
@depends: collections, typing, numpy, logging
@used_by: src.layout.knowledge_layout, src.visualizer
"""

from collections import deque
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


def assign_knowledge_levels_from_dag(
    nodes: Dict[str, Any],
    edges: List[Any]
) -> Dict[str, float]:
    """
    Calculate knowledge_level based on topological distance from root concepts.

    Algorithm:
    1. Find root nodes (in_degree == 0, no incoming prerequisite edges)
    2. BFS from roots to calculate depth
    3. Normalize depth to knowledge_level [0.1, 1.0]

    Result: foundational concepts near 0.1, advanced near 1.0
    """

    logger.info("[SemanticLayout] Assigning knowledge levels via DAG distance...")

    node_ids = set(nodes.keys())
    in_degrees = {node_id: 0 for node_id in node_ids}
    adjacency = {node_id: [] for node_id in node_ids}

    edge_type_counts = {}

    for edge in edges:
        if hasattr(edge, 'type'):
            edge_type = edge.type
            source = edge.source
            target = edge.target
        else:
            edge_type = edge.get('type', 'contains')
            source = edge.get('source')
            target = edge.get('target')

        edge_type_counts[edge_type] = edge_type_counts.get(edge_type, 0) + 1

        if edge_type == 'prerequisite':
            if target in in_degrees:
                in_degrees[target] += 1
            if source in adjacency:
                adjacency[source].append(target)

    logger.info(f"[SemanticLayout] Edge types: {edge_type_counts}")

    root_nodes = [n for n in node_ids if in_degrees.get(n, 0) == 0]
    logger.info(f"[SemanticLayout] Found {len(root_nodes)} root nodes")

    if not root_nodes:
        logger.warning("[SemanticLayout] No root nodes found! Using default knowledge_level=0.5")
        return {node_id: 0.5 for node_id in node_ids}

    depths = {node_id: float('inf') for node_id in node_ids}
    queue = deque()

    for root in root_nodes:
        depths[root] = 0
        queue.append((root, 0))

    while queue:
        node_id, depth = queue.popleft()
        for target in adjacency.get(node_id, []):
            if target in depths and depths[target] > depth + 1:
                depths[target] = depth + 1
                queue.append((target, depth + 1))

    finite_depths = [d for d in depths.values() if d != float('inf')]
    max_depth = max(finite_depths) if finite_depths else 1

    logger.info(f"[SemanticLayout] Max depth in DAG: {max_depth}")

    knowledge_levels = {}
    orphan_count = 0

    for node_id in node_ids:
        if depths[node_id] == float('inf'):
            knowledge_levels[node_id] = 0.5
            orphan_count += 1
        else:
            knowledge_levels[node_id] = 0.1 + (depths[node_id] / max(max_depth, 1)) * 0.9

    if orphan_count > 0:
        logger.warning(f"[SemanticLayout] {orphan_count} orphan nodes (unreachable from roots)")

    levels = list(knowledge_levels.values())
    logger.info(f"[SemanticLayout] Knowledge level distribution: min={min(levels):.2f}, max={max(levels):.2f}")

    return knowledge_levels


def distribute_by_similarity(
    node_ids: List[str],
    embeddings: Dict[str, np.ndarray],
    x_spread: float = 800
) -> List[float]:
    """
    Distribute nodes horizontally by embedding similarity.

    Similar nodes are placed closer together on X-axis.
    Uses 1D MDS-like projection of cosine similarities.

    Args:
        node_ids: List of node IDs to position
        embeddings: Dict of node_id -> embedding vector
        x_spread: Total X spread range

    Returns:
        List of X positions (same order as node_ids)
    """
    n = len(node_ids)

    if n == 0:
        return []
    if n == 1:
        return [0.0]
    if n == 2:
        return [-x_spread / 4, x_spread / 4]

    # Get embeddings for nodes
    valid_embeddings = []
    valid_indices = []

    for i, node_id in enumerate(node_ids):
        if node_id in embeddings and embeddings[node_id] is not None:
            emb = embeddings[node_id]
            if hasattr(emb, '__len__') and len(emb) > 0:
                valid_embeddings.append(emb)
                valid_indices.append(i)

    if len(valid_embeddings) < 2:
        # Fallback: linear distribution
        return [
            -x_spread / 2 + i * (x_spread / (n - 1))
            for i in range(n)
        ]

    # Normalize embeddings
    emb_matrix = np.array(valid_embeddings)
    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    norms = np.where(norms < 1e-8, 1, norms)
    emb_normalized = emb_matrix / norms

    # Calculate pairwise cosine similarities
    similarity_matrix = np.dot(emb_normalized, emb_normalized.T)

    # Convert to distance (1 - similarity)
    distance_matrix = 1 - similarity_matrix

    # Simple 1D MDS: project to principal axis
    # Use first principal component of distance matrix
    try:
        # Center the distance matrix
        n_valid = len(valid_embeddings)
        H = np.eye(n_valid) - np.ones((n_valid, n_valid)) / n_valid
        centered = -0.5 * H @ (distance_matrix ** 2) @ H

        # Get first eigenvector
        eigenvalues, eigenvectors = np.linalg.eigh(centered)
        first_component = eigenvectors[:, -1] * np.sqrt(max(eigenvalues[-1], 0))

        # Normalize to x_spread
        if np.std(first_component) > 1e-8:
            first_component = (first_component - np.mean(first_component)) / np.std(first_component)
            first_component = first_component * (x_spread / 4)  # Use 50% of spread

    except Exception as e:
        logger.warning(f"[SemanticLayout] MDS failed: {e}, using linear fallback")
        first_component = np.linspace(-x_spread/2, x_spread/2, n_valid)

    # Map back to all nodes
    x_positions = [0.0] * n

    for i, orig_idx in enumerate(valid_indices):
        x_positions[orig_idx] = float(first_component[i])

    # Fill in nodes without embeddings (linear interpolation)
    for i in range(n):
        if i not in valid_indices:
            x_positions[i] = -x_spread/2 + i * (x_spread / (n - 1))

    return x_positions


def distribute_horizontally(count: int, x_spread: float) -> List[float]:
    """
    Distribute N nodes evenly across X range [-x_spread/2, x_spread/2]
    """
    if count == 0:
        return []
    if count == 1:
        return [0.0]

    return [
        -x_spread / 2 + i * (x_spread / (count - 1))
        for i in range(count)
    ]


def calculate_semantic_sugiyama_layout(
    nodes: Dict[str, Any],
    edges: List[Any],
    max_y: float = 3000,
    x_spread: float = 800,
    z_offset: float = 30,
    use_similarity_x: bool = True
) -> Dict[str, Dict[str, float]]:
    """
    Calculate semantic layout using DAG hierarchy + X-axis similarity.

    Positioning:
    - Y = knowledge_level (0.1 → 0.9 maps to 100 → 3000 px) - COLUMNAR
    - X = semantic similarity within level (similar nodes cluster)
    - Z = z_offset per node (slight depth variation)

    Args:
        nodes: Dict mapping node_id -> node data (with 'embedding', 'type')
        edges: List of edge dicts/objects (with 'source', 'target', 'type')
        max_y: Maximum Y spread for layout
        x_spread: X-axis spread (-x_spread/2 to +x_spread/2)
        z_offset: Z offset for sibling separation
        use_similarity_x: If True, distribute X by semantic similarity

    Returns:
        Dict mapping node_id -> {x, y, z, layer, knowledge_level}
    """

    positions = {}

    if not nodes:
        logger.warning("[SemanticLayout] No nodes provided")
        return positions

    logger.info(f"[SemanticLayout] Starting DAG-based Sugiyama layout for {len(nodes)} nodes...")

    # PHASE 1: Calculate knowledge levels from DAG structure
    knowledge_levels = assign_knowledge_levels_from_dag(nodes, edges)

    # PHASE 2: Extract embeddings for similarity-based X positioning
    embeddings = {}
    for node_id, node in nodes.items():
        if hasattr(node, 'embedding') and node.embedding is not None:
            embeddings[node_id] = node.embedding
        elif isinstance(node, dict) and 'embedding' in node:
            embeddings[node_id] = node.get('embedding')

    logger.info(f"[SemanticLayout] Extracted {len(embeddings)} embeddings for X similarity")

    # PHASE 3: Group nodes into layers by knowledge level (10 buckets)
    layers: Dict[int, List[str]] = {}

    for node_id in nodes.keys():
        kl = knowledge_levels.get(node_id, 0.5)
        level = int(kl * 10)  # 0-10 buckets
        level = max(0, min(10, level))

        if level not in layers:
            layers[level] = []
        layers[level].append(node_id)

    logger.info(f"[SemanticLayout] Layer distribution: {[(l, len(n)) for l, n in sorted(layers.items())]}")

    # PHASE 4: Assign positions (COLUMNAR hierarchy with X similarity)
    z_counter = 0

    for level_idx in sorted(layers.keys()):
        layer = layers[level_idx]
        n_nodes = len(layer)

        # Y position based on knowledge_level (columnar, not circular!)
        y = 100 + (level_idx * (max_y / 10))

        # X positioning: by similarity or linear
        if use_similarity_x and len(embeddings) > 0:
            x_positions = distribute_by_similarity(layer, embeddings, x_spread)
        else:
            x_positions = distribute_horizontally(n_nodes, x_spread)

        logger.info(f"[SemanticLayout] Level {level_idx}: {n_nodes} nodes at Y={y:.0f}")

        for x_idx, node_id in enumerate(layer):
            positions[node_id] = {
                'x': float(x_positions[x_idx]),
                'y': float(y),
                'z': float(z_counter * z_offset),
                'layer': level_idx,
                'knowledge_level': float(knowledge_levels.get(node_id, 0.5))
            }
            z_counter += 1

    # PHASE 5: Crossing minimization (barycenter method)
    # Phase 17.20: DISABLED - destroys semantic X positioning
    # The Phase 17.19 fix preserves spacing but loses node↔position correspondence
    # minimize_crossings(positions, layers, edges, iterations=5, x_spread=x_spread)
    logger.info("[SemanticLayout] Phase 17.20: Skipped minimize_crossings to preserve semantic X")

    # PHASE 6: Soft repulsion within layers to avoid overlap
    apply_soft_repulsion_semantic(positions, layers)

    # Log position ranges
    if positions:
        x_vals = [p['x'] for p in positions.values()]
        y_vals = [p['y'] for p in positions.values()]
        z_vals = [p['z'] for p in positions.values()]

        logger.info(f"[SemanticLayout] Layout complete: {len(positions)} nodes positioned")
        logger.info(f"[SemanticLayout] Position ranges:")
        logger.info(f"  X: {min(x_vals):.0f} to {max(x_vals):.0f}")
        logger.info(f"  Y: {min(y_vals):.0f} to {max(y_vals):.0f} (columnar hierarchy)")
        logger.info(f"  Z: {min(z_vals):.0f} to {max(z_vals):.0f}")

    return positions


def minimize_crossings(
    positions: Dict[str, Dict[str, float]],
    layers: Dict[int, List[str]],
    edges: List[Any],
    iterations: int = 5,
    x_spread: float = 800
):
    """
    Minimize edge crossings between layers using barycenter method.

    For each layer, reorder nodes based on average position of connected nodes
    in adjacent layers.
    """

    # Build adjacency from edges
    connections = {}  # node_id -> list of connected node_ids

    for edge in edges:
        if hasattr(edge, 'type'):
            edge_type = edge.type
            source = edge.source
            target = edge.target
        else:
            edge_type = edge.get('type', 'contains')
            source = edge.get('source')
            target = edge.get('target')

        if edge_type == 'prerequisite':
            if source not in connections:
                connections[source] = []
            if target not in connections:
                connections[target] = []
            connections[source].append(target)
            connections[target].append(source)

    sorted_levels = sorted(layers.keys())

    for _ in range(iterations):
        # Forward pass
        for level_idx in sorted_levels[1:]:
            layer = layers[level_idx]

            # Calculate barycenter for each node
            barycenters = {}
            for node_id in layer:
                connected = connections.get(node_id, [])
                connected_x = [
                    positions[c]['x'] for c in connected
                    if c in positions and positions[c]['layer'] < level_idx
                ]
                if connected_x:
                    barycenters[node_id] = sum(connected_x) / len(connected_x)
                else:
                    barycenters[node_id] = positions.get(node_id, {}).get('x', 0)

            # Sort layer by barycenter
            layer.sort(key=lambda n: barycenters.get(n, 0))

            # PHASE 17.19 FIX: Preserve semantic X distances, only reorder
            # Get current X values (preserves similarity-based spacing!)
            current_xs = [positions[node_id]['x'] for node_id in layer if node_id in positions]

            if len(current_xs) >= 2:
                # Sort X values and reassign to reordered nodes
                # This preserves the SPACING while changing the ORDER
                current_xs_sorted = sorted(current_xs)

                for i, node_id in enumerate(layer):
                    if node_id in positions and i < len(current_xs_sorted):
                        positions[node_id]['x'] = current_xs_sorted[i]
            elif len(current_xs) == 1:
                # Single node - center it
                for node_id in layer:
                    if node_id in positions:
                        positions[node_id]['x'] = 0

        # Backward pass
        for level_idx in reversed(sorted_levels[:-1]):
            layer = layers[level_idx]

            barycenters = {}
            for node_id in layer:
                connected = connections.get(node_id, [])
                connected_x = [
                    positions[c]['x'] for c in connected
                    if c in positions and positions[c]['layer'] > level_idx
                ]
                if connected_x:
                    barycenters[node_id] = sum(connected_x) / len(connected_x)
                else:
                    barycenters[node_id] = positions.get(node_id, {}).get('x', 0)

            layer.sort(key=lambda n: barycenters.get(n, 0))

            # PHASE 17.19 FIX: Preserve semantic X distances, only reorder
            # Get current X values (preserves similarity-based spacing!)
            current_xs = [positions[node_id]['x'] for node_id in layer if node_id in positions]

            if len(current_xs) >= 2:
                # Sort X values and reassign to reordered nodes
                # This preserves the SPACING while changing the ORDER
                current_xs_sorted = sorted(current_xs)

                for i, node_id in enumerate(layer):
                    if node_id in positions and i < len(current_xs_sorted):
                        positions[node_id]['x'] = current_xs_sorted[i]
            elif len(current_xs) == 1:
                # Single node - center it
                for node_id in layer:
                    if node_id in positions:
                        positions[node_id]['x'] = 0


def apply_soft_repulsion_semantic(
    positions: Dict[str, Dict[str, float]],
    layers: Dict[int, List[str]],
    iterations: int = 3,
    min_distance: float = 100,
    repulsion_strength: float = 0.3
):
    """
    Soft repulsion within each layer to avoid overlap.
    """

    for level_idx, layer in layers.items():
        if len(layer) < 2:
            continue

        for iteration in range(iterations):
            for node_a in layer:
                if node_a not in positions:
                    continue

                force = 0.0

                for node_b in layer:
                    if node_a == node_b or node_b not in positions:
                        continue

                    pos_a = positions[node_a]
                    pos_b = positions[node_b]

                    dist = abs(pos_a['x'] - pos_b['x'])
                    if dist < min_distance:
                        repulsion = (min_distance - dist) * repulsion_strength
                        direction = 1 if pos_b['x'] < pos_a['x'] else -1
                        force += repulsion * direction

                positions[node_a]['x'] += force * 0.5


def calculate_semantic_positions_for_files(
    semantic_nodes: Dict[str, Any],
    semantic_edges: List[Any],
    file_ids: List[str],
    max_y: float = 3000
) -> Dict[str, Dict[str, float]]:
    """
    Calculate semantic positions for file nodes.

    Strategy:
    1. Calculate positions for concept nodes using DAG hierarchy + X similarity
    2. Position files relative to their parent concepts
    3. Files inherit parent's Y level, spread horizontally within cluster

    Args:
        semantic_nodes: All semantic nodes (dict of node_id -> node data)
        semantic_edges: All semantic edges
        file_ids: List of file IDs to position
        max_y: Maximum Y spread

    Returns:
        Dict mapping file_id -> {x, y, z, layer, knowledge_level}
    """

    logger.info(f"[SemanticLayout] Calculating positions for {len(file_ids)} files...")

    # Separate concepts and files
    concept_nodes = {}
    file_nodes = {}

    for node_id, node in semantic_nodes.items():
        if hasattr(node, 'type'):
            node_type = node.type
        elif isinstance(node, dict):
            node_type = node.get('type', 'file')
        else:
            node_type = 'file'

        if node_type == 'concept':
            concept_nodes[node_id] = node
        else:
            file_nodes[node_id] = node

    logger.info(f"[SemanticLayout] Found {len(concept_nodes)} concepts, {len(file_nodes)} files")

    # Get concept positions using DAG hierarchy + X similarity
    concept_positions = calculate_semantic_sugiyama_layout(
        concept_nodes,
        semantic_edges,
        max_y=max_y,
        use_similarity_x=True
    )

    # Build mapping: file_id -> parent concept_id
    file_to_concept = {}
    for edge in semantic_edges:
        if hasattr(edge, 'type'):
            edge_type = edge.type
            source = edge.source
            target = edge.target
        else:
            edge_type = edge.get('type', 'contains')
            source = edge.get('source')
            target = edge.get('target')

        if edge_type == 'contains':
            file_to_concept[target] = source

    logger.info(f"[SemanticLayout] File-to-concept mappings: {len(file_to_concept)}")

    # Get file embeddings for within-cluster similarity
    file_embeddings = {}
    for file_id, node in file_nodes.items():
        if hasattr(node, 'embedding') and node.embedding is not None:
            file_embeddings[file_id] = node.embedding
        elif isinstance(node, dict) and 'embedding' in node:
            file_embeddings[file_id] = node.get('embedding')

    # Group files by parent concept
    concept_to_files = {}
    for file_id in file_ids:
        concept_id = file_to_concept.get(file_id)
        if concept_id:
            if concept_id not in concept_to_files:
                concept_to_files[concept_id] = []
            concept_to_files[concept_id].append(file_id)

    # Position files relative to parent concepts with similarity-based X
    positions = {}

    for concept_id, files in concept_to_files.items():
        if concept_id not in concept_positions:
            continue

        parent_pos = concept_positions[concept_id]
        n_files = len(files)

        # Get X positions by similarity within cluster
        if len(file_embeddings) > 0:
            cluster_embeddings = {f: file_embeddings[f] for f in files if f in file_embeddings}
            if len(cluster_embeddings) >= 2:
                x_offsets = distribute_by_similarity(files, cluster_embeddings, x_spread=300)
            else:
                x_offsets = distribute_horizontally(n_files, 300)
        else:
            x_offsets = distribute_horizontally(n_files, 300)

        for i, file_id in enumerate(files):
            # Grid layout: spread in X, stack in rows
            num_cols = 8
            row = i // num_cols
            col = i % num_cols

            # X: similarity-based offset
            offset_x = x_offsets[i] if i < len(x_offsets) else (col - num_cols // 2) * 50
            # Y: below parent, stacked by row
            offset_y = -(row + 1) * 35
            # Z: small depth variation
            offset_z = i * 2

            positions[file_id] = {
                'x': parent_pos['x'] + offset_x,
                'y': parent_pos['y'] + offset_y,
                'z': parent_pos['z'] + offset_z,
                'layer': parent_pos['layer'],
                'knowledge_level': parent_pos['knowledge_level']
            }

    # Handle orphan files (no parent concept)
    orphan_files = [f for f in file_ids if f not in positions]
    if orphan_files:
        logger.info(f"[SemanticLayout] Positioning {len(orphan_files)} orphan files")

        for i, file_id in enumerate(orphan_files):
            node = semantic_nodes.get(file_id, {})
            if hasattr(node, 'knowledge_level'):
                kl = node.knowledge_level
            elif isinstance(node, dict):
                kl = node.get('knowledge_level', 0.5)
            else:
                kl = 0.5

            positions[file_id] = {
                'x': (i % 10 - 5) * 80,
                'y': 100 + kl * max_y,
                'z': i * 2,
                'layer': int(kl * 10),
                'knowledge_level': float(kl)
            }

    # Log position ranges
    if positions:
        x_vals = [p['x'] for p in positions.values()]
        y_vals = [p['y'] for p in positions.values()]

        logger.info(f"[SemanticLayout] File positions: {len(positions)} files")
        logger.info(f"  X range: {min(x_vals):.0f} to {max(x_vals):.0f}")
        logger.info(f"  Y range: {min(y_vals):.0f} to {max(y_vals):.0f}")

    return positions
