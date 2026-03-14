from __future__ import annotations

from pathlib import Path


def test_mini_context_has_search_input_and_results_markers() -> None:
    code = Path("client/src/components/mcc/MiniContext.tsx").read_text(encoding="utf-8")
    assert "MARKER_165.MCC.CONTEXT_SEARCH.UI_INPUT.V1" in code
    assert "MARKER_165.MCC.CONTEXT_SEARCH.UI_RESULTS.V1" in code
    assert "MARKER_165.MCC.CONTEXT_SEARCH.UI_RESULT_SELECT.V1" in code
    assert "onSelect?.(row)" in code
    assert "/api/mcc/search/file" in code
    assert "search in active project..." in code
    assert "SEARCH" in code
    assert "KEY" in code
    assert "FILE" in code


def test_mcc_context_search_bridge_wired_to_dag_focus() -> None:
    mcc_code = Path("client/src/components/mcc/MyceliumCommandCenter.tsx").read_text(encoding="utf-8")
    assert "MARKER_165.MCC.CONTEXT_SEARCH.NODE_FOCUS_BRIDGE.V1" in mcc_code
    assert "handleContextSearchSelect" in mcc_code
    assert "onSearchSelect={handleContextSearchSelect}" in mcc_code
    assert ".zoomToNode(" in mcc_code
