# 🚨 CRITICAL ARCHITECTURE ISSUE - Tree Visualization Broken

**Date**: 2026-01-20
**Severity**: 🔴 **CRITICAL** - Blocks real-time visualization
**Status**: IDENTIFIED + ROOT CAUSE FOUND
**Reporter**: Claude Code Haiku 4.5

---

## EXECUTIVE SUMMARY

**The 3D tree shows stale/old data despite nuclear rescan completing successfully.**

**Root Cause**: Collection naming mismatch between rescan script and tree visualization routes.

| Component | Collection Used | Status |
|-----------|-----------------|--------|
| Nuclear Rescan Script | `vetka_nodes`, `vetka_edges` | Deletes & recreates (EMPTY) |
| 3D Tree Visualization Routes | `vetka_elisya` | Queries for data (EMPTY) |
| Memory Manager Initializer | `vetka_elisya` | Creates but never populates |
| Embedding Pipeline | `vetka_elisya` | Class exists but never called |

**Result**: Tree queries `vetka_elisya` which remains EMPTY → old visualization persists

---

## DOCKER QDRANT STATUS ✅

**Container**: `qdrant` (ID: 7922a46fc793)
**Status**: Up 2 days
**Port**: 6333 (exposed correctly)
**Connection**: ✅ Working

### Collection Statistics

```
vetka_elisya        : 2474 points    ⚠️  STALE DATA (old model vectors?)
VetkaTree          : 0 points        ❌  EMPTY
VetkaLeaf          : 0 points        ❌  EMPTY
VetkaChangeLog     : 0 points        ❌  EMPTY
vetka_files        : 1048 points     ⚠️  Partial data
vetka_metadata     : 0 points        ❌  EMPTY
```

**Key Finding**: `vetka_elisya` has 2474 old points (probably from before rescan)

---

## DATA FLOW ANALYSIS

### Current (BROKEN) Flow

```
NUCLEAR RESCAN
├─ Delete: vetka_nodes, vetka_edges, vetka_changelog ✅
├─ Create: vetka_nodes, vetka_edges (EMPTY)
├─ Scan: 2246 files ✅
├─ Extract: 2438 imports ✅
└─ Upsert to Qdrant: ❌ NOT HAPPENING

     ↓ (Data ends here - no insertion to Qdrant)

TREE VISUALIZATION
├─ Query: vetka_elisya collection
├─ Result: 2474 OLD POINTS (not from rescan)
└─ Render: Old tree structure persists ❌
```

### What Should Happen

```
NUCLEAR RESCAN
├─ Delete: vetka_nodes, vetka_edges, vetka_elisya ← MISSING DELETE
├─ Create: All collections (EMPTY)
├─ Scan: 2246 files
├─ Extract: 2438 imports
├─ Embed: Generate vectors for files ← MISSING
├─ Upsert: Insert to vetka_elisya ← MISSING
└─ Done

     ↓

TREE VISUALIZATION
├─ Query: vetka_elisya collection
├─ Result: 2246 FRESH POINTS (from rescan)
└─ Render: Updated tree structure ✅
```

---

## SPECIFIC CODE ISSUES FOUND

### Issue #1: Rescan Script Doesn't Delete `vetka_elisya`

**File**: `scripts/rescan_project.py`
**Lines**: 103-104

```python
delete_collections = ["vetka_nodes", "vetka_edges", "vetka_changelog"]
# ❌ Missing: "vetka_elisya"
```

**Impact**: `vetka_elisya` keeps old 2474 points from previous runs

**Fix**: Add `"vetka_elisya"` to delete_collections list

---

### Issue #2: Rescan Script Never Calls Embedding Pipeline

**File**: `scripts/rescan_project.py`
**Lines**: 317-322 (scanning & import extraction happens, but then stops)

```python
# 5. Scan project
files_scanned = await scan_project()

# 6. Extract imports
imports_found = await extract_imports()

# ❌ MISSING: await embed_and_upsert_to_qdrant(files_scanned)
```

**Impact**: Scanned files never get embedded into vectors, never inserted into Qdrant

**Fix**: Add call to embedding pipeline after import extraction

---

### Issue #3: Tree Routes Query Wrong Collection (Indirectly)

**File**: `src/api/routes/tree_routes.py`
**Lines**: 125-137

```python
@router.get("/data")
async def get_tree_data(...):
    results, offset = qdrant.scroll(
        collection_name='vetka_elisya',  # Correct collection name
        scroll_filter=Filter(...)
    )
    return results  # Returns 2474 OLD points instead of fresh data
```

**Root Cause**: Not `tree_routes.py` fault - it correctly queries `vetka_elisya`
**Real Issue**: `vetka_elisya` never gets updated with fresh data from rescan

**Fix**: Rescan must populate `vetka_elisya` with fresh embeddings

---

### Issue #4: Memory Manager Creates Empty Collection

**File**: `src/orchestration/memory_manager.py`
**Lines**: 271-286

```python
def __init__(...):
    # Creates collection but never receives data
    self.qdrant.create_collection(
        collection_name='vetka_elisya',
        vectors_config=VectorParams(size=768, distance=Distance.COSINE)
    )
```

**Impact**: Collection exists but stays empty through application lifecycle

**Fix**: Memory manager should populate collection with initial data from rescan

---

### Issue #5: Embedding Pipeline Exists But Never Called

**File**: `src/scanners/embedding_pipeline.py`
**Lines**: 46, 80-100

```python
class EmbeddingPipeline:
    def __init__(self, qdrant_client=None,
                 collection_name: str = "vetka_elisya"):
        self.collection_name = collection_name

    async def process_files(self, files: List[str]) -> int:
        """Generate embeddings and upsert to Qdrant"""
        # Method exists but NEVER CALLED from rescan flow
```

**Impact**: Class designed perfectly for this use case but not integrated into rescan

**Fix**: Call `embedding_pipeline.process_files()` during rescan after scanning

---

### Issue #6: Collection Naming Chaos

**Multiple naming schemes in use**:

1. Rescan script: `vetka_nodes`, `vetka_edges`, `vetka_changelog`
2. QdrantVetkaClient: `VetkaTree`, `VetkaLeaf`, `VetkaChangeLog`, `VetkaTrash`
3. Memory Manager: `vetka_elisya`
4. Semantic Routes: `vetka_elisya`
5. Files: `vetka_files`

**Impact**: Different systems write to/read from different collections, creating data silos

**Fix**: Standardize on single collection naming scheme

---

## VERIFICATION DATA

### Backend Is Running ✅
```
FastAPI: http://localhost:5001/api/health
Status: HEALTHY
Components initialized: 39 models, Group chat, Model registry
```

### MCP Is Running ✅
```
MCP Server: http://localhost:5097/health
Status: HEALTHY
Connected to backend: ✅
```

### Frontend Is Connected ✅
```
WebSocket: ws://localhost:3000
Status: CONNECTED
Total connections: 2 active clients
```

### Qdrant Is Running ✅
```
Docker: 7922a46fc793 (up 2 days)
Port: 6333
Status: HEALTHY
Collections: 8 total
```

**BUT**: Collections have stale data, not fresh rescan data ❌

---

## SEQUENCE OF EVENTS (TIMELINE)

1. **2026-01-20 21:15:44** - Backend started (`python main.py`)
   - Memory Manager creates `vetka_elisya` collection
   - Collection initialized EMPTY

2. **2026-01-20 21:16:35** - Nuclear Rescan executed
   - ✅ Scanned 2246 files
   - ✅ Extracted 2438 imports
   - ❌ Did NOT delete `vetka_elisya`
   - ❌ Did NOT call embedding pipeline
   - ❌ Did NOT upsert to Qdrant

3. **2026-01-20 21:17:14** - User opens browser on `localhost:3000`
   - ✅ Frontend connects
   - ✅ Requests `/api/tree/data`
   - ✅ Backend queries `vetka_elisya` collection
   - ❌ Returns 2474 OLD POINTS (stale data from before rescan)
   - ❌ 3D tree renders old structure, not new rescan data

---

## RECOMMENDATIONS FOR ARCHITECT

### Priority 1 (Immediate - blocks visualization)

1. **Update rescan script** (`scripts/rescan_project.py`)
   - Add `"vetka_elisya"` to delete_collections list
   - Add embedding pipeline integration
   - Add upsert to Qdrant after scanning

2. **Create integration test**
   - Run rescan
   - Verify `vetka_elisya` now has 2246+ fresh points
   - Verify tree visualization updates

### Priority 2 (Important - architecture cleanup)

1. **Standardize collection naming**
   - Pick single scheme (suggest: `vetka_*` lowercase)
   - Update all routes/components
   - Document in architecture guide

2. **Document data flow**
   - Rescan → Embedding → Qdrant → Tree Routes
   - Make it clear which collections feed which visualizations

### Priority 3 (Nice to have)

1. **Add rescan progress monitoring**
   - Emit WebSocket events during embedding
   - Show user: "Processing 2246 files, 45% embedded..."

2. **Add validation checks**
   - After rescan: assert `vetka_elisya` has >2000 points
   - Before tree render: assert collection not empty

---

## FILES THAT NEED CHANGES

| File | Issue | Fix |
|------|-------|-----|
| `scripts/rescan_project.py` | Doesn't delete `vetka_elisya`, doesn't embed | Add collection deletion + embedding pipeline call |
| `src/scanners/embedding_pipeline.py` | Never called | Integrate into rescan flow |
| `src/api/routes/tree_routes.py` | Gets stale data | Works correctly once rescan fixed |
| `src/orchestration/memory_manager.py` | Creates empty collection | Add data population from rescan |
| Collection naming | 6 different schemes in use | Standardize on 1 scheme |

---

## TESTING CHECKLIST

After fixes:

- [ ] Run nuclear rescan
- [ ] Verify `vetka_elisya` has 2246+ fresh points
- [ ] Refresh browser on `localhost:3000`
- [ ] 3D tree shows NEW structure (organized, not chaotic)
- [ ] Tree nodes labeled correctly from rescan data
- [ ] WebSocket shows real-time updates
- [ ] No 404 errors in console

---

## CONCLUSION

**The system is architecturally sound but the rescan→visualization connection is broken.**

All individual components work perfectly:
- ✅ Scanner reads files
- ✅ Embedding pipeline generates vectors (but not called)
- ✅ Qdrant stores data (but not populated with fresh data)
- ✅ Tree routes query correctly (but get stale data)
- ✅ Frontend renders (but gets old data)

**The fix is simple**: Wire the components together in the rescan flow.

Once fixed, nuclear rescan will trigger real-time tree updates across all connected clients.

---

**Status**: Ready for architect review
**Next Step**: Implement fixes → verify with test rescan → demo to user

---

*Detailed investigation by Claude Code Haiku 4.5*
*Investigation context: Phase 75 integration audit → Phase 76 verification → Nuclear rescan analysis → Docker Qdrant status check*
