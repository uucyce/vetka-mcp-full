# MARKER_139.RECON_S1_2_UNIFIED_SEARCH_ARTIFACT
# Recon Report: tb_1770809269_2 (Unified Search Tavily wire + Artifact display)

Date: 2026-02-11
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

## Scope
Task: `tb_1770809269_2` — S1.2 Unified Search (web provider/Tavily) with practical issue:
results partially work but do not render correctly in Artifact viewer.

## Findings
1. Backend Tavily wiring is already present.
- `src/api/handlers/unified_search.py`:
  - Marker `MARKER_137.S1_2_TAVILY_WIRE`
  - `_web_search()` calls `WebSearchTool` (`vetka_web_search`) and normalizes results.
- Route exists:
  - `src/api/routes/unified_search_routes.py` (`POST /api/search/unified`)

2. Frontend has a memo dependency bug causing unified results not to update reliably.
- `client/src/components/search/UnifiedSearchBar.tsx`
  - `sortedResults` is built from `activeResults`, but `useMemo` deps use `results` instead of `activeResults`.
  - Effect: web/file unified payload can arrive, but visible list remains stale/empty.

3. Artifact opening path mismatch for unified results.
- Unified backend returns `file://...` URL for file source.
- Frontend uses `result.path` directly in ArtifactPanel load via `/api/files/read`.
- `file://...` and `https://...` are not valid local file paths for that endpoint.
- Result: ArtifactPanel fallback text:
  - `// Could not load file ...`
  - `// Backend not available`

## Implementation plan
1. `UnifiedSearchBar.tsx`
- Fix `useMemo` deps to include `activeResults`.
- Normalize unified result path:
  - `file://relative/path` -> `relative/path` for file source.
  - Keep URL for web source in metadata path.
- Add marker for fix.

2. `App.tsx`
- In `onOpenArtifact` callback:
  - If source is web/URL: open Artifact viewer with `rawContent` preview (title/url/snippet), not file read.
  - If source is file with `file://`: strip prefix before passing to ArtifactPanel.
- Add marker for traceability.

## Exclusions
- No changes to `main.py`, `agent_pipeline.py`, `debug_routes.py`.
- No backend route rewrites; issue is frontend mapping/render path.
