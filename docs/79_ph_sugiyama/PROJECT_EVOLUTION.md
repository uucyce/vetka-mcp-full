# 📚 PROJECT EVOLUTION: Vanilla → React (Reconstruction)

**Дата:** 2026-01-21
**Цель:** Восстановить логику развития VETKA, понять какие формулы остались, какие новые появились

---

## 📖 CHAPTER 1: VANILLA ERA (Pre-React)

### What We Know

На Vanilla-версии было **два слоя деревьев**, которые конфликтовали:

1. **DIRECTED MODE:** Иерархия папок
2. **KNOWLEDGE MODE:** Семантические теги

**Проблемы Vanilla-версии:**
- Деревья "хреновые" (по вашему описанию) в **обоих режимах**
- Коллизии между формулами (вероятно в одном файле)
- Проблема с Y-координатами (depth vs KL путались)
- Наложения узлов

### Гипотеза о структуре Vanilla

```
OLD VANILLA STRUCTURE (Hypothesis):
src/
  ├─ tree_layout.py (or similar)
  │   ├─ layout_directed()  ← formula 1 (depth-based)
  │   ├─ layout_knowledge()  ← formula 2 (KL-based)
  │   └─ [PROBLEM] Switching logic broken
  │
  ├─ formulas.py (maybe)
  │   ├─ Y_PER_DEPTH calculation
  │   ├─ KL computation
  │   └─ Edge building
  │
  └─ server.py (Flask?)
      └─ @app.route("/tree?mode=...")  [parameter ignored?]
```

**Симптомы Vanilla:**
- Branch overlap
- Files on same Y as folders
- Mode parameter didn't actually switch layout

---

## 🔄 CHAPTER 2: MIGRATION TO REACT (Current)

### What Changed

#### ✅ GOOD CHANGES

1. **Separation of Concerns:**
   - `fan_layout.py` (DIRECTED mode ONLY)
   - `knowledge_layout.py` (KNOWLEDGE mode ONLY)
   - Формулы больше не混合

2. **Advanced Formulas Added:**
   - Adaptive branch length: `calculate_branch_length()`
   - Adaptive file spacing: `calculate_file_spacing_adaptive()`
   - Adaptive layer height: `calculate_layer_height_vertical()`
   - Anti-gravity repulsion: `calculate_static_repulsion()`
   - Dynamic angle spread: `calculate_dynamic_angle_spread()`

3. **Phase 22 v4 (New):**
   - INTAKE branch for unclassified files
   - Auto-relocation logic
   - Enhanced KL formula with sigmoid

4. **API Changes:**
   - FastAPI (вместо Flask)
   - Better caching (`_semantic_cache`, `_knowledge_graph_cache`)
   - Query parameters for mode

#### ❌ PROBLEMS INTRODUCED

1. **Mode Parameter Broken:**
   - Принимается параметр `mode`
   - **НО никогда не используется**
   - `calculate_directory_fan_layout()` вызывается **всегда**
   - Режим KNOWLEDGE никогда не активируется в `get_tree_data()`

2. **Incomplete Knowledge Endpoint:**
   - Отдельный endpoint `/knowledge-graph` существует
   - **НО** основной `/tree/data` его не использует
   - Клиент не может переключаться между режимами

3. **Code Smell:**
   - Строка 80 (tree_routes.py): параметр `mode`
   - Строка 266-271: жесткий код DIRECTED layout
   - Нет условия `if mode == "knowledge"`

---

## 🔍 FORMULA ARCHAEOLOGY

### Formulas FROM Vanilla (гипотеза)

Судя по коду, эти формулы вероятно были в Vanilla:

```python
# FORMULA 1: Basic Y position
folder_y = depth * LAYER_SPACING
# VANILLA: LAYER_SPACING was probably fixed (200px?)
# REACT: LAYER_SPACING = calculate_layer_height_vertical() (adaptive)

# FORMULA 2: Basic Knowledge Level
kl = (1.0 - centrality) * 0.8 + bonus
# VANILLA: Simple linear (probably)
# REACT: Added sigmoid smoothing + RRF boost
```

---

### Formulas NEWLY CREATED in React

```python
# Phase 27.9: Adaptive branch length
BRANCH_LENGTH = calculate_branch_length(max_depth, max_folders_per_layer)
# Replaces hard-coded 300px → now 150-400px range

# Phase 14: Anti-gravity repulsion
calculate_static_repulsion(folders_at_depth, positions, ...)
# Completely new in React

# Phase 22 v4: Enhanced KL with sigmoid
sigmoid = 1.0 / (1.0 + exp(-10 * (normalized - 0.5)))
# Smooths the knowledge level distribution

# Phase 22 v4: INTAKE branch
INTAKE_TAG_ID = '_intake'  # Auto-relocate unclassified files
# Completely new workflow
```

---

### Formulas THAT MIGHT STILL BE BROKEN

```python
# FORMULA 3: File spacing (single file problem)
mid_index = (n_files - 1) / 2.0
y_offset = (i - mid_index) * FILE_SPACING
# When n_files=1: y_offset = 0 → file overlaps folder
# This issue might have existed in Vanilla too
```

---

## 🧩 RECONSTRUCTED DEVELOPMENT TIMELINE

```
PHASE 1: Vanilla (unknown date)
  ├─ Basic folder tree layout
  ├─ Knowledge graph experiment (failed?)
  ├─ Two conflicting formulas
  └─ Result: "хреновое дерево" (bad tree)

PHASE 2: Early React Migration (Phase 15-20?)
  ├─ Rewrite to React components
  ├─ Separate tree_routes.py (FastAPI)
  ├─ Create fan_layout.py for DIRECTED
  ├─ Create knowledge_layout.py for KNOWLEDGE
  └─ [But forgot to wire them together!]

PHASE 3: Adaptive Formulas (Phase 27.9)
  ├─ Add calculate_branch_length()
  ├─ Add calculate_file_spacing_adaptive()
  ├─ Add calculate_layer_height_vertical()
  ├─ Add calculate_dynamic_angle_spread()
  ├─ Result: More sophisticated layout
  └─ [Still no mode switching in get_tree_data()]

PHASE 4: Anti-gravity & Crossing Reduction (Phase 14)
  ├─ Add calculate_static_repulsion()
  ├─ Add minimize_crossing_barycenter()
  ├─ Prevent branch overlapping
  └─ [Branches fixed, but files still broken]

PHASE 5: Phase 22 v4 (Recent)
  ├─ Add INTAKE branch concept
  ├─ Add auto_relocate_from_intake()
  ├─ Add enhanced KL formula with sigmoid
  ├─ Add file spacing adaptive formulas
  ├─ Add RRF boost to KL
  └─ [All in knowledge_layout.py, separate from DIRECTED]

PHASE 76+: Rescan Infrastructure
  ├─ Fix parent_folder calculation (line 402-406)
  ├─ parent_folder = os.path.dirname(rel_path)  [WAS: always first segment]
  ├─ Result: Correct hierarchy in Qdrant
  └─ [But API still doesn't use this properly!]

CURRENT (Phase 79):
  ├─ Detect layer mixing issue
  ├─ Create audit documents
  └─ [Ready for fix!]
```

---

## 🔬 WHAT WAS LOST/BROKEN IN MIGRATION

### Issue 1: Mode Switching Lost

**Vanilla:** Probably had `layout_mode()` function or similar
**React:** Has `mode` parameter but doesn't use it
**Impact:** Cannot switch between DIRECTED and KNOWLEDGE in main endpoint

---

### Issue 2: File-Folder Nagging Lost

**Vanilla:** Probably had some offset logic
**React:** `y_offset = (i - mid_index) * FILE_SPACING`
**Problem:** When n_files=1, offset=0 → overlap
**Theory:** Vanilla had the same bug? Or it was "fixed" but broke in migration?

---

### Issue 3: Formulas Got Split

**Vanilla:** Everything in one place (messy but at least connected)
**React:** Split between fan_layout.py and knowledge_layout.py (cleaner but disconnected)
**Impact:** No unified view of how modes interact

---

## 🎯 WHAT ACTUALLY WORKS NOW

### ✅ DIRECTED MODE (mostly works)

- `calculate_directory_fan_layout()` correctly computes positions
- Y = depth * Y_PER_DEPTH ✅
- Fan spread works ✅
- Anti-gravity repulsion works ✅
- Files stack in folders ✅ (except overlap with single file)

**Status:** 80% ready, need single-file fix

---

### ✅ KNOWLEDGE MODE (exists but unreachable)

- `/knowledge-graph` endpoint works ✅
- `build_knowledge_graph_from_qdrant()` exists ✅
- Clustering with HDBSCAN ✅
- KL computation ✅
- INTAKE branch logic ✅
- Edge classification ✅

**Status:** 100% implemented, 0% used (no mode switching)

---

## 🚨 ROOT CAUSE: HOW DID WE GET HERE?

**Theory:**

1. **React migration was bottom-up:**
   - Created fan_layout.py first (DIRECTED works)
   - Created knowledge_layout.py next (KNOWLEDGE works)
   - But never connected them in the API

2. **API was incomplete:**
   - `tree_routes.py` was created to use DIRECTED layout
   - Parameters added (`mode: str = Query(...)`)
   - But parameter never actually used
   - Probably meant to be added "later"

3. **Testing Gap:**
   - DIRECTED mode visually works → looks "done"
   - KNOWLEDGE endpoint exists but unreachable
   - Nobody tested `?mode=knowledge`

4. **Vanilla Baggage:**
   - Single-file overlap issue might have been from Vanilla
   - Never properly debugged in React migration
   - Fixed "manually" in UI (you moved it with mouse)

---

## 💡 WHAT VANILLA PROBABLY HAD

### Constants (guessing based on React code)

```python
# Vanilla probably had:
BASE_RADIUS = 150          # ✅ Still in React
Y_PER_DEPTH = 200          # ✅ Now adaptive, was fixed
FAN_ANGLE = 130            # ✅ Still in React
FILE_SPACING = 40          # ✅ Now adaptive, was fixed

# But probably didn't have:
MIN_SPREAD = 45            # ❌ Not in Vanilla (added Phase 27.9)
DEPTH_DECAY_FLOOR = 0.4    # ❌ Not in Vanilla (added Phase 27.9)
```

### Formulas (guessing)

```python
# Vanilla simple version:
folder_y = depth * 200  # Fixed
folder_x = sin(angle) * 150  # Fixed

# Vanilla KL (guessing):
kl = (1.0 - centrality) + random_boost  # No sigmoid
```

---

## 📝 FORMULAS REQUIRING INVESTIGATION

### Formula A: Repulsion strength

**Current (fan_layout.py:200):**
```python
strength_factor = max(0.6, (max_depth - depth) / max(max_depth, 1))
repulsion_strength = 100 * strength_factor
```

**Question:** Was this adaptive in Vanilla or fixed?

---

### Formula B: Anti-gravity iterations

**Current (fan_layout.py:204):**
```python
for iteration in range(10):  # 10 passes
```

**Question:** Why 10? Was this optimized through testing?

---

### Formula C: RRF boost

**Current (knowledge_layout.py:229):**
```python
rrf_boost = rrf_score * 0.15  # Max +0.15
```

**Question:** Why 0.15? Is this tuned or placeholder?

---

## 🎓 LESSONS FOR NEXT PHASE

### ✅ DO

1. **Test both modes:** Create test cases for `?mode=directory` vs `?mode=knowledge`
2. **Document transitions:** Explain why formulas were split
3. **Add conditional logic:** Clearly if/elif the two modes
4. **Verify positions:** Check that Y values match expected ranges

### ❌ DON'T

1. **Merge files back:** Keep separation (fan_layout.py vs knowledge_layout.py)
2. **Hard-code modes:** Use parameters properly
3. **Ignore single-file case:** Handle edge cases
4. **Skip testing:** Test both modes before declaring "done"

---

## 🔮 HYPOTHESIS: What Vanilla Tried To Do

**Vanilla Goal:** One tree, two views
- Same **data** (files + folders)
- Two different **layouts** (by structure vs by semantics)
- Switch between them visually

**Vanilla Problem:** Formulas conflicted
- Y was sometimes depth, sometimes KL
- Nodes were sometimes folders, sometimes tags
- Edges were sometimes "contains", sometimes "similar"

**Vanilla Result:** "хреновое дерево" (broken tree)

**React Solution:** Complete separation
- `fan_layout.py`: ONLY DIRECTED
- `knowledge_layout.py`: ONLY KNOWLEDGE
- Different responses per mode

**React Oops:** Forgot to actually switch
- Parameter `mode` is there
- Just never used it in main API

---

## 🎯 NEXT INVESTIGATIVE STEPS

### For the Coder

1. **Search git history:** Find Vanilla version, look for these files:
   - `tree_layout.py` or `layout.py`
   - Look for both formulas in same file
   - Compare Y-calculation logic

2. **Check Phase history:**
   - Phase 14: Anti-gravity added?
   - Phase 22 v4: INTAKE added?
   - When was Vanilla → React migration?

3. **Test old issues:**
   - Does single-file overlap happen in current DIRECTED?
   - Can you reproduce it consistently?
   - Is it the same as in Vanilla?

---

## 📊 SUMMARY TABLE

| Aspect | Vanilla | React Now | Status |
|--------|---------|-----------|--------|
| **Mode parameter** | Unknown | Exists but ignored | ❌ Broken |
| **Formula separation** | Mixed | Split files | ✅ Good |
| **DIRECTED layout** | Broken | Works 80% | 🟡 Almost |
| **KNOWLEDGE layout** | Broken | Works 100% | ✅ Implemented |
| **Single-file fix** | ? | Missing | ❌ Not implemented |
| **Anti-gravity** | ? | Works | ✅ Added Phase 14 |
| **Adaptive formulas** | Fixed | Adaptive | ✅ Improved Phase 27.9 |

---

**Конец реконструкции истории развития.** ✅

Теория разработки VETKA восстановлена. Все недостающие кусочки задокументированы.
Готово к расследованию Vanilla версии и финальному fix-у.
