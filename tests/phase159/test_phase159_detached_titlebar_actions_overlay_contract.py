from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_detached_actions_render_in_toolbar_actions_slot():
    panel = _read('client/src/components/artifact/ArtifactPanel.tsx')
    toolbar = _read('client/src/components/artifact/Toolbar.tsx')

    assert "className=\"artifact-detached-title-actions\"" not in panel
    assert "detachedShowFavorite={windowMode === 'detached' && (isInVetka || !isFileMode)}" in panel
    assert "detachedShowVetka={windowMode === 'detached' && isFileMode && !isInVetka}" in panel
    assert "detachedRightActions" not in panel
    assert "detachedShowFavorite?: boolean;" in toolbar
    assert "detachedShowVetka?: boolean;" in toolbar
