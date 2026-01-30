# HAIKU RECON 02: All Weaviate Write Points

**Agent:** Haiku
**Date:** 2026-01-28
**Task:** Find ALL locations where data is written to Weaviate

---

## WEAVIATE WRITE OPERATIONS AUDIT

| File | Line | Function/Method | Write Method | Through TripleWrite | Markers |
|------|------|-----------------|--------------|---------------------|---------|
| src/orchestration/triple_write_manager.py | 384 | `_write_weaviate_internal()` | `.data_object.create()` | YES (core) | MARKER_TW_004 |
| src/orchestration/triple_write_manager.py | 372 | `_write_weaviate_internal()` | `.data_object.update()` | YES (core) | MARKER_TW_004 |
| src/orchestration/triple_write_manager.py | 569 | `clear_weaviate_eval_data()` | `.data_object.delete()` | YES (cleanup) | MARKER_TW_007 |
| src/scanners/embedding_pipeline.py | 370 | `_process_single()` | `tw.write_file()` | YES (indirect) | MARKER_TW_011 |
| src/scanners/qdrant_updater.py | 174 | `_write_via_triple_write()` | `tw.write_file()` | YES (when enabled) | MARKER_COHERENCE_BYPASS_004 |
| src/scanners/qdrant_updater.py | 391 | `update_file()` | direct Qdrant (NO Weaviate) | NO (fallback) | MARKER_COHERENCE_BYPASS_004 |
| src/scanners/qdrant_updater.py | 496 | `batch_update()` | direct Qdrant (NO Weaviate) | NO (fallback) | MARKER_COHERENCE_BYPASS_005 |
| src/memory/weaviate_helper.py | 89 | `upsert_node()` | `requests.post()` v1 REST | NO | MARKER_ARCH_001 |
| src/memory/vetka_weaviate_helper.py | 46 | `insert_object()` | `requests.post()` | NO | - |
| src/memory/vetka_weaviate_helper.py | 64 | `batch_insert()` | `requests.post()` batch | NO | - |
| src/memory/vetka_weaviate_helper.py | 81 | `update_object()` | `requests.patch()` | NO | - |
| scripts/sync_qdrant_to_weaviate.py | 317 | `sync_batch()` | v4 SDK `.data.insert_many()` | NO (standalone) | - |

---

## CRITICAL FINDINGS

### 1. THREE DIFFERENT WEAVIATE IMPLEMENTATIONS

| Implementation | Location | API Version | Used By |
|----------------|----------|-------------|---------|
| TripleWriteManager | triple_write_manager.py | v3 REST | Core indexing |
| WeaviateHelper | weaviate_helper.py | v1 REST | Legacy/hybrid search |
| VetkaWeaviateHelper | vetka_weaviate_helper.py | v4 SDK | Standalone sync |

**Marker:** `MARKER_ARCH_001_WEAVIATE_DUPLICATE` - needs consolidation

### 2. PATHS WITHOUT COHERENCE (not through TripleWrite)

| Path | File | Function | Problem |
|------|------|----------|---------|
| Direct Qdrant (single) | qdrant_updater.py:391 | `update_file()` | Skips Weaviate/Changelog |
| Direct Qdrant (batch) | qdrant_updater.py:496 | `batch_update()` | Skips Weaviate/Changelog |
| REST v1 | weaviate_helper.py:89 | `upsert_node()` | Not synced with Qdrant |
| v4 SDK batch | sync_qdrant_to_weaviate.py:317 | `sync_batch()` | Standalone, outside main flow |

### 3. WEAVIATE API VERSIONS IN USE

- **v3 (REST, old)**: used in TripleWriteManager
- **v1 (REST, legacy)**: used in WeaviateHelper
- **v4 (SDK, new)**: used in sync_qdrant_to_weaviate.py

---

## WRITE PATHS GROUPING

**VIA TripleWriteManager (GOOD):**
- embedding_pipeline.py → write_file()
- triple_write_routes.py → reindex/cleanup
- qdrant_updater.py → update_file() when enable_triple_write=True

**DIRECT QDRANT (BAD - no Weaviate sync):**
- qdrant_updater.py → update_file() when enable_triple_write=False (default!)
- qdrant_updater.py → batch_update()

**REST API (LEGACY):**
- weaviate_helper.py → upsert_node()
- vetka_weaviate_helper.py → insert/update/delete

**v4 SDK (STANDALONE):**
- sync_qdrant_to_weaviate.py → sync_batch()

---

## RECOMMENDATIONS

1. **Enable TripleWrite by default** in `qdrant_updater.py:730` (currently `enable_triple_write=False`)
2. **Consolidate** 3 Weaviate implementations into one (remove duplication)
3. **Update** `batch_update()` to work with TripleWrite instead of direct Qdrant upserts
4. **Upgrade** TripleWriteManager to v4 SDK API
