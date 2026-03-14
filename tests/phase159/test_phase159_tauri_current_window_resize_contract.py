from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_c5_tauri_current_window_resize_contract():
    tauri_ts = _read('client/src/config/tauri.ts')
    assert 'MARKER_159.C5.WINDOW_SIZE_API' in tauri_ts
    assert 'export async function setCurrentWindowLogicalSize' in tauri_ts
    assert "import('@tauri-apps/api/dpi')" in tauri_ts
    assert 'await win.setSize(new LogicalSize(w, h));' in tauri_ts
    assert 'Math.max(240, Math.round(Number(width) || 0))' in tauri_ts
    assert 'Math.max(224, Math.round(Number(height) || 0))' in tauri_ts
