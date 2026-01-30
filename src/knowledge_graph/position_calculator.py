# src/knowledge_graph/position_calculator.py
"""
VETKA Position Calculator - Phase 15.8
Calculates 3D positions for Knowledge Graph nodes using UMAP and HDBSCAN.
Follows VETKA Theory: Y=time+semantics, X=order/semantics, Z=duplicates only.

Phase 15.5 Changes:
- Return y_time and y_semantic separately for frontend blend slider
- Z-axis threshold increased to 0.95 with extension check
- Include created_time in node data for date display

Phase 15.7 Changes:
- Y-semantic now uses asymmetric projections to determine hierarchy
- Files that "depend on" others (higher projection ratio) are positioned higher

Phase 15.8 Changes:
- center_graph_by_mass() now uses true center of mass (average X and Z)
- Added apply_intraday_x_spread() to spread same-day files by time of day
- Graph is centered at scene origin (0, 0) for X and Z

Phase 15.9 Changes:
- Added parse_timestamp_precise() for second-level timestamp parsing
- Added get_effective_time() using max(created, modified)
- Added adaptive_y_scale_by_x_proximity() for minute-level Y separation
- Added ensure_min_y_separation() guaranteeing 15 units between adjacent Y
- Added modified_time and preview to node export data

@status: active
@phase: 96
@depends: numpy, networkx, umap, hdbscan
@used_by: src.knowledge_graph.graph_builder, src.visualizer.tree_renderer
"""

import numpy as np
import networkx as nx
from typing import Dict, List, Optional, Tuple
import logging
import re

logger = logging.getLogger(__name__)


def extract_phase_number(filename: str) -> float:
    """
    Extract phase number from filename for semantic Y positioning.

    Examples:
        PHASE_7_5_README.md → 7.5
        PHASE_54_README.md → 54.0
        PHASE7_README.md → 7.0
        PHASE_7_8_SESSION.md → 7.8
        README.md → 0.0 (no phase number)
    """
    if not filename:
        return 0.0

    # Pattern 1: PHASE_X_Y or PHASE_X-Y or PHASE X Y
    match = re.search(r'PHASE[_\-\s]*(\d+)[_\-\s]*(\d+)?', filename, re.IGNORECASE)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) else 0
        return major + minor / 10.0

    # Pattern 2: Just numbers at start like 7_5_something.md
    match = re.search(r'^(\d+)[_\-\s]*(\d+)?', filename)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) else 0
        return major + minor / 10.0

    return 0.0


def compute_semantic_hierarchy(
    embeddings: Dict[str, np.ndarray],
    graph: nx.Graph
) -> Dict[str, float]:
    """
    Compute Y-position by semantic hierarchy using asymmetric projections.

    Principle: If file A "depends on" B (A needs B to understand),
    then B should be LOWER on Y (it's more basic/foundational).

    Method: Asymmetric projections from embeddings.
    - proj_a_on_b: how much A is "contained" in B
    - proj_b_on_a: how much B is "contained" in A
    - If proj_a_on_b > proj_b_on_a, then A depends on B → A is higher

    Returns:
        Dict mapping node_id to normalized score [0, 1]
        Higher score = more advanced/dependent = higher Y position
    """
    node_ids = list(embeddings.keys())
    n = len(node_ids)

    if n == 0:
        return {}

    if n == 1:
        return {node_ids[0]: 0.5}

    # Matrix of "how much A depends on B"
    dependency_scores = {node: 0.0 for node in node_ids}

    for i, node_a in enumerate(node_ids):
        emb_a = embeddings[node_a]
        norm_a = np.linalg.norm(emb_a)

        if norm_a < 1e-8:
            continue

        for j, node_b in enumerate(node_ids):
            if i == j:
                continue

            emb_b = embeddings[node_b]
            norm_b = np.linalg.norm(emb_b)

            if norm_b < 1e-8:
                continue

            # Asymmetric projections
            # proj_a_on_b: how much of A projects onto B's direction
            proj_a_on_b = np.dot(emb_a, emb_b) / norm_b
            # proj_b_on_a: how much of B projects onto A's direction
            proj_b_on_a = np.dot(emb_b, emb_a) / norm_a

            # dependency_ratio > 1 means A depends on B
            # dependency_ratio < 1 means B depends on A
            if abs(proj_b_on_a) < 1e-8:
                continue

            dependency_ratio = proj_a_on_b / (proj_b_on_a + 1e-8)

            if dependency_ratio > 1.0:
                # A depends on B → A is more advanced → A gets higher score
                dependency_scores[node_a] += (dependency_ratio - 1.0)
            else:
                # B depends on A → A is more basic → A gets lower score
                dependency_scores[node_a] -= (1.0 - dependency_ratio)

    # Normalize to [0, 1]
    scores = list(dependency_scores.values())
    min_score = min(scores)
    max_score = max(scores)
    score_range = max_score - min_score

    if score_range < 1e-8:
        # All same — distribute evenly by name order for stability
        sorted_nodes = sorted(node_ids)
        return {node: i / max(n - 1, 1) for i, node in enumerate(sorted_nodes)}

    normalized = {}
    for node in node_ids:
        normalized[node] = (dependency_scores[node] - min_score) / score_range

    return normalized


def center_graph_by_mass(positions: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    Center the graph by its center of mass (average of all X and Z coordinates).

    Phase 15.8: True center of mass calculation.

    Why this is correct:
    - Preserves relative distances between nodes
    - Graph ends up centered at scene origin (0, 0) for X and Z
    - Camera rotates around the graph center
    - Y is NOT modified — tree grows upward from ground

    Args:
        positions: Dict of node_id -> {"x", "y", "z", ...}

    Returns:
        Modified positions dict with X and Z shifted to center
    """
    if not positions or len(positions) == 0:
        return positions

    # Compute center of mass
    all_x = [p.get('x', 0) for p in positions.values()]
    all_z = [p.get('z', 0) for p in positions.values()]

    center_x = sum(all_x) / len(all_x)
    center_z = sum(all_z) / len(all_z)

    logger.info(f"[CenterMass] Shifting by x={center_x:.1f}, z={center_z:.1f}")

    # Shift to scene center
    for node_id in positions:
        positions[node_id]['x'] = positions[node_id].get('x', 0) - center_x
        positions[node_id]['z'] = positions[node_id].get('z', 0) - center_z
        # Y stays as is — grows upward from ground

    return positions


def apply_intraday_x_spread(
    positions: Dict[str, Dict],
    graph: nx.Graph
) -> Dict[str, Dict]:
    """
    Spread files with the same Y position along X axis based on time of day.

    Phase 15.8: Files created on the same day often have nearly identical Y
    after normalization. This function spreads them horizontally by their
    creation time (hour:minute).

    Logic:
    1. Find groups of files with similar Y (±Y_TOLERANCE)
    2. Within each group, sort by time of day
    3. Distribute evenly along X around their current center

    Args:
        positions: Dict of node_id -> {"x", "y", "z", ...}
        graph: NetworkX graph with node payload containing created_time

    Returns:
        Modified positions dict with X spread for same-day files
    """
    if not positions:
        return positions

    Y_TOLERANCE = 5.0  # Files with Y difference < 5 are considered "same day"
    X_SPREAD_STEP = 15.0  # Distance between files

    # Group by Y
    y_groups: Dict[float, List[str]] = {}

    for node_id, pos in positions.items():
        y = pos.get('y', 0)

        # Find existing group with similar Y
        assigned = False
        for group_y in list(y_groups.keys()):
            if abs(y - group_y) < Y_TOLERANCE:
                y_groups[group_y].append(node_id)
                assigned = True
                break

        if not assigned:
            y_groups[y] = [node_id]

    # Process groups with >1 file
    for group_y, nodes in y_groups.items():
        if len(nodes) <= 1:
            continue

        # Get time of day for each file
        node_times = []
        for node_id in nodes:
            node_data = graph.nodes.get(node_id, {})
            payload = node_data.get('payload', {})
            created = (
                payload.get('created_time') or
                payload.get('created_at') or
                payload.get('modified_time')
            )

            time_of_day = 0.5  # default: noon
            if created:
                try:
                    from datetime import datetime

                    dt = None
                    if isinstance(created, str):
                        # Handle ISO format
                        created_clean = created.replace('Z', '+00:00')
                        if '+' in created_clean:
                            created_clean = created_clean.rsplit('+', 1)[0]
                        dt = datetime.fromisoformat(created_clean)
                    elif isinstance(created, (int, float)):
                        dt = datetime.fromtimestamp(created)

                    if dt:
                        # 0:00 → 0.0, 12:00 → 0.5, 23:59 → ~1.0
                        time_of_day = (dt.hour * 60 + dt.minute) / (24 * 60)
                except Exception:
                    pass

            node_times.append((node_id, time_of_day))

        # Sort by time of day
        node_times.sort(key=lambda x: x[1])

        # Compute group center X
        group_center_x = sum(positions[n]['x'] for n in nodes) / len(nodes)

        # Distribute evenly
        total_width = (len(nodes) - 1) * X_SPREAD_STEP
        start_x = group_center_x - total_width / 2

        for i, (node_id, _) in enumerate(node_times):
            positions[node_id]['x'] = start_x + i * X_SPREAD_STEP

        logger.info(f"[IntraDay] Y≈{group_y:.0f}: spread {len(nodes)} files")

    return positions


def parse_timestamp_precise(value) -> Optional[float]:
    """
    Parse timestamp with second-level precision.
    Returns Unix timestamp (float) or None.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        try:
            from datetime import datetime
            # ISO format: "2024-12-15T14:30:45Z"
            clean = value.replace('Z', '+00:00')
            if '+' in clean:
                clean = clean.rsplit('+', 1)[0]
            dt = datetime.fromisoformat(clean)
            return dt.timestamp()
        except Exception:
            pass

    return None


def get_effective_time(node_data: Dict) -> float:
    """
    Get effective time = max(created, modified).
    Later modification date "raises" the file higher.
    """
    payload = node_data.get('payload', {})

    created = parse_timestamp_precise(
        payload.get('created_time') or payload.get('created_at')
    )
    modified = parse_timestamp_precise(
        payload.get('modified_time') or payload.get('modified_at')
    )

    if created is None and modified is None:
        return 0.0

    if created is None:
        return modified
    if modified is None:
        return created

    return max(created, modified)


def adaptive_y_scale_by_x_proximity(
    positions: Dict[str, Dict],
    graph: nx.Graph,
    min_separation: float = 15.0
) -> Dict[str, Dict]:
    """
    Adaptive Y ranking based on X proximity.

    Phase 15.9: Files close on X axis get detailed Y ranking by exact time.

    Logic:
    1. Find groups of files with similar X (±X_PROXIMITY_THRESHOLD)
    2. Within group — sort by EXACT time (down to minutes)
    3. Guarantee minimum Y separation

    The closer files are on X → the more detailed Y ranking.
    """
    if not positions or len(positions) < 2:
        return positions

    X_PROXIMITY_THRESHOLD = 20.0  # Files within 20 units on X are a "group"

    # Group by X proximity
    x_groups = []
    sorted_by_x = sorted(positions.items(), key=lambda x: x[1].get('x', 0))

    current_group = []
    for node_id, pos in sorted_by_x:
        if not current_group:
            current_group.append(node_id)
        else:
            prev_x = positions[current_group[-1]].get('x', 0)
            curr_x = pos.get('x', 0)

            if abs(curr_x - prev_x) < X_PROXIMITY_THRESHOLD:
                current_group.append(node_id)
            else:
                if len(current_group) > 1:
                    x_groups.append(current_group)
                current_group = [node_id]

    if len(current_group) > 1:
        x_groups.append(current_group)

    # For each group — detailed Y ranking by time
    for group in x_groups:
        # Get exact time for each file
        node_times = []
        for node_id in group:
            node_data = graph.nodes.get(node_id, {})
            effective_time = get_effective_time(node_data)
            node_times.append((node_id, effective_time))

        # Sort by time (older at bottom, newer at top)
        node_times.sort(key=lambda x: x[1])

        # Find base Y (minimum in group)
        base_y = min(positions[n]['y'] for n in group)

        # Distribute with guaranteed separation
        for i, (node_id, _) in enumerate(node_times):
            positions[node_id]['y'] = base_y + i * min_separation

        logger.info(f"[AdaptiveY] X-group of {len(group)} files: "
                   f"spread with step {min_separation}")

    return positions


def ensure_min_y_separation(
    positions: Dict[str, Dict],
    min_separation: float = 15.0
) -> Dict[str, Dict]:
    """
    Guarantee minimum distance between adjacent Y values.

    Phase 15.9: Final pass — if two files are closer than min_separation, push apart.
    """
    if not positions or len(positions) < 2:
        return positions

    sorted_nodes = sorted(positions.items(), key=lambda x: x[1].get('y', 0))

    for i in range(1, len(sorted_nodes)):
        prev_id, prev_pos = sorted_nodes[i - 1]
        curr_id, curr_pos = sorted_nodes[i]

        gap = curr_pos['y'] - prev_pos['y']

        if gap < min_separation:
            # Push apart: shift current and all above
            offset = min_separation - gap

            for j in range(i, len(sorted_nodes)):
                node_id = sorted_nodes[j][0]
                positions[node_id]['y'] += offset

    return positions


class VETKAPositionCalculator:
    """
    Calculates 3D positions for knowledge graph nodes.
    Uses UMAP for dimensionality reduction and HDBSCAN for clustering.
    """

    # VETKA spatial parameters
    # Phase 17.1: X > Y (tree should be WIDE, not tall)
    SCALE = {
        "x": 400,    # Horizontal spread (semantics) - INCREASED
        "y": 200,    # Vertical spread (time) - DECREASED
        "z": 50      # Depth spread (only for duplicates)
    }

    # Cluster colors (Itten palette)
    CLUSTER_COLORS = [
        "#4A6B8A",  # Muted blue
        "#8AA0B0",  # Light blue-gray
        "#6B8E7B",  # Muted green
        "#9B8A7A",  # Warm gray
        "#7A6B8A",  # Muted purple
        "#8A7B6B",  # Taupe
        "#6B7A8A",  # Steel blue
        "#8A8A7A",  # Sage
    ]

    def __init__(
        self,
        n_neighbors: int = 15,
        min_dist: float = 0.1,
        min_cluster_size: int = 3
    ):
        """
        Initialize position calculator.

        Args:
            n_neighbors: UMAP neighbors parameter
            min_dist: UMAP minimum distance
            min_cluster_size: HDBSCAN minimum cluster size
        """
        self.n_neighbors = n_neighbors
        self.min_dist = min_dist
        self.min_cluster_size = min_cluster_size

    def calculate_positions(self, graph: nx.Graph) -> Dict[str, Dict]:
        """
        Calculate 3D positions for all nodes in the graph.

        Args:
            graph: NetworkX graph with 'embedding' attribute on nodes

        Returns:
            {node_id: {"x", "y", "z", "y_time", "y_semantic", "created_time", "cluster", "color"}}
            Phase 15.5: Added y_time, y_semantic for frontend blend slider
        """
        nodes = list(graph.nodes())
        if not nodes:
            return {}

        # Extract embeddings
        embeddings = []
        valid_nodes = []

        for node in nodes:
            emb = graph.nodes[node].get("embedding", [])
            if emb and len(emb) > 0:
                embeddings.append(emb)
                valid_nodes.append(node)

        if not embeddings:
            logger.warning("No embeddings found, using spring layout")
            return self._fallback_spring_layout(graph)

        embeddings = np.array(embeddings)

        # Calculate UMAP projection (for X positioning and clustering)
        try:
            positions_2d, clusters = self._umap_hdbscan(embeddings)
        except Exception as e:
            logger.warning(f"UMAP/HDBSCAN failed: {e}, using fallback")
            return self._fallback_spring_layout(graph)

        # Phase 15.5: Get separate Y components for blend slider
        y_time_norm = self._calculate_y_by_time(graph, valid_nodes)
        y_semantic_norm = self._calculate_y_by_semantic(graph, valid_nodes)

        # Calculate Y positions: Hybrid (50% time + 50% semantic phase number)
        # Y >= 20 to keep files above ground
        y_positions = self._calculate_all_y_positions(graph, valid_nodes)

        # Calculate Z positions: ONLY for duplicates (similarity > 0.95)
        # Non-duplicates: Z = 0
        z_positions = self._calculate_z_for_duplicates(graph, valid_nodes, embeddings)

        # Phase 15.5: Extract created_time for date display
        GROUND_OFFSET = 20
        scale_y = self.SCALE["y"]

        # Convert to VETKA 3D positions
        result = {}
        for i, node in enumerate(valid_nodes):
            cluster = int(clusters[i]) if clusters[i] >= 0 else -1
            color = self.CLUSTER_COLORS[cluster % len(self.CLUSTER_COLORS)] if cluster >= 0 else "#666666"

            # Get created_time for date display
            node_data = graph.nodes.get(node, {})
            payload = node_data.get("payload", {})
            created_time = (
                payload.get("created_time") or
                payload.get("created_at") or
                payload.get("modified_time") or
                payload.get("timestamp") or
                0
            )
            created_time_float = self._parse_timestamp(created_time)

            # Phase 15.5: Store separate Y values for blend slider
            y_t = y_time_norm.get(node, 0.5)
            y_s = y_semantic_norm.get(node, 0.5)

            result[node] = {
                "x": float(positions_2d[i, 0]) * self.SCALE["x"],
                "y": float(y_positions.get(node, 20)),  # Hybrid Y, minimum 20 (above ground)
                "z": float(z_positions.get(node, 0)),   # Z only for duplicates
                # Phase 15.5: Separate Y values for frontend blend slider
                "y_time": float(GROUND_OFFSET + y_t * scale_y),
                "y_semantic": float(GROUND_OFFSET + y_s * scale_y),
                "created_time": created_time_float,
                "cluster": cluster,
                "color": color
            }

        # Add nodes without embeddings above ground
        for node in nodes:
            if node not in result:
                result[node] = {
                    "x": 0,
                    "y": 20,  # Above ground, not at origin
                    "z": 0,
                    "y_time": 20,
                    "y_semantic": 20,
                    "created_time": 0,
                    "cluster": -1,
                    "color": "#666666"
                }

        # Phase 15.8: Spread files with same Y by time of day
        result = apply_intraday_x_spread(result, graph)

        # Phase 15.9: Adaptive Y scale for X-close files (minute-level separation)
        result = adaptive_y_scale_by_x_proximity(result, graph, min_separation=15.0)

        # Phase 15.9: Guarantee minimum Y separation
        result = ensure_min_y_separation(result, min_separation=15.0)

        # Phase 15.8: Center by center of mass (X and Z)
        result = center_graph_by_mass(result)

        return result

    def _umap_hdbscan(self, embeddings: np.ndarray) -> tuple:
        """
        Apply UMAP dimensionality reduction and HDBSCAN clustering.

        Returns:
            (positions_2d, cluster_labels)
        """
        try:
            import umap
            import hdbscan
        except ImportError as e:
            logger.error(f"Missing dependency: {e}")
            raise

        n_samples = len(embeddings)

        # Adjust UMAP parameters for small datasets
        n_neighbors = min(self.n_neighbors, max(2, n_samples - 1))

        # UMAP projection to 2D
        reducer = umap.UMAP(
            n_neighbors=n_neighbors,
            min_dist=self.min_dist,
            n_components=2,
            metric='cosine',
            random_state=42
        )

        positions_2d = reducer.fit_transform(embeddings)

        # Normalize to [-1, 1] range
        positions_2d = self._normalize(positions_2d)

        # HDBSCAN clustering
        min_cluster = min(self.min_cluster_size, max(2, n_samples // 3))

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster,
            metric='euclidean',
            cluster_selection_method='eom'
        )

        clusters = clusterer.fit_predict(positions_2d)

        return positions_2d, clusters

    def _normalize(self, positions: np.ndarray) -> np.ndarray:
        """Normalize positions to [-1, 1] range."""
        min_vals = positions.min(axis=0)
        max_vals = positions.max(axis=0)
        range_vals = max_vals - min_vals

        # Avoid division by zero
        range_vals[range_vals == 0] = 1

        normalized = 2 * (positions - min_vals) / range_vals - 1
        return normalized

    def _parse_timestamp(self, t) -> float:
        """
        Parse timestamp from various formats (Unix timestamp or ISO string).
        Returns Unix timestamp as float, or 0 on failure.
        """
        if t is None or t == 0:
            return 0.0

        # Try as float/int (Unix timestamp)
        try:
            return float(t)
        except (ValueError, TypeError):
            pass

        # Try as ISO string
        if isinstance(t, str):
            try:
                from datetime import datetime
                # Handle ISO format with timezone
                if '+' in t or 'Z' in t:
                    # Remove timezone for parsing
                    t_clean = t.replace('Z', '+00:00')
                    if '+' in t_clean:
                        t_clean = t_clean.rsplit('+', 1)[0]
                    dt = datetime.fromisoformat(t_clean)
                else:
                    dt = datetime.fromisoformat(t)
                return dt.timestamp()
            except (ValueError, TypeError):
                pass

        return 0.0

    def _calculate_y_by_time(self, graph: nx.Graph, valid_nodes: List[str]) -> Dict[str, float]:
        """
        Calculate normalized Y positions (0 to 1) based on time only.
        Uses IQR-based robust scaling with adaptive redistribution.
        """
        if not valid_nodes:
            return {}

        # Collect times for all valid nodes
        node_times = {}
        for node in valid_nodes:
            node_data = graph.nodes.get(node, {})
            payload = node_data.get("payload", {})

            t = (
                payload.get("created_time") or
                payload.get("created_at") or
                payload.get("modified_time") or
                payload.get("timestamp") or
                0
            )
            node_times[node] = self._parse_timestamp(t)

        times = list(node_times.values())
        n_nodes = len(times)

        if n_nodes == 0:
            return {}

        # Use IQR-based robust scaling
        times_sorted = sorted(times)
        q1_idx = n_nodes // 4
        q3_idx = (3 * n_nodes) // 4

        q1 = times_sorted[q1_idx] if q1_idx < n_nodes else times_sorted[0]
        q3 = times_sorted[q3_idx] if q3_idx < n_nodes else times_sorted[-1]
        iqr = q3 - q1

        if iqr > 0:
            robust_min = q1 - 1.5 * iqr
            robust_max = q3 + 1.5 * iqr
        else:
            robust_min = min(times)
            robust_max = max(times)

        actual_min = min(times)
        actual_max = max(times)
        robust_min = max(robust_min, actual_min)
        robust_max = min(robust_max, actual_max)
        robust_range = robust_max - robust_min

        # Normalize to [0, 1]
        if robust_range > 0:
            normalized = {}
            for node, t in node_times.items():
                t_clamped = max(robust_min, min(robust_max, t))
                normalized[node] = (t_clamped - robust_min) / robust_range
        else:
            normalized = {node: i / max(n_nodes - 1, 1) for i, node in enumerate(valid_nodes)}

        # Check IQR spread - if too small, redistribute by rank
        norm_values = sorted(normalized.values())
        norm_q1 = norm_values[len(norm_values) // 4]
        norm_q3 = norm_values[(3 * len(norm_values)) // 4]
        iqr_spread = norm_q3 - norm_q1

        if iqr_spread < 0.25:
            sorted_nodes = sorted(node_times.keys(), key=lambda n: node_times[n])
            for rank, node in enumerate(sorted_nodes):
                normalized[node] = rank / max(n_nodes - 1, 1)

        # Phase 15.6: Debug Y-axis assignment
        for node, norm_y in normalized.items():
            node_data = graph.nodes.get(node, {})
            name = node_data.get("name", node_data.get("payload", {}).get("name", "unknown"))
            timestamp = node_times.get(node, 0)
            logger.info(f"[Y-Time] {name}: timestamp={timestamp:.0f}, normalized_y={norm_y:.3f}")

        return normalized

    def _calculate_y_by_semantic(self, graph: nx.Graph, valid_nodes: List[str]) -> Dict[str, float]:
        """
        Calculate normalized Y positions (0 to 1) based on semantic hierarchy.

        Phase 15.7: Uses asymmetric projections to determine which files
        "depend on" others. Files that depend on many others are more
        advanced/complex and positioned higher.

        Principle:
        - Basic/foundational files (depended upon) → lower Y
        - Advanced/dependent files (depend on others) → higher Y
        """
        if not valid_nodes:
            return {}

        # Collect embeddings for all valid nodes
        embeddings = {}
        for node in valid_nodes:
            node_data = graph.nodes.get(node, {})
            emb = node_data.get("embedding", [])
            if emb and len(emb) > 0:
                embeddings[node] = np.array(emb)

        if len(embeddings) < 2:
            # Not enough embeddings for comparison — fallback to even distribution
            logger.warning(
                f"[Y-Semantic] Only {len(embeddings)} embeddings found, "
                "using even distribution"
            )
            return {node: 0.5 for node in valid_nodes}

        # Compute semantic hierarchy using asymmetric projections
        normalized = compute_semantic_hierarchy(embeddings, graph)

        # For nodes without embeddings, assign middle value
        for node in valid_nodes:
            if node not in normalized:
                normalized[node] = 0.5

        # Phase 15.7: Debug Y-axis semantic assignment with dependency scores
        for node, norm_y in normalized.items():
            node_data = graph.nodes.get(node, {})
            payload = node_data.get("payload", {})
            filename = payload.get("name", "") or node_data.get("name", "unknown")
            logger.info(
                f"[Y-Semantic] {filename}: hierarchy_score={norm_y:.3f} "
                f"({'advanced/high' if norm_y > 0.7 else 'basic/low' if norm_y < 0.3 else 'middle'})"
            )

        # Log overall distribution
        scores = list(normalized.values())
        logger.info(
            f"[Y-Semantic] Distribution: min={min(scores):.3f}, "
            f"max={max(scores):.3f}, spread={max(scores) - min(scores):.3f}"
        )

        return normalized

    def _calculate_all_y_positions(self, graph: nx.Graph, valid_nodes: List[str]) -> Dict[str, float]:
        """
        Calculate Y positions using HYBRID formula: 50% time + 50% semantic.

        Phase 15.4: Files are positioned ABOVE ground (Y >= 20).
        Higher phase numbers and newer files are positioned higher.
        """
        if not valid_nodes:
            return {}

        n_nodes = len(valid_nodes)

        # 1. Get time-based Y (normalized 0-1)
        y_time = self._calculate_y_by_time(graph, valid_nodes)

        # 2. Get semantic-based Y (normalized 0-1)
        y_semantic = self._calculate_y_by_semantic(graph, valid_nodes)

        # 3. Combine: 50% time + 50% semantic
        y_combined = {}
        for node in valid_nodes:
            y_t = y_time.get(node, 0.5)
            y_s = y_semantic.get(node, 0.5)
            y_combined[node] = 0.5 * y_t + 0.5 * y_s

        # 4. Scale to final range: [GROUND_OFFSET, GROUND_OFFSET + SCALE_Y]
        # This ensures ALL files are ABOVE ground (Y >= 20)
        GROUND_OFFSET = 20  # Minimum Y value above ground
        scale_y = self.SCALE["y"]  # 300

        y_positions = {}
        for node, norm_y in y_combined.items():
            # Range: [20, 320] instead of [-150, 150]
            y_positions[node] = GROUND_OFFSET + norm_y * scale_y

        # Log results
        final_ys = list(y_positions.values())
        logger.info(f"[Y-Axis] Hybrid output range: {min(final_ys):.1f} to {max(final_ys):.1f}")

        return y_positions

    def _calculate_z_for_duplicates(
        self,
        graph: nx.Graph,
        valid_nodes: List[str],
        embeddings: np.ndarray
    ) -> Dict[str, float]:
        """
        Calculate Z positions: Only duplicates get non-zero Z.

        Z-axis is used ONLY for near-duplicate files (cosine similarity > 0.95).
        Phase 15.5: Increased threshold and check same extension.
        - Original (created earlier): Z = 0
        - Duplicates (created later): Z = -50, -100, ... (behind original)

        All non-duplicate files: Z = 0
        """
        DUPLICATE_THRESHOLD = 0.95  # Phase 15.5: Increased from 0.92
        Z_OFFSET = -50  # Each duplicate goes further back

        z_positions = {node: 0.0 for node in valid_nodes}
        processed = set()

        # Build node -> embedding index map
        node_to_idx = {node: i for i, node in enumerate(valid_nodes)}

        # Helper: get file extension
        def get_extension(node):
            payload = graph.nodes.get(node, {}).get("payload", {})
            name = payload.get("name", "") or graph.nodes.get(node, {}).get("name", "")
            if "." in name:
                return name.rsplit(".", 1)[-1].lower()
            return ""

        for i, node_i in enumerate(valid_nodes):
            if node_i in processed:
                continue

            emb_i = embeddings[i]
            norm_i = np.linalg.norm(emb_i)

            if norm_i == 0:
                continue

            ext_i = get_extension(node_i)

            # Find duplicates of this file
            duplicates = []
            for j, node_j in enumerate(valid_nodes):
                if i == j or node_j in processed:
                    continue

                emb_j = embeddings[j]
                norm_j = np.linalg.norm(emb_j)

                if norm_j == 0:
                    continue

                # Phase 15.5: Check same extension
                ext_j = get_extension(node_j)
                if ext_i and ext_j and ext_i != ext_j:
                    continue  # Different extensions = not duplicates

                # Cosine similarity
                similarity = np.dot(emb_i, emb_j) / (norm_i * norm_j)

                if similarity > DUPLICATE_THRESHOLD:
                    duplicates.append((node_j, similarity))

            if duplicates:
                # Collect all nodes in this duplicate group
                all_group = [node_i] + [d[0] for d in duplicates]

                # Get creation times
                def get_time(n):
                    payload = graph.nodes.get(n, {}).get("payload", {})
                    t = (
                        payload.get("created_time") or
                        payload.get("modified_time") or
                        0
                    )
                    return self._parse_timestamp(t)

                # Sort by creation time (oldest first = original)
                all_group.sort(key=get_time)

                # Original (first) stays at Z=0, duplicates go back
                for idx, node in enumerate(all_group):
                    z_positions[node] = idx * Z_OFFSET
                    processed.add(node)

                logger.info(f"[Z-Axis] Duplicate group: {len(all_group)} files, original={all_group[0]}")

        # Count non-zero Z positions
        non_zero = sum(1 for z in z_positions.values() if z != 0)
        logger.info(f"[Z-Axis] Duplicates found: {non_zero} files with Z != 0")

        return z_positions

    def _calculate_y(
        self,
        graph: nx.Graph,
        node: str,
        index: int,
        total: int
    ) -> float:
        """
        Calculate Y position based on created_time (VETKA Theory: Y = time).
        Older files are lower, newer files are higher.

        NOTE: This method is kept for backwards compatibility but the main
        logic now uses _calculate_all_y_positions for adaptive distribution.
        """
        # Get created_time from node payload
        node_data = graph.nodes.get(node, {})
        payload = node_data.get("payload", {})

        # Try to get created_time from multiple sources
        created_time = (
            payload.get("created_time") or
            payload.get("created_at") or
            payload.get("modified_time") or
            payload.get("timestamp") or
            0
        )

        # Convert to float if needed
        try:
            created_time = float(created_time)
        except (ValueError, TypeError):
            created_time = 0

        # Collect all times from graph to normalize
        all_times = []
        for n in graph.nodes():
            n_data = graph.nodes.get(n, {})
            n_payload = n_data.get("payload", {})
            t = (
                n_payload.get("created_time") or
                n_payload.get("created_at") or
                n_payload.get("modified_time") or
                n_payload.get("timestamp") or
                0
            )
            try:
                all_times.append(float(t))
            except (ValueError, TypeError):
                all_times.append(0)

        if not all_times or max(all_times) == min(all_times):
            # Fallback to index-based positioning
            return (index / max(total - 1, 1)) * self.SCALE["y"]

        # Normalize time to [0, 1] range
        min_time = min(all_times)
        max_time = max(all_times)
        time_range = max_time - min_time

        normalized = (created_time - min_time) / time_range if time_range > 0 else 0.5

        # Scale to Y range: center around 0 for better Three.js positioning
        # Range: [-SCALE/2, +SCALE/2] so older files are below, newer above
        return (normalized - 0.5) * self.SCALE["y"]

    def _fallback_spring_layout(self, graph: nx.Graph) -> Dict[str, Dict]:
        """
        Fallback to NetworkX spring layout when UMAP fails.
        Phase 15.6: Use time-based Y positioning, not random spring Y.
        """
        if graph.number_of_nodes() == 0:
            return {}

        valid_nodes = list(graph.nodes())

        # Use spring layout for X/Z only
        pos = nx.spring_layout(graph, dim=3, seed=42, scale=100)

        # Phase 15.6: Calculate time-based Y positions (same as main flow)
        y_time_norm = self._calculate_y_by_time(graph, valid_nodes)
        y_semantic_norm = self._calculate_y_by_semantic(graph, valid_nodes)
        y_positions = self._calculate_all_y_positions(graph, valid_nodes)

        GROUND_OFFSET = 20
        scale_y = self.SCALE["y"]

        result = {}
        for node, coords in pos.items():
            # Get time-based Y, not spring layout Y
            y_t = y_time_norm.get(node, 0.5)
            y_s = y_semantic_norm.get(node, 0.5)
            y_final = y_positions.get(node, 20)

            # Get created_time for date display
            node_data = graph.nodes.get(node, {})
            payload = node_data.get("payload", {})
            created_time = (
                payload.get("created_time") or
                payload.get("modified_time") or
                0
            )
            created_time_float = self._parse_timestamp(created_time)

            result[node] = {
                "x": float(coords[0]),
                "y": float(y_final),  # Phase 15.6: Use time-based Y
                "z": float(coords[2]),
                "y_time": float(GROUND_OFFSET + y_t * scale_y),
                "y_semantic": float(GROUND_OFFSET + y_s * scale_y),
                "created_time": created_time_float,
                "cluster": -1,
                "color": "#8AA0B0"
            }

        # Phase 15.8: Spread files with same Y by time of day
        result = apply_intraday_x_spread(result, graph)

        # Phase 15.9: Adaptive Y scale for X-close files
        result = adaptive_y_scale_by_x_proximity(result, graph, min_separation=15.0)

        # Phase 15.9: Guarantee minimum Y separation
        result = ensure_min_y_separation(result, min_separation=15.0)

        # Phase 15.8: Center by center of mass (X and Z)
        result = center_graph_by_mass(result)

        logger.info(f"[Fallback] Applied time-based Y to {len(result)} nodes")
        return result

    def apply_positions_to_graph(
        self,
        graph: nx.Graph,
        positions: Dict[str, Dict]
    ) -> nx.Graph:
        """
        Apply calculated positions to graph nodes.
        Modifies graph in place and returns it.
        """
        for node, pos in positions.items():
            if node in graph.nodes:
                graph.nodes[node]["x"] = pos["x"]
                graph.nodes[node]["y"] = pos["y"]
                graph.nodes[node]["z"] = pos["z"]
                graph.nodes[node]["cluster"] = pos["cluster"]
                graph.nodes[node]["node_color"] = pos["color"]

        return graph

    def export_with_positions(self, graph: nx.Graph) -> Dict:
        """
        Calculate positions and export in Three.js format.

        Phase 15.5: Added y_time, y_semantic, created_time for frontend blend slider.

        Returns:
            {
                "nodes": [{"id", "path", "name", "x", "y", "z", "y_time", "y_semantic", "created_time", "cluster", "color"}],
                "edges": [...],
                "clusters": [{"id", "count", "color"}]
            }
        """
        positions = self.calculate_positions(graph)

        nodes = []
        cluster_counts = {}

        for node_id, data in graph.nodes(data=True):
            pos = positions.get(node_id, {
                "x": 0, "y": 20, "z": 0,
                "y_time": 20, "y_semantic": 20, "created_time": 0,
                "cluster": -1, "color": "#666666"
            })
            cluster = pos["cluster"]

            # Phase 15.9: Get both created_time and modified_time
            payload = data.get("payload", {})
            created_time = pos.get("created_time", 0)
            modified_time = (
                payload.get("modified_time") or
                payload.get("modified_at") or
                0
            )
            if isinstance(modified_time, str):
                modified_time = parse_timestamp_precise(modified_time) or 0

            nodes.append({
                "id": node_id,
                "path": data.get("path", payload.get("path", "unknown")),
                "name": data.get("name", payload.get("name", "unknown")),
                "language": data.get("language", "unknown"),
                "preview": payload.get("preview", ""),  # Phase 15.9: Add preview
                "x": pos["x"],
                "y": pos["y"],
                "z": pos["z"],
                # Phase 15.5: Separate Y values for frontend blend slider
                "y_time": pos.get("y_time", pos["y"]),
                "y_semantic": pos.get("y_semantic", pos["y"]),
                "created_time": created_time,
                "modified_time": modified_time,  # Phase 15.9: Add modified_time
                "cluster": cluster,
                "color": pos["color"]
            })

            # Count cluster members
            if cluster >= 0:
                cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1

        edges = []
        for source, target, data in graph.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                "type": data.get("edge_type", "depends_on"),
                "color": data.get("color", "#8AA0B0"),
                "weight": data.get("weight", 0.5)
            })

        # Build cluster info
        clusters = []
        for cluster_id, count in sorted(cluster_counts.items()):
            clusters.append({
                "id": cluster_id,
                "count": count,
                "color": self.CLUSTER_COLORS[cluster_id % len(self.CLUSTER_COLORS)]
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "clusters": clusters,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "cluster_count": len(clusters)
            }
        }
