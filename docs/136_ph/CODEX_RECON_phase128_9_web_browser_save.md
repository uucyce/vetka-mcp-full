# MARKER_128.9.RECON_WEB_BROWSER_SAVE
# Recon Report: Native Research Window + Save-to-VETKA Flow

Date: 2026-02-11
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

## Findings
1. `LIVE` preview currently works via iframe and fails on some domains due to X-Frame-Options/CSP.
2. Existing `NATIVE WINDOW` path is frontend-only (`@tauri-apps/api/webviewWindow`) and can fail silently under current capability/runtime conditions.
3. Tauri backend already has stable command pattern (`open_mycelium`) and can create windows via Rust (`WebviewWindowBuilder`).
4. Backend already has web text extractor (`src/intake/web.py`: trafilatura + BeautifulSoup fallback) but UI does not use it for web-artifact MD mode.

## Plan (isolated)
1. Add Rust command `open_research_browser(url, title?)` and invoke it from frontend helper.
2. Add API endpoint `POST /api/artifacts/save-webpage`:
- fetch + extract readable text,
- write markdown artifact into `data/artifacts/web_research/`.
3. Upgrade Artifact web header:
- `SAVE TO VETKA` action (stores and switches to MD view with real content),
- keep `LIVE` as default.

## Markers
- `MARKER_128.9B_TAURI_CMD`
- `MARKER_128.9C_TAURI_INVOKE`
- `MARKER_128.9D_BACKEND_SAVE`
- `MARKER_128.9A_WEB_SAVE_UI`
