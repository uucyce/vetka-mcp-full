# HAIKU RECON 04: File Watcher Data Flow

**Agent:** Haiku
**Date:** 2026-01-28
**Task:** Trace complete data flow from file detection to database

---

## THREE DATA PATHWAYS

### PATHWAY 1: File Watcher (Real-time)
```
Watchdog event → file_watcher.py → qdrant_updater.py → Qdrant ONLY
```

### PATHWAY 2: Directory Scan (Initial Index)
```
Add directory → watcher_routes.py → scan_directory() → Qdrant ONLY
```

### PATHWAY 3: Embedding Pipeline (Full Semantic)
```
LocalScanner → embedding_pipeline.py → TripleWriteManager → ALL THREE STORES
```

---

## PATHWAY 1: FILE WATCHER DETAIL

### Stage 1: File Detection
**File:** `src/scanners/file_watcher.py`
**Handler:** VetkaFileHandler (debounced 400ms)

```
Watchdog detects: FileSystemEvent
    ↓
Filter by:
  - Skip directories
  - SKIP_PATTERNS (git, node_modules, __pycache__, .venv, changelog)
  - SUPPORTED_EXTENSIONS (.py, .js, .ts, .tsx, .json, .yaml, .md)
    ↓
Coalesce events (debounce 400ms)
    ↓
Bulk detection (>10 events = bulk_update)
```

### Stage 2: Qdrant Client Acquisition
**MARKER_90.7** - Multi-source fallback:
1. `get_qdrant_manager()` → manager.client
2. `get_memory_manager()` → memory_manager.qdrant_client (preferred)
3. `get_qdrant_client()` singleton

**If unavailable:** Non-blocking retry via `threading.Timer` (2s, 4s, 8s)

### Stage 3: Event Handler
**File:** `src/scanners/qdrant_updater.py:766`

```python
handle_watcher_event(event, enable_triple_write=True)
  ├─ 'created' → updater.update_file(file_path)
  ├─ 'modified' → updater.update_file(file_path)
  ├─ 'deleted' → updater.soft_delete(file_path)
  └─ 'bulk_update' → logger.info() [placeholder]
```

### Stage 4: Update File
**File:** `src/scanners/qdrant_updater.py:311`

```
update_file(file_path)
    ├─ Check file exists (if deleted → soft_delete)
    ├─ _file_changed() → hash-based change detection
    ├─ If changed:
    │   ├─ _read_file_content()
    │   ├─ _get_embedding() → Ollama embeddinggemma:300m
    │   ├─ Prepare metadata
    │   ├─ MARKER_TW_DECISION: If use_triple_write enabled:
    │   │   └─ _write_via_triple_write() [DISABLED BY DEFAULT]
    │   └─ Direct Qdrant upsert [ACTUAL PATH]
    └─ If unchanged: skip
```

### Stage 5: Metadata Collected (Directory Mode)

```python
metadata = {
    'type': 'scanned_file',
    'source': 'incremental_updater',
    'path': str(file_path),
    'name': file_path.name,
    'extension': file_path.suffix.lower(),
    'size_bytes': stat.st_size,          # Directory mode
    'modified_time': stat.st_mtime,      # Directory mode
    'content_hash': sha256_hash,
    'content': content[:500],            # Preview only
    'updated_at': time.time(),
    'deleted': False
}
```

**NO Knowledge/CAM fields collected at watcher stage!**

---

## TRIPLEWRITE PARADOX

**In function signature:**
```python
handle_watcher_event(event, enable_triple_write=True)  # Default True
```

**But in actual call:**
```python
handle_watcher_event(event, qdrant_client=qdrant_client)  # No enable param!
```

**And in updater:**
```python
self._use_triple_write = False  # Internal state still False!
```

**Result:** TripleWrite code path NOT executed in practice.

---

## COHERENCE BYPASS MARKERS (5 Found)

| Marker | File | Line | Issue |
|--------|------|------|-------|
| MARKER_COHERENCE_ROOT_001 | qdrant_updater.py | 53 | Class writes directly to Qdrant only |
| MARKER_COHERENCE_BYPASS_001 | watcher_routes.py | 160 | Directory scan uses QdrantUpdater |
| MARKER_COHERENCE_BYPASS_002 | watcher_routes.py | 460 | Browser files bypass TripleWrite |
| MARKER_COHERENCE_BYPASS_003 | watcher_routes.py | 634 | Drag-drop bypasses TripleWrite |
| MARKER_COHERENCE_BYPASS_004 | qdrant_updater.py | 387 | Single file upsert bypasses |
| MARKER_COHERENCE_BYPASS_005 | qdrant_updater.py | 493 | Batch upsert bypasses |

---

## DIRECTORY MODE vs KNOWLEDGE MODE

### Directory Mode (Collected by Watcher)
- path, name, extension
- size_bytes (from file stat)
- modified_time, created_time
- content_hash (SHA256)
- content (preview 500 chars)
- parent_folder, depth

### Knowledge Mode (NOT collected by Watcher)
Only in embedding_pipeline with OCR:
- ocr_source, ocr_confidence
- ocr_pages, has_tables, has_formulas
- image_description (Vision model semantic output)
- processing_time_ms, vision_model

### CAM Fields (NOT collected anywhere currently)
- No CAM metadata at index time
- No semantic enrichment
- No knowledge graph connections

---

## FLOW SUMMARY DIAGRAM

```
FILE SYSTEM EVENT
       │
       ▼
┌──────────────────┐
│  VetkaFileHandler│ (debounced 400ms, filtered)
│  file_watcher.py │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     Retry (2s, 4s, 8s)
│ Get Qdrant Client│◄──────────────┐
│  (3 fallbacks)   │               │
└────────┬─────────┘               │
         │                         │
         ▼                         │
┌──────────────────┐               │
│handle_watcher_   │               │
│event()           │───── fail ────┘
│qdrant_updater.py │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ update_file()    │
│ - hash check     │
│ - embedding      │
│ - metadata       │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
[TW Path]  [Direct Path] ◄── ACTUAL
(disabled)  (enabled)
    │         │
    ▼         ▼
3 stores   Qdrant ONLY
           vetka_elisya
              │
              ▼
┌──────────────────┐
│ Socket.IO emit   │
│ node_added/etc   │
└──────────────────┘
              │
              ▼
         Frontend
         tree refresh
```

---

## KEY INSIGHTS

1. **TripleWrite Paradox**: Enabled in embedding_pipeline, disabled in watcher paths
2. **Change Detection**: Hash-based (_file_changed), efficient for incremental
3. **Non-blocking**: All Qdrant upserts use `wait=False`
4. **Retry Logic**: Exponential backoff (2s, 4s, 8s) for missing Qdrant
5. **Directory vs Knowledge**: Only OCR adds semantic fields
6. **Socket.IO**: Updates frontend after indexing (MARKER_90.11)
