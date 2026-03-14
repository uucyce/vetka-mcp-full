from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_artifact_video_timeupdate_is_throttled():
    src = _read("client/src/components/artifact/ArtifactPanel.tsx")
    assert "const MEDIA_TIMEUPDATE_THROTTLE_MS = 120;" in src
    assert "if (now - lastTimeupdateRef.current < MEDIA_TIMEUPDATE_THROTTLE_MS) return;" in src


def test_phase159_artifact_video_has_fullscreen_and_poster():
    src = _read("client/src/components/artifact/ArtifactPanel.tsx")
    player = _read("client/src/components/artifact/viewers/VideoArtifactPlayer.tsx")
    assert "poster={videoPoster}" in src
    assert "requestFullscreen" in player
