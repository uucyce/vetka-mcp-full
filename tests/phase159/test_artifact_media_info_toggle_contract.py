from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_media_info_toggle_exists_and_controls_noise():
    src = _read("client/src/components/artifact/ArtifactPanel.tsx")
    assert "const [mediaInfoOpen, setMediaInfoOpen] = useState<boolean>(false);" in src
    assert "onInfo={isMediaArtifact ? () => setMediaInfoOpen((v) => !v) : undefined}" in src
    assert "{mediaPreview && mediaInfoOpen && (" in src
    assert "{activeSeekSec !== undefined && (!isMediaArtifact || mediaInfoOpen) && (" in src
    assert "{mediaPreview.modality === 'video' && mediaPreview.preview_assets?.poster_url && (" in src
    assert "{mediaPreview.modality === 'video' && mediaPreview.preview_assets?.animated_preview_url_300ms && (" in src
