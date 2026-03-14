# Phase 159 — Selective Clean From VETKA (RECON + Markers)

Date: 2026-03-04
Protocol: `RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`
Status: RECON complete, waiting for GO.

## 1) Request interpreted
Need user-facing selective cleanup for a folder:
- remove data from VETKA index/storage/view/search/backend,
- keep files on disk untouched,
- block watchdog updates for that folder,
- expose action in clear UX (folder click -> mode/context category, wording like `Clean folder from VETKA`).

## 2) Recon findings (what already exists)

### UI entrypoints already present
- Folder right-click context menu exists and is fed from file/folder cards:
  - `FileCard` emits `vetka-node-context-menu` with `path/type/id` ([FileCard.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx:944)).
  - Global folder mode menu is rendered in `App.tsx` with `Directed/Knowledge/Media Edit` actions ([App.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx:1072)).
- Scanner panel has only global wipe (`Clear All`) and no per-folder clean action ([ScanPanel.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/scanner/ScanPanel.tsx:924)).

### Backend cleanup primitives already present
- There are selective cleanup endpoints for special cases:
  - `DELETE /api/watcher/cleanup-browser-files` ([watcher_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py:940)).
  - `DELETE /api/watcher/cleanup-playground-files` with `dry_run` and batched ID deletion ([watcher_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py:983)).
- There is runtime watchdog block endpoint:
  - `POST /api/watcher/spam-block` appends pattern to `SKIP_PATTERNS` ([watcher_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py:1081)).

### Watchdog behavior
- Skip logic is substring-based against `SKIP_PATTERNS` ([file_watcher.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/file_watcher.py:420)).
- `SKIP_PATTERNS` is in-memory global list ([file_watcher.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/file_watcher.py:62)).
- Watcher persisted state currently stores `watched_dirs` + heat only, not user blocklist ([file_watcher.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/file_watcher.py:1046)).

### Visibility filtering today
- Tree build path already filters `deleted=false` ([tree_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/tree_routes.py:257)).
- Hybrid/semantic/filename search path does **not** enforce `deleted=false` in Qdrant helper:
  - vector search filter only by `type=scanned_file` ([qdrant_client.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_client.py:333)).
  - filename search filter only by `type=scanned_file` ([qdrant_client.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_client.py:397)).
  - Hybrid search uses these methods directly ([hybrid_search.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/search/hybrid_search.py:478)).

## 3) Gaps vs requested behavior
1. No user action `Clean folder from VETKA` in folder mode/context menu.
2. No generic backend endpoint to clean arbitrary folder prefix (only browser/playgrounds/global clear).
3. Watchdog block via `spam-block` is runtime-only and not persisted across restart.
4. Search can still return cleaned docs if only soft delete is used and search helpers ignore `deleted` flag.
5. Weaviate keyword side likely remains stale unless explicit folder-scope deletion is done there too.

## 4) Proposed markers (for narrow implementation)

### UI markers
- `MARKER_159.CLEAN_UI_CONTEXT_MENU`
  - File: [App.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx)
  - Add new section under folder mode menu:
    - Label: `Clean Folder from VETKA`
    - Subtext/confirm: `Removes from VETKA index only. Files remain on disk.`
  - Trigger new backend endpoint with selected `nodePath`.

- `MARKER_159.CLEAN_UI_SCANNER_ACTION` (optional if you want second entrypoint)
  - File: [ScanPanel.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/scanner/ScanPanel.tsx)
  - Add per-folder clean control near local source actions (not replacing global clear).

### API markers
- `MARKER_159.CLEAN_API_FOLDER_SCOPE`
  - File: [watcher_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py)
  - New endpoint:
    - `POST /api/watcher/cleanup-folder-from-vetka`
    - Body: `{ path: string, dry_run?: bool, block_watchdog?: bool }`
  - Behavior:
    - Normalize/validate path.
    - Collect matching Qdrant points where payload `path` starts with folder path prefix.
    - Delete in batches.
    - Delete Weaviate VetkaLeaf objects by `file_path` prefix (batched).
    - Optionally add watcher block pattern.
    - Return summary counts per storage + block status.

- `MARKER_159.CLEAN_API_DRY_RUN`
  - Same endpoint supports dry-run for safe preview.

### Watchdog markers
- `MARKER_159.CLEAN_WATCHDOG_BLOCK`
  - Files: [watcher_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py), [file_watcher.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/file_watcher.py)
  - Add explicit helper for folder block to avoid accidental partial patterns.

- `MARKER_159.CLEAN_WATCHDOG_PERSIST`
  - File: [file_watcher.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/file_watcher.py)
  - Persist `user_blocked_patterns` in watcher state and restore on startup.

### Search/backend consistency markers
- `MARKER_159.CLEAN_SEARCH_EXCLUDE_DELETED`
  - File: [qdrant_client.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_client.py)
  - Add `deleted=false` condition to `search_by_vector` and `search_by_filename` filters.

- `MARKER_159.CLEAN_BACKEND_CACHE_INVALIDATE`
  - Files: tree/search routes caches where needed.
  - Invalidate relevant caches after folder cleanup to reflect immediate UI removal.

## 5) Narrow implementation sequence (post-GO)
1. Add backend endpoint `cleanup-folder-from-vetka` with `dry_run` and `block_watchdog`.
2. Implement Qdrant prefix deletion + Weaviate prefix deletion.
3. Add/restore persistent watchdog blocklist.
4. Add `deleted=false` filtering in Qdrant search helpers.
5. Wire folder context menu action in `App.tsx`.
6. Minimal tests for endpoint + filter behavior.

## 6) Verification checklist (post-impl)
1. Clean folder action on folder node shows explicit warning that disk files are preserved.
2. After clean, files from that folder disappear from tree/UI/search.
3. Files still exist on disk (`ls`/finder check).
4. New file edits in blocked folder do not reappear (watchdog skip effective).
5. After app restart, block persists if persistence enabled.
6. Dry-run returns counts and performs no deletions.

## 7) Open decisions before GO
1. Should watchdog block be permanent by default or user-toggle (`temporary/permanent`)?
2. Keep soft-delete or do hard-delete for this feature? (recommended: hard-delete for explicit user clean)
3. Require `dry_run` preview step always, or optional?

---
WAITING FOR `GO`.
No implementation performed in this step.
