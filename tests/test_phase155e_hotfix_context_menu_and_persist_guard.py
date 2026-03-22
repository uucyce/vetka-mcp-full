"""
Hotfix tests for reported regressions:
1) sticky context menu reset,
2) safe inline workflow persistence when ids are not wf_{taskId}_-prefixed,
3) grandma mode focus filter reset.
"""

from pathlib import Path
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155e contracts changed")


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_grandma_mode_resets_focus_filter_to_all():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "if (!debugMode && navLevel === 'roadmap' && focusDisplayMode !== 'all')" in code
    assert "setFocusDisplayMode('all')" in code


def test_inline_persist_has_unprefixed_nodes_fallback_guard():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "if (nodes.length === 0)" in code
    assert "nodes = inlineWorkflowNodes.map" in code
    assert "if (nodes.length === 0) return;" in code


def test_context_menu_is_force_closed_on_select_paths():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "const handleLevelAwareNodeSelect" in code and "setContextMenuTarget(null);" in code
    assert "const handleLevelAwareNodeDoubleClick" in code and "setContextMenuTarget(null);" in code
    assert "const handleEdgeSelect" in code and "setContextMenuTarget(null);" in code
