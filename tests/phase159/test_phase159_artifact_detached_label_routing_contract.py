from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_c2_detached_window_label_routed_to_player_and_close():
    standalone = _read('client/src/ArtifactStandalone.tsx')
    panel = _read('client/src/components/artifact/ArtifactPanel.tsx')

    assert "const windowLabel = decodeParam(params.get('window_label')) || 'artifact-main';" in standalone
    assert 'detachedWindowLabel={query.windowLabel}' in standalone
    assert "detachedWindowLabel = 'artifact-media'" in panel
    assert 'closeArtifactMediaWindow(detachedWindowLabel)' in panel
    assert "windowLabel={windowMode === 'detached' ? detachedWindowLabel : 'main'}" in panel
