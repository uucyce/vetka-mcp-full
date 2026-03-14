from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_detached_media_geometry_trace_contract():
    commands = _read("client/src-tauri/src/commands.rs")
    tauri_ts = _read("client/src/config/tauri.ts")
    player = _read("client/src/components/artifact/viewers/VideoArtifactPlayer.tsx")
    debug_helper = _read("client/src/utils/detachedMediaDebug.ts")

    assert "DetachedMediaNativeGeometry" in commands
    assert "native_inner_physical" in commands
    assert "native_outer_physical" in commands
    assert "Promise<DetachedMediaNativeGeometry | null>" in tauri_ts
    assert 'MARKER_159.R12.DETACHED_MEDIA_DOM_GEOMETRY' in player
    assert 'MARKER_159.R14.DETACHED_MEDIA_NATIVE_GEOMETRY' in player
    assert 'vetka_detached_media_native_geometry_last' in player
    assert "window.devicePixelRatio || 1" in player
    assert "querySelector('[data-artifact-toolbar=\"1\"]')" in player
    assert "wrapperRef.current?.getBoundingClientRect()" in player
    assert "nativeInnerPhysicalWidth" in debug_helper
