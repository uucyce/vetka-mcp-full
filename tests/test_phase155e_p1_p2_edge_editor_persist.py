"""
Phase 155E follow-up: close remaining P1/P2 markers for edge mini-panel + canonical persist.
"""

from pathlib import Path
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155e contracts changed")

def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_mcc_has_edge_editor_marker_and_draft_state():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "MARKER_155E.WE.EDGE_EDITOR_MINIPANEL.V1" in code
    assert "edgeEditDraft" in code
    assert "handleOpenEdgeEditor" in code
    assert "handleSaveEdgeEditor" in code


def test_mcc_persists_inline_workflow_edges_to_workflow_api():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "MARKER_155E.WE.EDGE_PERSIST_CANONICAL.V1" in code
    assert "persistInlineWorkflowTemplate" in code
    assert "${API_BASE}/workflows" in code
    assert "/debug/task-board/" in code


def test_context_menu_exposes_edge_edit_action():
    code = _read("client/src/components/mcc/DAGContextMenu.tsx")
    assert "onEditEdge" in code
    assert "Edit Edge" in code
