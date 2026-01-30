# PHASE 17.0: Dynamic Stem Binding - COMPLETE

**Date:** 2025-12-24
**Status:** WORKING - 213 stems dynamically follow files

---

## Problem Solved

When Y-blend slider moves:
- Files move (change Y position)
- Stems NOW follow files dynamically

---

## Key Code Locations

### 1. Stem Creation
**File:** `src/visualizer/tree_renderer.py`
**Function:** `createStemLine()` - Lines 2113-2155

```javascript
function createStemLine(start, end, parentInfo = null, childInfo = null) {
    // ... validation ...

    const line = new THREE.Line(geometry, material);

    // CRITICAL: Store IDs for dynamic binding
    line.userData = {
        type: 'stem',              // Must be 'stem' for updates
        parentId: parentInfo?.id,  // Folder ID
        childId: childInfo?.id,    // File ID (used for lookup)
        // ... other metadata
    };

    return line;
}
```

### 2. Stem Storage
**Line 2812:** `branchMeshes.push(stem);`

The `branchMeshes` array contains BOTH:
- **Stems** (THREE.Line with `userData.type = 'stem'`) - 213 items
- **Branches** (THREE.Mesh folder-to-folder, no userData.type) - 28 items

### 3. Dynamic Update on Y-Blend
**Function:** `updateYBlend()` - Lines 5985-6039

```javascript
branchMeshes.forEach((stem, idx) => {
    // Skip non-stems
    if (!stem.userData) return;
    if (stem.userData.type !== 'stem') return;

    const childId = stem.userData.childId;

    // Lookup file mesh by ID
    const childInfo = nodeObjects.get(childId);

    if (childInfo?.mesh) {
        // Update stem end point to file's CURRENT position
        const positions = stem.geometry.attributes.position.array;
        positions[3] = childInfo.mesh.position.x;
        positions[4] = childInfo.mesh.position.y;  // This changes with Y-blend!
        positions[5] = childInfo.mesh.position.z;
        stem.geometry.attributes.position.needsUpdate = true;
    }
});
```

### 4. File Registration in nodeObjects
**Line 2839:** `nodeObjects.set(file.id, { mesh: card, ... });`

This is what `updateYBlend()` looks up to get current file position.

---

## Data Flow

```
1. Page Load:
   ├─ createStemLine() creates stems with childId in userData
   ├─ branchMeshes.push(stem) stores them
   └─ nodeObjects.set(file.id, {mesh: card}) registers file meshes

2. Y-Blend Slider Change:
   ├─ updateYBlend(value) called
   ├─ File card positions updated (mesh.position.y changes)
   └─ branchMeshes.forEach() updates each stem's end point
       └─ stem.geometry.attributes.position.needsUpdate = true
```

---

## Console Output (Working)

```
[STEMS] Updated: 213, Skipped: 0, NoUserData: 0
[STEMS] Total: 241 (stems: 213, branches: 28)
```

- **213 stems** = file-to-folder connections (dynamically updated)
- **28 branches** = folder-to-folder connections (static)

---

## Files Modified

| File | Lines | Change |
|------|-------|--------|
| `tree_renderer.py` | 2113-2155 | `createStemLine()` with userData |
| `tree_renderer.py` | 5985-6039 | `updateYBlend()` stem update loop |

---

## Related Cleanup (Same Session)

1. **Removed file labels** - duplicate info (file cards show names)
2. **Removed connector lines** - visual clutter to labels
3. **Stems are now the ONLY file-to-folder connections**

---

## How to Find This Code Later

```bash
# Find stem creation
grep -n "createStemLine\|userData.*stem" src/visualizer/tree_renderer.py

# Find stem updates
grep -n "branchMeshes\.forEach\|stemsUpdated" src/visualizer/tree_renderer.py

# Find Y-blend function
grep -n "function updateYBlend" src/visualizer/tree_renderer.py
```

---

*Completed: 2025-12-24*
*Author: Claude Opus 4.5*
