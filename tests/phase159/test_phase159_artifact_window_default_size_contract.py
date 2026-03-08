from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_c2_artifact_window_default_size_reduced():
    commands_rs = _read('client/src-tauri/src/commands.rs')
    assert '.inner_size(960.0, 680.0)' in commands_rs
    assert '.min_inner_size(760.0, 460.0)' in commands_rs
    assert '.inner_size(960.0, 540.0)' in commands_rs
    assert '.min_inner_size(240.0, 224.0)' in commands_rs
    assert '.always_on_top(true)' in commands_rs
