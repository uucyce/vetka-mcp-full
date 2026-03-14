from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_filecard_supports_media_category_and_16_9_shape():
    src = _read("client/src/components/canvas/FileCard.tsx")
    assert "const getFileCategory = (name: string): 'code' | 'doc' | 'media' => {" in src
    assert "return cardCategory === 'code' ? [14, 8] : cardCategory === 'media' ? [16, 9] : [8, 12];" in src


def test_phase159_filecard_treats_m4a_as_binary_non_previewable():
    src = _read("client/src/components/canvas/FileCard.tsx")
    assert "'mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a'" in src


def test_phase159_filecard_media_draws_play_triangle():
    src = _read("client/src/components/canvas/FileCard.tsx")
    assert 'ctx.strokeStyle = "rgba(255,255,255,0.95)";' in src
    assert 'ctx.fillStyle = "rgba(255,255,255,0.99)";' in src
    assert "ctx.lineTo(cx + triW * 0.55, cy);" in src


def test_phase159_filecard_media_hover_uses_preview_assets_300ms():
    src = _read("client/src/components/canvas/FileCard.tsx")
    assert "const mediaPreviewAssetCache = new Map<string, { posterUrl: string; animatedUrl: string; durationSec: number }>();" in src
    assert "const mediaPosterImageCache = new Map<string, HTMLImageElement>();" in src
    assert "fetch('/api/artifacts/media/preview'" in src
    assert "animated_preview_url_300ms" in src
    assert "ctx.drawImage(posterImg, 1, 1, w - 2, h - 2);" in src
    assert "isHovered && getFileCategory(name) === 'media'" in src
    assert "alt=\"video preview 300ms\"" in src
