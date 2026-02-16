# CODEX RECON — Phase 150 File Mode Boundary

Date: 2026-02-15
Scope: `/file` UX + backend pipeline boundaries vs `/web` + `/vetka`

## MARKER_150.FILE_VIEWPORT_LEAK
Status: FOUND

- `/file` request currently sends `viewport_context` from `UnifiedSearchBar`.
  - File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/search/UnifiedSearchBar.tsx`
  - Lines around file API call include: `viewport_context: viewportContext`.
- Backend `search_files(...)` currently derives roots from viewport nodes.
  - File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/search/file_search_service.py`
  - Function: `_roots_from_viewport(...)`

Impact:
- `/file` results depend on camera/pinned nodes, which is against required UX.

Fix:
- Remove `viewport_context` from `/file` request body.
- Remove viewport-root derivation from file search service.
- Keep `/file` root strategy on allowed roots only.

## MARKER_150.FILE_ALL_ALLOWED_ROOTS
Status: PARTIAL

- Current allowed root logic exists (`cwd`, `cwd.parent`, optional `VETKA_FILE_SEARCH_ROOTS`).
  - File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/search/file_search_service.py`
  - Function: `_allowed_search_roots(...)`
- Issue: provider `mdfind` path may return empty without fallback walk for some cases.

Fix:
- If `mdfind` gives no hits for a root, fallback to walk-based filename search.
- Keep mode `filename` and `keyword` behavior unchanged for UI compatibility.
- macOS: full-system search via Spotlight root (`/`) + home/workspace roots.
- Linux/Windows: keep placeholder scoped roots for now (explicitly marked in code for later adapter rollout).

## MARKER_150.FILE_ACTIONS_GAP
Status: PARTIAL

What exists:
- `Pin` already exists on each result row.
- `Artifact` open already exists (preview route via existing artifact panel flow).

Missing in `/file` row UX:
- Explicit `Add to VETKA` action (single-file index via existing pipeline).
- Explicit `Scan this folder` action (watcher add/scan using existing scanner route).

Fix:
- Add two compact row buttons (only for `/file` context):
  - `Add` -> `POST /api/watcher/index-file` for absolute file path.
  - `Scan` -> `POST /api/watcher/add` on parent dir (or path if directory).

## MARKER_150.FILE_PREVIEW_PARITY
Status: OK

- File result artifact preview path is already opened through existing artifact flow (`onOpenArtifact`).
- This matches desired “socket-style artifact behavior” (not Tauri webview).

## MARKER_150.VETKA_VIEWPORT_USAGE
Status: PRESENT (BY DESIGN TODAY)

- `/vetka` socket search currently can apply contextual rerank when `viewport_context` provided.
  - File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/search_handlers.py`
  - Marker in code references viewport rerank.

Note:
- This report only flags presence; no behavior change applied to `/vetka` in this step.

## MARKER_150.WEB_VIEWPORT_USAGE
Status: PRESENT (EXPECTED)

- `/web` unified search uses viewport-based query/context augmentation and rerank.
  - File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/unified_search.py`

## MARKER_150.PATCH_SEQUENCE

1. Decouple `/file` from viewport (frontend + backend).
2. Harden `/file` filename fallback (mdfind -> walk fallback).
3. Add `/file` row actions: `Add to VETKA`, `Scan folder` using existing watcher API.
4. Keep `/vetka` and `/web` behavior unchanged in this pass.
