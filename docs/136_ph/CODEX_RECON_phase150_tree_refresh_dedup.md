# MARKER_136.RECON.TREE_REFRESH_DEDUP
# Recon Report: duplicate GET /api/tree/data after single index operation

Date: 2026-02-15  
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

## Goal
Find no-guess causes of repeated `GET /api/tree/data` after one file index and define narrow dedup strategy without changing camera semantics.

## Evidence
Observed logs show one `POST /api/watcher/index-file 200`, then multiple `GET /api/tree/data` in short window (3+ requests).

## Sources that trigger tree reload now
1. `App.tsx`
- Path: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx`
- In drop flow, after successful native processing:
  - dispatches `vetka-tree-refresh-needed`.

2. `useTreeData.ts`
- Path: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/hooks/useTreeData.ts`
- Listens to `vetka-tree-refresh-needed` and calls `fetchTreeData()` (HTTP `/api/tree/data`).

3. `useSocket.ts` (direct HTTP reload path)
- Path: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/hooks/useSocket.ts`
- `node_added` -> `await reloadTreeFromHttp()` -> HTTP `/api/tree/data`.
- `file_indexed` -> `await reloadTreeFromHttp()` -> HTTP `/api/tree/data`.
- `directory_scanned` also reloads via HTTP.

4. `ArtifactWindow.tsx`
- Path: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/artifact/ArtifactWindow.tsx`
- After Add to VETKA success, dispatches `vetka-tree-refresh-needed` (another HTTP call via `useTreeData` listener).

## No-Guess Root Cause
Single indexing action can fan out into multiple independent refresh paths:
- socket-driven reload (`node_added` / `file_indexed`)
- event-driven reload (`vetka-tree-refresh-needed` -> `useTreeData`)
These paths are concurrent and currently uncoordinated/debounced, causing duplicate `/api/tree/data`.

## Narrow Fix Strategy (for GO)
1. Keep one canonical refresh channel for index flow:
- Prefer socket-driven reload in `useSocket.ts` for real-time indexing events.
- Remove `vetka-tree-refresh-needed` dispatch from `App.tsx` drop success path.

2. Preserve manual refresh intent in `ArtifactWindow.tsx`, but debounce at listener side:
- Add lightweight in-flight/time-window guard in `useTreeData` refresh handler (e.g. ignore duplicate event if reload started <300ms ago).

3. No camera logic changes in this task:
- focus behavior remains file->file, folder->folder as currently working.

## Files to touch in IMPL (minimal)
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/hooks/useTreeData.ts`

## Markers for implementation phase
- `MARKER_136.TREE_REFRESH_DEDUP_APP`
- `MARKER_136.TREE_REFRESH_DEDUP_TREEHOOK`
