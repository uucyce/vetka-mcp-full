from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_in_vetka_hint_wired_from_main_to_detached_window():
    app = _read('client/src/App.tsx')
    tauri_ts = _read('client/src/config/tauri.ts')
    commands = _read('client/src-tauri/src/commands.rs')
    standalone = _read('client/src/ArtifactStandalone.tsx')
    media_standalone = _read('client/src/ArtifactMediaStandalone.tsx')
    panel = _read('client/src/components/artifact/ArtifactPanel.tsx')

    assert 'inVetka?: boolean;' in app
    assert 'inVetka,' in app
    assert 'inVetka?: boolean;' in tauri_ts
    assert 'inVetka: typeof params.inVetka === \"boolean\" ? params.inVetka : undefined' in tauri_ts or "inVetka: typeof params.inVetka === 'boolean' ? params.inVetka : undefined" in tauri_ts
    assert 'in_vetka: Option<bool>' in commands
    assert '&in_vetka=' in commands
    assert "params.get('in_vetka')" in standalone
    assert "detachedInitialInVetka={query.inVetka}" in standalone
    assert "params.get('in_vetka')" in media_standalone
    assert "detachedInitialInVetka={query.inVetka}" in media_standalone
    assert 'detachedInitialInVetka?: boolean;' in panel
    assert "windowMode === 'detached' && typeof detachedInitialInVetka === 'boolean'" in panel
