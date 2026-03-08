from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_media_window_metadata_route_contract():
    routes_py = _read("src/api/routes/artifact_routes.py")

    assert "class MediaWindowMetadataRequest(BaseModel):" in routes_py
    assert '@router.post("/media/window-metadata")' in routes_py
    assert "_probe_video_dimensions(target)" in routes_py
    assert '"width_px": int(width_px or 0)' in routes_py
    assert '"height_px": int(height_px or 0)' in routes_py
    assert '"aspect_ratio": _format_aspect_ratio(width_px, height_px) if is_video else None' in routes_py


def test_phase159_media_window_one_shot_size_contract():
    commands_rs = _read("client/src-tauri/src/commands.rs")

    assert "MARKER_159.R9.ONE_SHOT_MEDIA_INITIAL_SIZE" in commands_rs
    assert "fetch_media_window_metadata(clean_path).await" in commands_rs
    assert "compute_detached_media_initial_inner_size(" in commands_rs
    assert ".inner_size(initial_width, initial_height)" in commands_rs
