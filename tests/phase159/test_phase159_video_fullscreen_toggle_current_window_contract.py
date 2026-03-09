from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_c2_fullscreen_uses_current_window_set_authority():
    commands_rs = _read('client/src-tauri/src/commands.rs')
    main_rs = _read('client/src-tauri/src/main.rs')
    tauri_ts = _read('client/src/config/tauri.ts')
    player_tsx = _read('client/src/components/artifact/viewers/VideoArtifactPlayer.tsx')

    assert 'pub fn get_current_window_fullscreen(window: WebviewWindow)' in commands_rs
    assert 'pub fn set_current_window_fullscreen(window: WebviewWindow, fullscreen: bool)' in commands_rs
    assert 'commands::toggle_current_window_fullscreen' in main_rs
    assert 'commands::get_current_window_fullscreen' in main_rs
    assert 'commands::set_current_window_fullscreen' in main_rs
    assert "invoke<boolean>('get_current_window_fullscreen')" in tauri_ts
    assert "invoke<boolean>('set_current_window_fullscreen'" in tauri_ts
    assert 'const current = await getCurrentWindowFullscreen();' in player_tsx
    assert 'let applied = await setCurrentWindowFullscreen(target);' in player_tsx
    assert 'fullscreenToggleLockRef.current = true;' in player_tsx
