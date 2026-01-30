# src/knowledge_graph/__init__.py
"""
VETKA Knowledge Graph Module - Phase 16
Semantic graph building with UMAP positioning and dynamic tagging.

Phase 16 Changes:
- Added SemanticTagger for dynamic semantic tag search
- Fixed build_graph_for_tag() to use semantic similarity
- Added _build_graph_from_file_data() for frontend file selection

@status: active
@phase: 96
@depends: graph_builder, position_calculator, semantic_tagger
@used_by: src.api.routes.tree_routes, src.visualizer.tree_renderer
"""

from .graph_builder import VETKAKnowledgeGraphBuilder
from .position_calculator import VETKAPositionCalculator
from .semantic_tagger import SemanticTagger

__all__ = [
    "VETKAKnowledgeGraphBuilder",
    "VETKAPositionCalculator",
    "SemanticTagger"
]
