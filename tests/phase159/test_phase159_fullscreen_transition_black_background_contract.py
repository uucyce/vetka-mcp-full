from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_c2_fullscreen_transition_uses_black_root_background():
    index_html = _read('client/index.html')
    assert 'html, body, #root { width: 100%; height: 100%; overflow: hidden; background: #000; }' in index_html
