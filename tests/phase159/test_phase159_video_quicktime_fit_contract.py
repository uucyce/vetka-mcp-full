from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_c5_video_quicktime_fit_contract():
    player = _read('client/src/components/artifact/viewers/VideoArtifactPlayer.tsx')
    assert 'MARKER_159.R8.AUTO_FIT_DISABLED' in player
    assert 'windowMode?: "embedded" | "detached";' in player
    assert 'windowMode || (windowLabel === "artifact-media" ? "detached" : "embedded")' in player
    assert 'automatic detached window resize-by-video-aspect was removed' in player
    assert 'background: "transparent"' in player
    assert 'height: "100%"' in player
