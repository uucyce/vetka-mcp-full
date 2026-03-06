from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_detached_title_actions_fixed_to_window_titlebar_level():
    toolbar = _read('client/src/components/artifact/Toolbar.tsx')

    # Detached VETKA/Favorite actions should be rendered in same toolbar row as Close(X)
    assert "detachedShowFavorite && (" in toolbar
    assert "detachedShowVetka && (" in toolbar
    assert "{onClose && (" in toolbar
