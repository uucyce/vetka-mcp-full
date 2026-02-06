# 🔬 VETKA LAYOUT SYSTEM - DEEP ANALYSIS REQUEST

## 🎯 ЦЕЛЬ ПРОЕКТА
VETKA - это 3D Knowledge Graph визуализатор. Мы строим **дерево файлов в 3D пространстве** где:
- **Y-ось** = высота (дети ВЫШЕ родителей, дерево растёт вверх)
- **X-ось** = горизонтальный разброс (веер)
- **Z-ось** = глубина/параллакс

## 🐛 ПРОБЛЕМА
Несмотря на все исправления в backend, **визуализация остаётся плоской** - все папки на одном уровне Y. Подозреваем что где-то позиции перезаписываются или игнорируются.

## 🔧 ЧТО МЫ УЖЕ СДЕЛАЛИ
1. Backend `fan_layout.py`: `folder_y = parent_y + Y_PER_DEPTH` (дети выше родителей)
2. Backend `tree_routes.py`: Пересчёт depth относительно root (root=0)
3. Frontend `useTreeData.ts`: Исправили детекцию invalid nodes (root с Y=0 теперь валиден)
4. Добавили логирование

## ❓ ЧТО НУЖНО НАЙТИ
1. **Где Y позиции перезаписываются?** - Ищите любые присваивания к `position.y` или `y:`
2. **Есть ли fallback который срабатывает?** - calculateSimpleLayout, другие layout функции
3. **Правильно ли передаются позиции из backend в frontend?** - API response → store
4. **Есть ли конфликт между Directory и Knowledge mode?**
5. **Кэширование?** - Может старые позиции где-то кэшируются

## 📊 ОЖИДАЕМОЕ ПОВЕДЕНИЕ
```
Root folder (depth=0) → Y = 0
  └── Child folder (depth=1) → Y = Y_PER_DEPTH (например 200)
       └── Grandchild (depth=2) → Y = 2 * Y_PER_DEPTH (400)
            └── Files → Y = parent_y + offset
```

## 🔍 МАРКЕРЫ ДЛЯ ПОИСКА
- `MARKER_111` - наши последние фиксы
- `MARKER_109` - DevPanel threshold
- `MARKER_110` - Y formula
- `calculateSimpleLayout` - fallback который может всё ломать
- `position.y` или `'y':` - где устанавливается Y

---

=== FILE 1: src/layout/fan_layout.py ===
```python
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

# MARKER_109_Y_FLOOR: Position protection constants
# Phase 109: Hard floor/ceiling to prevent nodes going "underground" or too high
MIN_Y_FLOOR = 20      # minimum Y position - nothing below this
MAX_Y_CEILING = 5000  # maximum Y position - reasonable upper bound


# MARKER_110_BACKEND_CONFIG: Import config getter with fallback for standalone usage
def _get_layout_config():
    """
    Get layout config from socket handler, with fallback for standalone usage.

    This function attempts to import the layout config from the socket handler.
    If the import fails (e.g., when running standalone without the full server),
    it returns the default config values.

    Returns:
        dict with layout configuration values
    """
    try:
        from src.api.handlers.layout_socket_handler import get_layout_config
        config = get_layout_config()
        print(f"[LAYOUT_CONFIG] Using dynamic config: Y_WEIGHT_TIME={config.get('Y_WEIGHT_TIME')}, MIN_Y={config.get('MIN_Y_FLOOR')}")
        return config
    except ImportError as e:
        # Fallback for standalone usage (tests, CLI, etc.)
        print(f"[LAYOUT_CONFIG] ImportError, using defaults: {e}")
        return {
            'Y_WEIGHT_TIME': 0.5,
            'Y_WEIGHT_KNOWLEDGE': 0.5,
            'MIN_Y_FLOOR': 20,
            'MAX_Y_CEILING': 5000,
            'FALLBACK_THRESHOLD': 0.5,
            'USE_SEMANTIC_FALLBACK': True,
        }


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
            # MARKER_111_FIX: Simple tree layout
            # X = parent_x + horizontal offset from angle
            # Y = parent_y + fixed step upward (children ABOVE parents)
            folder_x = parent_x + math.sin(angle_rad) * adaptive_length
            folder_y = parent_y + Y_PER_DEPTH  # Children are ABOVE parent (Y grows up)

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
                angle_step = dynamic_fan_angle / max(n_children - 1, 1)

                # MARKER_111_SPREAD: Spread siblings by angle only (no extra offsets)
                # The angle spread + branch length naturally separates them
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

            # MARKER_110_Y_FORMULA: Get Y-axis weights from config
            layout_config = _get_layout_config()
            y_weight_time = layout_config.get('Y_WEIGHT_TIME', 0.5)
            y_weight_knowledge = layout_config.get('Y_WEIGHT_KNOWLEDGE', 0.5)

            for i, file_data in enumerate(folder_files):
                # Phase 27.9: Files positioned along branch using adaptive length
                # Distance along branch (70% toward parent from folder)
                file_dist = adaptive_length * 0.7
                file_x = folder_x + math.sin(angle_rad) * file_dist

                # Phase 13: Vertical stacking by time
                # Phase 14: ADAPTIVE spacing per folder
                mid_index = (n_files - 1) / 2.0
                y_offset = (i - mid_index) * FILE_SPACING

                # MARKER_110_Y_FORMULA: Blend time-based and knowledge-based Y positioning
                # y_time_component: older files lower (based on sort index)
                # y_knowledge_component: semantic clustering (folder_y as base)
                y_time_component = folder_y + y_offset  # Original time-sorted stacking
                y_knowledge_component = folder_y  # Semantic: all files at folder level

                # Final Y = weighted blend: time vs knowledge
                file_y = (y_weight_time * y_time_component) + (y_weight_knowledge * y_knowledge_component)

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

    # ========================================================================
    # MARKER_109_Y_FLOOR + MARKER_110_BACKEND_CONFIG: ENFORCE HARD FLOOR/CEILING
    # Phase 109: Prevent nodes from going "underground" or too high
    # Phase 110: Use dynamic config values from DevPanel
    # ========================================================================

    # MARKER_110_BACKEND_CONFIG: Get dynamic config values
    config = _get_layout_config()
    min_y = config.get('MIN_Y_FLOOR', MIN_Y_FLOOR)
    max_y = config.get('MAX_Y_CEILING', MAX_Y_CEILING)

    floor_violations = 0
    ceiling_violations = 0

    for node_id, pos in positions.items():
        original_y = pos.get('y', 0)

        # Enforce floor
        if original_y < min_y:
            positions[node_id]['y'] = min_y
            positions[node_id]['y_time'] = max(pos.get('y_time', min_y), min_y)
            floor_violations += 1

        # Enforce ceiling
        elif original_y > max_y:
            positions[node_id]['y'] = max_y
            positions[node_id]['y_time'] = min(pos.get('y_time', max_y), max_y)
            ceiling_violations += 1

    if floor_violations > 0 or ceiling_violations > 0:
        print(f"[Y-FLOOR] Enforced position limits: {floor_violations} floor violations, {ceiling_violations} ceiling violations")
        print(f"[Y-FLOOR] MIN_Y={min_y}, MAX_Y={max_y} (from dynamic config)")

    return positions, root_folders, BRANCH_LENGTH, FAN_ANGLE, Y_PER_DEPTH
```

=== FILE 2: src/api/routes/tree_routes.py (lines 200-550) ===
```python
    7. Interaction:
       - Click chat node → opens ChatPanel with that chat
       - Shift+click → pins chat node (shows in context)
       - Can drag chat nodes to reorganize conversations
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    from datetime import datetime
    import math

    # MARKER_101.8_START: Source collection selection
    collection_name = "VetkaTree" if source == "vetka_tree" else "vetka_elisya"
    # MARKER_101.8_END

    try:
        memory = _get_memory_manager(request)
        qdrant = memory.qdrant if memory else None

        if not qdrant:
            return {
                'error': 'Qdrant not connected',
                'tree': {'nodes': [], 'edges': []}
            }

        # Import layout functions
        from src.layout.fan_layout import calculate_directory_fan_layout
        from src.layout.incremental import (
            detect_new_branches,
            incremental_layout_update,
            get_last_branch_count,
            set_last_branch_count,
        )
        from src.orchestration.cam_engine import calculate_surprise_metrics_for_tree

        # ═══════════════════════════════════════════════════════════════════
        # STEP 1: Get ALL scanned files from Qdrant
        # ═══════════════════════════════════════════════════════════════════
        all_files = []
        offset = None

        while True:
            results, offset = qdrant.scroll(
                collection_name=collection_name,  # MARKER_101.8: Use selected source
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="type", match=MatchValue(value="scanned_file")),
                        FieldCondition(key="deleted", match=MatchValue(value=False))
                    ]
                ),
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            all_files.extend(results)
            if offset is None:
                break

        print(f"[API] Found {len(all_files)} files in {collection_name}")

        if not all_files:
            return {'tree': {'nodes': [], 'edges': []}}

        # ═══════════════════════════════════════════════════════════════════
        # STEP 1.5: Mark deleted files (don't filter - show as ghost/transparent)
        # Phase 90.11: Keep deleted files but mark them for transparent rendering
        # ═══════════════════════════════════════════════════════════════════
        valid_files = []
        deleted_count = 0
        browser_count = 0
        for point in all_files:
            file_path = (point.payload or {}).get('path', '')
            # Phase 54.5: Keep browser:// virtual paths (from drag & drop)
            if file_path.startswith('browser://'):
                valid_files.append(point)
                browser_count += 1
            elif file_path:
                # Phase 90.11: Mark as deleted if file doesn't exist on disk
                if not os.path.exists(file_path):
                    point.payload['is_ghost'] = True  # Ghost file - render transparent
                    deleted_count += 1
                valid_files.append(point)

        if deleted_count > 0 or browser_count > 0:
            print(f"[API] Ghost files: {deleted_count}, browser files: {browser_count}, total: {len(valid_files)}")

        all_files = valid_files

        # ═══════════════════════════════════════════════════════════════════
        # STEP 2: Build folder hierarchy
        # ═══════════════════════════════════════════════════════════════════
        folders = {}
        files_by_folder = {}

        for point in all_files:
            p = point.payload or {}
            file_path = p.get('path', '')
            file_name = p.get('name', 'unknown')

            parent_folder = p.get('parent_folder', '')
            if not parent_folder and file_path:
                parent_folder = '/'.join(file_path.split('/')[:-1])
            if not parent_folder:
                parent_folder = 'root'

            if parent_folder not in files_by_folder:
                files_by_folder[parent_folder] = []
            files_by_folder[parent_folder].append({
                'id': str(point.id),
                'name': file_name,
                'path': file_path,
                'created_time': p.get('created_time', 0),
                'modified_time': p.get('modified_time', 0),
                'extension': p.get('extension', ''),
                'content': p.get('content', '')[:150] if p.get('content') else '',
                'is_ghost': p.get('is_ghost', False)  # Phase 90.11: Ghost files (deleted from disk)
            })

            # Phase 54.5: Handle browser:// paths specially
            if parent_folder.startswith('browser://'):
                # browser://folder_name -> ['browser:', 'folder_name']
                browser_parts = parent_folder.replace('browser://', '').split('/')
                browser_parts = [p for p in browser_parts if p]  # Remove empty parts

                # Create browser root folder if needed
                browser_root = 'browser://' + browser_parts[0] if browser_parts else 'browser://unknown'
                if browser_root not in folders:
                    folders[browser_root] = {
                        'path': browser_root,
                        'name': browser_parts[0] if browser_parts else 'unknown',
                        'parent_path': None,  # Browser folders are top-level
                        'depth': 1,
                        'children': []
                    }

                # Create nested browser folders
                for i in range(1, len(browser_parts)):
                    folder_path = 'browser://' + '/'.join(browser_parts[:i+1])
                    parent_path = 'browser://' + '/'.join(browser_parts[:i])

                    if folder_path not in folders:
                        folders[folder_path] = {
                            'path': folder_path,
                            'name': browser_parts[i],
                            'parent_path': parent_path,
                            'depth': i + 1,
                            'children': []
                        }

                    if parent_path in folders and folder_path not in folders[parent_path]['children']:
                        folders[parent_path]['children'].append(folder_path)
            else:
                # Original logic for regular file paths
                parts = parent_folder.split('/') if parent_folder != 'root' else ['root']
                for i in range(len(parts)):
                    folder_path = '/'.join(parts[:i+1]) if parts[0] != 'root' else 'root' if i == 0 else '/'.join(parts[:i+1])
                    parent_path = '/'.join(parts[:i]) if i > 0 else None

                    if folder_path and folder_path not in folders:
                        folders[folder_path] = {
                            'path': folder_path,
                            'name': parts[i] if parts[i] else 'root',
                            'parent_path': parent_path,
                            'depth': i,
                            'children': []
                        }

                    if parent_path and parent_path in folders and folder_path not in folders[parent_path]['children']:
                        folders[parent_path]['children'].append(folder_path)

        print(f"[API] Built {len(folders)} folders")

        # ═══════════════════════════════════════════════════════════════════
        # STEP 2.6: CALCULATE FOLDER CREATED_TIME (Phase 111)
        # Folder time = minimum created_time of all files inside
        # ═══════════════════════════════════════════════════════════════════
        for folder_path, folder_files in files_by_folder.items():
            if folder_path in folders and folder_files:
                min_time = min(f.get('created_time', 0) for f in folder_files)
                folders[folder_path]['created_time'] = min_time

        # Propagate created_time up the tree (parent = min of children times)
        def propagate_folder_times(folder_path):
            folder = folders.get(folder_path)
            if not folder:
                return float('inf')
            # Get min time from direct files
            min_time = folder.get('created_time', float('inf'))
            # Get min time from children
            for child_path in folder.get('children', []):
                child_time = propagate_folder_times(child_path)
                min_time = min(min_time, child_time)
            folder['created_time'] = min_time if min_time != float('inf') else 0
            return min_time

        # Find root folders and propagate
        root_folder_paths = [p for p, f in folders.items() if not f.get('parent_path')]
        for root_path in root_folder_paths:
            propagate_folder_times(root_path)

        print(f"[API] Calculated created_time for {len(folders)} folders")

        # ═══════════════════════════════════════════════════════════════════
        # STEP 2.7: RECALCULATE DEPTH RELATIVE TO ROOT (Phase 111 FIX)
        # The original depth was based on absolute path position, not tree depth
        # ═══════════════════════════════════════════════════════════════════
        def recalculate_depth(folder_path, current_depth):
            """Recursively set correct depth from root (root=0, children=1, etc.)"""
            if folder_path in folders:
                folders[folder_path]['depth'] = current_depth
                for child_path in folders[folder_path].get('children', []):
                    recalculate_depth(child_path, current_depth + 1)

        for root_path in root_folder_paths:
            recalculate_depth(root_path, 0)  # Root folders are depth 0

        print(f"[API] Recalculated depth for {len(folders)} folders (root=0)")

        # ═══════════════════════════════════════════════════════════════════
        # STEP 2.5: CAM SURPRISE METRICS
        # ═══════════════════════════════════════════════════════════════════
        cam_metrics = {}
        try:
            cam_metrics = calculate_surprise_metrics_for_tree(
                files_by_folder=files_by_folder,
                qdrant_client=qdrant,
                collection_name='vetka_elisya'
            )
            print(f"[CAM] Calculated surprise metrics for {len(cam_metrics)} files")
        except Exception as cam_err:
            print(f"[CAM] Warning: Could not calculate surprise metrics: {cam_err}")

        # ═══════════════════════════════════════════════════════════════════
        # STEP 3: FAN LAYOUT
        # ═══════════════════════════════════════════════════════════════════
        positions, root_folders, BRANCH_LENGTH, FAN_ANGLE, Y_PER_DEPTH = calculate_directory_fan_layout(
            folders=folders,
            files_by_folder=files_by_folder,
            all_files=[],
            socketio_instance=None  # No socketio in FastAPI context
        )

        # Incremental update
        new_branches, affected_nodes = detect_new_branches(
            folders, positions, get_last_branch_count()
        )

        if new_branches or affected_nodes:
            print(f"[PHASE 15] Detected changes: {len(new_branches)} new branches")
            incremental_layout_update(new_branches, affected_nodes, folders, positions, files_by_folder)
            set_last_branch_count(len(folders))
        else:
            set_last_branch_count(len(folders))

        # ═══════════════════════════════════════════════════════════════════
        # STEP 4: Build nodes list
        # ═══════════════════════════════════════════════════════════════════
        nodes = []
        edges = []

        root_id = "main_tree_root"
        nodes.append({
            'id': root_id,
            'type': 'root',
            'name': 'VETKA',
            'visual_hints': {
                'layout_hint': {'expected_x': 0, 'expected_y': 0, 'expected_z': 0},
                'color': '#8B4513'
            }
        })

        EXT_COLORS = {
            '.py': '#4A5A3A', '.js': '#5A5A3A', '.ts': '#3A4A6A',
            '.md': '#3A4A5A', '.json': '#5A4A3A', '.html': '#5A4A4A'
        }

        # Folder nodes
        for folder_path, folder in folders.items():
            folder_id = f"folder_{abs(hash(folder_path)) % 100000000}"
            pos = positions.get(folder_path, {'x': 0, 'y': 0})

            if folder['parent_path']:
                parent_id = f"folder_{abs(hash(folder['parent_path'])) % 100000000}"
            else:
                parent_id = root_id

            nodes.append({
                'id': folder_id,
                'type': 'branch',
                'name': folder['name'],
                'parent_id': parent_id,
                'metadata': {
                    'path': folder_path,
                    'depth': folder['depth'],
                    'file_count': len(files_by_folder.get(folder_path, []))
                },
                'visual_hints': {
                    'layout_hint': {
                        'expected_x': pos.get('x', 0),
                        'expected_y': pos.get('y', 0),
                        'expected_z': 0
                    },
                    'color': '#8B4513'
                }
            })

            edges.append({
                'from': parent_id,
                'to': folder_id,
                'semantics': 'contains'
            })

        # File nodes
        for folder_path, folder_files in files_by_folder.items():
            folder_id = f"folder_{abs(hash(folder_path)) % 100000000}"

            for file_data in folder_files:
                pos = positions.get(file_data['id'], {'x': 0, 'y': 0})
                ext = file_data.get('extension', '')
                color = EXT_COLORS.get(ext, '#3A3A4A')

                folder_depth = folders.get(folder_path, {}).get('depth', 0)
                file_depth = folder_depth + 1

                file_cam = cam_metrics.get(file_data['id'], {})

                # Phase 90.11: Ghost files get muted color
                is_ghost = file_data.get('is_ghost', False)
                ghost_color = '#2A2A2A' if is_ghost else color  # Darker for ghosts

                nodes.append({
                    'id': file_data['id'],
                    'type': 'leaf',
                    'name': file_data['name'],
                    'parent_id': folder_id,
                    'metadata': {
                        'path': file_data['path'],
                        'name': file_data['name'],
                        'extension': ext,
                        'depth': file_depth,
                        'created_time': file_data['created_time'],
                        'modified_time': file_data['modified_time'],
                        'content_preview': file_data.get('content', ''),
                        'qdrant_id': file_data['id'],
                        'is_ghost': is_ghost  # Phase 90.11: Deleted from disk
                    },
                    'visual_hints': {
                        'layout_hint': {
                            'expected_x': pos.get('x', 0),
                            'expected_y': pos.get('y', 0),
                            'expected_z': pos.get('z', 0)
                        },
```

=== FILE 3: client/src/hooks/useTreeData.ts ===
```typescript
/**
 * Hook for loading and managing tree data from VETKA API.
 * Handles both new VETKA format and legacy API responses with automatic layout.
 *
 * @status active
 * @phase 96
 * @depends zustand, apiConverter, layout
 * @used_by App, TreeViewer
 */

import { useEffect, useState } from 'react';
import { useStore, TreeNode, VetkaNodeType } from '../store/useStore';
import { fetchTreeData, ApiTreeNode } from '../utils/api';
import { calculateSimpleLayout } from '../utils/layout';
import {
  convertApiResponse,
  convertLegacyNode,
  convertLegacyEdge,
  convertChatNode,
  convertChatEdge,
  chatNodeToTreeNode,
  VetkaApiResponse,
} from '../utils/apiConverter';
import { getDevPanelConfig } from '../utils/devConfig';
import { useChatTreeStore } from '../store/chatTreeStore';

export function useTreeData() {
  const {
    setNodes,
    setNodesFromRecord,
    setEdges,
    setLoading,
    setError,
    nodes,
    isLoading,
    error,
  } = useStore();

  // MARKER_108_CHAT_FRONTEND: Phase 108.2 - Chat tree store for chat nodes
  const { addChatNode } = useChatTreeStore();

  // MARKER_110_FIX: Trigger for manual tree refresh (from DevPanel)
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);

      const response = await fetchTreeData();

      if (!response.success) {
        setError(response.error || 'Failed to load tree data');
        setLoading(false);

        // console.warn('[useTreeData] API unavailable, using demo data');
        const demoNodes = getDemoNodes();
        const positioned = calculateSimpleLayout(demoNodes);
        setNodes(positioned);
        return;
      }

      // Check if response is new VETKA format or legacy format
      if (response.tree) {
        // New VETKA API format
        const vetkaResponse: VetkaApiResponse = {
          tree: {
            nodes: response.tree.nodes,
            edges: response.tree.edges || [],
          },
        };

        const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);

        // MARKER_108_CHAT_FRONTEND: Phase 108.2 - Process chat nodes
        let chatTreeNodes: TreeNode[] = [];
        const chatEdges: typeof edges = [];

        if (response.chat_nodes && response.chat_nodes.length > 0) {
          console.log('[useTreeData] Processing chat nodes:', response.chat_nodes.length);

          // Convert chat nodes to ChatNode type and add to chatTreeStore
          response.chat_nodes.forEach((apiChatNode) => {
            const chatNode = convertChatNode(apiChatNode);
            addChatNode(chatNode.parentId, chatNode);

            // Convert ChatNode to TreeNode for 3D rendering
            const position = {
              x: apiChatNode.visual_hints.layout_hint.expected_x,
              y: apiChatNode.visual_hints.layout_hint.expected_y,
              z: apiChatNode.visual_hints.layout_hint.expected_z,
            };
            const treeNode = chatNodeToTreeNode(chatNode, position);
            chatTreeNodes.push(treeNode);
          });

          // Convert chat edges
          if (response.chat_edges) {
            response.chat_edges.forEach((apiChatEdge, idx) => {
              chatEdges.push(convertChatEdge(apiChatEdge, idx));
            });
          }

          console.log('[useTreeData] Converted chat nodes:', chatTreeNodes.length);
          console.log('[useTreeData] Chat edges:', chatEdges.length);
        }

        // Merge file tree nodes and chat nodes
        const allNodes = { ...convertedNodes };
        chatTreeNodes.forEach((chatNode) => {
          allNodes[chatNode.id] = chatNode;
        });

        // Merge edges
        const allEdges = [...edges, ...chatEdges];

        // MARKER_109_DEVPANEL: Threshold-based fallback for layout
        const config = getDevPanelConfig();
        const nodeArray = Object.values(allNodes);
        const totalNodes = nodeArray.length;

        // MARKER_111_FIX: Count nodes with TRULY invalid positions
        // Y=0 is VALID for root nodes! Only count as invalid if ALL coords are exactly 0
        // AND it's not a root node (depth > 0 or has parent)
        const invalidCount = nodeArray.filter(
          (n) => {
            const isZeroPosition = n.position.x === 0 && n.position.y === 0 && n.position.z === 0;
            const isRootNode = n.depth === 0 || !n.parentId;
            // Root nodes with (0,0,0) are VALID - they should be at origin
            // Only non-root nodes with (0,0,0) are invalid
            return isZeroPosition && !isRootNode;
          }
        ).length;

        const invalidRatio = totalNodes > 0 ? invalidCount / totalNodes : 0;
        const needsLayout = invalidRatio > (config.FALLBACK_THRESHOLD ?? 0.5);

        // MARKER_109_DEVPANEL: If semantic fallback enabled, try semantic_position first
        if (config.USE_SEMANTIC_FALLBACK && !needsLayout) {
          nodeArray.forEach((node) => {
            if (node.position.x === 0 && node.position.y === 0 && node.position.z === 0) {
              // Check for semanticPosition on the node
              const semanticPos = (node as any).semanticPosition;
              if (semanticPos) {
                node.position = {
                  x: semanticPos.x,
                  y: semanticPos.y,
                  z: semanticPos.z,
                };
              }
            }
          });
        }

        if (needsLayout) {
          console.log(`[useTreeData] Layout fallback triggered: ${invalidCount}/${totalNodes} nodes invalid (${(invalidRatio * 100).toFixed(1)}% > ${(config.FALLBACK_THRESHOLD * 100).toFixed(0)}% threshold)`);
          const positioned = calculateSimpleLayout(Object.values(allNodes));
          setNodes(positioned);
        } else {
          setNodesFromRecord(allNodes);
        }

        setEdges(allEdges);
      } else if (response.nodes) {
        // Legacy API format
        const treeNodes: TreeNode[] = response.nodes.map((n: ApiTreeNode) =>
          convertLegacyNode({
            path: n.path,
            name: n.name,
            type: n.type,
            depth: n.depth,
            parent_path: n.parent_path,
            position: n.position,
            children: n.children,
          })
        );

        const positioned = calculateSimpleLayout(treeNodes);
        setNodes(positioned);

        if (response.edges) {
          setEdges(
            response.edges.map((e: { source: string; target: string }, i: number) =>
              convertLegacyEdge(e, i)
            )
          );
        }
      }

      setLoading(false);
    }

    loadData();
  }, [setNodes, setNodesFromRecord, setEdges, setLoading, setError, addChatNode, refreshTrigger]);

  // MARKER_110_FIX: Listen for tree refresh events from DevPanel
  useEffect(() => {
    const handleTreeRefresh = () => {
      console.log('[useTreeData] Received vetka-tree-refresh-needed event, triggering refetch...');
      // Increment trigger to cause useEffect re-run
      setRefreshTrigger(prev => prev + 1);
    };

    window.addEventListener('vetka-tree-refresh-needed', handleTreeRefresh);
    return () => {
      window.removeEventListener('vetka-tree-refresh-needed', handleTreeRefresh);
    };
  }, []);

  return { nodes, isLoading, error };
}

function getDemoNodes(): TreeNode[] {
  const makeNode = (
    id: string,
    name: string,
    type: 'file' | 'folder',
    depth: number,
    parentId: string | null,
    color: string
  ): TreeNode => {
    const backendType: VetkaNodeType =
      depth === 0 ? 'root' : type === 'folder' ? 'branch' : 'leaf';

    return {
      id,
      path: id,
      name,
      type,
      backendType,
      depth,
      parentId,
      position: { x: 0, y: 0, z: 0 },
      color,
    };
  };

  return [
    makeNode('/root', 'vetka_project', 'folder', 0, null, '#6366f1'),
    makeNode('/root/src', 'src', 'folder', 1, '/root', '#374151'),
    makeNode('/root/client', 'client', 'folder', 1, '/root', '#374151'),
    makeNode('/root/src/main.py', 'main.py', 'file', 2, '/root/src', '#1f2937'),
    makeNode('/root/src/config.py', 'config.py', 'file', 2, '/root/src', '#1f2937'),
    makeNode('/root/client/App.tsx', 'App.tsx', 'file', 2, '/root/client', '#1f2937'),
    makeNode('/root/README.md', 'README.md', 'file', 1, '/root', '#1f2937'),
  ];
}
```

=== FILE 4: client/src/utils/layout.ts ===
```typescript
/**
 * Layout calculation utilities for positioning tree nodes in 3D space.
 *
 * @status active
 * @phase 96
 * @depends ../store/useStore
 * @used_by ./hooks/useTreeData, ./components/canvas
 */
import type { TreeNode } from '../store/useStore';

const LEVEL_HEIGHT = 20;
const HORIZONTAL_SPREAD = 30;

export function calculateSimpleLayout(nodes: TreeNode[]): TreeNode[] {
  const byDepth: Record<number, TreeNode[]> = {};
  nodes.forEach(node => {
    const d = node.depth;
    if (!byDepth[d]) byDepth[d] = [];
    byDepth[d].push(node);
  });

  Object.keys(byDepth).forEach(depth => {
    byDepth[Number(depth)].sort((a, b) => {
      if (a.parentId === b.parentId) {
        return a.name.localeCompare(b.name);
      }
      return (a.parentId || '').localeCompare(b.parentId || '');
    });
  });

  const positioned = nodes.map(node => {
    const siblings = byDepth[node.depth];
    const index = siblings.indexOf(node);
    const count = siblings.length;

    const totalWidth = (count - 1) * HORIZONTAL_SPREAD;
    const x = -totalWidth / 2 + index * HORIZONTAL_SPREAD;
    const y = node.depth * LEVEL_HEIGHT;
    const z = 0;

    return {
      ...node,
      position: { x, y, z }
    };
  });

  return positioned;
}
```

=== FILE 5: client/src/store/useStore.ts (lines 1-300) ===
```typescript
/**
 * Global Zustand store for VETKA 3D visualization state.
 * Manages tree nodes, edges, selections, chat messages, camera, and pinned files.
 *
 * @status active
 * @phase 96
 * @depends zustand, ../types/chat, three
 * @used_by App.tsx, ChatPanel.tsx, FileCard.tsx, TreeVisualization.tsx, most components
 */
import { create } from 'zustand';
import type { ChatMessage, WorkflowStatus } from '../types/chat';
import type { PerspectiveCamera } from 'three';

// Backend node types
export type VetkaNodeType = 'root' | 'branch' | 'leaf';

export interface TreeNode {
  id: string;
  path: string;
  name: string;
  type: 'file' | 'folder' | 'chat' | 'artifact';
  backendType: VetkaNodeType;
  depth: number;
  parentId: string | null;
  position: { x: number; y: number; z: number };
  color: string;
  extension?: string;
  semanticPosition?: {
    x: number;
    y: number;
    z: number;
    knowledgeLevel: number;
  };
  children?: string[];
  isGhost?: boolean;  // Phase 90.11: Deleted from disk but kept in memory
  opacity?: number;   // Phase 90.11: Transparency for ghost files (0.3 for ghosts)
  // MARKER_108_3_CHAT_METADATA: Phase 108.3 - Chat node metadata
  metadata?: {
    chat_id?: string;
    message_count?: number;
    participants?: string[];
    decay_factor?: number;
    last_activity?: string;
    context_type?: string;
  };
}

export interface TreeEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
}

// Chat message from agent
export interface AgentMessage {
  id: string;
  agent: string;
  content: string;
  timestamp: number;
  artifacts?: Array<{
    name: string;
    content: string;
    type: string;
    language?: string;
  }>;
  sourceFiles?: string[];
}

// Camera control command
export interface CameraCommand {
  target: string;
  zoom: 'close' | 'medium' | 'far';
  highlight: boolean;
}

// [PHASE70-M1] useStore.ts: Camera ref field — IMPLEMENTED

interface TreeState {
  nodes: Record<string, TreeNode>;
  edges: TreeEdge[];
  rootPath: string | null;

  selectedId: string | null;
  hoveredId: string | null;
  highlightedId: string | null;  // Legacy single highlight
  // Phase 69: Multi-highlight support
  highlightedIds: Set<string>;
  isLoading: boolean;
  error: string | null;

  isSocketConnected: boolean;
  isDraggingAny: boolean;

  // Legacy agent messages (for backwards compat)
  messages: AgentMessage[];

  // New chat system
  chatMessages: ChatMessage[];
  currentWorkflow: WorkflowStatus | null;
  isTyping: boolean;
  streamingContent: string;
  conversationId: string | null;

  // Camera
  cameraCommand: CameraCommand | null;
  // Phase 70: Camera ref for viewport context
  cameraRef: PerspectiveCamera | null;

  // Phase 61: Pinned files for multi-file context
  pinnedFileIds: string[];

  // FIX_109.4: Current chat ID for unified ID system (solo chats like groups)
  currentChatId: string | null;
  setCurrentChatId: (id: string | null) => void;

  setNodes: (nodes: TreeNode[]) => void;
  setNodesFromRecord: (nodes: Record<string, TreeNode>) => void;
  setEdges: (edges: TreeEdge[]) => void;
  selectNode: (id: string | null) => void;
  hoverNode: (id: string | null) => void;
  highlightNode: (id: string | null) => void;
  // Phase 69: Multi-highlight methods
  highlightNodes: (ids: string[]) => void;
  clearHighlights: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setSocketConnected: (connected: boolean) => void;
  setDraggingAny: (dragging: boolean) => void;
  updateNodePosition: (id: string, position: { x: number; y: number; z: number }) => void;
  moveNodeWithChildren: (id: string, position: { x: number; y: number; z: number }) => void;
  addNode: (node: TreeNode) => void;
  removeNode: (id: string) => void;

  // Legacy chat
  addMessage: (message: AgentMessage) => void;
  clearMessages: () => void;

  // New chat system
  addChatMessage: (msg: ChatMessage) => void;
  updateChatMessage: (id: string, updates: Partial<ChatMessage>) => void;
  setWorkflowStatus: (status: WorkflowStatus | null) => void;
  setIsTyping: (typing: boolean) => void;
  appendStreamingContent: (delta: string) => void;
  clearStreamingContent: () => void;
  clearChat: () => void;
  setConversationId: (id: string | null) => void;

  // Camera
  setCameraCommand: (command: CameraCommand | null) => void;
  // Phase 70: Camera ref setter
  setCameraRef: (camera: PerspectiveCamera | null) => void;

  // Phase 61: Pinned files actions
  togglePinFile: (nodeId: string) => void;
  pinSubtree: (rootId: string) => void;
  clearPinnedFiles: () => void;
  // Phase 100.2: Set pinned files from backend (for persistence)
  setPinnedFiles: (ids: string[]) => void;

  // Phase 65: Smart pin based on node type
  pinNodeSmart: (nodeId: string) => void;

  // Phase 65: Grab mode for Blender-style node movement
  grabMode: boolean;
  setGrabMode: (enabled: boolean) => void;
}

export const useStore = create<TreeState>((set) => ({
  nodes: {},
  edges: [],
  rootPath: null,
  selectedId: null,
  hoveredId: null,
  highlightedId: null,
  // Phase 69: Multi-highlight support
  highlightedIds: new Set<string>(),
  isLoading: false,
  error: null,
  isSocketConnected: false,
  isDraggingAny: false,
  messages: [],
  chatMessages: [],
  currentWorkflow: null,
  isTyping: false,
  streamingContent: '',
  conversationId: null,
  cameraCommand: null,
  // Phase 70: Camera ref for viewport context
  cameraRef: null,

  // Phase 61: Pinned files
  pinnedFileIds: [],

  // FIX_109.4: Current chat ID for unified ID system
  currentChatId: null,
  setCurrentChatId: (id) => set({ currentChatId: id }),

  // Phase 65: Grab mode
  grabMode: false,

  setNodes: (nodesList) => set({
    nodes: Object.fromEntries(nodesList.map(n => [n.id, n])),
    rootPath: nodesList.find(n => n.depth === 0)?.path || null
  }),

  setNodesFromRecord: (nodes) => set({
    nodes,
    rootPath: Object.values(nodes).find(n => n.depth === 0)?.path || null
  }),

  setEdges: (edges) => set({ edges }),

  selectNode: (id) => set({ selectedId: id }),

  hoverNode: (id) => set({ hoveredId: id }),

  highlightNode: (id) => set({ highlightedId: id }),

  // Phase 69: Multi-highlight implementation
  highlightNodes: (ids) => set({ highlightedIds: new Set(ids) }),
  clearHighlights: () => set({ highlightedIds: new Set() }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  setSocketConnected: (isSocketConnected) => set({ isSocketConnected }),

  setDraggingAny: (isDraggingAny) => set({ isDraggingAny }),

  updateNodePosition: (id, position) => set((state) => {
    if (!state.nodes[id]) return state;
    return {
      nodes: {
        ...state.nodes,
        [id]: { ...state.nodes[id], position }
      }
    };
  }),

  // MARKER_111_DRAG: Move node with all children (branch follows)
  moveNodeWithChildren: (id, newPosition) => set((state) => {
    const node = state.nodes[id];
    if (!node) return state;

    // Calculate delta from old position to new position
    const delta = {
      x: newPosition.x - node.position.x,
      y: newPosition.y - node.position.y,
      z: newPosition.z - node.position.z,
    };

    // Find all descendants recursively
    const findDescendants = (nodeId: string): string[] => {
      const descendants: string[] = [];
      Object.values(state.nodes).forEach((n) => {
        if (n.parentId === nodeId) {
          descendants.push(n.id);
          descendants.push(...findDescendants(n.id));
        }
      });
      return descendants;
    };

    const descendantIds = findDescendants(id);
    const updatedNodes = { ...state.nodes };

    // Update the dragged node
    updatedNodes[id] = {
      ...node,
      position: newPosition,
    };

    // Update all descendants with delta
    descendantIds.forEach((childId) => {
      const child = updatedNodes[childId];
      if (child) {
        updatedNodes[childId] = {
          ...child,
          position: {
            x: child.position.x + delta.x,
            y: child.position.y + delta.y,
            z: child.position.z + delta.z,
          },
        };
      }
    });

    console.log(`[DRAG] Moved ${id} + ${descendantIds.length} children by delta (${delta.x.toFixed(1)}, ${delta.y.toFixed(1)}, ${delta.z.toFixed(1)})`);

    return { nodes: updatedNodes };
  }),

  addNode: (node) => set((state) => ({
    nodes: { ...state.nodes, [node.id]: node }
  })),

  removeNode: (id) => set((state) => {
    const { [id]: _, ...rest } = state.nodes;
```
