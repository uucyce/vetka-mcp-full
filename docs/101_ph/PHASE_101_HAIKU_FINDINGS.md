# Phase 101.2 - Haiku Scout Findings Report

**Date:** 2025-01-29
**Mission:** VetkaTree Gap Analysis & Artifact Rendering Investigation

---

## Executive Summary

9 Haiku scouts investigated the VetkaTree indexing gap and artifact rendering issues. Key finding: **Two separate Qdrant writing systems exist that don't communicate**.

---

## Critical Findings

### 1. Dual Qdrant Client Architecture (ROOT CAUSE)

| Component | Collection | Used By | Status |
|-----------|------------|---------|--------|
| `QdrantVetkaClient` (qdrant_client.py) | **VetkaTree** | Unused for files | Points: 0 |
| `TripleWriteManager` (triple_write_manager.py) | **vetka_elisya** | Active | Points: 1760 |

**Problem:** Files are indexed to `vetka_elisya` but UI/Tree expects `VetkaTree`.

### 2. Triple Write Manager Analysis (H1)

**File:** `src/orchestration/triple_write_manager.py`

- **Line 453:** Writes to `vetka_elisya` collection (not VetkaTree!)
- **Line 296-318:** `write_file()` method writes to Weaviate VetkaLeaf + Qdrant vetka_elisya
- **Missing:** No integration with `QdrantVetkaClient.triple_write()` which targets VetkaTree
- **Gap:** No `parent_id` or hierarchy fields in payload

**Recommendation:** Add VetkaTree upsert after line 318:
```python
# After Qdrant write, also write to VetkaTree for hierarchy
from src.memory.qdrant_client import get_qdrant_client
vetka_client = get_qdrant_client()
if vetka_client:
    vetka_client.triple_write(
        workflow_id=f"scan_{file_id}",
        node_id=file_id,
        path=file_path,
        content=content[:500],
        metadata={'type': 'file', 'parent': os.path.dirname(file_path)},
        vector=embedding
    )
```

### 3. File Watcher Integration (H2)

**File:** `src/scanners/file_watcher.py`

- **Lines 49-52:** SKIP_PATTERNS includes venv (FIX_101.1 applied)
- **Line 143-147:** `_should_skip()` checks patterns
- **Gap:** No direct call to VetkaTree indexing on file events
- **Events:** Handles created/modified/deleted but only updates `qdrant_updater`

**Recommendation:** Add hook in `on_created()` and `on_modified()`:
```python
# After qdrant_updater.update_file()
self._update_vetka_tree_hierarchy(file_path)
```

### 4. Qdrant Updater Hierarchy (H3)

**File:** `src/scanners/qdrant_updater.py`

- **Line 393:** Generates UUID via `uuid.uuid5(uuid.NAMESPACE_URL, file_path)`
- **Line 443-449:** Payload includes `file_path, file_name, file_type, depth`
- **Line 693:** skip_dirs updated with `venv_mcp, site-packages` (FIX_101.1)
- **Missing:** `parent_id` field for tree hierarchy
- **Missing:** VetkaTree collection write

**Current Payload Fields:**
```python
payload = {
    'file_path': file_path,
    'file_name': file_name,
    'file_type': file_type,
    'depth': depth,
    'type': 'scanned_file',
    'source': 'incremental_updater'
}
```

**Recommended Addition:**
```python
payload['parent_path'] = os.path.dirname(file_path)
payload['parent_id'] = uuid.uuid5(uuid.NAMESPACE_URL, parent_path)
```

### 5. UI Artifacts Rendering (H4)

**Files:** `client/src/components/MessageBubble.tsx`, `UnifiedSearchBar.tsx`

- Search results come from `/api/search/semantic` endpoint
- Artifacts rendered based on `files` array in response
- No fallback if semantic search returns empty
- `pinned_files` from viewport affect rendering priority

**Gap:** UI expects consistent data format but backend returns different structures

### 6. Response Formatter (H5)

**File:** `src/mcp/vetka_mcp_bridge.py`

- **Line 1264:** `format_result()` looked for `results` key
- **FIX_101.2 Applied:** Now checks `files` first, then `results`
- Semantic search now returns proper format

### 7. Weaviate Schema (H6)

**File:** `src/memory/create_collections.py`

- VetkaTree schema exists in Weaviate (line 21)
- Properties: content, path, timestamp, creator, node_type, agent_role, metadata
- **Gap:** Schema doesn't include `parent` or `children` for hierarchy
- VetkaLeaf is primary target for file writes

### 8. Tree Routes API (H7)

**File:** `src/api/routes/tree_routes.py` (or knowledge_routes.py)

- `/api/tree/data` returns tree from **memory** not Qdrant
- Tree built from file system scan, not database
- **Why Files=0:** Tree nodes marked as "branch/folder" not "file"
- Qdrant VetkaTree collection has 0 points (not populated)

### 9. Hybrid Search RRF (H9)

**File:** `src/search/hybrid_search.py`

- Line 468: Maps "tree" to "vetka_tree" collection
- Hybrid search combines Qdrant semantic + Weaviate BM25
- **Issue:** VetkaTree empty, so tree searches return nothing
- RRF properly implemented but no data to fuse

---

## Architecture Diagram

```
Current Flow (BROKEN):
FileWatcher → QdrantUpdater → vetka_elisya ✅
                           → VetkaTree ❌ (not written)

Expected Flow (FIXED):
FileWatcher → QdrantUpdater → vetka_elisya ✅
           → TripleWriteManager → VetkaLeaf (Weaviate) ✅
                               → VetkaTree (Qdrant) ✅ NEW
```

---

## Action Items (Priority Order)

### P0: Critical (Blocks Search)
1. **Add VetkaTree write** in `triple_write_manager.py` after vetka_elisya write
2. **Backfill VetkaTree** with existing 1760 files from vetka_elisya

### P1: High (Improves UX)
3. **Add parent_id** to payload in qdrant_updater.py for hierarchy
4. **Update tree_routes.py** to pull from Qdrant instead of memory

### P2: Medium (Polish)
5. **Add fallback** in UI for empty search results
6. **Sync Weaviate schema** to include parent/children fields

---

## Verification Checklist (For Sonnet Phase)

- [ ] Verify VetkaTree collection creation in Qdrant
- [ ] Verify triple_write() is called for file indexing
- [ ] Verify parent_id generation is deterministic (UUID5)
- [ ] Verify UI receives artifacts from search endpoint
- [ ] Verify HNSW index rebuilt after VetkaTree population

---

*Report generated by Haiku Scout Squadron + Claude Opus Coordinator*
*Phase 101.2 - VETKA AI Project*
