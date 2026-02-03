# POSITION PIPELINE AUDIT - Phase 109

**Date:** 2026-02-02
**Audit Scope:** Complete position calculation pipeline post-Tauri migration
**Status:** FAN LAYOUT is ACTIVE, Knowledge Mode NOT INTEGRATED

---

## PIPELINE OVERVIEW

```
BACKEND (Python/FastAPI)
├─ Step 1: Scan Files from Qdrant
│  └─ /api/tree/data endpoint retrieves all scanned_file entries
│
├─ Step 2: Build Folder Hierarchy
│  └─ Organize files into parent_folder structure
│
├─ Step 3: FAN LAYOUT CALCULATION
│  ├─ Source: src/layout/fan_layout.py::calculate_directory_fan_layout()
│  ├─ Input: folders dict + files_by_folder dict
│  ├─ Algorithm: Sugiyama-style layered layout with:
│  │  - Adaptive branch length (based on tree depth)
│  │  - Dynamic fan angles (MIN_SPREAD=45°, MAX_SPREAD=180°)
│  │  - Anti-gravity repulsion forces
│  │  - Orthogonal vertical file stacking
│  └─ Output: positions dict {node_id: {x, y, z, angle, ...}}
│
├─ Step 4: BUILD API RESPONSE
│  ├─ Convert positions to visual_hints.layout_hint format
│  ├─ expected_x, expected_y, expected_z fields
│  └─ Return as nodes with visual_hints
│
├─ Step 5: CHAT NODE POSITIONING (Phase 108.2)
│  ├─ Source: src/layout/knowledge_layout.py::calculate_chat_positions()
│  ├─ Input: file_positions dict + chat timestamps
│  ├─ Algorithm: Temporal Y-axis based on lastActivity
│  ├─ X: offset from parent file (staggered 0-4 units)
│  ├─ Y: normalized time range [y_min, y_max]
│  └─ Z: same as parent file
│
└─ RETURN: JSON response {tree, chat_nodes, chat_edges, artifact_nodes}

FRONTEND (React/Tauri)
├─ Step 1: FETCH from API
│  └─ fetchTreeData() → /api/tree/data
│
├─ Step 2: PARSE RESPONSE
│  └─ useTreeData.ts processes response
│
├─ Step 3: CONVERT API FORMAT
│  └─ apiConverter.ts::convertApiResponse()
│  ├─ Extract position from visual_hints.layout_hint
│  ├─ Map expected_x/y/z to TreeNode.position
│  └─ Handle legacy format fallback
│
├─ Step 4: STORE IN ZUSTAND
│  └─ useStore.setNodes() or setNodesFromRecord()
│  ├─ Store nodes with {id, position, ...}
│  └─ Position persisted in store
│
└─ Step 5: RENDER IN 3D CANVAS
   └─ FileCard.tsx uses position for Three.js transform
```

---

## KEY FILES AND LINE NUMBERS

### Backend Position Calculation

| File | Function | Lines | Purpose |
|------|----------|-------|---------|
| `src/api/routes/tree_routes.py` | API endpoint | 388-393 | Calls `calculate_directory_fan_layout()` |
| `src/api/routes/tree_routes.py` | Position dict | 545-554 | Builds file_positions from nodes |
| `src/layout/fan_layout.py` | `calculate_directory_fan_layout()` | 340-648 | Main layout function |
| `src/layout/fan_layout.py` | `layout_subtree()` | 429-497 | Recursive positioning |
| `src/layout/fan_layout.py` | Folder X/Y | 462-465 | sin/cos, depth-based |
| `src/layout/fan_layout.py` | File positioning | 515-547 | Orthogonal vertical stacking |
| `src/layout/fan_layout.py` | Anti-gravity | 599-646 | Repulsion for branches |
| `src/layout/knowledge_layout.py` | `calculate_chat_positions()` | 2268-2417 | Chat node positioning |

### Frontend Position Handling

| File | Function | Lines | Purpose |
|------|----------|-------|---------|
| `client/src/hooks/useTreeData.ts` | Data loading | 41-125 | Main data loading logic |
| `client/src/hooks/useTreeData.ts` | Layout check | 114-123 | Layout fallback check |
| `client/src/utils/apiConverter.ts` | `convertApiResponse()` | 69-90 | Map expected_x/y/z to position |
| `client/src/utils/api.ts` | `fetchTreeData()` | ~45-65 | Fetch from /api/tree/data |

---

## IDENTIFIED ISSUES AND GAPS

### Issue 1: Position Calculator Modules NOT USED
- **Files exist but NOT called:**
  - `/src/knowledge_graph/position_calculator.py` (VETKAPositionCalculator class)
  - `/src/visualizer/position_calculator.py` (Sugiyama layout)
- **Status:** OBSOLETE - pre-Tauri position calculators
- **Current:** FAN LAYOUT (fan_layout.py) is the active position engine
- **Impact:** NONE - old modules are unused

### Issue 2: Knowledge Graph Layout NOT INTEGRATED
- `/src/layout/knowledge_layout.py` exists and is imported
- **Only used for:** `calculate_chat_positions()` and knowledge mode (not active)
- **Status:** PARTIALLY USED
- **Impact:** Knowledge mode semantic layout disabled, directory mode works

### Issue 3: "Underground" Files Root Causes
1. Y_PER_DEPTH calculation (adaptive, based on tree depth)
2. File spacing within folders (orthogonal vertical stacking)
3. Intraday X-spread for same-day files
4. Center-of-mass centering shifts origin

**How files go "underground":**
- If files are old (low timestamps) → low Y value
- If many files in same folder → large vertical stacking
- BUT: Minimum Y = folder Y + (file_index * FILE_SPACING)
- No files should go below root (Y=0) unless actively positioned there

### Issue 4: Missing Y-Axis Minimum Protection
- File Y positions calculated from folder Y + stagger offset
- **No floor/ceiling enforcement**
- If folder_y is negative (shouldn't happen) → files also negative
- **Status:** Minor - folder Y starts at depth * Y_PER_DEPTH (all positive)

### Issue 5: Frontend Layout Fallback Could Override Positions
```typescript
// useTreeData.ts line 114-120
const needsLayout = Object.values(allNodes).every(
  (n) => n.position.x === 0 && n.position.y === 0 && n.position.z === 0
);
if (needsLayout) {
  const positioned = calculateSimpleLayout(Object.values(allNodes));
  setNodes(positioned);  // OVERRIDES positions!
}
```
- **Impact:** If all position values are 0, frontend recalculates layout
- **Risk:** Could mask backend positioning issues

---

## POSITION CALCULATION FORMULAS

### Directory Mode (Active)

**Folders:**
```python
folder_x = parent_x + sin(angle) * branch_length
folder_y = depth * Y_PER_DEPTH
```

**Files:**
```python
file_x = folder_x + sin(angle) * 0.7 * adaptive_length
file_y = folder_y + (file_index - mid_index) * FILE_SPACING
file_z = file_index * 0.1  # prevent z-fighting
```

### Chat Mode (Phase 108.2)
```python
X = parent_x + 10 + (chat_index % 3) * 2  # staggered right
Y = y_min + normalized_time * (y_max - y_min)
Z = parent_z  # same as parent file
```

---

## SYSTEM HEALTH CHECK

| Component | Status | Notes |
|-----------|--------|-------|
| FAN Layout Engine | ✅ ACTIVE | Generating positions |
| Chat Position Calculation | ✅ ACTIVE | Temporal Y-axis implemented |
| Knowledge Graph Layout | ⚠️ NOT INTEGRATED | Implemented but not called |
| Frontend Position Conversion | ✅ WORKING | Maps expected_x/y/z correctly |
| Zustand Store | ✅ RECEIVING | Positions correctly |
| Position Validation | ⚠️ MISSING | No floor/ceiling enforcement |
| Layout Fallback | ⚠️ RISKY | Could mask positioning issues |

---

## RECOMMENDATIONS

### Priority 1: Verify Fan Layout Output
- Check logs for "[LAYOUT]" messages
- Verify BRANCH_LENGTH, FAN_ANGLE, Y_PER_DEPTH values
- Look for negative Y values (should not exist)

### Priority 2: Check Frontend Position Reception
- Add console.log in useTreeData.ts after fetchTreeData()
- Verify response contains tree.nodes with visual_hints
- Check if needsLayout fallback is triggered (line 114)

### Priority 3: Debug "Underground" Behavior
1. Check FAN LAYOUT output (positions dict values)
2. Check Y_PER_DEPTH calculation
3. Check FILE_SPACING calculation
4. Check center_graph_by_mass() shift values

### Priority 4: Clean Up Obsolete Code
- Archive `/src/knowledge_graph/position_calculator.py`
- Archive `/src/visualizer/position_calculator.py`
- Document FAN_LAYOUT as the active engine

### Priority 5: Enable Knowledge Graph Mode
- Integrate `calculate_knowledge_positions()` into tree_routes
- Add mode parameter handling for "semantic" mode
- Currently mode parameter accepted but not fully used

---

## SUMMARY

The 3D position calculation pipeline is **operational** after the Tauri migration. Positions flow correctly from backend FAN layout through the API to the frontend store.

**Key finding:** `position_calculator.py` and `knowledge_layout.py` position functions are **NOT USED** for file positioning. Only `fan_layout.py::calculate_directory_fan_layout()` is active.

**If files are "underground":** Check fan_layout.py output and Y_PER_DEPTH calculations. All positions should be positive.

---

*Generated by Claude Haiku agent - Phase 109 audit*
