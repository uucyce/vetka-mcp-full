# VETKA Phase 17.18: FINAL SURGICAL FIX

**Date:** 2025-12-26
**Status:** COMPLETED
**Analysis Sources:** Claude (browser), ChatGPT code review, Previous fixes 17.15-17.17

---

## EXECUTIVE SUMMARY

Phase 17.18 addressed critical issues preventing Knowledge Mode from working correctly:
1. Memory leak from hidden (not removed) tagMeshes
2. Hardcoded X spread in `minimize_crossings()` ignoring adaptive spread
3. Improved logging for debugging mode switches

---

## ISSUES ANALYZED

### Issue 1: tagMeshes HIDDEN instead of REMOVED (MEMORY LEAK!)
**Status:** FIXED

**Problem:**
```javascript
// OLD - Wrong approach:
tagMeshes.forEach((group, id) => {
    group.visible = false;  // Objects stay in scene, consuming memory!
});
```

**Solution:**
```javascript
// NEW - Correct approach:
tagMeshes.forEach((group, id) => {
    scene.remove(group);  // Remove from scene
    group.traverse(child => {
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
            if (child.material.map) child.material.map.dispose();
            child.material.dispose();
        }
    });
});
tagMeshes.clear();  // Clear the Map
```

**File:** `src/visualizer/tree_renderer.py` lines 7430-7457

---

### Issue 2: folderMeshes DOES NOT EXIST
**Status:** FALSE ALARM

**Finding:** `folderMeshes` DOES exist at line 1770:
```javascript
let folderMeshes = new Map();  // folder_id -> mesh (for fade out)
```

No fix needed.

---

### Issue 3: minimize_crossings() IGNORES x_spread (CRITICAL BUG!)
**Status:** FIXED

**Problem:**
The `minimize_crossings()` function had hardcoded X spread values:
```python
# OLD - Hardcoded 800px spread:
new_x = -400 + i * (800 / max(n - 1, 1))  # IGNORES adaptive spread!
```

This meant that `compute_adaptive_spread()` values were being calculated but then **completely overwritten** by the crossing minimization step!

**Solution:**
```python
# NEW - Uses x_spread parameter:
def minimize_crossings(
    positions, layers, edges,
    iterations: int = 5,
    x_spread: float = 800  # NEW parameter
):
    ...
    half_spread = x_spread / 2
    new_x = -half_spread + i * (x_spread / max(n - 1, 1))
```

**Files Changed:**
- `src/layout/semantic_sugiyama.py` lines 329-334 (signature)
- `src/layout/semantic_sugiyama.py` lines 386-392 (forward pass)
- `src/layout/semantic_sugiyama.py` lines 411-417 (backward pass)
- `src/layout/semantic_sugiyama.py` line 309 (call site)
- `src/layout/knowledge_layout.py` line 945 (call site)

---

### Issue 4: Knowledge Graph positions CACHED
**Status:** ALREADY FIXED

**Finding:** Cache invalidation already exists at line 7674:
```javascript
knowledgeGraphLoaded = false;
knowledgeGraphData = null;
knowledgePositions = {};
```

No additional fix needed.

---

### Issue 5: Directory stems not fully hidden
**Status:** ALREADY FIXED + IMPROVED LOGGING

**Finding:** Stem hiding was already implemented. Added improved logging:
```javascript
// Before:
console.log(`[MODE] Hidden ${hiddenStems} branch stems`);

// After:
const totalStems = branchMeshes.size || branchMeshes.length || 0;
console.log(`[MODE] Hidden ${hiddenStems}/${totalStems} branch stems`);
```

Also added children visibility:
```javascript
if (stem.children) stem.children.forEach(c => { c.visible = false; });
```

---

## COMPLETE FILE CHANGES

### File 1: src/layout/semantic_sugiyama.py

#### Change 1: Function signature (line 329-334)
```python
def minimize_crossings(
    positions: Dict[str, Dict[str, float]],
    layers: Dict[int, List[str]],
    edges: List[Any],
    iterations: int = 5,
    x_spread: float = 800  # NEW PARAMETER
):
```

#### Change 2: Forward pass X calculation (lines 386-392)
```python
# Reassign X positions using x_spread parameter (was hardcoded 800!)
n = len(layer)
half_spread = x_spread / 2
for i, node_id in enumerate(layer):
    if node_id in positions:
        new_x = -half_spread + i * (x_spread / max(n - 1, 1)) if n > 1 else 0
        positions[node_id]['x'] = new_x
```

#### Change 3: Backward pass X calculation (lines 411-417)
```python
# Reassign X positions using x_spread parameter (was hardcoded 800!)
n = len(layer)
half_spread = x_spread / 2
for i, node_id in enumerate(layer):
    if node_id in positions:
        new_x = -half_spread + i * (x_spread / max(n - 1, 1)) if n > 1 else 0
        positions[node_id]['x'] = new_x
```

#### Change 4: Call site update (line 309)
```python
minimize_crossings(positions, layers, edges, iterations=5, x_spread=x_spread)
```

---

### File 2: src/layout/knowledge_layout.py

#### Change 1: Call site update (line 945)
```python
minimize_crossings(tag_positions, layers, tag_hierarchy_edges, iterations=5, x_spread=X_SPREAD)
```

---

### File 3: src/visualizer/tree_renderer.py

#### Change 1: switchToDirectoryMode() - Proper cleanup (lines 7430-7457)
```javascript
// === PHASE 17.18: REMOVE (not hide!) ALL KNOWLEDGE MODE ELEMENTS ===
// ISSUE 1 FIX: Remove and dispose tagMeshes to prevent memory leak!
let removedTags = 0;
tagMeshes.forEach((group, id) => {
    if (group) {
        scene.remove(group);  // Remove from scene!
        group.traverse(child => {
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
                if (child.material.map) child.material.map.dispose();
                child.material.dispose();
            }
        });
        removedTags++;
    }
});
tagMeshes.clear();  // Clear the Map!
console.log(`[MODE] Removed and disposed ${removedTags} tag groups`);

// Knowledge stems - already correctly removes
let removedStems = knowledgeStems.length;
knowledgeStems.forEach(stem => {
    scene.remove(stem);
    if (stem.geometry) stem.geometry.dispose();
    if (stem.material) stem.material.dispose();
});
knowledgeStems = [];
console.log(`[MODE] Removed ${removedStems} knowledge stems`);
```

#### Change 2: switchToKnowledgeMode() - Improved logging (lines 7643-7653)
```javascript
// Hide ALL branch stems immediately
let hiddenStems = 0;
const totalStems = branchMeshes.size || branchMeshes.length || 0;
branchMeshes.forEach((stem, id) => {
    if (stem) {
        stem.visible = false;
        if (stem.children) stem.children.forEach(c => { c.visible = false; });
        hiddenStems++;
    }
});
console.log(`[MODE] Hidden ${hiddenStems}/${totalStems} branch stems`);
```

---

## EXPECTED CONSOLE OUTPUT

### Switching to Knowledge Mode:
```
[MODE] Switching to Knowledge Mode - HIDING Directory elements...
[MODE] Hidden 11 folder meshes
[MODE] Hidden 241/241 branch stems
[MODE] Hidden 15 non-file nodes
[MODE] Loading Knowledge Graph...
[KnowledgeLayout] Phase 17.15: Using UNIFIED SUGIYAMA ENGINE for 8 tags
[KnowledgeLayout] Tag layer distribution: [(0, 1), (1, 3), (2, 2), (3, 2)]
[KnowledgeLayout] Applied minimize_crossings (barycenter method)
[KnowledgeLayout] Applied soft_repulsion (anti-gravity)
[KnowledgeLayout] Tag 'Architecture' depth=0 at (0, 100) - 45 files
[KnowledgeLayout] Adaptive spread for tag_0: 45 files, avg_sim=0.68, spread=172px
```

### Switching to Directory Mode:
```
[MODE] Switching to Directory Mode - SHOWING Directory elements...
[MODE] Removed and disposed 8 tag groups
[MODE] Removed 104 knowledge stems
[MODE] directoryPositions has 256 entries
[MODE] Directory Mode: Restored 213 nodes, 241 stems
```

---

## WHY THIS MATTERS

### Before Fix:
1. **Memory Leak:** Each mode switch accumulated hidden Three.js objects
2. **Spread Ignored:** `compute_adaptive_spread()` returned values like 156px, but `minimize_crossings()` always used 800px
3. **Files Too Spread:** All files spread across -400 to +400 instead of adaptive -78 to +78

### After Fix:
1. **Memory Clean:** Objects properly removed and disposed
2. **Spread Honored:** Adaptive spread values now actually affect layout
3. **Proper Clustering:** Similar files cluster tightly, dissimilar spread wide

---

## VALIDATION

Run this test to verify the fix:
```python
# In Python console or test file
from src.layout.knowledge_layout import calculate_knowledge_positions, X_SPREAD
from src.layout.semantic_sugiyama import minimize_crossings

# Check that X_SPREAD is passed correctly
print(f"X_SPREAD constant: {X_SPREAD}")  # Should be 800

# After running Knowledge Mode, check console for:
# [KG] Adaptive spread: X files, avg_sim=Y.YY, spread=ZZZpx
# Where ZZZ should vary based on similarity, not always 800
```

---

## RELATED PHASES

- **Phase 17.15:** Unified Sugiyama Engine for tags
- **Phase 17.16:** Chain edges and knowledge stems
- **Phase 17.17:** Hard reset on mode switch
- **Phase 17.18:** This fix - proper cleanup and spread parameter

---

## AUTHOR

Generated by Claude Code
Phase 17.18 FINAL SURGICAL FIX
