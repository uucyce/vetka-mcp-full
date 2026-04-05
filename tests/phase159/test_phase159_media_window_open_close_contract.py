from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_r2_media_window_open_close_commands_registered():
    commands_rs = _read("client/src-tauri/src/commands.rs")
    main_rs = _read("client/src-tauri/src/main.rs")
    tauri_ts = _read("client/src/config/tauri.ts")
    main_tsx = _read("client/src/main.tsx")

    assert "pub fn open_artifact_media_window(" in commands_rs
    assert "pub fn close_artifact_media_window(" in commands_rs
    assert "commands::open_artifact_media_window" in main_rs
    assert "commands::close_artifact_media_window" in main_rs
    assert "invoke<boolean>('open_artifact_media_window'" in tauri_ts
    assert "invoke<boolean>('close_artifact_media_window'" in tauri_ts
    assert "pathname === '/artifact-media'" in main_tsx

