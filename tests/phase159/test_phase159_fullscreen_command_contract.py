from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_r1_tauri_fullscreen_command_registered():
    main_rs = _read("client/src-tauri/src/main.rs")
    commands_rs = _read("client/src-tauri/src/commands.rs")
    tauri_ts = _read("client/src/config/tauri.ts")

    assert "pub fn set_window_fullscreen(" in commands_rs
    assert "set_fullscreen(fullscreen)" in commands_rs
    assert "commands::set_window_fullscreen" in main_rs
    assert "invoke<boolean>('set_window_fullscreen'" in tauri_ts
