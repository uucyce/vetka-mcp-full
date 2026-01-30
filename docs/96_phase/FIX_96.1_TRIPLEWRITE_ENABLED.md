# FIX_96.1: TripleWrite Enabled by Default

**Date:** 2026-01-28
**Author:** Claude Opus 4.5
**Status:** IMPLEMENTED

---

## Summary

Changed TripleWrite from opt-in to opt-out. All file indexing operations now write to **three stores** by default:
- Qdrant (vector search)
- Weaviate (BM25/keyword search)
- ChangeLog (audit trail)

---

## Changes Made

### 1. `src/scanners/qdrant_updater.py`

**Line 730:** Changed default parameter
```python
# BEFORE
def get_qdrant_updater(..., enable_triple_write: bool = False)

# AFTER
def get_qdrant_updater(..., enable_triple_write: bool = True)
```

**Line 53-62:** Updated MARKER_COHERENCE_ROOT_001 with FIX_96.1 status

**Line 393-397:** Updated MARKER_COHERENCE_BYPASS_004 status to MITIGATED

**Line 502-508:** Updated MARKER_COHERENCE_BYPASS_005 status (still PENDING for batch)

### 2. `src/scanners/file_watcher.py`

**Line 415:** Added explicit parameter
```python
# BEFORE
result = handle_watcher_event(event, qdrant_client=qdrant_client)

# AFTER
result = handle_watcher_event(event, qdrant_client=qdrant_client, enable_triple_write=True)
```

**Line 473:** Same fix in retry logic

### 3. `src/api/routes/watcher_routes.py`

**Line 160-167:** BYPASS_001 - Directory scan now uses TW
```python
# Added explicit enable_triple_write=True
updater = get_qdrant_updater(qdrant_client=qdrant_client, enable_triple_write=True)
```

**Line 459-492:** BYPASS_002 - Browser files now use TW
```python
# Replaced direct qdrant_client.upsert() with:
tw = get_triple_write_manager()
tw.write_file(file_path, content, embedding, metadata)
# With fallback to direct Qdrant on error
```

**Line 661-692:** BYPASS_003 - Drag-drop files now use TW
```python
# Same pattern: TW first, fallback to direct Qdrant
```

---

## Data Flow After Fix

```
BEFORE (data divergence):
File Event → Watcher → QdrantUpdater → Qdrant ONLY
                                      (Weaviate & ChangeLog empty)

AFTER (coherent writes):
File Event → Watcher → QdrantUpdater → TripleWriteManager
                                              ↓
                                      ┌───────┼───────┐
                                      ↓       ↓       ↓
                                   Qdrant  Weaviate  ChangeLog
```

---

## Marker Status Summary

| Marker | Location | Status |
|--------|----------|--------|
| MARKER_COHERENCE_ROOT_001 | qdrant_updater.py:53 | PARTIAL FIX |
| MARKER_COHERENCE_BYPASS_001 | watcher_routes.py:160 | ✅ FIXED |
| MARKER_COHERENCE_BYPASS_002 | watcher_routes.py:459 | ✅ FIXED |
| MARKER_COHERENCE_BYPASS_003 | watcher_routes.py:661 | ✅ FIXED |
| MARKER_COHERENCE_BYPASS_004 | qdrant_updater.py:393 | ⚠️ MITIGATED (fallback only) |
| MARKER_COHERENCE_BYPASS_005 | qdrant_updater.py:502 | ❌ PENDING (batch ops) |

---

## Remaining Work

### BYPASS_005: Batch Operations

Batch updates (`batch_update()` method) still write directly to Qdrant because:
1. TripleWriteManager lacks a `batch_write()` method
2. Calling `write_file()` in loop would be slow for 100+ files

**Workaround:** Use `scan_directory()` which calls `update_file()` per file (goes through TW)

**Future fix:** Add `TripleWriteManager.batch_write(files)` with:
- Batch Weaviate insert
- Batch Qdrant insert
- Atomic ChangeLog append

---

## Testing

### Verify TripleWrite is Active

```bash
# Check coherence after adding files
curl http://localhost:5002/api/triple-write/check-coherence?depth=full

# Expected: Qdrant and Weaviate counts should match
```

### Test File Watcher

1. Add a new file to a watched directory
2. Check logs for `[Watcher] ✅ Indexed via TripleWrite: ...`
3. Verify file appears in both Qdrant and Weaviate

### Test Browser Upload

1. Drag files to browser upload
2. Check logs for `[Watcher] Indexed via TripleWrite: ...`
3. Verify files in both stores

---

## Rollback

If issues occur, revert by setting `enable_triple_write=False`:

```python
# In file_watcher.py line 415:
result = handle_watcher_event(event, qdrant_client=qdrant_client, enable_triple_write=False)

# In watcher_routes.py line 167:
updater = get_qdrant_updater(qdrant_client=qdrant_client, enable_triple_write=False)
```

---

## Related Files

- `src/orchestration/triple_write_manager.py` - Core TW implementation
- `src/api/routes/triple_write_routes.py` - TW API endpoints
- `docs/96_phase/HAIKU_05_TRIPLEWRITE_INTEGRATION.md` - Full TW analysis
