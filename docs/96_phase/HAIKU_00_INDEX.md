# HAIKU SWARM RECON - Phase 96 Index

**Date:** 2026-01-28
**Agents:** 8 Haiku explorers
**Coordinator:** Claude Opus 4.5

---

## REPORTS GENERATED

| # | File | Topic | Key Finding |
|---|------|-------|-------------|
| 01 | HAIKU_01_QDRANT_WRITE_POINTS.md | All Qdrant writes | 15 write points, only 1 uses TripleWrite |
| 02 | HAIKU_02_WEAVIATE_WRITE_POINTS.md | All Weaviate writes | 3 different implementations, need consolidation |
| 03 | HAIKU_03_SEARCH_FILTERING_BUG.md | Search returns 0 | RRF scores 0.001-0.03, old threshold 0.3 filtered 100% |
| 04 | HAIKU_04_FILE_WATCHER_FLOW.md | Data flow | TripleWrite disabled by default in watcher |
| 05 | HAIKU_05_TRIPLEWRITE_INTEGRATION.md | TW usage | 4 integration points, only 2 actually used |
| 06 | HAIKU_06_CAM_ARCHITECTURE.md | CAM system | 4 operations, connected to Qdrant/Weaviate |
| 07 | HAIKU_07_ALL_CODE_MARKERS.md | Code markers | 38 markers found, 13 pending |
| 08 | HAIKU_08_VETKALEAF_SCHEMA.md | VetkaLeaf | Schema definition, BM25 search |

---

## CRITICAL FINDINGS SUMMARY

### 1. DATA COHERENCE PROBLEM (Root Cause)

```
EXPECTED STATE:
  Qdrant count = N
  Weaviate count = N
  ChangeLog entries = N

ACTUAL STATE (after normal usage):
  Qdrant count = N + X    ← ALL writes go here
  Weaviate count = N      ← Not updated
  ChangeLog entries = N   ← Not updated

WHERE X = files indexed via watcher/browser/drag-drop
```

**Why?** 5 code paths bypass TripleWriteManager:
1. File watcher events → direct Qdrant
2. Directory scan → direct Qdrant
3. Browser file upload → direct Qdrant
4. Drag-drop indexing → direct Qdrant
5. Batch updates → direct Qdrant

### 2. SEARCH RETURNS 0 RESULTS

**Root cause:** RRF scores are 0.001-0.03, but min_score threshold was 0.3

**Fixed in FIX_95.12:** New default is 0.005

**Still needed:** Mode-aware thresholds:
- Keyword: 0.0 (BM25 scores vary)
- Hybrid: 0.005 (RRF scores)
- Filename: 0.0 (no scores)
- Semantic: 0.3 (cosine similarity)

### 3. TRIPLEWRITE PARADOX

**In code:** `enable_triple_write=True` (default)
**In practice:** Internal state `_use_triple_write=False`
**Result:** TripleWrite code path never executed for watcher

### 4. THREE WEAVIATE IMPLEMENTATIONS

| Location | API Version | Purpose |
|----------|-------------|---------|
| TripleWriteManager | v3 REST | Core indexing |
| WeaviateHelper | v1 REST | Legacy/search |
| sync_script | v4 SDK | Standalone sync |

**Need:** Consolidate to single v4 SDK implementation

---

## HYPOTHESIS VALIDATION

### "Search works, just no data" - PARTIALLY CONFIRMED

**Search mechanism:** Working correctly
- Hybrid search with RRF fusion ✓
- BM25 in Weaviate ✓
- Vector search in Qdrant ✓

**But:**
1. Weaviate may be empty/out of sync with Qdrant
2. Score threshold was filtering 100% of results (now fixed)
3. Cyrillic queries need testing

### "Data exists in Qdrant but not Weaviate" - CONFIRMED

**Evidence:**
- 5 COHERENCE_BYPASS markers document direct Qdrant writes
- TripleWrite disabled by default in QdrantUpdater
- No sync mechanism running automatically

---

## RECOMMENDED ACTIONS

### Option A: Sync Qdrant → Weaviate

**Pros:**
- Preserves existing Qdrant data
- Fast (batch sync script exists)

**Cons:**
- Doesn't fix root cause
- Will diverge again

**How:**
```bash
# Check coherence first
curl http://localhost:5002/api/triple-write/check-coherence

# Run sync script
python scripts/sync_qdrant_to_weaviate.py
```

### Option B: Clean Weaviate + Rescan

**Pros:**
- Clean slate
- Ensures correct data

**Cons:**
- Loses any Weaviate-only data
- Takes time to rescan

**How:**
```bash
# Clear Weaviate
curl -X POST http://localhost:5002/api/triple-write/cleanup

# Reindex
curl -X POST http://localhost:5002/api/triple-write/reindex
```

### Option C: Fix Root Cause (Recommended)

**Enable TripleWrite for all paths:**

1. **File watcher** (`file_watcher.py:415`):
```python
updater = get_qdrant_updater()
updater.use_triple_write(enable=True)  # Add this!
handle_watcher_event(event, qdrant_client=qdrant_client)
```

2. **QdrantUpdater default** (`qdrant_updater.py:730`):
```python
def get_qdrant_updater(enable_triple_write=True):  # Change default
```

3. **Watcher routes** (`watcher_routes.py`):
- Fix MARKER_COHERENCE_BYPASS_001-003

Then rescan to populate all three stores.

---

## VERIFICATION STEPS

### 1. Check Current Coherence
```bash
curl http://localhost:5002/api/triple-write/check-coherence?depth=full
```

### 2. Test Search Modes
```bash
# Semantic (should work - uses Qdrant)
curl "http://localhost:5002/api/search?q=test&mode=semantic"

# Keyword (may fail - uses Weaviate BM25)
curl "http://localhost:5002/api/search?q=test&mode=keyword"

# Hybrid (depends on both)
curl "http://localhost:5002/api/search?q=test&mode=hybrid"
```

### 3. Check Weaviate Content
```bash
# Check if VetkaLeaf has any objects
curl http://localhost:8080/v1/objects?class=VetkaLeaf&limit=5
```

---

## FILES CREATED THIS SESSION

```
docs/96_phase/
├── HAIKU_00_INDEX.md          (this file)
├── HAIKU_01_QDRANT_WRITE_POINTS.md
├── HAIKU_02_WEAVIATE_WRITE_POINTS.md
├── HAIKU_03_SEARCH_FILTERING_BUG.md
├── HAIKU_04_FILE_WATCHER_FLOW.md
├── HAIKU_05_TRIPLEWRITE_INTEGRATION.md
├── HAIKU_06_CAM_ARCHITECTURE.md
├── HAIKU_07_ALL_CODE_MARKERS.md
├── HAIKU_08_VETKALEAF_SCHEMA.md
└── RECON_REPORT_PHASE_96.md   (initial recon)
```

---

## NEXT STEPS

1. **Immediate:** Check coherence, decide sync strategy
2. **Short-term:** Fix TripleWrite defaults, enable for watcher
3. **Medium-term:** Consolidate 3 Weaviate implementations
4. **Long-term:** Consider moving to Tauri for reliable file watching

---

*Generated by Claude Opus 4.5 coordinating Haiku Swarm reconnaissance*
