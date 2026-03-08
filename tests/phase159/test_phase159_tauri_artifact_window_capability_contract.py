from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_tauri_artifact_window_capability_contract():
    capability = _read("client/src-tauri/capabilities/default.json")

    assert '"artifact-main"' in capability
    assert '"artifact-media"' in capability
    assert '"core:window:allow-set-size"' in capability
