from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_c2_video_controls_stick_to_bottom_in_fullscreen_and_notify_panel():
    player = _read('client/src/components/artifact/viewers/VideoArtifactPlayer.tsx')

    assert 'const isAnyFullscreen = isFullscreen || isFallbackFullscreen || isNativeWindowFullscreen;' in player
    assert 'onFullscreenChange?.(isAnyFullscreen);' in player
    assert 'if (isAnyFullscreen) return 0;' in player
    assert 'bottom: 0,' in player
    assert 'padding: isAnyFullscreen ? "8px 12px 12px" : "8px 12px 10px"' in player
    assert 'transition: "opacity 220ms ease"' in player
