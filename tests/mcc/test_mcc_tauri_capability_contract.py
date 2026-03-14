from __future__ import annotations

import json
from pathlib import Path


def test_tauri_default_capability_includes_mycelium_dialog_window() -> None:
    # MARKER_161.7.MULTIPROJECT.TAURI.CAPABILITY_MYSELIUM_DIALOG.V1
    data = json.loads(
        Path("client/src-tauri/capabilities/default.json").read_text(encoding="utf-8")
    )
    windows = list(data.get("windows") or [])
    permissions = list(data.get("permissions") or [])

    assert "mycelium" in windows
    assert "dialog:default" in permissions


def test_tauri_native_folder_picker_fallback_wired() -> None:
    tauri_ts = Path("client/src/config/tauri.ts").read_text(encoding="utf-8")
    main_rs = Path("client/src-tauri/src/main.rs").read_text(encoding="utf-8")
    commands_rs = Path("client/src-tauri/src/commands.rs").read_text(encoding="utf-8")

    assert "MARKER_161.7.MULTIPROJECT.UI.OPEN_FOLDER_FALLBACK.V1" in tauri_ts
    assert "pick_folder_native" in tauri_ts
    assert "commands::pick_folder_native" in main_rs
    assert "MARKER_161.7.MULTIPROJECT.TAURI.NATIVE_FOLDER_PICKER.V1" in commands_rs
