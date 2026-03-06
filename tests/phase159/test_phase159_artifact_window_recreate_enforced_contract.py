from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_artifact_window_recreate_enforced_contract():
    commands = _read("client/src-tauri/src/commands.rs")
    assert "MARKER_159.C4.WINDOW_RECREATE_ENFORCED" in commands
    assert "existing.close();" in commands
