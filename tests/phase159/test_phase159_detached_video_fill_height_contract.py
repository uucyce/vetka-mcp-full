from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_detached_video_fill_height_contract():
    player = _read("client/src/components/artifact/viewers/VideoArtifactPlayer.tsx")

    assert "MARKER_159.R8.AUTO_FIT_DISABLED" in player
    assert "overrode user-controlled window sizing" in player
