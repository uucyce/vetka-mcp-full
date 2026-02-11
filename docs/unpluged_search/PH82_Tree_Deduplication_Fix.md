# Phase 82: Duplicate Detection & Qdrant Deduplication Research

**Date**: 2026-01-21
**Status**: CRITICAL FINDINGS
**Priority**: High (affecting tree visualization)

---

## Executive Summary

Found **TWO ROOT CAUSES** for folder duplication in tree visualization:

1. **Qdrant Upsert Logic**: Uses `path` + `content_hash` for uniqueness, but scanned files have BOTH full paths AND relative paths
2. **Tree Builder Logic**: `tree_routes.py` creates folders from multiple path representations (absolute + relative), causing 81_ph_mcp_fixes to appear twice

---

## Problem Analysis

### Visual Symptom
Folder `81_ph_mcp_fixes` appears **twice** in tree:
- **Left side**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/81_ph_mcp_fixes` (absolute path)
- **Right side**: `docs/81_ph_mcp_fixes` (relative path)

Files under left: 5 files (full metadata)
Files under right: 4 files (no metadata, extension='')

### Root Cause #1: Embedding Pipeline Duplication

**File**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/embedding_pipeline.py`

#### Current Uniqueness Logic (Lines 441-445):

```python
def _generate_id(self, file_data: Dict[str, Any]) -> str:
    """Generate unique ID for a file."""
    path = file_data.get('path', '')
    content_hash = file_data.get('content_hash', '')
    return hashlib.md5(f"{path}:{content_hash}".encode()).hexdigest()
```

**Problem**: The ID is based on `path:content_hash`, but `rescan_project.py` scans files with **full absolute paths**:

```python
# rescan_project.py, lines 348-356:
files_data.append({
    'path': file_path,  # ABSOLUTE: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/81_ph_mcp_fixes/FILE.md
    'name': file,
    'extension': ext,
    'type': file_type,
    'content': content,
    'content_hash': content_hash,
    'created_time': created_time,
    'modified_time': modified_time,
    'size_bytes': size_bytes,
    'depth': depth,
    'parent_folder': parent_folder  # EMPTY for root-level files
})
```

#### Qdrant Upsert (Lines 411-439):

```python
def _save_to_qdrant(self, doc_id: str, embedding: List[float], metadata: Dict) -> bool:
    # ...
    point_id = uuid.uuid5(uuid.NAMESPACE_DNS, doc_id).int & 0x7FFFFFFFFFFFFFFF

    point = PointStruct(
        id=point_id,
        vector=embedding,
        payload=metadata  # CONTAINS FULL PATH
    )

    self.qdrant.upsert(
        collection_name=self.collection_name,
        points=[point]  # UPSERT = UPDATE OR INSERT
    )
```

**Analysis**: The `upsert` call is **correct** - it uses `uuid5` which is deterministic. Same `doc_id` always produces same point ID. Problem is elsewhere.

---

### Root Cause #2: Tree Builder Path Duplication

**File**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/tree_routes.py`

#### Step 1: Fetch from Qdrant (Lines 124-137):

```python
all_files = []
offset = None

while True:
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
    all_files.extend(results)
```

Result: Returns **mixed paths** (some absolute, some relative)

#### Step 2: Build Folder Hierarchy (Lines 169-246):

```python
for point in all_files:
    p = point.payload or {}
    file_path = p.get('path', '')
    parent_folder = p.get('parent_folder', '')

    if not parent_folder and file_path:
        parent_folder = '/'.join(file_path.split('/')[:-1])  # LINE 179
    if not parent_folder:
        parent_folder = 'root'

    # ... create folder entry ...
    parts = parent_folder.split('/') if parent_folder != 'root' else ['root']
    for i in range(len(parts)):
        folder_path = '/'.join(parts[:i+1]) if parts[0] != 'root' else 'root' if i == 0 else '/'.join(parts[:i+1])
        # ... add to folders dict ...
```

**Problem**: Files with these paths create different folder hierarchies:

| File Path | Extracted parent_folder | Folder Hierarchy |
|-----------|------------------------|-----------------|
| `/Users/danilagulin/.../docs/81_ph_mcp_fixes/FILE.md` | `/Users/danilagulin/.../docs/81_ph_mcp_fixes` | Long absolute path chain |
| `docs/81_ph_mcp_fixes/FILE.md` | `docs/81_ph_mcp_fixes` | Short relative path chain |

**Result**: Two separate folder trees created under different parent paths!

#### Step 3: Folder ID Generation (Line 309):

```python
folder_id = f"folder_{abs(hash(folder_path)) % 100000000}"
```

Different folder_path strings → Different hash values → **Different folder IDs**

This means folders with same name but different path representations get **different IDs** and are treated as **separate nodes**.

---

## Qdrant Data Quality Check

### Data Structure in vetka_elisya

Files are stored with inconsistent path representations:

```javascript
// Type 1: Files from absolute path scan
{
  "type": "scanned_file",
  "path": "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/81_ph_mcp_fixes/FILE.md",
  "parent_folder": "docs/81_ph_mcp_fixes",  // OR EMPTY
  "name": "FILE.md",
  "extension": ".md",
  "created_time": 1769012225.59,
  "modified_time": 1769012225.59
}

// Type 2: Files from relative path scan (in same Qdrant)
{
  "type": "scanned_file",
  "path": "docs/81_ph_mcp_fixes/FILE.md",
  "parent_folder": "",
  "name": "FILE.md",
  "extension": "",  // MISSING!
  "created_time": 0,
  "modified_time": 0
}
```

### Why Both Types Exist

Looking at tree visualization output, files under `folder_8003271` (right side) have:
- `extension: ""`
- `created_time: 0`
- `modified_time: 0`

While files under `folder_12034514` (left side) have full metadata.

**Hypothesis**: A previous scan or MCP operation added relative-path entries **without full metadata**.

---

## Deduplication Mechanisms (Current vs. Needed)

### Current Detection
- **Primary**: `path:content_hash` → MD5 hash → UUID5(namespace_dns) → deterministic point ID
- **Issue**: Works IF same file rescanned, but doesn't prevent mixed absolute/relative paths

### What's Missing

1. **No path normalization** before storing in Qdrant
2. **No uniqueness check on absolute path** (files with same absolute path but different representations)
3. **No deduplication in tree_routes.py** (same folder appears with different IDs)

---

## Proposed Deduplication Strategies

### Plan A: Normalize Paths in Scanner (Recommended)

**Location**: `scripts/rescan_project.py` (lines 348-423)

```python
import os

# In scan loop, normalize ALL paths to PROJECT_ROOT-relative
for root, dirs, files_list in os.walk(PROJECT_ROOT):
    for file in files_list:
        file_path = os.path.join(root, file)

        # NORMALIZE: Convert to relative path from PROJECT_ROOT
        try:
            rel_path = os.path.relpath(file_path, PROJECT_ROOT)
        except ValueError:
            # File outside PROJECT_ROOT (e.g., /Users/...)
            rel_path = file_path  # Keep absolute

        # Use RELATIVE path for everything downstream
        files_data.append({
            'path': rel_path,  # "docs/81_ph_mcp_fixes/FILE.md" NOT "/Users/..."
            'absolute_path': file_path,  # Store original for reference
            'parent_folder': os.path.dirname(rel_path),  # "docs/81_ph_mcp_fixes"
            # ... rest of fields ...
        })
```

**Benefits**:
- Single representation for each file
- Smaller payloads (relative paths shorter)
- Deterministic folder IDs in tree builder
- No duplicate folders in visualization

**Changes needed**:
1. `rescan_project.py`: Normalize to relative paths
2. `embedding_pipeline.py`: Accept both absolute and relative paths
3. `tree_routes.py`: No changes needed (already uses relative paths in Qdrant)

### Plan B: Deduplicate in Tree Builder

**Location**: `src/api/routes/tree_routes.py` (lines 169-246)

Add normalization step after fetching from Qdrant:

```python
# After fetching all_files from Qdrant
normalized_files = []
seen_paths = {}

for point in all_files:
    p = point.payload or {}
    file_path = p.get('path', '')

    # Normalize to PROJECT_ROOT-relative
    if file_path.startswith('/Users/'):
        # Absolute path - extract relative portion
        try:
            rel_path = file_path.split('vetka_live_03/')[-1]  # Hack but works
        except:
            rel_path = file_path
    else:
        rel_path = file_path  # Already relative

    # Deduplicate by normalized path
    if rel_path not in seen_paths:
        seen_paths[rel_path] = True
        point.payload['path'] = rel_path  # Update payload
        normalized_files.append(point)

all_files = normalized_files
```

**Benefits**:
- No scanner changes needed
- Filters out duplicates before tree building
- Works with existing Qdrant data

**Limitations**:
- Cleanup still in Qdrant (duplicates remain stored)
- Requires path parsing heuristics

### Plan C: Full Qdrant Cleanup

**Location**: `scripts/cleanup_qdrant_duplicates.py` (NEW)

```python
#!/usr/bin/env python3
"""
Phase 82: Remove duplicate entries from Qdrant
Keeps one copy per absolute path (latest modified_time)
"""

from src.memory.qdrant_client import get_qdrant_client
from qdrant_client.models import FieldCondition, MatchValue, Filter

def cleanup_duplicates():
    qdrant = get_qdrant_client()

    # Get all scanned files
    points, _ = qdrant.scroll(
        collection_name='vetka_elisya',
        scroll_filter=Filter(
            must=[FieldCondition(key="type", match=MatchValue(value="scanned_file"))]
        ),
        limit=10000,
        with_payload=True,
        with_vectors=False
    )

    # Group by normalized path
    by_normalized_path = {}
    for point in points:
        p = point.payload or {}
        absolute_path = p.get('absolute_path') or p.get('path', '')

        # Normalize to compare
        if absolute_path not in by_normalized_path:
            by_normalized_path[absolute_path] = []

        by_normalized_path[absolute_path].append((point.id, p))

    # Find duplicates
    to_delete = []
    for abs_path, entries in by_normalized_path.items():
        if len(entries) > 1:
            # Keep newest, delete others
            entries.sort(key=lambda x: x[1].get('modified_time', 0), reverse=True)
            for point_id, _ in entries[1:]:  # Skip first (newest)
                to_delete.append(point_id)
            print(f"Found {len(entries)} copies of {abs_path}, keeping 1")

    # Delete duplicates
    for point_id in to_delete:
        qdrant.delete(
            collection_name='vetka_elisya',
            points_selector=PointIdsList(ids=[point_id])
        )

    print(f"Deleted {len(to_delete)} duplicate points")

if __name__ == "__main__":
    cleanup_duplicates()
```

**Benefits**:
- Permanent cleanup
- Single source of truth in Qdrant
- Smallest payload (no duplicates)

**Limitations**:
- Destructive (deletes data)
- Need to run once per rescan cycle

---

## Implementation Recommendation

### Immediate Fix (Today)

**Use Plan A + Plan C (Combined)**

1. **Normalize scanner output** (`rescan_project.py`):
   - Convert all paths to PROJECT_ROOT-relative at scan time
   - Store `absolute_path` separately if needed

2. **Run cleanup script** after rescan:
   - Removes existing duplicates from Qdrant
   - Future scans won't create duplicates

3. **Test tree visualization**:
   - Verify `81_ph_mcp_fixes` appears only once
   - Verify folder IDs are consistent

### Timeline

- **Phase 82a**: Implement Plan A (scanner normalization)
- **Phase 82b**: Implement Plan C (cleanup script)
- **Phase 82c**: Update tree_routes.py to handle any legacy data
- **Phase 82d**: Run cleanup and verify

---

## Qdrant Query Reference

### Find Duplicates (By Path)

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Get all scanned_file entries
points, _ = qdrant.scroll(
    collection_name='vetka_elisya',
    scroll_filter=Filter(
        must=[FieldCondition(key="type", match=MatchValue(value="scanned_file"))]
    ),
    limit=10000,
    with_payload=True,
    with_vectors=False
)

# Group and find duplicates
from collections import defaultdict
by_path = defaultdict(list)
for point in points:
    path = point.payload.get('path', '')
    by_path[path].append(point.id)

# Print duplicates
duplicates = {path: ids for path, ids in by_path.items() if len(ids) > 1}
for path, ids in duplicates.items():
    print(f"Path: {path}, IDs: {ids}")
```

### Delete by Point ID

```python
from qdrant_client.models import PointIdsList

qdrant.delete(
    collection_name='vetka_elisya',
    points_selector=PointIdsList(ids=[point_id])
)
```

### Get Collection Stats

```python
stats = qdrant.get_collection('vetka_elisya')
print(f"Total points: {stats.points_count}")
```

---

## Code Locations to Monitor

| File | Lines | Issue |
|------|-------|-------|
| `scripts/rescan_project.py` | 348-423 | Stores absolute paths without normalization |
| `src/scanners/embedding_pipeline.py` | 441-445 | Uniqueness based on path, doesn't normalize |
| `src/api/routes/tree_routes.py` | 169-246 | Creates folder hierarchies from mixed paths |
| `src/api/routes/tree_routes.py` | 309 | Folder ID generation doesn't normalize |

---

## Testing Plan

### Verify Fix

```bash
# 1. Check before cleanup
curl http://localhost:3000/api/tree/data | jq '.tree.nodes | map(select(.name=="81_ph_mcp_fixes")) | length'
# Expected: 2 (before)

# 2. Run cleanup
python scripts/cleanup_qdrant_duplicates.py

# 3. Run rescan with normalized paths
python scripts/rescan_project.py

# 4. Check after
curl http://localhost:3000/api/tree/data | jq '.tree.nodes | map(select(.name=="81_ph_mcp_fixes")) | length'
# Expected: 1 (after)

# 5. Verify metadata
curl http://localhost:3000/api/tree/data | jq '.tree.nodes[] | select(.name=="81_ph_mcp_fixes")'
# Expected: Single node with correct metadata
```

---

## Summary Table

| Issue | Root Cause | Impact | Fix Strategy | Effort |
|-------|-----------|--------|--------------|--------|
| Path mix (absolute + relative) | Scanner stores both | Duplicates in Qdrant | Normalize in scanner (Plan A) | 20 min |
| Folder ID collision | Hash on mixed paths | Separate folder nodes | Tree builder dedup (Plan B) | 15 min |
| Persistent duplicates | No cleanup | Disk bloat, queries slower | Cleanup script (Plan C) | 30 min |

**Total estimated effort**: 1 hour for full fix + testing

---

## References

- **UUID5 Uniqueness**: Deterministic, namespace-based (not randomized)
- **Qdrant Upsert**: Replaces existing point with same ID, no deduplication within upsert
- **FAN Layout**: Creates tree structure from folders, sensitive to path representation
