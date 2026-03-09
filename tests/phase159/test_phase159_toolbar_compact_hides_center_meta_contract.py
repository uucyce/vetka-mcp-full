from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_toolbar_compact_hides_center_meta_block():
    toolbar = _read('client/src/components/artifact/Toolbar.tsx')
    assert "{!compact && (" in toolbar
    assert "{compact && <div style={{ flex: 1 }} />}" in toolbar
