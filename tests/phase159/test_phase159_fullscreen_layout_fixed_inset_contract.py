from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_c2_fullscreen_layout_uses_fixed_inset_shells():
    app = _read('client/src/App.tsx')
    artifact_standalone = _read('client/src/ArtifactStandalone.tsx')
    artifact_media_standalone = _read('client/src/ArtifactMediaStandalone.tsx')

    assert "<div style={{ position: 'fixed', inset: 0, background: '#0a0a0a' }}" in app
    assert "<div style={{ position: 'fixed', inset: 0, background: '#0a0a0a', overflow: 'hidden' }}" in artifact_standalone
    assert "<div style={{ position: 'fixed', inset: 0, background: '#0a0a0a', overflow: 'hidden' }}" in artifact_media_standalone
