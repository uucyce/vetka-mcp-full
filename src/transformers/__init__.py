"""
VETKA Phase 10/11 Transformers.

Transforms Phase 9 workflow output into VETKA-JSON v1.3 format
for 3D visualization in Phase 10/11 UI.

Principle: "ПРИРАСТАЕТ, НЕ ЛОМАЕТСЯ"
- Transformer READS from Phase 9, does NOT modify it
- All new fields are OPTIONAL for backward compatibility

Phase 11 adds:
- BFS bottom-up completion calculation
- Graceful degradation for missing data
- Debug logging
- All 13 bug fixes from AI Council review

@status: active
@phase: 96
@depends: src.transformers.phase9_to_vetka, src.transformers.phase11_transformer
@used_by: src.orchestration, src.visualizer
"""

from .phase9_to_vetka import (
    Phase10Transformer,
    AgentType,
    BranchType,
    EdgeSemantics,
    EdgeType,
    AnimationType,
    VisualHintsCalculator,
    AGENT_COLORS,
    EDGE_STYLES,
    BRANCH_TYPE_ICONS,
    FILE_EXTENSION_ICONS,
    ANIMATION_PARAMS,
    LAYOUT_CONSTANTS,
    LOD_THRESHOLDS,
    DEFAULTS,
)

from .phase11_transformer import Phase11Transformer

__all__ = [
    # Phase 10 (backward compatibility)
    "Phase10Transformer",
    # Phase 11 (recommended)
    "Phase11Transformer",
    # Shared
    "AgentType",
    "BranchType",
    "EdgeSemantics",
    "EdgeType",
    "AnimationType",
    "VisualHintsCalculator",
    "AGENT_COLORS",
    "EDGE_STYLES",
    "BRANCH_TYPE_ICONS",
    "FILE_EXTENSION_ICONS",
    "ANIMATION_PARAMS",
    "LAYOUT_CONSTANTS",
    "LOD_THRESHOLDS",
    "DEFAULTS",
]
