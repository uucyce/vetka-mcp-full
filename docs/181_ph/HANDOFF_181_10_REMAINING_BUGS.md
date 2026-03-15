# HANDOFF: Phase 181.10 — Remaining Bugs After Chunked Embedding Fix

**Date:** 2026-03-15
**Author:** Opus (Claude Code)
**Commit:** `214480b9e` — `phase181.10: chunked embeddings — zero data loss for large files`
**Branch:** main (pushed)

---

## What Was Fixed (commit 214480b9e)

Chunked embedding pipeline — полный импорт файлов без потери данных:

| Component | Change |
|-----------|--------|
| `src/utils/text_chunker.py` | NEW — hierarchical splitting (paragraphs→sentences→words) with configurable overlap |
| `src/utils/embedding_service.py` | `get_embedding_chunked()` + `get_embedding_chunked_async()` — chunk→embed→mean pool |
| `src/scanners/qdrant_updater.py` | `_get_embedding()` uses chunked, removed `[:3800]` and `[:8000]` truncation |
| `src/api/routes/watcher_routes.py` | Removed truncation, added `_diagnose_embedding_failure()` |
| `client/src/components/chat/ChatPanel.tsx` | MYCO scanner feedback, MessageInput always visible |
| `client/src/components/scanner/ScanPanel.css` | `flex-shrink: 1` + `max-height: 60vh` |
| `client/src/types/chat.ts` | Added `'MYCO'` agent type |
| `tests/test_phase181_chunked_embedding.py` | 26 tests (12 chunker + 7 mocked + 3 integration + 4 live) |

**Verified:** Single file import (Cmd+K) returns 200 OK. Folder scan indexes files. CSV/HTML/MD files that previously failed (>4000 chars) now embed correctly via chunking.

---

## Bug 1: Camera Flyto on Re-Import of Existing Folder

**Severity:** LOW (UX polish)
**Component:** Scanner / 3D viewport

### Problem
When user imports a folder that is **already indexed** in Qdrant, the scanner silently does nothing — no feedback, no camera movement. User expects the camera to fly to the existing folder node in the 3D graph.

### Expected Behavior
1. Scanner detects folder is already imported (all files already in Qdrant)
2. Instead of silently returning, emit a SocketIO event: `scanner:already_indexed`
3. Frontend receives event → calls `vetka_camera_focus` on the folder's node in the graph
4. MYCO posts a chat message: "📁 Folder already indexed. Showing in graph."

### Investigation Points

**Backend — `src/scanners/qdrant_updater.py`:**
- `update_file()` method already skips files with matching hash (line ~370)
- Need to track "skipped because already indexed" count
- If ALL files skipped → emit `scanner:already_indexed` event with folder path

**Backend — `src/api/routes/watcher_routes.py`:**
- `/api/watcher/scan-folder` endpoint (line ~850)
- After scan completes, check if `indexed_count == 0` and `skipped_count > 0`
- Emit SocketIO event with folder name for camera targeting

**Frontend — `client/src/components/chat/ChatPanel.tsx`:**
- `handleScannerEvent` already handles scanner events
- Add handler for `scanner:already_indexed` → trigger camera flyto
- Post MYCO message in chat

**Frontend — 3D viewport:**
- Need to find the node ID for the folder in the graph
- Call camera focus API or dispatch camera event

### Files to Modify
| File | Change |
|------|--------|
| `src/scanners/qdrant_updater.py` | Track skipped-because-exists count in scan results |
| `src/api/routes/watcher_routes.py` | Emit `scanner:already_indexed` when all files already present |
| `client/src/components/chat/ChatPanel.tsx` | Handle `already_indexed` event → camera + MYCO message |

---

## Bug 2: Scanner Panel Covers Chat (CSS Cache Issue)

**Severity:** LOW (may self-resolve after rebuild)
**Component:** Scanner panel CSS

### Problem
Scanner panel still covers chat messages and input field in some cases. The CSS fix was applied (`flex-shrink: 1`, `max-height: 60vh`) but the user still sees the old layout — likely browser CSS cache.

### Diagnosis Steps
1. Hard refresh browser (Cmd+Shift+R) or clear cache
2. Rebuild frontend: `cd client && npm run build`
3. Check if `ScanPanel.css` changes are reflected in the served bundle
4. If still broken after cache clear → the CSS fix is insufficient, need deeper investigation

### Current CSS Fix (already in commit 214480b9e)
```css
/* ScanPanel.css */
.scan-panel {
  flex-shrink: 1;      /* was: 0 — panel now shrinks when space is tight */
  max-height: 60vh;    /* cap scanner panel height */
}
```

### If CSS Fix Is Insufficient
The real issue may be in the parent flex container layout:

**`client/src/components/chat/ChatPanel.tsx`:**
- Scanner container uses `overflow: 'auto'` (changed from `overflow: 'hidden'`)
- MessageInput is now rendered regardless of `activeTab` (no longer hidden when scanner is active)
- Parent flex container may need `min-height: 0` on the scanner wrapper to allow proper shrinking

### Files to Investigate
| File | Check |
|------|-------|
| `client/src/components/scanner/ScanPanel.css` | Verify CSS is loaded (DevTools → Sources) |
| `client/src/components/chat/ChatPanel.tsx` | Parent flex layout, min-height constraints |
| `client/src/components/scanner/ScanPanel.tsx` | Component height behavior |

### Likely Resolution
Cache clear + frontend rebuild. If that doesn't fix it, add `min-height: 0` to scanner wrapper and ensure flex parent has `overflow: hidden` with child scroll.

---

## Permanent Fix Confirmation

### Chunked Embeddings — Permanent Architecture

The fix in commit `214480b9e` is **permanent and architectural**, not a workaround:

1. **`text_chunker.py`** — standalone utility with no external dependencies (only `re` + `typing`). Hierarchical splitting handles any text size.

2. **`EmbeddingService.get_embedding_chunked()`** — sits on top of existing `get_embedding()` and `get_embedding_batch()`. Does NOT change the underlying Ollama calls. Short texts (<3000 chars) take the fast path (zero overhead). Long texts get chunked + mean-pooled automatically.

3. **Mean pooling** is a standard technique for combining chunk embeddings into a single document vector. Used by sentence-transformers, LangChain, LlamaIndex.

4. **No truncation anywhere** — the `[:3800]` and `[:8000]` limits in `qdrant_updater.py` and `watcher_routes.py` are permanently removed. The chunker handles sizing.

5. **Backward compatible** — `get_embedding()` still works for callers that don't need chunking. `get_embedding_chunked()` is additive.

6. **Model-agnostic** — `max_chars=3000` default works for `embeddinggemma:300m` (2048 tokens ≈ 4000 chars, with safety margin). If model changes, just adjust the parameter.

### What Could Break This Fix?
- Someone re-adding `[:3800]` truncation (grep for it in CI/pre-commit)
- Changing `_get_embedding()` in `qdrant_updater.py` back to `get_embedding` (non-chunked)
- Ollama service not running (but `_diagnose_embedding_failure()` now gives actionable errors)

---

## References
- Bug doc: `docs/181_ph_MCC_projectID/BUG_SESSION_INIT_JSON_NAMESPACE.md`
- Zombie doc: `docs/181_ph_MCC_projectID/BUG_MCP_ZOMBIE_GRACEFUL_SHUTDOWN.md`
- Tests: `tests/test_phase181_chunked_embedding.py`
- Plan: `.claude/plans/mellow-booping-teacup.md`
