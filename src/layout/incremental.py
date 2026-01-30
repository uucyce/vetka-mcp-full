"""
Phase 15: Incremental Layout & Soft Repulsion.

Real-time layout updates with velocity-based soft repulsion
and AABB collision detection for file columns. Supports
incremental branch detection and SocketIO real-time updates.

@status: active
@phase: 96
@depends: math, collections, typing
@used_by: src.layout, src.visualizer.tree_renderer
"""

import math
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Callable


# ============================================================================
# MODULE-LEVEL STATE
# ============================================================================

# Global state for Phase 15 incremental detection
_phase15_last_branch_count = 0
_phase15_velocity = {}  # Persistent velocity for soft repulsion


def reset_incremental_state() -> None:
    """Reset incremental layout state. Call when starting fresh layout."""
    global _phase15_last_branch_count, _phase15_velocity
    _phase15_last_branch_count = 0
    _phase15_velocity = {}


def get_last_branch_count() -> int:
    """Get the last known branch count for change detection."""
    return _phase15_last_branch_count


def set_last_branch_count(count: int) -> None:
    """Update the last known branch count."""
    global _phase15_last_branch_count
    _phase15_last_branch_count = count


# ============================================================================
# CHANGE DETECTION
# ============================================================================

def detect_new_branches(
    folders: Dict[str, dict],
    positions: Dict[str, dict],
    last_branch_count: int
) -> Tuple[List[str], List[str]]:
    """
    PHASE 15: Detect newly added branches.

    Compares current folder count with last known count to detect additions.
    Also identifies affected siblings and parents for incremental updates.

    Args:
        folders: Current dict of folder_path -> folder_data
        positions: Current positions dict
        last_branch_count: Previous count of folders

    Returns:
        Tuple of:
        - new_branches: List of newly added branch paths
        - affected_nodes: Parents and siblings that need recalculation

    Example:
        If a new folder "/Users/dan/docs/new" is added:
        - new_branches = ["/Users/dan/docs/new"]
        - affected_nodes = ["/Users/dan/docs/existing1", "/Users/dan/docs/existing2", "/Users/dan/docs"]
    """
    current_count = len(folders)

    if current_count > last_branch_count:
        # Something was added!
        new_branches = []
        for path in folders.keys():
            # This branch is new if not in positions yet
            if path not in positions:
                new_branches.append(path)

        if new_branches:
            print(f"[PHASE 15] Detected {len(new_branches)} new branches!")

        # Find affected siblings (neighbors of new branch)
        affected = set()
        for new_path in new_branches:
            # Get parent path
            parts = new_path.split('/')
            if len(parts) > 1:
                parent_path = '/'.join(parts[:-1])
            else:
                parent_path = ''

            # All children of this parent are affected
            for path in folders.keys():
                if path.startswith(parent_path + '/') if parent_path else True:
                    # Check if same depth level (sibling)
                    if path.count('/') == new_path.count('/'):
                        affected.add(path)

            # Parent is also affected
            if parent_path and parent_path in folders:
                affected.add(parent_path)

        return new_branches, list(affected)

    return [], []


# ============================================================================
# SOFT REPULSION (VELOCITY-BASED)
# ============================================================================

def apply_soft_repulsion(
    nodes_list: List[str],
    positions: Dict[str, dict],
    strength: float = 0.3,
    iterations: int = 3
) -> None:
    """
    PHASE 15: Soft repulsion with velocity and damping (Grok recommended).

    Uses inverse-square law for natural physics-like behavior.
    Velocity + damping ensures smooth motion without oscillation.

    Args:
        nodes_list: List of node paths at same depth level
        positions: Current positions dict (will be modified!)
        strength: 0.0-1.0 (0.3 = soft, 0.8 = strong)
        iterations: 3-5 recommended (not more for performance)

    Physics model:
        Force = k_repulsion / distance^2 (inverse square law)
        Velocity = (velocity + force) * damping
        Position += velocity
    """
    global _phase15_velocity

    if len(nodes_list) <= 1:
        return

    k_repulsion = 150 * strength  # Repulsion force constant
    damping = 0.5  # Damping for smoothness
    min_distance = 100  # Minimum distance (avoid division by near-zero)

    for iteration in range(iterations):
        for i, node_a in enumerate(nodes_list):
            if node_a not in positions:
                continue

            # Accumulate forces from all neighbors
            force_x = 0.0

            for j, node_b in enumerate(nodes_list):
                if i >= j or node_b not in positions:
                    continue

                pos_a = positions[node_a].get('x', 0)
                pos_b = positions[node_b].get('x', 0)

                distance = abs(pos_a - pos_b)

                # Inverse-square law (real physics!)
                if distance < min_distance:
                    distance = min_distance

                direction = 1 if pos_b < pos_a else -1
                repulsion = direction * k_repulsion / (distance ** 2)

                force_x += repulsion

            # Velocity integration with damping
            if node_a not in _phase15_velocity:
                _phase15_velocity[node_a] = 0.0

            v = _phase15_velocity[node_a]
            v = (v + force_x) * damping  # Apply force and damping

            # Update position
            positions[node_a]['x'] = positions[node_a].get('x', 0) + v
            _phase15_velocity[node_a] = v


def apply_soft_repulsion_for_layer(
    layer_nodes: List[str],
    positions: Dict[str, dict],
    strength: float = 0.3,
    iterations: int = 3
) -> None:
    """
    Apply soft repulsion to a single layer of nodes.

    Convenience wrapper for apply_soft_repulsion that first sorts
    nodes by X position for consistent repulsion direction.

    Args:
        layer_nodes: List of node paths at same depth
        positions: Current positions dict (modified in place)
        strength: Repulsion strength (0.0-1.0)
        iterations: Number of physics iterations
    """
    if len(layer_nodes) <= 1:
        return

    # Sort by current X position for consistent ordering
    layer_nodes_sorted = sorted(
        layer_nodes,
        key=lambda p: positions.get(p, {}).get('x', 0)
    )

    apply_soft_repulsion(layer_nodes_sorted, positions, strength, iterations)


def apply_soft_repulsion_all_layers(
    layers: Dict[int, List[str]],
    positions: Dict[str, dict],
    max_depth: int,
    strength: float = 0.3,
    iterations: int = 3
) -> None:
    """
    Apply soft repulsion to all layers in the tree.

    Processes layers from shallowest to deepest, ensuring
    parent positions settle before affecting children.

    Args:
        layers: Dict of depth -> [node_paths] at that depth
        positions: Current positions dict (modified in place)
        max_depth: Maximum tree depth
        strength: Repulsion strength (0.0-1.0)
        iterations: Physics iterations per layer
    """
    for depth in range(max_depth + 1):
        if depth in layers:
            layer_nodes = layers[depth]
            if len(layer_nodes) > 1:
                apply_soft_repulsion_for_layer(
                    layer_nodes,
                    positions,
                    strength,
                    iterations
                )
                print(f"[PHASE 15] Applied repulsion at depth {depth}: {len(layer_nodes)} nodes")


# ============================================================================
# COLLISION DETECTION
# ============================================================================

def check_file_collisions(
    branch_a_pos: dict,
    branch_b_pos: dict,
    files_a_count: int,
    files_b_count: int
) -> Tuple[bool, float]:
    """
    PHASE 15: AABB collision detection for file columns.

    Prevents file columns from different folders overlapping.
    Uses dynamic margin based on file count.

    Args:
        branch_a_pos: Position dict {x, y, ...} for first branch
        branch_b_pos: Position dict {x, y, ...} for second branch
        files_a_count: Number of files in first folder
        files_b_count: Number of files in second folder

    Returns:
        Tuple of:
        - collision: True if file columns overlap
        - overlap_amount: Amount of X-axis overlap in pixels
    """
    file_card_width = 60  # Width of file card
    file_spacing = 40  # Vertical spacing between files

    # Dynamic margin (more files = wider margin)
    base_margin = 20
    dynamic_margin = max(0, (max(files_a_count, files_b_count) - 5) / 20 * 10)
    min_gap = base_margin + dynamic_margin

    half_width = file_card_width / 2 + min_gap

    # AABB bounds for each folder
    bounds_a = {
        'x_min': branch_a_pos.get('x', 0) - half_width,
        'x_max': branch_a_pos.get('x', 0) + half_width,
        'y_min': branch_a_pos.get('y', 0),
        'y_max': branch_a_pos.get('y', 0) + (files_a_count - 1) * file_spacing
    }

    bounds_b = {
        'x_min': branch_b_pos.get('x', 0) - half_width,
        'x_max': branch_b_pos.get('x', 0) + half_width,
        'y_min': branch_b_pos.get('y', 0),
        'y_max': branch_b_pos.get('y', 0) + (files_b_count - 1) * file_spacing
    }

    # AABB overlap test
    overlap_x = not (bounds_a['x_max'] < bounds_b['x_min'] or
                     bounds_b['x_max'] < bounds_a['x_min'])
    overlap_y = not (bounds_a['y_max'] < bounds_b['y_min'] or
                     bounds_b['y_max'] < bounds_a['y_min'])

    if overlap_x and overlap_y:
        # Collision detected!
        overlap_amount = min(bounds_a['x_max'], bounds_b['x_max']) - max(bounds_a['x_min'], bounds_b['x_min'])
        return True, overlap_amount

    return False, 0


def resolve_file_collisions(
    folders: Dict[str, dict],
    positions: Dict[str, dict],
    files_by_folder: Dict[str, List[dict]]
) -> int:
    """
    Detect and resolve all file column collisions between sibling folders.

    Args:
        folders: Dict of folder_path -> folder_data
        positions: Current positions dict (modified in place)
        files_by_folder: Dict of folder_path -> [file_data]

    Returns:
        Number of collisions resolved
    """
    collision_resolved = 0
    all_branches = list(positions.keys())

    for i, branch_a in enumerate(all_branches):
        if branch_a not in folders:
            continue
        files_a = files_by_folder.get(branch_a, [])

        for j, branch_b in enumerate(all_branches):
            if i >= j or branch_b not in folders:
                continue

            # Only check siblings (same depth)
            if branch_a.count('/') != branch_b.count('/'):
                continue

            files_b = files_by_folder.get(branch_b, [])

            if files_a and files_b:
                collision, overlap = check_file_collisions(
                    positions.get(branch_a, {}),
                    positions.get(branch_b, {}),
                    len(files_a),
                    len(files_b)
                )

                if collision:
                    # Push branches apart
                    shift = overlap / 2 + 10  # Extra 10px margin
                    if positions[branch_a].get('x', 0) < positions[branch_b].get('x', 0):
                        positions[branch_a]['x'] -= shift
                        positions[branch_b]['x'] += shift
                    else:
                        positions[branch_a]['x'] += shift
                        positions[branch_b]['x'] -= shift
                    collision_resolved += 1

    if collision_resolved > 0:
        print(f"[PHASE 15] Resolved {collision_resolved} file collisions")

    return collision_resolved


# ============================================================================
# INCREMENTAL LAYOUT UPDATE
# ============================================================================

def incremental_layout_update(
    new_branches: List[str],
    affected_nodes: List[str],
    folders: Dict[str, dict],
    positions: Dict[str, dict],
    files_by_folder: Dict[str, List[dict]],
    layout_subtree_func: Optional[Callable] = None,
    max_depth: int = 0
) -> None:
    """
    PHASE 15: Update layout incrementally for new and affected nodes.

    Only recalculates positions for new branches and their siblings,
    not the entire tree. Much faster for real-time updates.

    Args:
        new_branches: List of new branch paths
        affected_nodes: List of nodes that need recalculation
        folders: Dict of all folder data
        positions: Current positions (will be modified!)
        files_by_folder: Dict of files per folder
        layout_subtree_func: Reference to layout_subtree function (optional)
        max_depth: Maximum tree depth

    Algorithm:
        1. Group affected nodes by depth level
        2. Apply soft repulsion to each depth level (siblings only)
        3. Check for file column collisions and resolve
    """
    print(f"[PHASE 15] Incremental update: {len(new_branches)} new, {len(affected_nodes)} affected")

    # Group affected nodes by depth level
    by_depth = defaultdict(list)

    for path in affected_nodes:
        if path in positions:
            depth = path.count('/')
            by_depth[depth].append(path)

    # Apply soft repulsion to each depth level
    for depth, siblings in by_depth.items():
        if len(siblings) > 1:
            # Sort by current X position
            siblings.sort(key=lambda p: positions.get(p, {}).get('x', 0))

            # Apply soft repulsion
            apply_soft_repulsion(siblings, positions, strength=0.3, iterations=3)

            print(f"[PHASE 15] Applied repulsion at depth {depth}: {len(siblings)} siblings")

    # Check for file collisions and resolve
    resolve_file_collisions(folders, positions, files_by_folder)


# ============================================================================
# REAL-TIME UPDATE WITH SOCKETIO
# ============================================================================

def emit_layout_update(
    socketio_instance,
    new_branches: List[str],
    affected_count: int,
    total_folders: int
) -> bool:
    """
    Emit real-time layout update via SocketIO.

    Args:
        socketio_instance: Flask-SocketIO instance
        new_branches: List of new branch paths
        affected_count: Number of affected nodes
        total_folders: Total folder count

    Returns:
        True if emit succeeded, False otherwise
    """
    if not socketio_instance:
        return False

    try:
        socketio_instance.emit('layout_updated', {
            'new_branches': new_branches,
            'affected_count': affected_count,
            'total_folders': total_folders
        }, broadcast=True)
        return True
    except Exception as e:
        print(f"[PHASE 15] SocketIO emit skipped: {e}")
        return False
