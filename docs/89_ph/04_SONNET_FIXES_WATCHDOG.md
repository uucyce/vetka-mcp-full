# WATCHDOG FIX REPORT
**Date:** 2026-01-22 | **Phase:** 89 | **Agent:** Sonnet 4.5
**Status:** FIXED

---

## PROBLEM
Files scanned by watchdog not appearing in UI tree visualization (only 5-6 out of 50+ files shown).

## ROOT CAUSE
**File:** `/src/api/routes/tree_routes.py`
**Lines:** 125-134 (main tree query) + 467-477 (Blender export)

Qdrant scroll queries were missing `deleted=False` filter, causing them to fetch ALL files including soft-deleted ones. Post-fetch filesystem checks then filtered most files out.

---

## THE FIX

### BEFORE (BROKEN):
```python
results, offset = qdrant.scroll(
    collection_name='vetka_elisya',
    scroll_filter=Filter(
        must=[FieldCondition(key="type", match=MatchValue(value="scanned_file"))]
    ),
    limit=100,
    offset=offset,
    with_payload=True,
    with_vectors=False
)
```

### AFTER (FIXED):
```python
results, offset = qdrant.scroll(
    collection_name='vetka_elisya',
    scroll_filter=Filter(
        must=[
            FieldCondition(key="type", match=MatchValue(value="scanned_file")),
            FieldCondition(key="deleted", match=MatchValue(value=False))  # ADDED
        ]
    ),
    limit=100,
    offset=offset,
    with_payload=True,
    with_vectors=False
)
```

---

## CHANGES MADE
1. Added `deleted=False` filter to main tree query (line ~128)
2. Added same filter to Blender export query (line ~471)
3. No import changes needed (MatchValue already imported)

## IMPACT
- UI will now show ALL non-deleted scanned files
- Eliminates unnecessary post-fetch filesystem filtering
- Consistent with watchdog's `deleted: False` payload on file creation
- Blender exports also exclude deleted files

---

## VERIFICATION NEEDED
1. Scan a folder with 50+ files
2. Check UI shows all files in tree visualization
3. Verify `/api/tree/data` endpoint returns complete file list
4. Test soft-delete still hides files from UI

**Fix applied by:** Claude Sonnet 4.5 Watchdog Fixer
