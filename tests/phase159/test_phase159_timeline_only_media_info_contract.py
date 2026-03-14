from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_timeline_banner_gated_to_media_info_only():
    panel = _read('client/src/components/artifact/ArtifactPanel.tsx')
    assert "activeSeekSec !== undefined && isMediaArtifact && mediaInfoOpen" in panel
