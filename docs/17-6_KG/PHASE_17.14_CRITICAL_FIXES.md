# PHASE 17.14: CRITICAL FIXES - Knowledge Mode Layout Bugs

**Date:** 2025-12-26
**Status:** COMPLETED
**Files Modified:**
- `src/layout/knowledge_layout.py`
- `src/visualizer/tree_renderer.py`

---

## BUGS FIXED

### Bug 1: File Y Coordinates Going to INFINITY
**Symptom:** Console showed Y=1060, Y=2560, Y=5810 instead of reasonable values.

**Root Cause Analysis:** The backend code was actually correct! The formula:
```python
y = tag_y + FILE_START_OFFSET + (i * FILE_STEP_Y)
# With FILE_START_OFFSET=60, FILE_STEP_Y=50
# Result: 350+60+0*50=410, 350+60+1*50=460, etc.
```

**Fix:** Added enhanced diagnostic logging to backend to verify coordinates:
```python
# Phase 17.14: Log first 5 files with EXACT coordinates
for i, (fid, p) in enumerate(file_positions[:5]):
    logger.info(f"[KnowledgeLayout] FILE[{i}] id={fid} x={p['x']:.1f} y={p['y']:.1f}")

# SANITY CHECK: Y should be in range 150-2000 max
if max(y_vals) > 2000:
    logger.error(f"[KnowledgeLayout] BUG DETECTED! Y value too high: {max(y_vals):.0f}")
```

---

### Bug 2: All Files on SAME X Position
**Symptom:** All files had X=-105.0 (no fan spread visible).

**Root Cause:** In chain mode, all files in a chain got the same `chain_x_offset` with no variation:
```python
# OLD CODE - all files in chain get same X:
x = tag_x + chain_x_offset
```

**Fix:** Added fan spread WITHIN chains (lines 868-876):
```python
# Phase 17.14: X = chain base + small fan within chain
if num_files_in_chain > 1:
    file_normalized = (file_idx / (num_files_in_chain - 1)) - 0.5
    file_x_offset = file_normalized * (FILE_FAN_SPREAD * 0.5)
else:
    file_x_offset = 0

x = tag_x + chain_x_base + file_x_offset
```

**Result:**
- Chain 0, File 0: X = tag_x + 0 + (-20) = -20
- Chain 0, File 1: X = tag_x + 0 + (-10) = -10
- Chain 0, File 2: X = tag_x + 0 + (0) = 0
- Chain 0, File 3: X = tag_x + 0 + (+10) = +10
- Chain 0, File 4: X = tag_x + 0 + (+20) = +20

---

### Bug 3: Tags Named "Topic N" Instead of Real Names
**Symptom:** Tags showed generic names like "Topic 2", "Topic 3".

**Root Cause:** `_generate_tag_name_from_folders()` returned fallback when:
- file_metadata was empty
- No path info in metadata
- No common folders found

**Fix:** Enhanced naming with multi-strategy approach (lines 260-338):
```python
def _generate_tag_name_from_folders(...):
    """
    Phase 17.14: Multi-strategy tag naming

    Priority 1: Most common parent folder (at least 2 files)
    Priority 2: Common word from file names (at least 2 occurrences)
    Priority 3: Common path prefix
    Priority 4: Any folder name found
    Priority 5: Fallback to "Cluster N"
    """
    # Strategy 1: Count folder names
    folder_counts[folder_name] += 1

    # Strategy 2: Extract words from file names
    words = re.split(r'[_\-\.\s]+', name_no_ext)
    for word in words:
        if len(word) >= 3 and word not in common_words:
            word_counts[word] += 1

    # Return most meaningful name
    if folder_counts and max_count >= 2:
        return most_common_folder.capitalize()
    if word_counts and max_count >= 2:
        return most_common_word.capitalize()
    # ... more fallbacks
```

**Examples:**
- `/src/api/routes.py`, `/src/api/handlers.py` → "Api"
- `auth_login.py`, `auth_register.py` → "Auth"
- Mixed files with no pattern → "Cluster 1"

---

### Bug 4: Directory Mode Artifacts Visible in Knowledge Mode
**Symptom:** Old folder meshes, stems from Directory Mode still visible when switching to Knowledge Mode.

**Fix in `switchToKnowledgeMode()` (lines 7276-7306):**
```javascript
// === 3. HIDE ALL DIRECTORY MODE ELEMENTS ===
// Phase 17.14: Complete cleanup of Directory Mode artifacts

// Hide folder nodes AND all children (labels, etc.)
nodeObjects.forEach((nodeInfo, nodeId) => {
    if (nodeInfo.type === 'branch' || nodeInfo.type === 'root') {
        nodeInfo.mesh.visible = false;
        nodeInfo.mesh.traverse?.(child => { child.visible = false; });
    }
});

// Hide folder meshes AND all children
folderMeshes.forEach((mesh) => {
    mesh.visible = false;
    mesh.traverse?.(child => { child.visible = false; });
});

// HIDE ALL Directory Mode stems FIRST
branchMeshes.forEach((stem) => {
    stem.visible = false;
});
console.log('[MODE] Hidden', stemsHidden, 'Directory Mode stems');
```

**Fix in `switchToDirectoryMode()` (lines 7075-7168):**
```javascript
// === 3. SHOW FOLDERS ===
// Phase 17.14: Show folders AND all their children
nodeObjects.forEach((nodeInfo) => {
    if (isFolder) {
        nodeInfo.mesh.visible = true;
        nodeInfo.mesh.traverse?.(child => {
            child.visible = true;
            if (child.material) child.material.opacity = 0.9;
        });
    }
});

// === 8. SHOW FOLDER MESHES ===
folderMeshes.forEach((mesh) => {
    mesh.visible = true;
    mesh.traverse?.(child => {
        child.visible = true;
        if (child.material) child.material.opacity = 0.9;
    });
});
```

---

## VALIDATION CHECKLIST

After fixes, console should show:
```
[KnowledgeLayout] FILE[0] id=123 x=-40.0 y=410.0 z=0.0 tag=tag_0
[KnowledgeLayout] FILE[1] id=124 x=-20.0 y=460.0 z=0.0 tag=tag_0
[KnowledgeLayout] FILE[2] id=125 x=0.0 y=510.0 z=0.0 tag=tag_0
[KnowledgeLayout] FILE[3] id=126 x=20.0 y=560.0 z=0.0 tag=tag_0
[KnowledgeLayout] File X range: -40 to 40
[KnowledgeLayout] File Y range: 410 to 610

[MODE] Hidden 213 Directory Mode stems
[MODE] Showing 8 tags
```

Visual result:
```
           [Root Tag "Api"] Y=100
          /        |        \
    [Auth]     [Models]    [Utils]  Y=350
       |
  file file file file file  Y=410-610, X varied!
```

---

---

## ADDITIONAL FIX: JavaScript SyntaxError on Line 4493

**Symptom:** `SyntaxError: Unexpected string` at line 4492:98

**Root Cause:** Incorrect quote escaping in `onclick` attribute:
```javascript
// BROKEN (in generated HTML):
onclick="openArtifactModal(event, '' + (msg.artifact_type...) + '', ..."
//                               ^^  ← Two empty strings = syntax error!
```

**The Problem:**
Python triple-quoted string `'''...'''` contains `\'` which becomes `'` in output.
But inside HTML `onclick="..."` attribute, these single quotes broke the JavaScript.

**Fix (line 4563-4566):**
```javascript
// Use HTML entities &apos; instead of escaped quotes
const artType = String(msg.artifact_type || 'text').replace(/"/g, '&quot;');
const artAgent = String(msg.agent || 'Unknown').replace(/"/g, '&quot;');
html += '<a ... onclick="openArtifactModal(event, &apos;' + artType + '&apos;, &apos;' + artAgent + '&apos;); ...">';
```

**Also fixed:** Removed ES2020 `?.()` optional chaining with function calls (not supported in all browsers):
```javascript
// BEFORE (may cause syntax error in older browsers):
nodeInfo.mesh.traverse?.(child => { ... });

// AFTER (compatible):
if (nodeInfo.mesh.traverse) nodeInfo.mesh.traverse(child => { ... });
```

---

## Phase 17.14 ADDITIONAL FIXES (Post-Screenshot Analysis)

### Bug 5: File Y Explosion (Y=1060 → 5810)
**Root Cause:** 181 files in one chain × 50px step = 9050px height!
**Fix:** GRID layout instead of vertical chain (lines 875-909):
```python
# Files arranged in grid: 10 columns × N rows
GRID_COLS = MAX_CHAIN_LENGTH  # 10 files per row
row = file_idx // GRID_COLS
col = file_idx % GRID_COLS
y = tag_y + FILE_START_OFFSET + (row * GRID_CELL_Y)  # Max 18 rows for 181 files
```
**Result:** 181 files → 18 rows × 40px = 720px (instead of 9050px)

### Bug 6: All Files Same X (-105)
**Root Cause:** Chain X spread formula only worked for multiple chains
**Fix:** Grid column spread (lines 904-909):
```python
cols_in_row = min(GRID_COLS, num_files_in_chain - row * GRID_COLS)
col_offset = (col - (cols_in_row - 1) / 2) * GRID_CELL_X
x = tag_x + chain_x_base + col_offset
```
**Result:** Files spread horizontally in grid pattern

### Bug 7: Uncategorized Tag as Root
**Root Cause:** `tag_uncategorized` (noise files) was closest to global centroid
**Fix:** Exclude uncategorized from root selection (lines 390-401):
```python
if tag_id == 'tag_uncategorized' or tags[tag_id].name.lower() == 'uncategorized':
    continue  # Skip noise tag for root selection
```

---

## FILES CHANGED

### src/layout/knowledge_layout.py
| Line | Change |
|------|--------|
| 260-338 | Rewrote `_generate_tag_name_from_folders()` with multi-strategy naming |
| 390-401 | Exclude uncategorized from root tag selection |
| 709 | Added `MAX_CHAIN_LENGTH = 10` constant |
| 875-909 | Replaced vertical chain with GRID layout |
| 945-958 | Enhanced diagnostic logging with sanity checks |

### src/visualizer/tree_renderer.py
| Line | Change |
|------|--------|
| 7276-7306 | Added complete Directory Mode hiding with traverse() |
| 7075-7090 | Added traverse() for showing folder children |
| 7157-7168 | Added traverse() for folder meshes restoration |

---

## CONSTANTS REFERENCE

```python
# Tag Layout
TAG_Y_BASE = 100              # Root tag Y position
TAG_LAYER_HEIGHT = 250        # Y gap between tag levels
TAG_SIBLING_SPREAD = 350      # X spread between sibling tags

# File Layout
FILE_START_OFFSET = 60        # Y gap from tag to first file
FILE_STEP_Y = 50              # Y gap between files (going DOWN)
FILE_FAN_SPREAD = 80          # X spread for files

# Expected Results:
# Tag at Y=350 with 5 files:
#   File 0: Y=410, X=-40
#   File 1: Y=460, X=-20
#   File 2: Y=510, X=0
#   File 3: Y=560, X=+20
#   File 4: Y=610, X=+40
```
