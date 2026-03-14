from pathlib import Path


def test_expanded_miniwindow_supports_frictionless_all_edge_resize() -> None:
    code = Path("client/src/components/mcc/MiniWindow.tsx").read_text(encoding="utf-8")
    assert "MARKER_177.MINIWINDOW.RESIZE_ALL_EDGES.V1" in code
    assert "handleExpandedResizeStart" in code
    assert "expandedFrameStorageKey" in code
    assert "clampExpandedFrame" in code
    assert "key={`expanded-${h.dir}`}" in code
    assert "cursor: 'ns-resize'" in code
    assert "cursor: 'ew-resize'" in code
    assert "cursor: 'nwse-resize'" in code
    assert "cursor: 'nesw-resize'" in code
