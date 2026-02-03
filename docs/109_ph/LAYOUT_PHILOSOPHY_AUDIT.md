# VETKA LAYOUT PHILOSOPHY AUDIT - Phase 109

**Date:** 2026-02-02
**Purpose:** Compare current layouts against VETKA Theory philosophy
**Status:** CRITICAL GAPS IDENTIFIED

---

## VETKA PHILOSOPHY (Target)

### Core Principles:

1. **Y-axis = TIME + KNOWLEDGE_LEVEL** (causality hierarchy)
   - Bottom (Y=0): Original sources, base concepts, early documents
   - Top (Y=max): Derivatives, complex concepts, later versions

2. **Universal "IMPORT" = Temporal + Semantic**
   - If A created BEFORE B, AND A semantically similar to B → A is "import" for B
   - Works for ALL content types (code, video, audio, books, scripts, documents)

3. **NODE as ROOT** = Point from which dependent entities "grow"
   - In code: main.py, __init__.py, hub files
   - In documents: original source (created earlier, spawned others)

---

## COMPLIANCE MATRIX

| Principle | Component | Status | Evidence |
|-----------|-----------|--------|----------|
| **Y = TIME + KNOWLEDGE** | semantic_sugiyama.py | ✅ COMPLIANT | Lines 26-111, knowledge_level from DAG |
| **Y = TIME + KNOWLEDGE** | fan_layout.py | ❌ NON-COMPLIANT | Line 465: uses DEPTH, not knowledge |
| **Y = TIME + KNOWLEDGE** | position_calculator.py | ✅ COMPLIANT | Lines 74-141, asymmetric projections |
| **Temporal Import Formula** | dependency_calculator.py | ⚠️ PARTIAL | Temporal decay exists (Phase 72.5) but no semantic gating in layout |
| **Temporal Import Formula** | Layout modules | ❌ NOT IMPLEMENTED | No created(A)<created(B) + similarity check in layout |
| **Root Node Centrality** | semantic_sugiyama.py | ✅ COMPLIANT | DAG-based root detection (in_degree=0) |
| **Root Node Centrality** | fan_layout.py | ⚠️ PARTIAL | Filesystem-based, not semantic-based |
| **Universal Content Support** | Scanners | ✅ COMPLIANT | Multiple scanner types, uniform dependency model |
| **Universal Content Support** | Layout engines | ❌ NON-COMPLIANT | Directory-specific fan_layout |

---

## DETAILED FINDINGS

### 1. Y-AXIS PHILOSOPHY

**Philosophy:** Y = TIME + KNOWLEDGE_LEVEL

| Module | Implementation | Verdict |
|--------|---------------|---------|
| `semantic_sugiyama.py` | `assign_knowledge_levels_from_dag()` - roots at bottom, derivatives at top | ✅ CORRECT |
| `fan_layout.py` | `folder_y = depth * Y_PER_DEPTH` - DEPTH based, not semantic | ❌ WRONG |
| `position_calculator.py` | `compute_semantic_hierarchy()` - asymmetric projections | ✅ CORRECT |

**Problem in fan_layout.py (line 465):**
```python
folder_y = depth * Y_PER_DEPTH  # Uses DEPTH, not knowledge_level!
```

**Should be:**
```python
folder_y = compute_knowledge_level(folder) * Y_SCALE  # Based on dependencies
```

---

### 2. TEMPORAL IMPORT FORMULA

**Philosophy:** `created(A) < created(B) AND similarity(A,B) > threshold` → A is "import" for B

**Current state in `dependency_calculator.py` (Phase 72.5):**
```python
# Temporal decay exists but decays importance, doesn't elevate earlier files
E(ΔT) = 0.2 + 0.8·e^(-ΔT/τ)  # Temporal floor: 20% memory
ΔT = max(0, created(B) - created(A)) / 86400
```

**What's missing:**
- This formula is NOT applied to layout Y-positioning
- Older files should be at BOTTOM (Y=low), not decayed
- Semantic similarity threshold not used for hierarchy

**Current flow in fan_layout.py:**
```python
# Files sorted by time but positioned linearly within folder
folder_files.sort(key=lambda f: f['created_time'])
file_y = folder_y + (file_index - mid_index) * FILE_SPACING  # Linear, not knowledge-based!
```

---

### 3. ROOT NODE DETECTION

**Philosophy:** Root = node with highest in-degree (many files depend on this)

| Module | Method | Verdict |
|--------|--------|---------|
| `semantic_sugiyama.py` | `in_degree == 0` for DAG roots | ✅ CORRECT |
| `fan_layout.py` | `if not f['parent_path']` for filesystem roots | ⚠️ PARTIAL |

**Problem:** Directory mode uses FILESYSTEM roots (folders without parents), not SEMANTIC roots (files others depend on).

---

### 4. UNIVERSAL CONTENT SUPPORT

**Philosophy:** Same layout works for code, video, audio, books, scripts, documents

**Current scanners (GOOD):**
- ✅ `python_scanner.py` - Python imports
- ✅ `base_scanner.py` - Abstract base
- ✅ Semantic tagger - All content types

**Current layouts (BAD):**
- ❌ `fan_layout.py` - Requires folder hierarchy (directory-specific)
- ⚠️ `semantic_sugiyama.py` - Requires DAG with prerequisite edges
- ❌ No universal layout for pure semantic graphs

---

## GAP ANALYSIS

### Critical Gap 1: Two Separate Y-Axis Philosophies

| Mode | Y-axis Logic | Problem |
|------|-------------|---------|
| Directory | Y = depth (file structure) | Ignores semantic importance |
| Knowledge | Y = knowledge_level (DAG) | Not connected to directory mode |

**Solution:** Unify: `Y = w₁·created_time + w₂·knowledge_level`

---

### Critical Gap 2: Temporal Import NOT Applied to Layout

**dependency_calculator.py has:**
- Temporal decay formula
- Semantic gating
- Import detection

**But layout engines DON'T USE IT!**

```
dependency_calculator.py → ScoringResult
                              ↓
                         (NOT USED)
                              ↓
fan_layout.py → positions based on FOLDER DEPTH
```

**Should be:**
```
dependency_calculator.py → ScoringResult
                              ↓
                         knowledge_level per file
                              ↓
unified_layout.py → Y = time + knowledge_level
```

---

### Critical Gap 3: Fan Layout Ignores File Creation Time for Y

**Current:**
```python
# Files sorted by time, then positioned linearly
folder_files.sort(key=lambda f: f['created_time'])
for i, file_data in enumerate(folder_files):
    file_y = folder_y + (i - mid_index) * FILE_SPACING  # Linear index!
```

**Should be:**
```python
# Files positioned by TIME, not index
for file_data in folder_files:
    time_factor = normalize_time(file_data['created_time'], time_range)
    file_y = Y_MIN + time_factor * (Y_MAX - Y_MIN)  # Time-based Y!
```

---

## RECOMMENDATIONS

### Phase 110 Priority 1: Unify Y-Axis Philosophy
```python
def compute_unified_y(node, time_range, knowledge_levels):
    """
    Y = 0.5 * time_factor + 0.5 * knowledge_factor

    Time factor: older = lower Y (foundational)
    Knowledge factor: more dependents = lower Y (root)
    """
    time_factor = (node.created_time - time_range.min) / time_range.span
    knowledge_factor = knowledge_levels.get(node.id, 0.5)

    return 0.5 * time_factor + 0.5 * knowledge_factor
```

### Phase 110 Priority 2: Apply Temporal Import to Layout
```python
def create_temporal_import_edge(file_a, file_b, similarity):
    """
    If A created before B, and similar → A is "import" for B
    """
    if file_a.created_time < file_b.created_time and similarity > 0.5:
        return Edge(source=file_a, target=file_b, type='temporal_import')
    return None
```

### Phase 110 Priority 3: Merge fan_layout + semantic_sugiyama
- Use DAG structure from semantic analysis
- Apply to files (not just concepts)
- Keep visual fan spread from Directory Mode
- Apply knowledge_level Y from Knowledge Mode

---

## SUMMARY

| Aspect | Current State | Target State | Gap |
|--------|--------------|--------------|-----|
| Y-axis | DEPTH-based (fan_layout) | TIME + KNOWLEDGE | ❌ CRITICAL |
| Temporal Import | Calculated but unused | Applied to Y-position | ❌ CRITICAL |
| Root Detection | Filesystem-based | Centrality-based | ⚠️ MEDIUM |
| Universal Layout | Directory-specific | Any content type | ⚠️ MEDIUM |

**Bottom line:** The philosophy is correct in `semantic_sugiyama.py` and `position_calculator.py`, but the **ACTIVE** layout engine (`fan_layout.py`) doesn't implement it!

**Fix:** Integrate knowledge_level calculation into fan_layout, or create unified layout engine.

---

*Generated by Claude Haiku agent - Phase 109 philosophy audit*
