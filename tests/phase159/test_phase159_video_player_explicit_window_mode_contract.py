from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_video_player_receives_explicit_window_mode_from_panel():
    panel = _read('client/src/components/artifact/ArtifactPanel.tsx')
    assert 'windowMode={windowMode}' in panel

