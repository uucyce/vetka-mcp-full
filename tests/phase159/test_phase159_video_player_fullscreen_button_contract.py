from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_c2_video_player_fullscreen_button_and_label_fallback():
    player = _read('client/src/components/artifact/viewers/VideoArtifactPlayer.tsx')

    assert "title=\"Fullscreen\"" in player
    assert 'aria-label="Toggle fullscreen"' in player
    assert "requested === \"artifact-media\" ? \"artifact-main\" : \"artifact-media\"" in player
    assert 'await setWindowFullscreen(next, label);' in player
    assert 'title="Settings"' in player
    assert 'aria-label="Video settings"' in player
    assert '⚙' not in player
