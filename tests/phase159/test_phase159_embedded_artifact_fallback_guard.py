from pathlib import Path


ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_c1_embedded_fallback_guard_contract():
    app_tsx = _read('client/src/App.tsx')

    assert 'vetka_force_embedded_artifact' in app_tsx
    assert 'const isEmbeddedArtifactFallbackForced = useCallback(() => {' in app_tsx
    assert 'openArtifactEmbeddedFallback(payload);' in app_tsx
    assert "console.info('[MARKER_159.C1_OPEN_PATH] opened_via=embedded_fallback')" in app_tsx
