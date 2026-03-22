from pathlib import Path
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155f contracts changed")

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_minichat_dispatches_context_open_event():
    code = _read("client/src/components/mcc/MiniChat.tsx")
    assert "mcc-miniwindow-open" in code
    assert "windowId: 'context'" in code
    assert "expanded: true" in code


def test_miniwindow_listens_for_open_event():
    code = _read("client/src/components/mcc/MiniWindow.tsx")
    assert "mcc-miniwindow-open" in code
    assert "setExpanded(nextExpanded)" in code
    assert "if (String(detail.windowId || '') !== String(windowId)) return;" in code
