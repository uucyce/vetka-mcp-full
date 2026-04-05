from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_r1_video_player_uses_native_fullscreen_before_dom_fallback():
    src = _read("client/src/components/artifact/viewers/VideoArtifactPlayer.tsx")
    assert "import { isTauri, setWindowFullscreen }" in src
    assert "if (isTauri()) {" in src
    assert "setWindowFullscreen(next, \"main\")" in src
    assert "setIsNativeWindowFullscreen(next)" in src
    # DOM fallback path is still present as secondary.
    assert "wrapper.requestFullscreen" in src
    assert "setIsFallbackFullscreen(true)" in src

