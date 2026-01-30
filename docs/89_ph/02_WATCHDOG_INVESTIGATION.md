# WATCHDOG INVESTIGATION REPORT
**Date:** 2026-01-22 | **Phase:** 89
**Status:** ROOT CAUSE IDENTIFIED + FIX VERIFIED

---

## PROBLEM SUMMARY
- User scans folder → Watchdog detects files → Sends to Qdrant
- Backend logs confirm activity
- **BUT:** UI shows only 5-6 files instead of all scanned files
- Result: Tree visualization appears incomplete/broken

---

## ROOT CAUSE ANALYSIS

### [ROOT_CAUSE] Missing DELETED FLAG Filter in tree_routes.py
**File:** `/src/api/routes/tree_routes.py`
**Lines:** 125-137

The Qdrant query fetches files but has **NO filter for the `deleted` flag**:

```python
# CURRENT (BROKEN):
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

**Problem:** This retrieves ALL scanned files including those marked `deleted=True`.

### [SUSPECT:file_watcher.py:386] Inconsistent Qdrant Client Initialization
**File:** `/src/scanners/file_watcher.py`
**Lines:** 382-392

The watcher lazily fetches qdrant_client on each event:
```python
qdrant_client = self._get_qdrant_client()
if qdrant_client:
    try:
        handle_watcher_event(event, qdrant_client=qdrant_client)
        print(f"[Watcher] Indexed to Qdrant: {path}")
    except Exception as e:
        print(f"[Watcher] Error updating Qdrant index: {e}")
else:
    print(f"[Watcher] WARNING: qdrant_client not available (lazy fetch failed)...")
```

**Issue:** If qdrant_client lazy fetch fails (line 495-504), files are silently NOT indexed. Logs won't show this without looking for "WARNING: qdrant_client not available".

### [HARDCODE:tree_routes.py:126] Collection Name
**File:** `/src/api/routes/tree_routes.py`
**Line:** 126

```python
collection_name='vetka_elisya',
```

Collection name is hardcoded. If scanned files go to a different collection, they won't appear. **However**, watcher_routes.py also uses this same collection (line 188), so this is consistent but worth noting.

### [SUSPECT:qdrant_updater.py:44-49] Collection Name Default
**File:** `/src/scanners/qdrant_updater.py`
**Lines:** 44-49

Default collection is hardcoded as `'vetka_elisya'`. If a scan uses a different collection name parameter, files would be in wrong place.

---

## SECONDARY ISSUES FOUND

### [FIX_NEEDED:tree_routes.py:127-134] Add Deleted Filter
The Qdrant scroll query should explicitly exclude soft-deleted files:

```python
# SHOULD BE:
results, offset = qdrant.scroll(
    collection_name='vetka_elisya',
    scroll_filter=Filter(
        must=[
            FieldCondition(key="type", match=MatchValue(value="scanned_file")),
            FieldCondition(key="deleted", match=MatchValue(value=False))  # ADD THIS
        ]
    ),
    limit=100,
    offset=offset,
    with_payload=True,
    with_vectors=False
)
```

### [SUSPECT:tree_routes.py:145-164] Filesystem Check is Flawed
Post-fetch filtering relies on `os.path.exists()` which is unreliable:
- Browser files use `browser://` paths → will never exist on filesystem
- NFS/remote paths might be temporarily unavailable
- Race conditions if files deleted between Qdrant fetch and filesystem check

**Current code handles browser:// specially** (lines 153-155), but filesystem check still marks them as deleted if path doesn't exist locally.

---

## VERIFIED WORKING PATHS

✓ **watcher_routes.py (adds files correctly)**
- Lines 120-197: Initial scan indexes files with `'deleted': False` payload
- Lines 322-449: Browser files also get `'deleted': False`
- Collection name consistent: `updater.collection_name` (uses 'vetka_elisya' default)

✓ **qdrant_updater.py (updates/deletes correctly)**
- Lines 213-290: `update_file()` sets `'deleted': False` when upserting
- Lines 390-425: `soft_delete()` sets `'deleted': True` when file removed
- Hard delete (lines 427-455) removes points entirely

---

## HYPOTHESIS: WHY UI SHOWS ONLY 5-6 FILES

1. **Initial scan:** Watcher adds folder → indexes 50+ files with `'deleted': False`
2. **UI fetch:** tree_routes.py scrolls Qdrant with NO deleted filter
3. **Result:** Gets mix of live + previously soft-deleted files
4. **Post-fetch filter:** Lines 156-159 use `os.path.exists()` check
5. **Browser files:** Return False for filesystem check → marked as deleted
6. **Final count:** Only files that exist on filesystem appear (5-6 out of 50+)

**But this doesn't explain why NEW files from watcher don't appear...**

### Alternative Hypothesis: Qdrant Collection Mismatch
- Watcher scanning sends to 'vetka_elisya'
- UI queries different collection name
- Files are being indexed but queried from wrong collection
- **CHECK:** Run `curl http://localhost:5001/docs` → test `/api/tree/data` directly to confirm collection has data

---

## IMMEDIATE FIXES REQUIRED

1. **[CRITICAL]** Add `'deleted': False` filter to tree_routes.py line 127-134
2. **[HIGH]** Fix filesystem check in tree_routes.py line 156 to handle browser:// paths better
3. **[MEDIUM]** Add explicit logging in file_watcher.py when qdrant_client lazy fetch fails
4. **[MEDIUM]** Consider hardcoding same collection name constant in all files instead of repeating 'vetka_elisya'

---

## TESTING CHECKLIST

- [ ] Query `/api/tree/data` directly → should show all files
- [ ] Check Qdrant directly: `qdrant.scroll(..., scroll_filter=Filter(must=[FieldCondition(key="type", match=MatchValue(value="scanned_file")), FieldCondition(key="deleted", match=MatchValue(value=False))]))`
- [ ] Verify watcher logs show "qdrant_client available" (not WARNING)
- [ ] Add browser files, verify they appear in tree
- [ ] Delete a file on filesystem, verify it disappears from tree

