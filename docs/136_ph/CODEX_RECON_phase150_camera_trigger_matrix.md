# MARKER_136.RECON.CAM_TRIGGER_MATRIX
# Recon Report: camera triggers for file/folder scan flows

Date: 2026-02-15  
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

## Objective
Validate trigger chain for camera focus after scan/index and enforce rule:
- folder added => camera focuses folder
- file indexed/changed => camera focuses file

## Checked Paths
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/hooks/useSocket.ts`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/CameraController.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py`

## Findings
1. `POST /api/watcher/index-file` emits `file_indexed`, but frontend had no `socket.on('file_indexed')` handler.
- Effect: file could be indexed and shown in tree, but no deterministic camera move.

2. Drop flow in `App.tsx` mixed file and folder handling through `index-file`.
- For directories this is wrong endpoint (`/index-file` is file-only).
- This breaks clean folder-focus contract.

3. `camera-fly-to-folder` handler is immediate and node-lookup based.
- If tree refresh races with focus event, focus can be dropped.
- Needed small retry window after refresh for file-focus path.

## No-Guess Root Causes
- Missing socket trigger consumer (`file_indexed`) in client.
- Wrong endpoint path for dropped directories.
- Race between tree refresh completion and camera lookup.

## Implemented Fixes
1. `App.tsx` drop router now splits native dropped items by type:
- folders -> `/api/watcher/add` (`recursive: true`)
- files -> `/api/watcher/index-file`

2. `App.tsx` camera rule is now explicit:
- first dropped folder => `camera-fly-to-folder`
- first dropped file => `setCameraCommand` with short retry until node exists

3. `useSocket.ts` now listens to `file_indexed` and triggers:
- `reloadTreeFromHttp()`
- short retry focus to indexed file path/base name

## Marker List (code)
- `MARKER_136.CAM_TRIGGER_ROUTING`
- `MARKER_136.CAM_TRIGGER_FOLDER_ADD`
- `MARKER_136.CAM_TRIGGER_FILE_INDEX`
- `MARKER_136.CAM_TRIGGER_CONDITIONAL`
- `MARKER_136.CAM_SOCKET_FILE_INDEXED`
