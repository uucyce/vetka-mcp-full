# Phase 82: Quick Reference - Duplicate Detection & Fix

**Problem**: Folder `81_ph_mcp_fixes` appears **TWICE** in tree visualization
- Left: Full absolute path + 5 files with metadata ✅
- Right: Relative path + 4 files without metadata ❌

---

## Root Causes

### 1. Mixed Path Representations in Qdrant

Same file stored with different paths:
```
/Users/danilagulin/.../vetka_live_03/docs/81_ph_mcp_fixes/FILE.md  (ABSOLUTE)
docs/81_ph_mcp_fixes/FILE.md                                      (RELATIVE)
```

### 2. Tree Builder Creates Separate Folders

Different path strings → Different folder IDs → Separate tree nodes

```python
# Folder ID generation (tree_routes.py line 309)
folder_id = f"folder_{abs(hash(folder_path)) % 100000000}"

# Example:
hash("/Users/.../docs/81_ph_mcp_fixes")  → Different ID than:
hash("docs/81_ph_mcp_fixes")
```

### 3. Files Lack Metadata in Relative Path Entries

Entries with relative paths have:
- `extension: ""`
- `created_time: 0`
- `modified_time: 0`

Suggests they were added without proper file scanning.

---

## Solution (3-Phase)

### Phase 82a: Normalize Scanner Output
**File**: `scripts/rescan_project.py` (lines 348-423)

Convert all paths to **relative from PROJECT_ROOT**:
```python
# Before
file_path = os.path.join(root, file)  # "/Users/.../docs/FILE.md"

# After
rel_path = os.path.relpath(file_path, PROJECT_ROOT)  # "docs/FILE.md"
files_data.append({'path': rel_path, ...})
```

**Benefit**: Single representation → No duplicates

### Phase 82b: Clean Existing Duplicates
**File**: `scripts/cleanup_qdrant_duplicates.py` (NEW)

```bash
python scripts/cleanup_qdrant_duplicates.py
```

Groups by normalized path, keeps newest copy, deletes others.

**Result**: Qdrant points_count reduced (247 instead of 250)

### Phase 82c: Defensive API Deduplication
**File**: `src/api/routes/tree_routes.py` (after line 164)

Add runtime dedup filter to handle any remaining mixed data:
```python
# Group by normalized path, keep best metadata copy
indices_to_keep = ... # logic to select best entry
all_files = [all_files[i] for i in sorted(indices_to_keep)]
```

**Benefit**: Works with legacy data, transparent to UI

---

## Implementation Order

```
Step 1: Deploy scanner normalization (82a)
        ↓ Run rescan
        ↓
Step 2: Run cleanup script (82b)
        ↓
Step 3: Restart server
        ↓
Step 4: Deploy defensive API filter (82c)
        ↓
Step 5: Verify tree visualization
```

**Total time**: ~1.5 hours

---

## Verification

### Before
```bash
curl http://localhost:3000/api/tree/data \
  | jq '.tree.nodes | map(select(.name=="81_ph_mcp_fixes")) | length'
# Returns: 2
```

### After
```bash
curl http://localhost:3000/api/tree/data \
  | jq '.tree.nodes | map(select(.name=="81_ph_mcp_fixes")) | length'
# Returns: 1
```

### Check Metadata
```bash
curl http://localhost:3000/api/tree/data \
  | jq '.tree.nodes[] | select(.name=="81_ph_mcp_fixes") | .metadata'
# Should show correct path, file_count, depth
```

---

## Files to Modify

| Phase | File | Lines | Change Type |
|-------|------|-------|-------------|
| 82a | `scripts/rescan_project.py` | 348-423 | Modify (use relative paths) |
| 82b | `scripts/cleanup_qdrant_duplicates.py` | - | Create (new script) |
| 82c | `src/api/routes/tree_routes.py` | 164-200 | Add (dedup filter) |

---

## Key Code Snippets

### Normalize Path (use in multiple places)
```python
def normalize_path(path: str) -> str:
    """Convert absolute/relative to standard relative form"""
    if path.startswith('/'):
        if '/vetka_live_03/' in path:
            return path.split('/vetka_live_03/')[-1]
    return path
```

### Find Duplicates in Qdrant
```python
from collections import defaultdict

by_path = defaultdict(list)
for point in all_points:
    path = point.payload.get('path', '')
    by_path[path].append(point.id)

duplicates = {p: ids for p, ids in by_path.items() if len(ids) > 1}
```

### Delete Duplicate Point
```python
from qdrant_client.models import PointIdsList

qdrant.client.delete(
    collection_name='vetka_elisya',
    points_selector=PointIdsList(ids=[point_id])
)
```

---

## Rollback

If something breaks:

```bash
# Option 1: Restore Qdrant backup
python scripts/restore_qdrant_backup.py

# Option 2: Re-run full rescan
python scripts/rescan_project.py

# Option 3: Disable Phase 82c (comment out code)
# No persistence needed, just restart server
```

---

## Expected Results After Fix

```
✅ Tree shows:
  ├── docs/
  │   ├── 81_ph_mcp_fixes (1 folder, 5 files) ← Correct!
  │   └── 79_ph_sugiyama (1 folder, 12 files)
  └── src/
      ├── layout/ (1 folder, 3 files)
      └── api/ (1 folder, 1 file)

✅ Folder metadata:
  - path: "docs/81_ph_mcp_fixes"
  - file_count: 5
  - depth: 2

✅ Files have metadata:
  - extension: ".md"
  - created_time: 1769012225.59
  - modified_time: 1769012238.18
```

---

## Related Documents

- **Detailed Research**: `DUPLICATE_DETECTION_RESEARCH.md`
- **Implementation Guide**: `DEDUPLICATION_MECHANISM.md`
- **Tree Visualization**: See `/api/tree/data` endpoint in `tree_routes.py`

---

## Questions?

Key points to remember:
1. Problem: Mixed absolute + relative paths in Qdrant
2. Solution: Normalize early (scanner) + cleanup late (script) + defend at API
3. Timeline: 1.5 hours implementation + testing
4. Risk: Low (isolated changes, easy rollback)
5. Benefit: Clean tree visualization, no duplicates, better performance

Next phase: Deploy in order (82a → 82b → restart → 82c → verify)
