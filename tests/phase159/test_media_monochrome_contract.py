from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_artifact_media_css_is_monochrome_on_key_surfaces():
    src = _read("client/src/components/artifact/ArtifactPanel.css")
    forbidden_tokens = [
        "#2563eb",
        "#3b82f6",
        "#93c5fd",
        "#fdba74",
        "#fca5a5",
        "#86efac",
        "#a78bfa",
        "#c4b5fd",
        "rgba(251, 191, 36",
        "rgba(52, 211, 153",
        "rgba(16, 185, 129",
        "rgba(59, 130, 246",
        "rgba(249, 115, 22",
    ]
    for token in forbidden_tokens:
        assert token not in src

