from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_artifact_window_recreate_enforced_contract():
    commands = _read("client/src-tauri/src/commands.rs")
    assert "MARKER_159.R7.UNIFIED_WINDOW_NAV_REUSE" in commands
    assert 'window.location.replace(' in commands
    assert "existing.set_always_on_top(true)" in commands
