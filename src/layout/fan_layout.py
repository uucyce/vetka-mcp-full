"""
Directory Mode FAN Layout Algorithm.

Phase 14 + 17: Adaptive fan layout with Grok formulas.
Sugiyama-style layout with crossing reduction and anti-gravity.
Provides adaptive branch length, file spacing, and repulsion calculations.

@status: active
@phase: 96
@depends: math, collections, typing
@used_by: src.layout, src.visualizer.tree_renderer
"""

import math
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Callable


# ============================================================================
# ADAPTIVE FORMULA FUNCTIONS (Grok research, December 2025)
# Phase 27.9: Fixed formulas for better tree spread
# ============================================================================

# CRITICAL CONSTANTS - Prevent "needle" branches at deep levels
MIN_SPREAD = 45  # degrees - FLOOR, branches never narrower than this
MAX_SPREAD = 180  # degrees - maximum spread at root level
BASE_RADIUS = 150  # base branch length in pixels
DEPTH_DECAY_FLOOR = 0.4  # minimum decay factor (40%) for deep branches


def calculate_adaptive_branch_params(
    folder_path: str,
    files_by_folder: Dict[str, List[dict]],
    current_depth: int,
    max_depth: int
) -> dict:
    """
    Phase 27.9: Adaptive branch parameter calculation.

    Solves the problem of deep branches collapsing into needles by:
    1. Using MIN_SPREAD floor for angles (never less than 45 degrees)
    2. Scaling branch length based on folder content density
    3. Maintaining minimum decay factor for deep levels

    Args:
        folder_path: Path to the folder
        files_by_folder: Dict of folder_path -> list of files
        current_depth: Current depth level (0 = root)
        max_depth: Maximum tree depth

    Returns:
        dict with keys:
        - length: Adaptive branch length (pixels)
        - max_angle: Maximum fan angle (degrees)
        - y_offset: Vertical offset for this branch (pixels)
    """
    # Count files in this folder
    files_count = len(files_by_folder.get(folder_path, []))

    # === ADAPTIVE LENGTH ===
    # Density factor: more files = longer branch (each 10 files +20%)
    density_factor = 1.0 + (files_count * 0.02)

    # Depth decay with FLOOR - deep branches don't disappear
    if max_depth > 0:
        depth_decay = max(DEPTH_DECAY_FLOOR, 1.0 - (current_depth / (max_depth + 1)))
    else:
        depth_decay = 1.0

    adaptive_length = BASE_RADIUS * density_factor * depth_decay

    # === ADAPTIVE ANGLE ===
    # Linear interpolation with FLOOR
    if max_depth > 0:
        spread_factor = 1.0 - (current_depth / (max_depth + 1))
        adaptive_max_angle = max(MIN_SPREAD, MAX_SPREAD * spread_factor)
    else:
        adaptive_max_angle = MAX_SPREAD

    # === Y-OFFSET ===
    # Heavy folders get more vertical space
    y_offset = 80 + (files_count * 0.5)

    return {
        'length': adaptive_length,
        'max_angle': adaptive_max_angle,
        'y_offset': y_offset
    }


def calculate_branch_length(max_depth: int, max_folders_per_layer: int, screen_width: int = 1920) -> float:
    """
    Calculate adaptive BRANCH_LENGTH based on tree width.

    Args:
        max_depth: Maximum directory depth
        max_folders_per_layer: Max folders at any single depth level
        screen_width: Screen width in pixels (default 1920)

    Returns:
        Branch length in pixels (150-400 range)
    """
    if max_depth <= 1:
        return 300

    # Available horizontal space (80% of screen, minus margins)
    available_width = screen_width * 0.8

    # Estimate: each layer adds branches horizontally
    estimated_width_needed = max_folders_per_layer * 100

    # Scale branch length to fit tree on screen
    branch_length = available_width / (max_depth * 1.5)

    # Constraints: readable but not too sparse
    return max(150, min(400, branch_length))


def calculate_file_spacing_adaptive(files_count: int, branch_length: float) -> float:
    """
    Calculate adaptive FILE_SPACING based on file count.

    Args:
        files_count: Number of files in folder
        branch_length: Current branch length

    Returns:
        File spacing in pixels (25-50 range)
    """
    if files_count <= 1:
        return 0

    # Available space along branch (70% of branch length)
    available = branch_length * 0.7

    # Distribute files evenly
    spacing = available / files_count

    # Constraints: readable stacking
    return max(25, min(50, spacing))


def calculate_layer_height_vertical(max_depth: int, screen_height: int = 1080) -> float:
    """
    Calculate adaptive vertical spacing for vertical tree growth.

    Inverse to calculate_branch_length:
    - Branch length: horizontal spread depends on max_depth
    - Layer height: vertical spacing depends on max_depth

    Args:
        max_depth: Maximum directory depth
        screen_height: Available screen height (default 1080px)

    Returns:
        Y spacing per depth level (pixels)

    Example:
        depth=3 -> 200px (taller, fewer levels)
        depth=6 -> 108px (medium)
        depth=10 -> 80px (compressed, many levels)
    """
    available_height = screen_height * 0.6  # 60% of screen for tree
    layer_height = available_height / max(1, max_depth)

    # Constraints: keep readable (80px min, 200px max)
    return max(80, min(200, layer_height))


# ============================================================================
# ANTI-GRAVITY FUNCTIONS (Phase 14 Part 2)
# ============================================================================

def calculate_static_repulsion(
    folders_at_depth: List[str],
    positions: Dict[str, dict],
    depth: int,
    max_depth: int,
    min_distance: int = 150
) -> None:
    """
    Apply static repulsion forces between folders at the same depth level.

    Uses AABB (Axis-Aligned Bounding Box) collision detection to prevent
    folder overlapping. Iteratively pushes folders apart if they're too close.

    Args:
        folders_at_depth: List of folder_paths at this depth level
        positions: Current positions dict (will be modified!)
        depth: Current depth level
        max_depth: Maximum tree depth
        min_distance: Minimum allowed distance between folder centers (pixels)

    Algorithm:
        1. Calculate repulsion strength based on depth (stronger at shallow levels)
        2. For each pair of folders at same depth:
           - Check distance between centers
           - If distance < min_distance, apply repulsion force
        3. Repeat 10 times for settling effect
    """
    if len(folders_at_depth) < 2:
        return  # No repulsion needed for single folder

    # Depth-based strength: maintain strong repulsion at all levels
    # Use minimum 0.6 factor so deep levels still get 60% strength
    strength_factor = max(0.6, (max_depth - depth) / max(max_depth, 1))
    repulsion_strength = 100 * strength_factor  # Increased from 80 to 100px

    # Iterative relaxation (10 passes for better settling)
    for iteration in range(10):
        for i, folder_a in enumerate(folders_at_depth):
            for j, folder_b in enumerate(folders_at_depth):
                if i >= j:
                    continue  # Avoid duplicate pairs and self-comparison

                pos_a = positions.get(folder_a)
                pos_b = positions.get(folder_b)

                if not pos_a or not pos_b:
                    continue

                # Calculate distance between folder centers
                dx = pos_b['x'] - pos_a['x']
                dy = pos_b['y'] - pos_a['y']
                distance = math.sqrt(dx**2 + dy**2)

                # Apply repulsion if too close
                if 0 < distance < min_distance:
                    # Normalize direction vector
                    if distance > 0:
                        nx = dx / distance
                        ny = dy / distance
                    else:
                        # Folders at exact same position - push in random direction
                        nx = 1.0
                        ny = 0.0

                    # Calculate push amount (aggressive)
                    overlap = min_distance - distance
                    push = overlap * 0.8  # 0.8 for stronger push

                    # Push folders apart (each moves half the distance)
                    pos_a['x'] -= nx * push * 0.5
                    pos_b['x'] += nx * push * 0.5
                    # Keep Y fixed to maintain layer structure


def calculate_dynamic_angle_spread(depth: int, max_depth: int, child_count: int) -> float:
    """
    Phase 27.9 FIX: Calculate adaptive fan angle with MIN_SPREAD floor.

    Returns wider angles for shallow levels (more spread needed)
    and narrower angles for deep levels, but NEVER below MIN_SPREAD.

    Args:
        depth: Current depth level
        max_depth: Maximum tree depth
        child_count: Number of children to spread

    Returns:
        Fan angle in degrees (minimum MIN_SPREAD)

    Formula (FIXED):
        spread_factor = 1 - depth / (max_depth + 1)
        angle = max(MIN_SPREAD, MAX_SPREAD * spread_factor)

    Examples (with MIN_SPREAD=45, MAX_SPREAD=180):
        depth=0 (root): 180 (wide spread)
        depth=3, max=6: ~103 (medium spread)
        depth=6, max=6: ~77 (still decent spread)
        depth=10, max=10: 45 (MIN_SPREAD floor kicks in)
    """
    if max_depth == 0:
        return MAX_SPREAD  # Single level = full spread

    # Phase 27.9 FIX: Use (max_depth + 1) to prevent division issues
    # and ensure deep levels still get reasonable spread
    spread_factor = 1.0 - (depth / (max_depth + 1))

    # Apply floor - NEVER go below MIN_SPREAD
    base_angle = max(MIN_SPREAD, MAX_SPREAD * spread_factor)

    # Adjust for child count: more children need more spread
    if child_count <= 1:
        return base_angle
    elif child_count == 2:
        # Less spread for binary splits, but still respect floor
        return max(MIN_SPREAD, base_angle * 0.7)
    else:
        return base_angle  # Full spread for multiple children


def minimize_crossing_barycenter(
    children_paths: List[str],
    parent_angle: float,
    folders: Dict[str, dict]
) -> List[str]:
    """
    Reorder children using barycenter method to minimize edge crossings.

    This is a simplified version of the Sugiyama crossing reduction algorithm.
    Orders children by their angular position relative to parent.

    Args:
        children_paths: List of child folder paths
        parent_angle: Parent folder's angle
        folders: Full folders dict for lookup

    Returns:
        Reordered list of children_paths

    Algorithm:
        1. Calculate barycenter (average position) for each child
        2. Sort children by their angular distance from parent
        3. Children aligned with parent come first, outliers come last
    """
    if len(children_paths) <= 1:
        return children_paths

    # Calculate "barycenter" as angular alignment with parent
    # Children that continue in parent direction get priority
    def calculate_priority(child_path):
        folder = folders.get(child_path)
        if not folder:
            return 0

        # Priority based on folder name (alphabetical for now)
        # In full implementation, this would use child positions
        return folder.get('name', '')

    # Sort children by priority (alphabetical as proxy for spatial ordering)
    sorted_children = sorted(children_paths, key=calculate_priority)
    return sorted_children


# ============================================================================
# MAIN LAYOUT FUNCTION
# ============================================================================

def calculate_directory_fan_layout(
    folders: Dict[str, dict],
    files_by_folder: Dict[str, List[dict]],
    all_files: List[dict],
    socketio_instance=None,
    screen_width: int = 1920,
    screen_height: int = 1080
) -> Tuple[Dict[str, dict], List[str], float, float, float]:
    """
    Calculate FAN layout for DIRECTORY MODE.

    Phase 14 + 17: Sugiyama-style adaptive fan layout with:
    - Adaptive branch length based on tree size
    - Adaptive file spacing based on file count
    - Anti-gravity repulsion to prevent overlapping
    - Crossing reduction via barycenter sorting
    - Orthogonal vertical file stacking

    Args:
        folders: Dict of folder_path -> folder_data
            folder_data = {
                'path': str,
                'name': str,
                'parent_path': str | None,
                'depth': int,
                'children': List[str]
            }
        files_by_folder: Dict of folder_path -> [file_data]
            file_data = {
                'id': str,
                'name': str,
                'path': str,
                'created_time': float,
                'modified_time': float,
                'extension': str,
                'content': str
            }
        all_files: List of all file data (for reference)
        socketio_instance: Optional Flask-SocketIO instance for real-time updates
        screen_width: Screen width in pixels (default 1920)
        screen_height: Screen height in pixels (default 1080)

    Returns:
        Tuple of:
        - positions: Dict of node_id -> {x, y, z, angle, ...}
        - root_folders: List of root folder paths
        - BRANCH_LENGTH: Calculated branch length
        - FAN_ANGLE: Fan angle (constant 130)
        - Y_PER_DEPTH: Calculated vertical spacing per depth
    """
    print("[LAYOUT] Starting ADAPTIVE FAN layout with Grok formulas...")

    # ========================================================================
    # PRE-CALCULATE: Analyze dataset for adaptive parameters
    # ========================================================================

    max_depth = max((f.get('depth', 0) for f in folders.values()), default=0)
    max_files_per_folder = max((len(files_by_folder.get(fp, [])) for fp in folders), default=0)

    # Count folders per depth layer
    folders_per_depth = defaultdict(int)
    for f in folders.values():
        folders_per_depth[f.get('depth', 0)] += 1
    max_folders_per_layer = max(folders_per_depth.values(), default=1)

    print(f"[LAYOUT] Dataset analysis:")
    print(f"  - max_depth: {max_depth}")
    print(f"  - max_files_per_folder: {max_files_per_folder}")
    print(f"  - max_folders_per_layer: {max_folders_per_layer}")

    # ========================================================================
    # CALCULATE ADAPTIVE PARAMETERS
    # ========================================================================

    BRANCH_LENGTH = calculate_branch_length(max_depth, max_folders_per_layer, screen_width)
    FAN_ANGLE = 130  # Keep fan angle constant for now
    Y_PER_DEPTH = calculate_layer_height_vertical(max_depth, screen_height)

    print(f"[LAYOUT] Adaptive parameters:")
    print(f"  - BRANCH_LENGTH: {BRANCH_LENGTH:.0f}px (was 300px)")
    print(f"  - FAN_ANGLE: {FAN_ANGLE} (constant)")
    print(f"  - Y_PER_DEPTH: {Y_PER_DEPTH:.0f}px (adaptive)")

    positions = {}  # node_id -> {x, y, angle}

    # ========================================================================
    # RECURSIVE LAYOUT FUNCTION
    # ========================================================================

    def layout_subtree(folder_path: str, parent_x: float, parent_y: float,
                       parent_angle: float, depth: int) -> None:
        """
        Recursively layout a folder and its children in a fan.

        Phase 17.3 FIX: Use sin for X, cos for Y
        - sin(0)=0, sin(+-60)=+-0.87 -> horizontal fan spread
        - Y based purely on depth for clean layering
        """
        folder = folders.get(folder_path)
        if not folder:
            return

        # Phase 27.9: Get adaptive branch parameters for this specific folder
        branch_params = calculate_adaptive_branch_params(
            folder_path, files_by_folder, depth, max_depth
        )
        adaptive_length = branch_params['length']

        # Calculate folder position
        angle_rad = math.radians(parent_angle)
        if depth == 0:
            # Phase 76.5: Root folders spread horizontally (using parent_angle as spread indicator)
            # When there are multiple roots, parent_angle indicates their spread position
            if parent_angle != 0 or len(root_folders) > 1:
                # Multiple roots: use angle to spread them horizontally
                root_spread = BASE_RADIUS * 1.5  # Spread distance for root folders
                folder_x = math.sin(angle_rad) * root_spread
                folder_y = 0  # All roots at Y=0
            else:
                # Single root: keep at center
                folder_x, folder_y = 0, 0
        else:
            # Phase 27.9: Use adaptive branch length per folder
            # sin for X spread (horizontal fan), depth for Y (grows upward)
            folder_x = parent_x + math.sin(angle_rad) * adaptive_length
            folder_y = depth * Y_PER_DEPTH  # Y strictly by depth (root=0, leaves=max)

        # Use folder_path as key (consistent across the same request)
        positions[folder_path] = {
            'x': folder_x,
            'y': folder_y,
            'angle': parent_angle
        }

        # Layout child folders in a fan
        children = folder['children']
        if children:
            n_children = len(children)
            if n_children == 1:
                # Single child continues same direction
                child_angle = parent_angle
                layout_subtree(children[0], folder_x, folder_y, child_angle, depth + 1)
            else:
                # Apply crossing reduction and dynamic angle spread

                # Step 1: Reorder children to minimize crossings
                ordered_children = minimize_crossing_barycenter(children, parent_angle, folders)

                # Step 2: Calculate dynamic fan angle based on depth
                dynamic_fan_angle = calculate_dynamic_angle_spread(depth, max_depth, n_children)

                # Step 3: Spread children in fan with dynamic angle
                start_angle = parent_angle - dynamic_fan_angle / 2
                angle_step = dynamic_fan_angle / (n_children - 1)

                for i, child_path in enumerate(ordered_children):
                    child_angle = start_angle + i * angle_step
                    layout_subtree(child_path, folder_x, folder_y, child_angle, depth + 1)

        # Layout files in this folder using ORTHOGONAL VERTICAL layout (Phase 13)
        # WITH ADAPTIVE SPACING (Phase 14)
        folder_files = files_by_folder.get(folder_path, [])
        if folder_files:
            # Sort files by time (older first)
            folder_files.sort(key=lambda f: f['created_time'])
            n_files = len(folder_files)

            # ADAPTIVE FILE SPACING (Grok formula - Phase 14)
            FILE_SPACING = calculate_file_spacing_adaptive(n_files, BRANCH_LENGTH)

            # Phase 13: Orthogonal Vertical Layout
            # Files stack VERTICALLY (along Y-axis) instead of horizontally
            # Oldest files at bottom (lower Y), newest at top (higher Y)
            # All files align along the branch direction (X-Z plane)

            for i, file_data in enumerate(folder_files):
                # Phase 27.9: Files positioned along branch using adaptive length
                # Distance along branch (70% toward parent from folder)
                file_dist = adaptive_length * 0.7
                file_x = folder_x + math.sin(angle_rad) * file_dist

                # Phase 13: Vertical stacking by time
                # Phase 14: ADAPTIVE spacing per folder
                mid_index = (n_files - 1) / 2.0
                y_offset = (i - mid_index) * FILE_SPACING
                file_y = folder_y + y_offset

                # Phase 27.9: Z-axis offset to prevent z-fighting
                # Each file in stack gets small Z offset (index * 0.1)
                z_offset = i * 0.1

                # Phase 13: Rotation for orthogonal orientation
                # Rotate 90 degrees to perpendicular alignment
                rotation_z = parent_angle + 90

                positions[file_data['id']] = {
                    'x': file_x,
                    'y': file_y,
                    'z': z_offset,  # Phase 27.9: Use smaller z offset
                    'y_time': file_y,
                    'y_semantic': folder_y,
                    'angle': parent_angle,
                    'rotation_z': rotation_z,
                    'file_index': i,
                    'total_files': n_files,
                    'folder_path': folder_path,
                    'created_time': file_data['created_time']
                }

    # ========================================================================
    # EXECUTE LAYOUT
    # ========================================================================

    # Find root folders (no parent or empty string parent)
    root_folders = [p for p, f in folders.items() if not f['parent_path']]

    if len(root_folders) == 1:
        # Phase 17.3: Base angle 0 = RIGHT (horizontal spread)
        # cos(0)=1 -> max X movement, sin(0)=0 -> minimal Y
        layout_subtree(root_folders[0], 0, 0, 0, 0)
    else:
        # Multiple roots - spread them in a HORIZONTAL fan (-60 to +60)
        n_roots = len(root_folders)
        start_angle = -60   # Bottom-right
        angle_range = 120   # Spread to top-right
        for i, rf in enumerate(root_folders):
            angle = start_angle + (i / max(n_roots - 1, 1)) * angle_range
            layout_subtree(rf, 0, 0, angle, 0)

    # ========================================================================
    # APPLY ANTI-GRAVITY REPULSION
    # ========================================================================
    print("[ANTI-GRAVITY] Applying static repulsion to BRANCHES only (not leaves)...")

    # Group ONLY BRANCHES (folders, not files) by depth level
    branches_by_depth = defaultdict(list)

    # Build map: folder_path -> list of ALL file_ids in subtree (including subfolders)
    files_under_branch = defaultdict(list)
    for folder_path, folder_files in files_by_folder.items():
        for file_data in folder_files:
            file_id = file_data.get('id')
            if file_id and file_id in positions:
                # Add file to its direct parent
                files_under_branch[folder_path].append(file_id)

                # Also add file to ALL ancestor folders
                parts = folder_path.split('/')
                for i in range(1, len(parts)):
                    ancestor_path = '/'.join(parts[:i+1])
                    if ancestor_path and ancestor_path != folder_path:
                        files_under_branch[ancestor_path].append(file_id)

    # Group folders by depth
    for folder_path, folder in folders.items():
        if folder_path in positions:  # Only consider positioned folders
            depth = folder.get('depth', 0)
            branches_by_depth[depth].append(folder_path)

    # Apply repulsion to ALL depth levels (branches only!)
    repulsion_applied = 0
    files_repositioned = 0

    for depth_level in sorted(branches_by_depth.keys()):
        branches_at_level = branches_by_depth[depth_level]
        if len(branches_at_level) > 1:
            print(f"[ANTI-GRAVITY] Depth {depth_level}: applying repulsion to {len(branches_at_level)} branches")

            # Step 1: Save OLD branch positions (before repulsion)
            old_branch_positions = {b: positions[b]['x'] for b in branches_at_level if b in positions}

            # Step 2: Apply repulsion (modifies positions[branch]['x'])
            calculate_static_repulsion(branches_at_level, positions, depth_level, max_depth, min_distance=200)

            # Step 3: Move files to follow their parent branches
            for branch_path in branches_at_level:
                if branch_path in positions and branch_path in old_branch_positions:
                    old_x = old_branch_positions[branch_path]
                    new_x = positions[branch_path]['x']
                    dx = new_x - old_x  # How much did this branch move?

                    if abs(dx) > 0.1:  # Only if branch actually moved
                        # Move ALL nodes in subtree: sub-branches AND files
                        nodes_moved = 0

                        # Step 1: Move all sub-branches (children, grandchildren, etc.)
                        for sub_branch_path in folders.keys():
                            # Check if sub_branch is descendant of this branch
                            if sub_branch_path.startswith(branch_path + '/') and sub_branch_path in positions:
                                positions[sub_branch_path]['x'] += dx
                                nodes_moved += 1

                        # Step 2: Move all files under this branch
                        for file_id in files_under_branch.get(branch_path, []):
                            if file_id in positions:
                                positions[file_id]['x'] += dx
                                files_repositioned += 1
                                nodes_moved += 1

                        if nodes_moved > 0:
                            branch_name = branch_path.split('/')[-1]
                            print(f"[ANTI-GRAVITY]   -> Moved {nodes_moved} nodes under '{branch_name}' by dx={dx:.1f}px")

            repulsion_applied += 1

    print(f"[ANTI-GRAVITY] Applied repulsion to {repulsion_applied} depth levels")
    print(f"[ANTI-GRAVITY] Repositioned {files_repositioned} files to follow their parent branches")

    return positions, root_folders, BRANCH_LENGTH, FAN_ANGLE, Y_PER_DEPTH
