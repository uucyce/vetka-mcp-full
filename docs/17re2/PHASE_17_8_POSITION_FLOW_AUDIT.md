# Phase 17.8: Position Calculation Flow Audit

**Date:** December 25, 2025
**Status:** AUDIT COMPLETE - Root Cause Identified
**Previous Phase:** 17.7 - Directory Mode Fixes

---

## Executive Summary

**CRITICAL FINDING:** Backend calculates file positions with Phase 14 vertical stacking, passes them to frontend via `visual_hints.layout_hint`, but **frontend IGNORES these values for files** and recalculates locally.

---

## Question 1: Backend Position Calculation

### Location: `src/layout/fan_layout.py`

**Phase 14 vertical stacking code IS PRESENT and ACTIVE:**

```python
# Lines 406-454 in calculate_directory_fan_layout()

# Sort files by time (older first)
folder_files.sort(key=lambda f: f['created_time'])

# Phase 13: Vertical stacking by time
# Phase 14: ADAPTIVE spacing per folder
mid_index = (n_files - 1) / 2.0
y_offset = (i - mid_index) * FILE_SPACING
file_y = folder_y + y_offset

positions[file_data['id']] = {
    'x': file_x,
    'y': file_y,           # ← Calculated with time sorting
    'z': z_overlap,
    'y_time': file_y,
    'y_semantic': folder_y,
    'angle': parent_angle,
    'created_time': file_data['created_time']
}
```

### Key Features:
- ✅ Time-based sorting: `folder_files.sort(key=lambda f: f['created_time'])`
- ✅ Adaptive file spacing: `FILE_SPACING = calculate_file_spacing_adaptive(n_files, BRANCH_LENGTH)`
- ✅ Vertical stacking formula: `y_offset = (i - mid_index) * FILE_SPACING`
- ✅ Both `y_time` and `y_semantic` calculated

---

## Question 2: API Data Flow

### Location: `src/server/routes/tree_routes.py`

**Backend positions ARE passed to frontend:**

```python
# Lines 367-372 - File node creation

'visual_hints': {
    'layout_hint': {
        'expected_x': pos.get('x', 0),
        'expected_y': pos.get('y', 0),    # ← Backend Y position
        'expected_z': pos.get('z', 0)
    },
    'color': color
},
'metadata': {
    'y_time': pos.get('y_time', pos.get('y', 0)),
    'y_semantic': pos.get('y_semantic', pos.get('y', 0)),
    'created_time': file_data['created_time'],
    ...
}
```

**Data sent to frontend includes:**
- `visual_hints.layout_hint.expected_x/y/z`
- `metadata.y_time`, `metadata.y_semantic`
- `metadata.created_time`
- `phase13_layout.file_index`, `phase13_layout.total_files`

---

## Question 3: Frontend Position Usage

### Location: `src/visualizer/tree_renderer.py`

### `useSugiyama` Variable Status:

```javascript
// Line 2571
const useSugiyama = window.VETKA_LAYOUT_MODE === 'sugiyama' ||
                    new URLSearchParams(window.location.search).get('layout') === 'sugiyama';
```

**CRITICAL:**
- `window.VETKA_LAYOUT_MODE` is **NEVER SET** anywhere in code
- URL parameter `?layout=sugiyama` is **NOT used by default**
- Therefore: **`useSugiyama = false`** in normal operation

### File Positioning Logic (Lines 2882-2898):

```javascript
if (sugiyamaPositions && sugiyamaPositions[file.id]) {
    // Sugiyama mode - use calculated positions
    const sp = sugiyamaPositions[file.id];
    x = sp.x + treeOffset;
    y = sp.y;
    z = 0;
} else {
    // FALLBACK - local calculation (IGNORES backend!)
    const theta = localIdx * FILE_GOLDEN_ANGLE;
    const radius = FILE_RADIUS_BASE + Math.sqrt(localIdx + 1) * FILE_RADIUS_GROWTH;
    x = parentPos.x + Math.cos(theta) * radius;
    z = 0;
    y = calculateFileY(file, localIdx, siblings, parentPos.y);  // ← Local calc!
}
```

**THE BUG:**
- When `useSugiyama = false`, `sugiyamaPositions = null`
- Code falls to `else` branch
- **Files use local `calculateFileY()`, NOT `file.visual_hints.layout_hint.expected_y`!**

### Folder Positioning (Works Correctly):

```javascript
// Lines 2713-2718 - Folders DO use backend positions
} else {
    // Non-Sugiyama mode: Get position from layout_hint (calculated in backend)
    const hint = folder.visual_hints?.layout_hint || {};
    folderPos = new THREE.Vector3(
        (hint.expected_x || 0) + treeOffset,
        hint.expected_y || (idx * 40),
        0
    );
}
```

**Folders correctly use `visual_hints.layout_hint` when `useSugiyama = false`.**

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ BACKEND: src/layout/fan_layout.py                                   │
│                                                                     │
│  calculate_directory_fan_layout()                                   │
│  ├── Sort files by created_time                                    │
│  ├── Calculate FILE_SPACING (adaptive)                             │
│  ├── y_offset = (i - mid_index) * FILE_SPACING                     │
│  └── positions[file_id] = {x, y, z, y_time, ...}                  │
│                                                                     │
│  ✅ Phase 14 vertical stacking WORKS HERE                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ API: src/server/routes/tree_routes.py                               │
│                                                                     │
│  GET /api/tree/data                                                 │
│  ├── visual_hints.layout_hint.expected_x = pos['x']                │
│  ├── visual_hints.layout_hint.expected_y = pos['y']  ← SENT!       │
│  └── metadata.y_time, metadata.created_time                        │
│                                                                     │
│  ✅ Backend positions ARE PASSED to frontend                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ FRONTEND: src/visualizer/tree_renderer.py                          │
│                                                                     │
│  buildTree()                                                        │
│  ├── useSugiyama = false (NEVER SET!)                              │
│  ├── sugiyamaPositions = null                                      │
│  │                                                                  │
│  ├── FOLDERS: ✅ Use hint.expected_x/y (backend)                   │
│  │                                                                  │
│  └── FILES: ❌ IGNORE hint.expected_y!                             │
│      └── Uses local calculateFileY() instead                       │
│                                                                     │
│  ❌ Backend file positions WASTED!                                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Three.js Render                                                     │
│                                                                     │
│  mesh.position.set(x, y, z)                                         │
│  └── Uses FRONTEND-calculated values, not backend                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Summary Table

| Question | Answer |
|----------|--------|
| **Where is file Y calculated?** | BOTH places - backend calculates, frontend IGNORES and recalculates |
| **Is Phase 14 code present?** | YES in `fan_layout.py`, but frontend doesn't use it |
| **Is Phase 14 code used?** | NO - frontend ignores `visual_hints.layout_hint` for files |
| **useSugiyama value?** | `false` (never set, no URL param) |
| **What sets mesh.position?** | `buildTree()` line 2900 using local calculation |

---

## Root Cause

**The frontend file positioning code NEVER reads `file.visual_hints.layout_hint.expected_y`!**

```javascript
// Current code (WRONG):
if (sugiyamaPositions && sugiyamaPositions[file.id]) {
    // Use Sugiyama
} else {
    // Local calculation - IGNORES backend!
    y = calculateFileY(file, localIdx, siblings, parentPos.y);
}

// Missing case:
// When useSugiyama=false, should use file.visual_hints.layout_hint.expected_y
```

---

## Fix Options

### Option A: Use Backend Positions When useSugiyama=false

```javascript
if (sugiyamaPositions && sugiyamaPositions[file.id]) {
    // Sugiyama mode
    const sp = sugiyamaPositions[file.id];
    x = sp.x + treeOffset;
    y = sp.y;
    z = 0;
} else if (file.visual_hints?.layout_hint) {
    // Backend mode - USE BACKEND POSITIONS!
    const hint = file.visual_hints.layout_hint;
    x = (hint.expected_x || 0) + treeOffset;
    y = hint.expected_y || parentPos.y + 40;
    z = 0;
} else {
    // Fallback - local calculation
    y = calculateFileY(file, localIdx, siblings, parentPos.y);
}
```

### Option B: Enable Sugiyama by Default

```javascript
// At top of script or in init()
window.VETKA_LAYOUT_MODE = 'sugiyama';
```

### Option C: Make Frontend Sugiyama Use Time Sorting

Update `calculateHierarchyLayout()` to sort by time (already done in Phase 17.7 Step 3).

---

## Recommendation

**Option A is the cleanest fix** - it respects backend calculations and provides proper fallback chain:

1. Sugiyama positions (if available)
2. Backend `layout_hint` positions (if available)
3. Local calculation (fallback)

This ensures Phase 14 backend work is not wasted.

---

## Files Involved

| File | Role | Status |
|------|------|--------|
| `src/layout/fan_layout.py` | Backend position calculation | ✅ Working correctly |
| `src/server/routes/tree_routes.py` | API - passes positions | ✅ Working correctly |
| `src/visualizer/tree_renderer.py` | Frontend - uses positions | ❌ Ignores backend for files |

---

*Audit completed: December 25, 2025*
*Author: Claude Opus 4.5*
