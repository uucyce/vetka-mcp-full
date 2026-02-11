# MARKER_139.RECON_S1_2_WEB_PREVIEW
# Recon Report: Web Page Preview in Artifact (Unified Search)

Date: 2026-02-11
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

## Goal
Implement internet page preview rendering in Artifact window for `web/` unified search results.

## Findings
1. Unified search already returns web results:
- Route: `POST /api/search/unified`
- Backend: `src/api/handlers/unified_search.py` (`_web_search` via Tavily tool)

2. Current frontend behavior opens web result as markdown snippet only:
- `client/src/App.tsx` sets `artifactContent` with `type: 'markdown'`.
- No backend endpoint for full HTML preview.

3. Artifact renderer lacks dedicated web mode:
- `client/src/components/artifact/ArtifactPanel.tsx` supports `text|markdown|code` only.

## Plan
1. Add backend proxy endpoint:
- `POST /api/search/web-preview`
- Fetch URL with timeout, block localhost/private hosts, sanitize HTML, return iframe-ready `srcDoc`.
- Marker: `MARKER_139.S1_3_WEB_PROXY`.

2. Add frontend open flow:
- `App.tsx`: for web result, request preview endpoint, then open Artifact in `type: 'web'`.
- Marker: `MARKER_139.S1_3_WEB_RENDER`.

3. Add Artifact web renderer:
- `ArtifactPanel.tsx`: new `web` mode -> sandboxed iframe + source URL bar.
