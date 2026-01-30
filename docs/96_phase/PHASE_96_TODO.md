# Phase 96: Search & Sync Fixes

**Date**: 2026-01-27 (updated 2026-01-28)
**Status**: IN PROGRESS
**Previous**: Phase 95 (commits c6d49bb, c0d7d1a)

---

## COMPLETED FIXES

### FIX_96.1: TripleWrite Enabled by Default ✅

**Problem:** File watcher and API routes were writing directly to Qdrant, bypassing Weaviate and ChangeLog.

**Solution:** Changed TripleWrite from opt-in to opt-out:
- `get_qdrant_updater()` now defaults to `enable_triple_write=True`
- `file_watcher.py` explicitly passes `enable_triple_write=True`
- `watcher_routes.py` BYPASS_001, BYPASS_002, BYPASS_003 fixed

**Files modified:**
- `src/scanners/qdrant_updater.py` (line 730)
- `src/scanners/file_watcher.py` (lines 415, 473)
- `src/api/routes/watcher_routes.py` (lines 167, 459-492, 661-692)

**Remaining:** BYPASS_005 (batch operations) still pending - needs TW batch_write() method

**Documentation:** `docs/96_phase/FIX_96.1_TRIPLEWRITE_ENABLED.md`

---

## CRITICAL BUGS

### BUG_96.1: Keyword search returns 0 results (filtered=100) ✅ FIXED

**Problem**: Two issues combined:
1. FIX_95.12 set `min_score=0.005` but BM25 scores are in different range
2. Frontend ALWAYS sends `min_score=0.3` as default (useSocket.ts:1360)

**Root cause**: `data.get('min_score', default)` returns frontend's 0.3, not our mode-aware default

**Fix (FIX_96.3.1)**: Override frontend's 0.3 with mode-aware thresholds
```python
frontend_min_score = data.get('min_score')
if frontend_min_score is None or frontend_min_score == 0.3:
    min_score = default_thresholds.get(mode, 0.001)  # Mode-aware
else:
    min_score = frontend_min_score  # User explicit value
```

**Files modified**: `src/api/handlers/search_handlers.py` (lines 77-85)

### BUG_96.2: Hybrid search returns 0 results (filtered=100) ✅ FIXED

Same fix as BUG_96.1 (FIX_96.3.1). Hybrid mode threshold now 0.001 instead of 0.3.

### BUG_96.3: Filename search returns 0 results

**Logs**:
```
[FILENAME] Scroll with type=scanned_file returned 554 points
[HYBRID] Filename search '3d' → 0 results
```

**Problem**: 554 files scanned but 0 matched "3d". Check matching logic in `_filename_search()`.

**File**: `src/search/hybrid_search.py` line ~458

**Debug**: Add logging to see what filenames are being checked:
```python
logger.debug(f"[FILENAME] Checking: {payload.get('file_name')} against pattern '{query}'")
```

---

## SYNC ISSUES

### ISSUE_96.4: Weaviate not synced with Qdrant ✅ FIXED

**Problem:** Clear button only deleted from Qdrant, leaving stale data in Weaviate.

**Fix (FIX_96.4):** Clear-all endpoint now deletes from BOTH stores:
- Qdrant: `vetka_elisya` collection recreated
- Weaviate: `VetkaLeaf` class deleted (auto-recreates on next write)
- Chat history (JSON) preserved

**Files modified:**
- `src/api/routes/semantic_routes.py` (lines 871-990)
- `client/src/components/scanner/ScanPanel.tsx` (lines 429-465)

**Documentation:** `docs/96_phase/HAIKU_09_CLEANUP_BUTTON_RECON.md`

### ISSUE_96.5: New files not appearing (camera not focusing)

Watchdog detects files, indexes to Qdrant, but:
- Camera doesn't fly to new node
- Tree may not refresh properly

**Root cause**: React state update timing race (FIX_95.9.4 added retries but may not be enough)

---

## UI ISSUES

### ISSUE_96.6: Duplicate search method buttons (left + right)

Screenshot shows search mode buttons appearing in two places.

**Files to check**:
- `client/src/components/search/UnifiedSearchBar.tsx`
- Check if mode selector is rendered twice

---

## DEFERRED TO TAURI

### WONTFIX: File watcher reliability on macOS

FSEvents API misses events. PollingObserver is workaround but resource-intensive.
Tauri will use native Rust file watching (notify crate) which is more reliable.

---

## PRIORITY ORDER

1. **BUG_96.1** - Keyword search (quick fix: mode-aware thresholds)
2. **BUG_96.2** - Hybrid search (same fix + check caching)
3. **BUG_96.3** - Filename search (debug matching logic)
4. **ISSUE_96.4** - Weaviate sync (run reindex)
5. **ISSUE_96.6** - UI duplicate buttons (CSS/component fix)

---

## FILES TO MODIFY

| File | Issue | Change |
|------|-------|--------|
| `src/api/handlers/search_handlers.py` | BUG_96.1, BUG_96.2 | Mode-aware min_score |
| `src/search/hybrid_search.py` | BUG_96.3 | Debug filename matching |
| `client/src/components/search/UnifiedSearchBar.tsx` | ISSUE_96.6 | Remove duplicate buttons |

---

## QUICK START TOMORROW

```bash
# 1. Check Weaviate sync status
curl http://localhost:5002/api/triple-write/check-coherence

# 2. If mismatched, reindex
curl -X POST http://localhost:5002/api/triple-write/reindex

# 3. Test search modes
# - Semantic should work (shows 100 results)
# - Keyword needs fix (shows 0 after filtering)
# - Filename needs debug (0 matches)
```
