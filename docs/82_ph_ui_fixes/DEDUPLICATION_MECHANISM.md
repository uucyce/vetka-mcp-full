# Phase 82: Deduplication Mechanism Design

**Status**: Detailed Implementation Plan
**Complexity**: Medium
**Risk**: Low (isolated to scanner and cleanup)

---

## Problem Summary

Current VETKA tree visualization shows folder `81_ph_mcp_fixes` **twice**:

```
❌ BEFORE (Duplicates):
├── docs/
│   ├── 81_ph_mcp_fixes (folder_8003271) - 4 files, no metadata
│   └── 79_ph_sugiyama
└── /Users/danilagulin/.../docs/
    └── 81_ph_mcp_fixes (folder_12034514) - 5 files, full metadata
```

Root cause: Qdrant stores files with **mixed path representations** (absolute + relative).

---

## Mechanism A: Smart Path Normalization (Recommended)

### Phase 82a-1: Modify Scanner to Use Relative Paths

**File**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/rescan_project.py`

**Current behavior (lines 348-423)**:
```python
for root, dirs, files_list in os.walk(PROJECT_ROOT):
    for file in files_list:
        file_path = os.path.join(root, file)  # ❌ ABSOLUTE PATH

        files_data.append({
            'path': file_path,  # e.g., "/Users/.../docs/FILE.md"
            'parent_folder': os.path.dirname(rel_path),
        })
```

**Proposed fix**:
```python
import os

for root, dirs, files_list in os.walk(PROJECT_ROOT):
    skip_dirs = {'.git', 'node_modules', '__pycache__', '.pytest_cache', 'venv', '.venv', ...}
    dirs[:] = [d for d in dirs if d not in skip_dirs]

    for file in files_list:
        file_path = os.path.join(root, file)

        # NORMALIZE: Use relative path from PROJECT_ROOT
        try:
            rel_path = os.path.relpath(file_path, PROJECT_ROOT)
        except ValueError:
            # File outside PROJECT_ROOT - keep absolute but mark
            rel_path = file_path

        # Get file type extension
        ext = os.path.splitext(file)[1].lower()
        file_type = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.jsx': 'react', '.tsx': 'react', '.md': 'markdown',
            '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml'
        }.get(ext, 'other')

        # Read content with size limit
        content = ""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(8000)
        except:
            pass

        # Calculate content hash from ACTUAL file bytes
        try:
            with open(file_path, 'rb') as f:
                content_hash = hashlib.md5(f.read()).hexdigest()
        except:
            content_hash = hashlib.md5(b"").hexdigest()

        # Get file metadata
        try:
            file_stats = os.stat(file_path)
            created_time = file_stats.st_birthtime if hasattr(file_stats, 'st_birthtime') else file_stats.st_ctime
            modified_time = file_stats.st_mtime
            size_bytes = file_stats.st_size
        except:
            created_time = os.path.getctime(file_path)
            modified_time = os.path.getmtime(file_path)
            size_bytes = 0

        # Calculate depth from RELATIVE path
        depth = len(rel_path.split(os.sep))

        # Parent folder = dirname of relative path (empty for root files)
        parent_folder = os.path.dirname(rel_path)

        # BUILD RECORD with relative path
        files_data.append({
            'path': rel_path,  # ✅ USE RELATIVE: "docs/81_ph_mcp_fixes/FILE.md"
            'absolute_path': file_path,  # Store original for reference only
            'name': file,
            'extension': ext,
            'type': file_type,
            'content': content,
            'content_hash': content_hash,
            'created_time': created_time,
            'modified_time': modified_time,
            'size_bytes': size_bytes,
            'depth': depth,
            'parent_folder': parent_folder
        })

print_success(f"Prepared {len(files_data)} files for embedding")
```

**Key changes**:
1. Use `os.path.relpath()` to convert to relative path
2. Store `absolute_path` separately (for reference/debugging only)
3. Use relative path for `parent_folder` calculation
4. Calculate depth from relative path length

**Impact**: All downstream systems (embedding_pipeline, tree_routes) automatically get consistent paths

---

### Phase 82a-2: Update Embedding Pipeline to Accept Both Paths

**File**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/embedding_pipeline.py`

**Current behavior (lines 441-445)**:
```python
def _generate_id(self, file_data: Dict[str, Any]) -> str:
    """Generate unique ID for a file."""
    path = file_data.get('path', '')
    content_hash = file_data.get('content_hash', '')
    return hashlib.md5(f"{path}:{content_hash}".encode()).hexdigest()
```

**Proposed update** (Normalize before generating ID):
```python
def _generate_id(self, file_data: Dict[str, Any]) -> str:
    """
    Generate unique ID for a file.

    Normalizes path to handle both absolute and relative representations.
    Phase 82a: Ensures same file always gets same ID regardless of path format.
    """
    # Get path (prefer absolute_path if available for legacy compatibility)
    path = file_data.get('absolute_path') or file_data.get('path', '')
    content_hash = file_data.get('content_hash', '')

    # Normalize: extract PROJECT_ROOT-relative part if absolute path
    if path.startswith('/'):
        # Absolute path - extract relative portion
        try:
            # Extract relative portion: everything after PROJECT_ROOT/
            if '/vetka_live_03/' in path:
                path = path.split('/vetka_live_03/')[-1]  # "docs/FILE.md"
            elif '/VETKA_Project/' in path:
                path = path.split('/VETKA_Project/')[-1]
        except:
            pass  # Use path as-is if extraction fails

    # Generate deterministic ID from normalized path + hash
    unique_key = f"{path}:{content_hash}"
    return hashlib.md5(unique_key.encode()).hexdigest()
```

**Why this works**:
- Files with same content but different path representations → **same normalized path** → **same ID**
- UUID5(namespace_dns, same_id) → **always same point_id** → Qdrant upsert replaces old entry
- No duplicates in Qdrant

---

### Phase 82a-3: Update Tree Builder to Handle Legacy Data

**File**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/tree_routes.py`

**Add normalization step** (after line 137, before line 167):

```python
# Step 1.5: NORMALIZE PATHS (Phase 82a)
# Handle mixed absolute/relative paths from legacy scans
print(f"[API] Normalizing {len(all_files)} file paths...")

for point in all_files:
    p = point.payload or {}
    path = p.get('path', '')

    # Normalize absolute paths to relative
    if path.startswith('/'):
        try:
            if '/vetka_live_03/' in path:
                normalized = path.split('/vetka_live_03/')[-1]
            elif '/VETKA_Project/' in path:
                normalized = path.split('/VETKA_Project/')[-1]
            else:
                normalized = path  # Keep as-is

            point.payload['path'] = normalized
        except:
            pass  # Keep original if normalization fails

# After normalization, optionally deduplicate
seen_paths = {}
deduplicated = []
duplicates_removed = 0

for point in all_files:
    p = point.payload or {}
    path = p.get('path', '')

    if path not in seen_paths:
        seen_paths[path] = True
        deduplicated.append(point)
    else:
        duplicates_removed += 1

if duplicates_removed > 0:
    print(f"[API] Removed {duplicates_removed} duplicate paths from tree")
    all_files = deduplicated

print(f"[API] After normalization: {len(all_files)} unique files")
```

**Why this works**:
- Normalizes mixed paths before building folder hierarchy
- Deduplicates at API level (fast, doesn't require Qdrant changes)
- Works with existing data

---

## Mechanism B: Explicit Deduplication Script

### Phase 82b: Create Cleanup Script

**File**: `scripts/cleanup_qdrant_duplicates.py` (NEW)

```python
#!/usr/bin/env python3
"""
Phase 82b: Remove duplicate entries from Qdrant
Keep one copy per logical file (by normalized path)
"""

import os
import sys
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent

# Add project root to Python path
sys.path.insert(0, str(PROJECT_ROOT))

from src.memory.qdrant_client import get_qdrant_client
from qdrant_client.models import Filter, FieldCondition, MatchValue, PointIdsList


def normalize_path(path: str) -> str:
    """Normalize absolute/relative paths to standard form."""
    if path.startswith('/'):
        # Absolute path - extract relative portion
        if '/vetka_live_03/' in path:
            return path.split('/vetka_live_03/')[-1]
        elif '/VETKA_Project/' in path:
            return path.split('/VETKA_Project/')[-1]
    return path


def cleanup_duplicates():
    """Remove duplicate file entries from Qdrant."""
    print("\n" + "=" * 60)
    print("  PHASE 82b: QDRANT DEDUPLICATION")
    print("=" * 60 + "\n")

    qdrant = get_qdrant_client()

    if not qdrant or not qdrant.client:
        print("❌ Qdrant not connected")
        return False

    try:
        # Step 1: Fetch all scanned_file entries
        print("Step 1: Fetching all scanned files from Qdrant...")
        points, offset = qdrant.scroll(
            collection_name='vetka_elisya',
            scroll_filter=Filter(
                must=[FieldCondition(key="type", match=MatchValue(value="scanned_file"))]
            ),
            limit=100,
            with_payload=True,
            with_vectors=False
        )

        all_points = points.copy()

        # Fetch all pages
        while offset is not None:
            points, offset = qdrant.scroll(
                collection_name='vetka_elisya',
                scroll_filter=Filter(
                    must=[FieldCondition(key="type", match=MatchValue(value="scanned_file"))]
                ),
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            all_points.extend(points)

        print(f"✅ Fetched {len(all_points)} total files")

        # Step 2: Group by normalized path
        print("\nStep 2: Grouping by normalized path...")
        by_path = defaultdict(list)

        for point in all_points:
            p = point.payload or {}
            raw_path = p.get('path', '')
            normalized = normalize_path(raw_path)
            by_path[normalized].append({
                'id': point.id,
                'raw_path': raw_path,
                'modified_time': p.get('modified_time', 0),
                'size': p.get('size_bytes', 0),
                'name': p.get('name', '')
            })

        # Step 3: Find duplicates
        duplicates = {path: entries for path, entries in by_path.items() if len(entries) > 1}
        print(f"✅ Found {len(duplicates)} paths with duplicates")

        if not duplicates:
            print("\n✅ No duplicates found - Qdrant is clean!")
            return True

        # Step 4: Select entries to keep/delete
        print("\nStep 3: Selecting entries to keep/delete...")
        to_delete = []
        kept_count = 0

        for normalized_path, entries in duplicates.items():
            # Sort by modified_time (descending) - keep newest
            entries.sort(key=lambda x: x['modified_time'], reverse=True)

            kept = entries[0]
            duplicates_list = entries[1:]

            print(f"\n  Path: {normalized_path}")
            print(f"    Keeping: ID={kept['id']}, name={kept['name']}, mtime={kept['modified_time']}")

            for dup in duplicates_list:
                print(f"    Deleting: ID={dup['id']}, name={dup['name']}, mtime={dup['modified_time']}")
                to_delete.append(dup['id'])

            kept_count += 1

        # Step 5: Delete duplicates
        if to_delete:
            print(f"\nStep 4: Deleting {len(to_delete)} duplicate entries...")

            # Delete in batches to avoid timeout
            batch_size = 50
            deleted_count = 0

            for i in range(0, len(to_delete), batch_size):
                batch = to_delete[i:i+batch_size]
                try:
                    qdrant.client.delete(
                        collection_name='vetka_elisya',
                        points_selector=PointIdsList(ids=batch)
                    )
                    deleted_count += len(batch)
                    print(f"  Deleted {deleted_count}/{len(to_delete)}...")
                except Exception as e:
                    print(f"  ⚠️  Batch delete error: {e}")
                    return False

            print(f"✅ Deleted {deleted_count} duplicate entries")

        # Step 6: Verify
        print(f"\nStep 5: Verifying cleanup...")
        stats = qdrant.get_collection('vetka_elisya')
        print(f"✅ Final collection stats:")
        print(f"   - Total points: {stats.points_count}")
        print(f"   - Vector count: {stats.vectors_count}")

        print("\n" + "=" * 60)
        print("  ✅ DEDUPLICATION COMPLETE")
        print("=" * 60 + "\n")

        return True

    except Exception as e:
        print(f"\n❌ Deduplication failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = cleanup_duplicates()
    exit(0 if success else 1)
```

**Usage**:
```bash
python scripts/cleanup_qdrant_duplicates.py
```

**Output example**:
```
============================================================
  PHASE 82b: QDRANT DEDUPLICATION
============================================================

Step 1: Fetching all scanned files from Qdrant...
✅ Fetched 250 total files

Step 2: Grouping by normalized path...
✅ Found 3 paths with duplicates

Step 3: Selecting entries to keep/delete...

  Path: docs/81_ph_mcp_fixes/00_README.md
    Keeping: ID=1079027742394321864, name=00_README.md, mtime=1769012225.59
    Deleting: ID=4207080362750208322, name=00_README.md, mtime=0

  Path: docs/81_ph_mcp_fixes/AUDIT_MCP_NOTIFICATIONS.md
    Keeping: ID=730410068651246713, name=AUDIT_MCP_NOTIFICATIONS.md, mtime=1769012238.18
    Deleting: ID=16920635514813871418, name=AUDIT_MCP_NOTIFICATIONS.md, mtime=0

Step 4: Deleting 3 duplicate entries...
  Deleted 3/3...
✅ Deleted 3 duplicate entries

Step 5: Verifying cleanup...
✅ Final collection stats:
   - Total points: 247
   - Vector count: 247

============================================================
  ✅ DEDUPLICATION COMPLETE
============================================================
```

---

## Mechanism C: Tree Builder Resilience

### Phase 82c: Defensive Programming in tree_routes.py

Add deduplication filter **after** all files are fetched but **before** folder hierarchy is built:

```python
# After line 164 (all_files = valid_files)
# Add Phase 82c: Defensive deduplication

print(f"[API] Starting deduplication check (Phase 82c)...")

# Group files by normalized path
from collections import defaultdict
by_normalized_path = defaultdict(list)

for i, point in enumerate(all_files):
    p = point.payload or {}
    raw_path = p.get('path', '')

    # Normalize for comparison
    if raw_path.startswith('/'):
        if '/vetka_live_03/' in raw_path:
            normalized = raw_path.split('/vetka_live_03/')[-1]
        else:
            normalized = raw_path
    else:
        normalized = raw_path

    by_normalized_path[normalized].append(i)

# Find duplicates and keep only the best copy
duplicates_removed = 0
indices_to_keep = set(range(len(all_files)))

for normalized_path, indices in by_normalized_path.items():
    if len(indices) > 1:
        # Keep the entry with best metadata (non-zero modified_time)
        best_idx = indices[0]
        best_score = 0

        for idx in indices:
            score = 0
            p = all_files[idx].payload or {}
            if p.get('modified_time', 0) > 0:
                score += 10
            if p.get('extension', ''):
                score += 5
            if p.get('content', ''):
                score += 3

            if score > best_score:
                best_score = score
                best_idx = idx

        # Mark others for removal
        for idx in indices:
            if idx != best_idx:
                indices_to_keep.discard(idx)
                duplicates_removed += 1

if duplicates_removed > 0:
    all_files = [all_files[i] for i in sorted(indices_to_keep)]
    print(f"[API] Phase 82c: Removed {duplicates_removed} duplicate entries")

print(f"[API] After deduplication: {len(all_files)} unique files")
```

**Why this works**:
- Operates at API layer (no persistence, runtime dedup)
- Selects best copy by metadata quality
- Transparent to visualization
- Can be toggled with feature flag

---

## Execution Order

### Recommended sequence:

```
1. Deploy scanner normalization (Phase 82a-1)
   └─ Run: python scripts/rescan_project.py
   └─ Verify: All files have relative paths in Qdrant

2. Run cleanup script (Phase 82b)
   └─ Run: python scripts/cleanup_qdrant_duplicates.py
   └─ Verify: Duplicates removed, points_count reduced

3. Deploy tree builder resilience (Phase 82c)
   └─ No changes to data, just safer API
   └─ Works with both new and legacy data

4. Optional: Deploy embedding pipeline update (Phase 82a-2)
   └─ Extra safety for future path handling
```

**Total time**: ~2 hours (implementation + testing)

---

## Testing Checklist

### Before Fix
- [ ] Count duplicates: `curl http://localhost:3000/api/tree/data | jq '.tree.nodes | map(select(.name=="81_ph_mcp_fixes")) | length'` → Expected: 2
- [ ] Verify metadata issues: Note which copy has metadata

### During Fix
- [ ] Run scanner with normalization
- [ ] Run cleanup script
- [ ] Check Qdrant points reduced
- [ ] Restart server

### After Fix
- [ ] Tree loads without errors
- [ ] Folder appears once: Expected: 1
- [ ] All metadata present
- [ ] No 404 errors in browser console
- [ ] Run full test suite

---

## Rollback Plan

If deduplication causes issues:

```bash
# 1. Restore from backup
python scripts/restore_qdrant_backup.py

# 2. Or re-run rescan
python scripts/rescan_project.py

# 3. Disable Phase 82c in tree_routes.py (comment out filter code)
```

---

## Summary

| Phase | File | Change | Impact | Risk |
|-------|------|--------|--------|------|
| 82a-1 | `rescan_project.py` | Use relative paths | Prevents future duplicates | Low |
| 82a-2 | `embedding_pipeline.py` | Normalize in ID generation | Handles legacy data | Low |
| 82b | `cleanup_qdrant_duplicates.py` | New cleanup script | Removes existing duplicates | Medium |
| 82c | `tree_routes.py` | Defensive dedup at API | Resilience to mixed data | Low |

**Key benefit**: Single folder `81_ph_mcp_fixes` with full metadata, no duplicates in tree visualization.
