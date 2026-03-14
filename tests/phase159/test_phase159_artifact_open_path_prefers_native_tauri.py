from pathlib import Path


ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_c1_open_path_prefers_native_tauri_window():
    app_tsx = _read('client/src/App.tsx')

    assert 'openArtifactWindow({' in app_tsx
    assert "windowLabel: 'artifact-main'" in app_tsx
    assert "console.info('[MARKER_159.C1_OPEN_PATH] opened_via=native_window')" in app_tsx
    assert 'if (!forceEmbedded && isTauri() && path)' in app_tsx
    assert "native artifact open failed; embedded fallback suppressed" in app_tsx
    assert "(!isTauri() || !artifactPath || isEmbeddedArtifactFallbackForced())" in app_tsx
