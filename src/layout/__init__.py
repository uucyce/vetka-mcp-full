"""
VETKA Layout Package - Layout algorithms for tree visualization.

Phase 14: Adaptive FAN layout with Grok formulas
Phase 15: Incremental layout with soft repulsion
Phase 17: Sugiyama-style directory fan layout

@status: active
@phase: 96
@depends: src.layout.fan_layout, src.layout.incremental
@used_by: src.visualizer.tree_renderer, frontend 3D visualization
"""

# Directory Mode FAN Layout
from src.layout.fan_layout import (
    calculate_directory_fan_layout,
    calculate_branch_length,
    calculate_file_spacing_adaptive,
    calculate_layer_height_vertical,
    calculate_static_repulsion,
    calculate_dynamic_angle_spread,
    minimize_crossing_barycenter,
)

# Incremental Layout (Phase 15)
from src.layout.incremental import (
    detect_new_branches,
    apply_soft_repulsion,
    apply_soft_repulsion_for_layer,
    apply_soft_repulsion_all_layers,
    check_file_collisions,
    resolve_file_collisions,
    incremental_layout_update,
    emit_layout_update,
    reset_incremental_state,
    get_last_branch_count,
    set_last_branch_count,
)

__all__ = [
    # FAN Layout
    'calculate_directory_fan_layout',
    'calculate_branch_length',
    'calculate_file_spacing_adaptive',
    'calculate_layer_height_vertical',
    'calculate_static_repulsion',
    'calculate_dynamic_angle_spread',
    'minimize_crossing_barycenter',
    # Incremental Layout
    'detect_new_branches',
    'apply_soft_repulsion',
    'apply_soft_repulsion_for_layer',
    'apply_soft_repulsion_all_layers',
    'check_file_collisions',
    'resolve_file_collisions',
    'incremental_layout_update',
    'emit_layout_update',
    'reset_incremental_state',
    'get_last_branch_count',
    'set_last_branch_count',
]
