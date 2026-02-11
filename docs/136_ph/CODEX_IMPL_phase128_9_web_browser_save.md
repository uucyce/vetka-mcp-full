# MARKER_128.9.IMPL_WEB_BROWSER_SAVE
# Implementation Report: Native Research Window + Save-to-VETKA

Date: 2026-02-11
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

## Implemented
1. Native browser opening moved to Rust command:
- `open_research_browser(url, title?)`
- File: `client/src-tauri/src/commands.rs`
- Registered in `client/src-tauri/src/main.rs`
- Frontend bridge now invokes Rust command from `client/src/config/tauri.ts`

2. Web page save pipeline added:
- New API: `POST /api/artifacts/save-webpage`
- Route: `src/api/routes/artifact_routes.py`
- Handler: `src/api/handlers/artifact_routes.py`
- Uses `WebIntake` extractor (trafilatura/bs4 fallback)
- Saves markdown to: `data/artifacts/web_research/web_*.md`

3. Artifact web UI upgraded:
- `SAVE TO VETKA` button added in web header
- On success: switches to `MD` mode with real extracted content
- Status note shown in panel
- File: `client/src/components/artifact/ArtifactPanel.tsx`

## Markers
- `MARKER_128.9B_TAURI_CMD`
- `MARKER_128.9C_TAURI_INVOKE`
- `MARKER_128.9D_BACKEND_SAVE`
- `MARKER_128.9A_WEB_SAVE_UI`

## Notes
- This patch keeps `LIVE` default and avoids touching `main.py`, `agent_pipeline.py`, `debug_routes.py`.
- Embeddings/Qdrant indexing is not part of this isolated patch yet; now there is stable saved markdown artifact output for the next indexing step.
