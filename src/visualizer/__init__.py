"""
VETKA Phase 11 Visualizer.

Three.js visualization module for VETKA-JSON v1.3.
Generates interactive HTML with 3D tree visualization.

Bug fixes included:
- Haiku #2: CatmullRomCurve3 for organic edges
- Haiku #5: Recursive focus mode
- Haiku #10: Unified click handler
- Qwen #4: LOD with entropy*evalScore

@status: active
@phase: 96
@depends: src.visualizer.tree_renderer
@used_by: src.api.routes, src.orchestration
"""

from .tree_renderer import TreeRenderer

__all__ = ["TreeRenderer"]
