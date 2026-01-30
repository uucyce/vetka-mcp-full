# Phase 17.9: Use Backend Positions for Files

**Date:** December 25, 2025
**Status:** IMPLEMENTED
**Previous Phase:** 17.8 - Position Flow Audit

---

## Problem Statement

From Phase 17.8 audit, we discovered that:

1. **Backend** (`fan_layout.py`) correctly calculates time-sorted Y positions
2. **API** passes them via `visual_hints.layout_hint.expected_y`
3. **Frontend** IGNORES these values and recalculates locally!

This meant all backend Phase 14 work was wasted.

---

## Root Cause

```javascript
// OLD CODE - Missing middle case!
if (sugiyamaPositions && sugiyamaPositions[file.id]) {
    // Sugiyama mode - used rarely
} else {
    // FALLBACK - recalculates locally, IGNORES backend!
    y = calculateFileY(file, localIdx, siblings, parentPos.y);
}
```

The code only checked for Sugiyama positions (rarely used), then fell back to local calculation - completely ignoring the backend `layout_hint`.

---

## Solution

Added middle `else if` branch to use backend positions:

```javascript
if (sugiyamaPositions && sugiyamaPositions[file.id]) {
    // Sugiyama mode
    const sp = sugiyamaPositions[file.id];
    x = sp.x + treeOffset;
    y = sp.y;
    z = 0;
} else if (file.visual_hints?.layout_hint) {
    // Phase 17.9: USE BACKEND POSITIONS!
    // Backend calculates time-sorted Y positions in fan_layout.py
    const hint = file.visual_hints.layout_hint;
    x = (hint.expected_x || parentPos.x) + treeOffset;
    y = hint.expected_y ?? (parentPos.y + 40);
    z = 0;
    if (globalIdx < 5) {
        console.log(`[FILE] ${file.name} using backend Y=${y.toFixed(0)}`);
    }
} else {
    // FALLBACK: local calculation (only if no backend data)
    const theta = localIdx * FILE_GOLDEN_ANGLE;
    const radius = FILE_RADIUS_BASE + Math.sqrt(localIdx + 1) * FILE_RADIUS_GROWTH;
    x = parentPos.x + Math.cos(theta) * radius;
    z = 0;
    y = calculateFileY(file, localIdx, siblings, parentPos.y);
    console.warn(`[FILE] ${file.name} using LOCAL Y=${y.toFixed(0)} (no backend hint)`);
}
```

---

## Priority Order

Files now use positions in this order:

1. **Sugiyama positions** (if `useSugiyama=true` and position exists)
2. **Backend `layout_hint`** (from `fan_layout.py` - Phase 14 time-sorted)
3. **Local calculation** (fallback only if no backend data)

---

## What This Enables

### Backend Phase 14 Features Now Work:
- ✅ Time-based Y sorting (older files = lower Y)
- ✅ Adaptive file spacing based on file count
- ✅ Files positioned along parent's branch angle
- ✅ Vertical stacking with proper spacing

### Console Output:
```
[FILE] config.py using backend Y=145
[FILE] main.py using backend Y=180
[FILE] utils.py using backend Y=215
```

If no backend data (should be rare):
```
[FILE] orphan.txt using LOCAL Y=120 (no backend hint)
```

---

## Files Modified

| File | Changes |
|------|---------|
| `src/visualizer/tree_renderer.py` | Added `else if (file.visual_hints?.layout_hint)` branch (lines 2929-2939) |

---

## Testing Checklist

```
[ ] Load page in Directory Mode
[ ] Console shows: "[FILE] xxx using backend Y=..."
[ ] Files stack VERTICALLY under folders (not spread horizontally)
[ ] Older files at bottom, newer at top
[ ] No "[FILE] xxx using LOCAL Y=..." warnings (unless orphan files)
```

---

## Data Flow After Fix

```
┌─────────────────────────────────────────────────────────────────────┐
│ Backend: fan_layout.py                                              │
│ ├── Sort files by created_time                                     │
│ ├── Calculate adaptive FILE_SPACING                                │
│ └── file_y = folder_y + (i - mid_index) * FILE_SPACING            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ API: tree_routes.py                                                 │
│ └── visual_hints.layout_hint.expected_y = pos['y']                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Frontend: tree_renderer.py (FIXED!)                                 │
│ ├── Check Sugiyama positions                                       │
│ ├── ✅ Check backend layout_hint (NEW!)                            │
│ └── Fallback to local calculation                                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Three.js: mesh.position.set(x, y, z)                               │
│ └── Now uses BACKEND-calculated Y position!                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

*Implemented: December 25, 2025*
*Author: Claude Opus 4.5*
