from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_codeviewer_search_strip_removed_contract():
    code = _read("client/src/components/artifact/viewers/CodeViewer.tsx")
    assert "Press Ctrl+F to search" not in code
