from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_seek_parse_does_not_default_empty_to_zero():
    standalone = _read('client/src/ArtifactStandalone.tsx')
    media = _read('client/src/ArtifactMediaStandalone.tsx')
    assert "const hasSeek = seekRaw !== '';" in standalone
    assert "const hasSeek = seekRaw !== '';" in media
    assert "hasSeek && Number.isFinite(seekNum) && seekNum >= 0 ? seekNum : undefined" in standalone
    assert "hasSeek && Number.isFinite(seekNum) && seekNum >= 0 ? seekNum : undefined" in media
