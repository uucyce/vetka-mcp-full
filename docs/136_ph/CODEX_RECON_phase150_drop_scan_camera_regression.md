# MARKER_136.RECON.PH150_DROP_SCAN_CAMERA
# Recon Report: drop scan + camera regression + branch placement

Date: 2026-02-15  
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

## Scope
- Verify why dropped file is indexed but not clearly visible in expected branch.
- Verify `/file` behavior against real project file.
- Verify camera behavior regression after recent edits.

## What was inspected
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/CameraController.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/files_routes.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/search/file_search_service.py`

## Findings
1. Camera regression is confirmed in `App.tsx`.
- Real-path drop branch was changed from `folderName = firstName` to parent-folder derivation.
- `camera-fly-to-folder` is resolved by name/path match in `CameraController.findNode()`.
- Passing parent folder instead of dropped file name/path can miss file focus behavior.

2. Direct root issue for branch placement is in index metadata coherence.
- `POST /api/watcher/index-file` writes through `TripleWrite`.
- Tree builder (`/api/tree/data`) relies on payload fields like `path`, `parent_folder`, `name`, `type`, `deleted`.
- Without explicit metadata in TripleWrite path, placement may be inconsistent/implicit.

3. `/file` symptom from screenshot is ranking mismatch, not absence on disk.
- Query `claude_desktop_config` can surface many same-name artifacts from `~/Library`.
- Required behavior: project path in `Documents/VETKA_Project` must win in ranking.

## Decision Boundary
- Revert camera behavior in `App.tsx` to pre-regression behavior.
- Keep only fixes related to:
  - real path usage before browser fallback (`resolve-path -> index-file` flow),
  - coherent metadata for `index-file` so new file lands in correct branch,
  - `/file` ranking relevance.

## Implementation Plan (approved by recon)
1. Restore `App.tsx` real-path drop camera target logic to original value (`firstName` path/name behavior).
2. Keep `watcher_routes.py` metadata enrichment in `index-file` (branch placement fix).
3. Keep `file_search_service.py` ranking improvements (project-first relevance).
