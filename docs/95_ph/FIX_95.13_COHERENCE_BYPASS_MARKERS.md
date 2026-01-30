# FIX_95.13: COHERENCE_BYPASS Markers Complete

**Date**: 2026-01-27
**Phase**: 95.13
**Status**: COMPLETED

## Summary

All 5 COHERENCE_BYPASS markers are now documented in the codebase. These markers identify points where writes go directly to Qdrant, bypassing TripleWriteManager (Qdrant + Weaviate + Changelog coherence).

## Marker Locations

| Marker | File | Line | Description |
|--------|------|------|-------------|
| MARKER_COHERENCE_BYPASS_001 | src/api/routes/watcher_routes.py | 160 | Watchdog scan direct Qdrant write |
| MARKER_COHERENCE_BYPASS_002 | src/api/routes/watcher_routes.py | 460 | Browser files bypass TripleWrite |
| MARKER_COHERENCE_BYPASS_003 | src/api/routes/watcher_routes.py | 634 | Drag-drop files bypass TripleWrite |
| MARKER_COHERENCE_BYPASS_004 | src/scanners/qdrant_updater.py | 387 | Single file upsert (was missing, now added) |
| MARKER_COHERENCE_BYPASS_005 | src/scanners/qdrant_updater.py | 493 | Batch upsert bypasses Weaviate/Changelog |

## Fix Applied

Added missing MARKER_COHERENCE_BYPASS_004 to qdrant_updater.py:

```python
# TODO_95.9: MARKER_COHERENCE_BYPASS_004 - Single file upsert bypasses Weaviate/Changelog
# ROOT CAUSE: update_file() writes only to Qdrant when TripleWrite unavailable
# FIX: Ensure TW is enabled via use_triple_write(enable=True) in initialization
# FALLBACK: Direct Qdrant upsert is only for backward compatibility
```

## Architectural Context

```
Data Flow with TripleWrite:
┌─────────────────┐
│   File Change   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ TripleWrite     │────▶│    Qdrant       │ (semantic search)
│ Manager         │     └─────────────────┘
│                 │     ┌─────────────────┐
│                 │────▶│   Weaviate      │ (BM25 keyword search)
│                 │     └─────────────────┘
│                 │     ┌─────────────────┐
│                 │────▶│   Changelog     │ (audit trail)
└─────────────────┘     └─────────────────┘

Data Flow WITHOUT TripleWrite (BYPASS points):
┌─────────────────┐
│   File Change   │
└────────┬────────┘
         │ (BYPASS)
         ▼
┌─────────────────┐
│    Qdrant       │ ← Only semantic search works
└─────────────────┘
         ✗ Weaviate (BM25 broken)
         ✗ Changelog (no audit)
```

## Risk Assessment

When TripleWrite is bypassed:
- **Semantic search** (Qdrant) ✅ Works
- **Keyword search** (Weaviate) ❌ Stale/missing results
- **Audit trail** (Changelog) ❌ No change history
- **Sync issues** - Qdrant and Weaviate become inconsistent

## Recommended Actions

1. **Enable TripleWrite by default** in initialization
2. **Add fallback sync** that catches up Weaviate/Changelog periodically
3. **Monitor bypass events** via logging (already in place)
4. **Implement tw.batch_write()** for MARKER_005 (batch operations)

## Verification

```bash
grep -rn "MARKER_COHERENCE_BYPASS_00[1-5]" src/
# Should return 5 results (all markers present)
```
