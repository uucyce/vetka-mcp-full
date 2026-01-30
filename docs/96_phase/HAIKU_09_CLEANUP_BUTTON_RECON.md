# HAIKU RECON 09: Cleanup Button Analysis

**Agent:** Haiku
**Date:** 2026-01-28
**Task:** Find scan panel cleanup button and Weaviate integration points

---

## FILE LOCATIONS

| File | Lines | Purpose |
|------|-------|---------|
| `client/src/components/scanner/ScanPanel.tsx` | 429-464 | Button handler, confirms, calls API |
| `client/src/components/scanner/ScanPanel.tsx` | 589-597 | Button UI component |
| `client/src/components/scanner/ScanPanel.css` | 111-140 | Button styling |
| `src/api/routes/semantic_routes.py` | 871-958 | **DELETE endpoint (QDRANT ONLY)** |
| `src/orchestration/triple_write_manager.py` | 564-590 | Partial Weaviate eval cleanup |
| `src/api/routes/triple_write_routes.py` | 187-205 | Route for eval cleanup |

---

## CURRENT CLEANUP LOGIC

**Frontend Button Handler (ScanPanel.tsx:429-464):**
```tsx
const handleClearAll = useCallback(async () => {
  const confirmed = window.confirm(
    'Are you sure you want to clear ALL indexed files?\n\n' +
    'This will delete all scanned data from Qdrant.\n' +
    'You will need to re-scan folders to rebuild the index.'
  );
  if (!confirmed) return;

  const response = await fetch(`${API_BASE}/scanner/clear-all`, {
    method: 'DELETE',
  });
  // ... handles result
}, [onEvent]);
```

**Backend Endpoint (semantic_routes.py:871-958):**
- Deletes from `vetka_elisya` collection in Qdrant
- Uses `recreate_collection()` for efficient bulk delete
- Emits socket event: `scan_cleared`
- **DOES NOT TOUCH WEAVIATE**

---

## CRITICAL MARKERS

### MARKER_CLEANUP_001: Weaviate VetkaLeaf NOT Cleared
**Location:** `semantic_routes.py:871`
**Status:** ❌ MISSING

The `clear_all_scans()` endpoint only clears Qdrant. Weaviate `VetkaLeaf` collection retains all old data.

### MARKER_CLEANUP_002: Partial Weaviate Cleanup Exists
**Location:** `triple_write_manager.py:564-590`
**Status:** ⚠️ EVAL DATA ONLY

Method `clear_weaviate_eval_data()` only removes evaluation data, not scanned files.

### MARKER_CLEANUP_003: TripleWriteManager Not Used for Clear
**Location:** `semantic_routes.py:871`
**Status:** ❌ BYPASSED

Clear endpoint directly uses Qdrant client, doesn't go through TripleWriteManager.

---

## REQUIRED FIX: FIX_96.4

Add Weaviate cleanup to `clear_all_scans()` endpoint:

```python
# In semantic_routes.py clear_all_scans():

# 1. Clear Qdrant (existing code)
# 2. Clear Weaviate VetkaLeaf
try:
    import requests
    weaviate_url = "http://localhost:8080"

    # Delete entire VetkaLeaf class (fastest approach)
    resp = requests.delete(f"{weaviate_url}/v1/schema/VetkaLeaf", timeout=10)

    if resp.status_code in (200, 204):
        weaviate_deleted = True
        print(f"[Scanner] Cleared VetkaLeaf class from Weaviate")
    elif resp.status_code == 404:
        weaviate_deleted = True  # Class doesn't exist, that's fine
    else:
        weaviate_deleted = False
        print(f"[Scanner] Failed to clear Weaviate: {resp.status_code}")

except Exception as e:
    weaviate_deleted = False
    print(f"[Scanner] Weaviate cleanup error: {e}")

# 3. Return combined result
return {
    "success": True,
    "message": f"Cleared {points_before} from Qdrant, Weaviate: {'cleared' if weaviate_deleted else 'failed'}",
    "deleted_count": points_before,
    "qdrant_cleared": True,
    "weaviate_cleared": weaviate_deleted
}
```

---

## SOCKET EVENTS

**Current:**
- `scan_cleared` - Qdrant only

**After Fix:**
- `scan_cleared` with `{qdrant_cleared: true, weaviate_cleared: true}`

---

## STATUS

| Component | Status |
|-----------|--------|
| Frontend button | ✅ Ready |
| Qdrant cleanup | ✅ Working |
| Weaviate cleanup | ❌ Missing |
| Coherence check | ⚠️ Exists but not integrated |
