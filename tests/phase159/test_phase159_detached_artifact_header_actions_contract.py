import pytest
from pathlib import Path

pytestmark = pytest.mark.stale(reason="Phase 159 import errors — UI contracts removed in CUT refactor")

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_detached_mode_restores_vetka_and_favorite_actions():
    panel = _read('client/src/components/artifact/ArtifactPanel.tsx')

    assert "windowMode === 'detached'" in panel
    assert "title={isFavorite ? 'Remove favorite' : 'Add favorite'}" in panel
    assert "title={isIndexingToVetka ? 'Adding to VETKA...' : 'Add to VETKA'}" in panel
    assert "fetch('/api/watcher/index-file'" in panel
    assert "fetch('/api/tree/favorite'" in panel
