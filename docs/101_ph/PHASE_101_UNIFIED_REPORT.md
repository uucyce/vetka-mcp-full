# Phase 101.2 - Unified Investigation Report

**Date:** 2025-01-29
**Methodology:** 9 Haiku Scouts → 3 Sonnet Verifiers → Consolidated Report
**Status:** ✅ ALL VERIFIED

---

## Executive Summary

Investigation confirmed **3 root causes** for VetkaTree/Artifact issues:

| # | Issue | Verified By | Fix Priority |
|---|-------|-------------|--------------|
| 1 | Dual Qdrant clients - files go to `vetka_elisya`, VetkaTree empty | S1 ✅ | P0 CRITICAL |
| 2 | Missing `parent_folder` and `depth` in qdrant_updater.py payload | S2 ✅ | P1 HIGH |
| 3 | TreeStructureTool counts `"file"` instead of `"leaf"` → Files=0 | S3 ✅ | P0 CRITICAL |

---

## Verified Findings

### Finding 1: Dual Qdrant Client Architecture (S1 VERIFIED)

**Evidence:**
- `TripleWriteManager` (line 453) → writes to `vetka_elisya`
- `QdrantVetkaClient.triple_write()` (line 254) → writes to `VetkaTree`
- **Nobody calls** QdrantVetkaClient for file indexing

**Result:** VetkaTree has 0 points, vetka_elisya has 1760 points

**Fix Location:** `src/orchestration/triple_write_manager.py` line 318

```python
# FIX_101.3: Also write to VetkaTree for hierarchy
from src.memory.qdrant_client import get_qdrant_client
vetka_client = get_qdrant_client()
if vetka_client:
    vetka_client.triple_write(
        workflow_id=f"scan_{file_id}",
        node_id=file_id,
        path=file_path,
        content=content[:500],
        metadata={'type': 'scanned_file', 'parent_id': parent_id},
        vector=embedding
    )
```

---

### Finding 2: Missing Hierarchy Fields (S2 VERIFIED)

**Evidence:**
- `qdrant_updater.py` payload has: path, name, extension, size, modified_time
- `embedding_pipeline.py` payload has: **parent_folder, depth** (which qdrant_updater lacks)
- `tree_routes.py` expects `parent_folder` to build hierarchy

**Current payload (qdrant_updater.py:362):**
```python
metadata = {
    'type': 'scanned_file',
    'path': str(file_path),
    'name': file_path.name,
    # ❌ MISSING: parent_folder, depth
}
```

**Fix Location:** `src/scanners/qdrant_updater.py` line 362

```python
# FIX_101.4: Add hierarchy fields
parent_folder = str(file_path.parent)
depth = len(file_path.parts) - 1

metadata = {
    ...existing fields...,
    'parent_folder': parent_folder,  # NEW
    'depth': depth,                   # NEW
}
```

---

### Finding 3: TreeStructureTool Type Mismatch (S3 VERIFIED)

**Evidence:**
- API returns files with `type: "leaf"`
- TreeStructureTool searches for `type: "file"` → finds 0
- TreeStructureTool searches for `type: "branch"` → finds 312 folders ✅

**Bug Location:** `src/bridge/shared_tools.py` line 331

```python
# CURRENT (BUG):
file_count = sum(1 for n in nodes if n.get("type") == "file")  # ❌

# FIX_101.5:
file_count = sum(1 for n in nodes if n.get("type") == "leaf")  # ✅
```

---

## Architecture Diagram

```
CURRENT STATE (BROKEN):
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│ file_watcher│────▶│ qdrant_updater   │────▶│ vetka_elisya │ (1760 pts)
└─────────────┘     └──────────────────┘     └──────────────┘
                                                    │
                    ┌──────────────────┐            │
                    │ triple_write_mgr │────────────┘
                    └──────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  VetkaTree   │ (0 pts) ❌ NOT WRITTEN
                    └──────────────┘

FIXED STATE:
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│ file_watcher│────▶│ qdrant_updater   │────▶│ vetka_elisya │
└─────────────┘     │ + parent_folder  │     └──────────────┘
                    │ + depth          │            │
                    └──────────────────┘            │
                           │                        │
                           ▼                        │
                    ┌──────────────────┐            │
                    │ triple_write_mgr │────────────┘
                    └──────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  VetkaTree   │ ✅ NOW WRITTEN
                    └──────────────┘
```

---

## Action Plan (Priority Order)

### P0 - Critical (Do Now)

| # | Fix | File | Line | Time |
|---|-----|------|------|------|
| 1 | Change `"file"` to `"leaf"` in TreeStructureTool | shared_tools.py | 331 | 2 min |
| 2 | Add VetkaTree write in TripleWriteManager | triple_write_manager.py | 318 | 10 min |
| 3 | Backfill VetkaTree from vetka_elisya | one-time script | - | 5 min |

### P1 - High (Do Today)

| # | Fix | File | Line | Time |
|---|-----|------|------|------|
| 4 | Add parent_folder, depth to qdrant_updater | qdrant_updater.py | 362 | 5 min |
| 5 | Rebuild HNSW index after VetkaTree population | Qdrant API | - | 2 min |

### P2 - Medium (Later)

| # | Fix | Description |
|---|-----|-------------|
| 6 | Unify metadata creation | Extract to shared function |
| 7 | Add Qdrant source option to /api/tree/data | `?source=vetka_tree` param |
| 8 | Add unit tests for tree counts | tests/test_tree_routes.py |

---

## Verification Checklist

After applying fixes:

- [ ] `curl localhost:6333/collections/VetkaTree` → points_count > 0
- [ ] `curl localhost:5001/api/tree/data` → total_files > 0
- [ ] MCP `vetka_search_semantic "Phase 100"` → returns results with hierarchy
- [ ] UI tree shows files, not just folders

---

## Scout Report Summary

| Scout | Area | Key Finding | Status |
|-------|------|-------------|--------|
| H1 | Triple Write | No VetkaTree write in write_file() | ✅ S1 Verified |
| H2 | File Watcher | No VetkaTree hook on events | ✅ Noted |
| H3 | Qdrant Updater | Missing parent_id field | ✅ S2 Verified |
| H4 | UI Artifacts | Depends on search endpoint | ✅ Noted |
| H5 | Response Formatter | FIX_101.2 already applied | ✅ Done |
| H6 | Weaviate Schema | Schema exists, not used | ✅ Noted |
| H7 | Tree Routes | Uses vetka_elisya, not VetkaTree | ✅ S3 Verified |
| H8 | Embedding Pipeline | Has parent_folder (qdrant_updater missing) | ✅ S2 Verified |
| H9 | Hybrid Search | VetkaTree mapped but empty | ✅ Noted |

---

*Report by Claude Opus 4.5 with Haiku/Sonnet Squadron*
*Phase 101.2 - VETKA AI Project*
