# HAIKU RECON 07: All Code Markers

**Agent:** Haiku
**Date:** 2026-01-28
**Task:** Find ALL markers in the codebase

---

## SUMMARY STATISTICS

| Category | Found | Fixed | Pending |
|----------|-------|-------|---------|
| MARKER_COHERENCE | 7 | 1 | 6 |
| MARKER_TW | 10 | 10 | 0 |
| TODO_95 | 11 | 4 | 7 |
| FIX_95 | 10 | 10 | 0 |
| BUG_96 | 0 | 0 | 0 |
| **TOTAL** | **38** | **25** | **13** |

---

## COHERENCE MARKERS (7)

### MARKER_COHERENCE_ROOT_001 [PENDING]
- **File:** `src/scanners/qdrant_updater.py:53`
- **Issue:** QdrantUpdater writes directly to Qdrant only, bypasses TripleWriteManager
- **Root Cause:** All file watcher events bypass TW
- **Fix:** Add `use_triple_write(tw_manager)` and route writes through TW

### MARKER_COHERENCE_BYPASS_001 [PENDING]
- **File:** `src/api/routes/watcher_routes.py:160`
- **Issue:** Directory scan uses QdrantUpdater (Qdrant-only)
- **Fix:** Replace with `get_triple_write_manager()` with fallback

### MARKER_COHERENCE_BYPASS_002 [PENDING]
- **File:** `src/api/routes/watcher_routes.py:460`
- **Issue:** Browser files bypass TripleWrite
- **Fix:** Use `tw.write_file()` with virtual_path and browser metadata

### MARKER_COHERENCE_BYPASS_003 [PENDING]
- **File:** `src/api/routes/watcher_routes.py:634`
- **Issue:** Drag-drop files bypass TripleWrite
- **Fix:** Use `get_triple_write_manager().write_file()`

### MARKER_COHERENCE_BYPASS_004 [PENDING]
- **File:** `src/scanners/qdrant_updater.py:387`
- **Issue:** Single file upsert bypasses Weaviate/Changelog
- **Fix:** Ensure TW enabled via `use_triple_write(enable=True)`

### MARKER_COHERENCE_BYPASS_005 [PENDING]
- **File:** `src/scanners/qdrant_updater.py:493`
- **Issue:** Batch upsert bypasses Weaviate/Changelog
- **Fix:** Implement `tw.batch_write(files)` or loop `tw.write_file()`

### MARKER_COHERENCE_001 [FIXED]
- **File:** `src/api/routes/triple_write_routes.py:77`
- **Issue:** Coherence check endpoint needed
- **Status:** Implemented `/api/triple-write/check-coherence`

---

## TRIPLE WRITE MARKERS (10) - ALL FIXED

### MARKER_TW_004_SILENT_FAILURES [FIXED x3]
- **Files:** `triple_write_manager.py:94, 407, 464`
- **Issue:** Silent failures needed retry with exponential backoff
- **Fix:** `_retry_with_backoff()` with 3 attempts, 0.5s base delay

### MARKER_TW_010_RACE_CONDITION [FIXED x2]
- **Files:** `triple_write_manager.py:74, 482`
- **Issue:** Race condition in changelog writes
- **Fix:** Thread lock `self._changelog_lock`

### MARKER_TW_011_NO_EMBEDDING_VALIDATION [FIXED]
- **File:** `triple_write_manager.py:263`
- **Issue:** No embedding dimension validation
- **Fix:** Check `len(embedding) != self.embedding_dim`

### MARKER_TW_012_RETRY_FALSE_CONTINUES [FIXED]
- **File:** `triple_write_manager.py:108`
- **Issue:** False means client unavailable, shouldn't retry
- **Fix:** `if result is True:` - only continue retry on True

### MARKER_TW_013_NO_WRITE_LOCK [FIXED x2]
- **Files:** `triple_write_manager.py:77, 289`
- **Issue:** No thread lock for concurrent writes
- **Fix:** `self._write_lock = threading.Lock()`

### MARKER_TW_014_NO_INPUT_VALIDATION [FIXED]
- **File:** `triple_write_manager.py:258`
- **Issue:** Empty file_path not validated
- **Fix:** Check `if not file_path or not file_path.strip()`

---

## TODO_95 MARKERS (11)

### TODO_95.9 COHERENCE_* [PENDING x6]
- Lines documented above in COHERENCE MARKERS section

### TODO_95.9 MARKER_ARCH_001_WEAVIATE_DUPLICATE [PENDING]
- **File:** `src/memory/weaviate_helper.py:8`
- **Issue:** Consolidate with vetka_weaviate_helper.py and triple_write_manager.py

### MARKER_WATCHDOG_001 [FIXED]
- **File:** `src/scanners/file_watcher.py:401`
- **Issue:** Removed blocking sleep(2), added non-blocking retry via threading.Timer

### MARKER_WATCHDOG_002 [PENDING]
- **File:** `src/scanners/file_watcher.py:33`
- **Issue:** macOS FSEvents may miss 'created' events
- **Workaround:** USE_POLLING_OBSERVER env var fallback

---

## FIX_95 MARKERS (10) - ALL IMPLEMENTED

| Marker | File | Description |
|--------|------|-------------|
| FIX_95.1_MODE_NONE | hybrid_search.py:264 | Preserve requested mode instead of "none" |
| FIX_95.3 | hybrid_search.py:465 | Pass collection to search_by_filename |
| FIX_95.3_FILENAME_SCROLL | qdrant_client.py:389,411,425 | Try scanned_file filter first |
| FIX_95.5 | provider_registry.py:716,1598 | OpenRouter key rotation |
| FIX_95.6 | mcp/vetka_mcp_bridge.py:49 | Increased timeout 30s→90s |
| FIX_95.7 | hybrid_search.py:127, semantic_routes.py:486 | Default collection "tree"→"leaf" |
| FIX_95.8 | qdrant_updater.py:24 | Proper logging instead of print |
| FIX_95.9 | qdrant_updater.py (multiple) | TripleWrite integration |
| FIX_95.10 | weaviate_helper.py:225 | VetkaLeaf field mapping |
| FIX_95.11 | file_watcher.py:49 | Added venv_ and site-packages patterns |
| FIX_95.12 | search_handlers.py:64-67,120-135 | RRF score threshold 0.3→0.005 |
| FIX_95.9.3 | file_watcher.py:52-55 | Skip changelog directory to prevent infinite loop |

---

## CRITICAL PENDING MARKERS

### Priority 1: Data Coherence
1. **MARKER_COHERENCE_ROOT_001** - QdrantUpdater bypasses TripleWriteManager completely
2. **MARKER_COHERENCE_BYPASS_001-005** - 5 points where Qdrant writes directly without TW

### Priority 2: Architecture Debt
3. **MARKER_ARCH_001_WEAVIATE_DUPLICATE** - 3 different Weaviate implementations need consolidation

### Priority 3: Platform Issues
4. **MARKER_WATCHDOG_002** - macOS FSEvents reliability (deferred to Tauri)

---

## MARKER DISTRIBUTION BY FILE

| File | Markers | Status |
|------|---------|--------|
| triple_write_manager.py | 10 | All Fixed |
| qdrant_updater.py | 4 | 1 Fixed, 3 Pending |
| watcher_routes.py | 3 | All Pending |
| file_watcher.py | 2 | 1 Fixed, 1 Pending |
| weaviate_helper.py | 1 | Pending |
| triple_write_routes.py | 1 | Fixed |
| hybrid_search.py | 3 | All Fixed |
| search_handlers.py | 1 | Fixed |
| qdrant_client.py | 3 | All Fixed |
| provider_registry.py | 1 | Fixed |
| vetka_mcp_bridge.py | 1 | Fixed |
| semantic_routes.py | 1 | Fixed |

---

## BUG_96 MARKERS

**None found in code** - BUG_96 markers haven't been added yet. They exist only in `docs/96_phase/PHASE_96_TODO.md`.

---

## KEY INSIGHT

TripleWrite integration is **70% complete**:
- Core structures exist and work
- But NOT all code paths use TW for writes
- Watchdog and some API endpoints still write directly to Qdrant
- This causes Qdrant/Weaviate data divergence over time
