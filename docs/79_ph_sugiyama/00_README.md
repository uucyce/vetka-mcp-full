# 🔍 PHASE 79: AUDIT - Layer Mixing Investigation

**Status:** ✅ AUDIT COMPLETE (Reconnaissance only)
**Date:** 2026-01-21
**Investigator:** Claude Haiku 4.5 (Разведчик)

---

## 📂 Documents in This Folder

### 1️⃣ AUDIT_LAYER_MIXING.md

**🎯 Purpose:** Root cause analysis of visual tree corruption

**Contains:**
- Executive summary
- Three critical markers (A, B, C) for coder
- Root cause analysis (mode parameter ignored)
- Layer separation requirements
- Action items for implementation

**Key Findings:**
- ❌ API parameter `mode` exists but is never used
- ❌ `calculate_directory_fan_layout()` always called, even for Knowledge mode
- ⚠️ Single-file folders overlap with parent folder
- 🔴 CRITICAL: Mode parameter needs condition `if mode == "knowledge"`

---

### 2️⃣ DEPENDENCY_MAP_DIRECTED.md

**🎯 Purpose:** Complete documentation of DIRECTED MODE (folder structure)

**Contains:**
- Data flow diagram
- 5 core formulas with math
- File-to-code mapping
- Constants reference table
- Verification checkpoints

**Key Formulas:**
```python
folder_y = depth * Y_PER_DEPTH
folder_x = parent_x + sin(angle_rad) * adaptive_length
```

---

### 3️⃣ DEPENDENCY_MAP_KNOWLEDGE.md

**🎯 Purpose:** Complete documentation of KNOWLEDGE MODE (semantic clusters)

**Contains:**
- Data flow diagram
- 6 core formulas including KL (Knowledge Level)
- File-to-code mapping
- Edge type classification
- Verification checkpoints

**Key Formulas:**
```python
kl = 0.1 + (sigmoid * 0.75) + (rrf_score * 0.15)
file_spacing = BASE_FILE_SPACING * count_factor * variance_factor * kl_factor * depth_factor
```

---

### 4️⃣ PROJECT_EVOLUTION.md

**🎯 Purpose:** Reconstruct development history and identify what was broken

**Contains:**
- Vanilla era hypothesis
- Migration to React timeline
- Which formulas were new vs from Vanilla
- Root cause of current issues
- Investigation steps to verify Vanilla

---

## 🔴 CRITICAL ISSUES FOUND

### Issue #1: Mode Parameter Ignored ⚠️ CRITICAL

**Location:** `tree_routes.py:78-420`

**Problem:**
```python
@router.get("/data")
async def get_tree_data(
    mode: str = Query("directory", ...),  # Parameter taken
    request: Request = None
):
    ...
    positions = calculate_directory_fan_layout(...)  # 🔴 ALWAYS CALLED!
```

**Fix:** Add condition `if mode == "knowledge"`

---

### Issue #2: Single-File Folder Overlap ⚠️ MEDIUM

**Location:** `fan_layout.py:517-519`

**Problem:**
```python
y_offset = (i - mid_index) * FILE_SPACING
# When n_files=1: y_offset = 0 → file overlaps folder
```

---

### Issue #3: Knowledge Mode Unreachable ⚠️ HIGH

**Problem:** KNOWLEDGE mode fully implemented but inaccessible from main API

---

## 🧭 THREE LAYERS DISCOVERED

| Layer | Status | Issues |
|-------|--------|--------|
| **Data** (rescan_project.py) | ✅ Working | None |
| **Layout** (fan_layout.py + knowledge_layout.py) | ✅ Working | Not connected to API |
| **API** (tree_routes.py) | ❌ Broken | Mode parameter unused |

---

## 🎯 QUICK FIXES NEEDED

1. **Priority 1:** Add mode switching in `tree_routes.py:get_tree_data()` (30min)
2. **Priority 2:** Fix single-file overlap in `fan_layout.py:517-519` (15min)
3. **Priority 3:** Add frontend mode toggle (1-2hr)

---

## 📊 FORMULA QUICK REFERENCE

### DIRECTED Mode Y-Formula
```
Y = depth × Y_PER_DEPTH
```

### KNOWLEDGE Mode Y-Formula
```
Y = 0.1 + sigmoid(centrality) × 0.75 + RRF × 0.15
```

---

## 🚀 QUICK START

1. **Read:** AUDIT_LAYER_MIXING.md
2. **Locate:** tree_routes.py lines 78-82
3. **Add:** `if mode == "knowledge"` condition
4. **Call:** `build_knowledge_graph_from_qdrant()`
5. **Test:** Both modes

---

## ✅ AUDIT COMPLETE

All markers identified, all formulas documented, all dependencies mapped.

Ready for implementation phase.

🔍 Разведка завершена. Переходим к исправлению. 🎯
