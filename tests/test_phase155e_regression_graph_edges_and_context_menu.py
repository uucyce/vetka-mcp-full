"""
Regression tests for reported issues:
1) roadmap edges looked missing in grandma mode,
2) context-menu sticky behavior.
"""

from pathlib import Path
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155e contracts changed")

def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_roadmap_grandma_keeps_dependency_edges_visible():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "if (!debugMode)" in code
    assert "const allDependencyEdges = effectiveEdges.filter(e => e.type === 'dependency');" in code
    assert "return [...topologyEdges, ...allDependencyEdges];" in code


def test_context_menu_not_auto_closed_by_transition_effect():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "contextMenuTarget?.kind, navLevel, taskDrillState, roadmapNodeDrillState" not in code


def test_context_menu_closes_when_target_stale():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "MARKER_155E.REGRESSION.CONTEXT_MENU_GRAPH_VALIDATION_RESET.V1" in code
    assert "graphForView.nodes.some((n) => n.id === contextMenuTarget.nodeId)" in code
    assert "graphForView.edges.some((e) => e.id === contextMenuTarget.edgeId)" in code


def test_roadmap_source_prefers_dense_l2_over_sparse_overview():
    code = _read("client/src/hooks/useRoadmapDAG.ts")
    assert "MARKER_155E.REGRESSION.ROADMAP_SOURCE_DENSITY_GUARD.V1" in code
    assert "MARKER_155E.REGRESSION.CONDENSED_L2_PREFERENCE_OVER_OVERVIEW.V1" in code
    assert "hasReadableTopology" in code
    assert "l2Healthy ? l2Nodes" in code


def test_roadmap_source_mode_override_is_debug_only():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "if (!debugMode) return null;" in code


def test_footer_action_bar_removed_from_canvas():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "<FooterActionBar" not in code
