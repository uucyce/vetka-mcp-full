# HAIKU RECON 01: All Qdrant Write Points

**Agent:** Haiku
**Date:** 2026-01-28
**Task:** Find ALL locations where data is written to Qdrant

---

## QDRANT WRITE OPERATIONS AUDIT

| # | File | Line | Function/Method | Collection | Direct Qdrant | Through TripleWrite | Markers |
|---|------|------|-----------------|------------|---|---|---|
| 1 | src/mcp/state/mcp_state_manager.py | 132 | `save_state()` | (dynamic) | YES | NO | None |
| 2 | src/orchestration/memory_manager.py | 433 | `save_entry()` | `vetka_elisya` | YES | NO | PATCH #1 |
| 3 | src/orchestration/triple_write_manager.py | 446 | `_write_qdrant_internal()` | `vetka_files` | YES | YES (core) | FIX_95.8 |
| 4 | src/orchestration/orchestrator_with_elisya.py | 372 | `_save_workflow_counter()` | `vetka_metadata` | YES | NO | Phase76.1 |
| 5 | src/memory/qdrant_client.py | 248 | `upsert_tree_node()` | `tree` | YES | NO | None |
| 6 | src/memory/qdrant_client.py | 660 | `upsert()` (wrapper) | (any) | YES | Depends | Wrapper |
| 7 | src/memory/replay_buffer.py | 211 | `add()` | `replay_buffer_examples` | YES | NO | LoRA |
| 8 | src/memory/trash.py | 230 | `move_to_trash()` | `vetka_trash` | YES | NO | Soft delete |
| 9 | src/api/routes/knowledge_routes.py | 415 | `create_branch()` | `vetka_elisya` | YES | NO | None |
| 10 | src/memory/engram_user_memory.py | 338 | `_qdrant_upsert()` | `engram_user_preferences` | YES | NO | User prefs |
| 11 | src/scanners/embedding_pipeline.py | 432 | `process_files()` | `vetka_elisya` | YES | NO | Phase 92 |
| 12 | src/scanners/qdrant_updater.py | 391 | `update_file()` | `vetka_elisya` | YES | NO | MARKER_COHERENCE_BYPASS_004 |
| 13 | src/scanners/qdrant_updater.py | 496 | `batch_update()` | `vetka_elisya` | YES | NO | MARKER_COHERENCE_BYPASS_005 |
| 14 | src/api/routes/watcher_routes.py | 464 | `index_browser_files()` | `vetka_elisya` | YES | NO | MARKER_COHERENCE_BYPASS_002 |
| 15 | src/api/routes/watcher_routes.py | 639 | `index_file()` | `vetka_elisya` | YES | NO | MARKER_COHERENCE_BYPASS_003 |

---

## KEY FINDINGS

### TripleWrite Integration Status

**1 location uses TripleWriteManager (correct):**
- `triple_write_manager.py:446` - Core vetka_files collection

**14 locations bypass TripleWrite (direct Qdrant writes):**
- All other collections use direct `.upsert()` calls
- **5 locations** have explicit TODO markers for COHERENCE_BYPASS fixes

### Collections & Write Patterns

| Collection | Write Locations | Through TW | Direct | Status |
|-----------|---|---|---|---|
| `vetka_files` | 1 | 1 | 0 | ✅ Correct |
| `vetka_elisya` | 7 | 0 | 7 | ❌ All direct |
| `vetka_metadata` | 1 | 0 | 1 | ⚠️ Workflow counter |
| `tree` | 1 | 0 | 1 | ❌ Direct |
| `replay_buffer_examples` | 1 | 0 | 1 | ❌ Direct (LoRA) |
| `vetka_trash` | 1 | 0 | 1 | ❌ Direct |
| `engram_user_preferences` | 1 | 0 | 1 | ❌ Direct |

### Non-blocking Operations
- `src/scanners/embedding_pipeline.py:432` - `wait=False`
- `src/scanners/qdrant_updater.py:391` - `wait=False`
- `src/scanners/qdrant_updater.py:496` - `wait=False`

---

## COHERENCE BYPASS MARKERS

```
MARKER_COHERENCE_BYPASS_002 - Browser files bypass TripleWrite
  Location: src/api/routes/watcher_routes.py:464
  Fix: Use tw.write_file() with virtual_path and browser metadata

MARKER_COHERENCE_BYPASS_003 - Drag-drop files bypass TripleWrite
  Location: src/api/routes/watcher_routes.py:639
  Fix: Use get_triple_write_manager().write_file() instead

MARKER_COHERENCE_BYPASS_004 - Single file upsert bypasses Weaviate/Changelog
  Location: src/scanners/qdrant_updater.py:391
  Fix: Ensure TW is enabled via use_triple_write(enable=True)

MARKER_COHERENCE_BYPASS_005 - Batch upsert bypasses Weaviate/Changelog
  Location: src/scanners/qdrant_updater.py:496
  Fix: Implement tw.batch_write(files) or loop tw.write_file()
```

---

## RECOMMENDATIONS

1. Route all file operations through TripleWriteManager
2. Add `use_triple_write(enable=True)` to QdrantUpdater initialization
3. Implement batch_write() method in TripleWriteManager
4. Consider separate TripleWrite for non-file collections (user prefs, metadata)
