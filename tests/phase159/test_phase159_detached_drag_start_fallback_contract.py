import pytest
from pathlib import Path

pytestmark = pytest.mark.stale(reason="Phase 159 import errors — UI contracts removed in CUT refactor")

ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_detached_drag_start_fallback_contract():
    panel = _read("client/src/components/artifact/ArtifactPanel.tsx")
    tauri = _read("client/src/config/tauri.ts")

    assert "startCurrentWindowDragging" in tauri
    assert "win.startDragging()" in tauri
    assert "MARKER_159.C4.DRAG_START_FALLBACK" in panel
    assert "onMouseDown={handleDetachedDragMouseDown}" in panel
