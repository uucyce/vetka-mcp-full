from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_toolbar_compact_contract_for_detached_media():
    panel = _read('client/src/components/artifact/ArtifactPanel.tsx')
    toolbar = _read('client/src/components/artifact/Toolbar.tsx')

    assert "compact={windowMode === 'detached' && isMediaArtifact}" in panel
    assert "MARKER_159.R12.DETACHED_MEDIA_FIXED_FOOTER" in panel
    assert "DETACHED_MEDIA_TOOLBAR_OUTER_PX" in panel
    assert 'compact?: boolean;' in toolbar
    assert 'compact = false,' in toolbar
    assert 'export const DETACHED_MEDIA_TOOLBAR_OUTER_PX = 49;' in toolbar
    assert "padding: compact ? 6 : 8" in toolbar
    assert "height: compact ? DETACHED_MEDIA_TOOLBAR_OUTER_PX : undefined" in toolbar
    assert "minHeight: compact ? DETACHED_MEDIA_TOOLBAR_OUTER_PX : 44" in toolbar
    assert "boxSizing: compact ? 'border-box' : undefined" in toolbar
    assert "!compact && (createdAt || modifiedAt)" in toolbar
