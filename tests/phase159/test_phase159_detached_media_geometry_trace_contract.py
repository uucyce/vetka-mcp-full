from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_detached_media_geometry_trace_contract():
    player = _read("client/src/components/artifact/viewers/VideoArtifactPlayer.tsx")

    assert 'MARKER_159.R12.DETACHED_MEDIA_DOM_GEOMETRY' in player
    assert "window.devicePixelRatio || 1" in player
    assert "querySelector('[data-artifact-toolbar=\"1\"]')" in player
    assert "wrapperRef.current?.getBoundingClientRect()" in player
