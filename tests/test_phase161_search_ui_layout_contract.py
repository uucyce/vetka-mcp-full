from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_FILE = ROOT / "client" / "src" / "App.tsx"
SEARCH_FILE = ROOT / "client" / "src" / "components" / "search" / "UnifiedSearchBar.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase161_top_left_search_icons_are_horizontal() -> None:
    src = _read(APP_FILE)
    assert "Icons next to search bar" in src
    assert "flexDirection: 'row'" in src


def test_phase161_search_rows_use_compact_density_tokens() -> None:
    src = _read(SEARCH_FILE)
    assert "alignItems: 'flex-start'" in src
    assert "const showMetaColumns = !isWebRow && isFileRow;" in src
    assert "minWidth: '42px'" in src
    assert "minWidth: '48px'" in src
