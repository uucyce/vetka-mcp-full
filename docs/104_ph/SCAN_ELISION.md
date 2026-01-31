# ELISION Glossary Scan - Phase 104

**Task:** Find all mentions of ELISION compression mechanism across the codebase.

**Definition:** ELISION = **Efficient Language-Independent Symbolic Inversion of Names** - a token compression mechanism for JSON context/memory to save 40-60% tokens.

---

## Summary

| Module | Type | Status | Token Savings |
|--------|------|--------|----------------|
| `elision.py` | Main module | **ACTIVE** | 40-60% (JSON keys + paths) |
| `compression.py` | Age-based embedding | **ACTIVE** | 50-90% (embedding dims) |
| `dep_compression.py` | Dependency graph | **ACTIVE** | Variable (top-k filtering) |
| `engram_user_memory.py` | Legacy mock | **PARTIAL** | Basic truncation only |

---

## Primary Modules

### 1. **ElisionCompressor** (`src/memory/elision.py`) - PRIMARY MODULE

**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/elision.py`

**Purpose:** Token-efficient JSON context compression via 4-level compression strategy.

**Key Components:**

| Component | Function |
|-----------|----------|
| `ELISION_MAP` | Dict of 30+ key abbreviations (e.g., `context→c`, `user→u`, `imports→imp`) |
| `PATH_PREFIXES` | Path compression (e.g., `/src/→s/`, `/orchestration/→o/`) |
| `ElisionCompressor.compress()` | Main compression method (levels 1-4) |
| `ElisionCompressor.expand()` | Reversible decompression with legend |
| `compress_json_context()` | Specialized VETKA context compression |

**Compression Levels:**

```
Level 1: Key abbreviation only (safe, reversible)
Level 2: Level 1 + path compression (DEFAULT)
Level 3: Level 2 + whitespace removal
Level 4: Level 3 + local dictionary (per-subtree)
```

**Target Ratio:** 40-60% token savings without semantic loss.

**Code Snippet:**
```python
class ElisionCompressor:
    """ELISION Compression Engine"""

    def compress(
        self,
        data: Any,
        level: int = 2,
        target_ratio: float = None
    ) -> ElisionResult:
        """Compress JSON data using ELISION"""
```

**Status:** ✅ **PROPERLY NAMED** - "ELISION" is correct technical name with full definition in docstring.

---

### 2. **MemoryCompression** (`src/memory/compression.py`) - AGE-BASED EMBEDDING COMPRESSION

**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/compression.py`

**Purpose:** Age-based embedding dimensionality reduction (like human memory decay curve).

**Strategy:**

| Age Range | Dimension | Layer | Quality |
|-----------|-----------|-------|---------|
| <7 days | 768D | active | 99% |
| <30 days | 384D | active | 90% |
| <90 days | 256D | archived | 80% |
| >180 days | 64D | archived | 60% |

**Key Classes:**

| Class | Function |
|-------|----------|
| `CompressedNodeState` | Result of age-based reduction |
| `MemoryCompression` | Compressor engine with PCA support |
| `CompressionScheduler` | Periodic compression scheduler |

**Status:** ⚠️ **MISNAMED** - This is NOT "ELISION" but rather **"Adaptive Embedding Compression"**. Should rename to `AdaptiveEmbeddingCompression` or `AgeBasedCompression` for clarity.

**Code Snippet:**
```python
class MemoryCompression:
    """Age-based embedding compression (like forgetting curve)"""

    COMPRESSION_SCHEDULE = [
        (0, 768, "active", 1.0),     # Fresh: full
        (30, 384, "active", 0.90),   # Month: PCA 384D
        (90, 256, "archived", 0.80), # Quarter: PCA 256D
    ]
```

---

### 3. **DEPCompression** (`src/memory/dep_compression.py`) - DEPENDENCY GRAPH COMPRESSION

**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/dep_compression.py`

**Purpose:** Age-based dependency edge pruning (top-k filtering by age).

**Strategy:**

| Age Range | Mode | Edges Kept |
|-----------|------|-----------|
| <30 days | full | All edges |
| 30-90 days | top_3 | 3 strongest |
| 90-180 days | top_1 | 1 primary |
| >180 days | none | None (lazy recompute) |

**Key Classes:**

| Class | Function |
|-------|----------|
| `CompressedDEP` | Result of DEP compression |
| `DEPCompression` | Compressor engine |
| `DEPCompressionStats` | Statistics tracker |

**Status:** ⚠️ **MISNAMED** - This is NOT "ELISION" but rather **"Dependency Graph Pruning"**. Should rename to `DependencyCompression` or `DEPPruning`.

**Code Snippet:**
```python
class DEPCompression:
    """Compresses dependency graph based on node age"""

    AGE_THRESHOLDS = {
        'full': 30,     # < 30 days: keep all
        'top_3': 90,    # 30-90 days: top 3
        'top_1': 180,   # 90-180 days: top 1
        'none': 365     # > 180 days: none
    }
```

---

### 4. **Legacy Mock** (`src/memory/engram_user_memory.py`)

**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/engram_user_memory.py:576-612`

**Purpose:** Mock ELISION implementation (for CAM surprise integration at level 2).

**Code:**
```python
# Simple ELISION-style compression (mock implementation)
# In a full implementation, this would use actual ELISION algorithm
# For now, provide a simple truncation-based compression

def compress_context(content, ratio):
    target_length = int(len(content) * ratio)
    return (
        content[:target_length] + "... [compressed]"
        if target_length < len(content)
        else content
    )
```

**Status:** ⚠️ **PLACEHOLDER** - Uses naive truncation, not actual ELISION. Should be replaced with `get_elision_compressor().compress()`.

---

## Usage Locations

### Direct Imports

| File | Line | Import | Function |
|------|------|--------|----------|
| `jarvis_prompt_enricher.py` | 39 | `from .elision import get_elision_compressor` | JARVIS enrichment |
| `shared_tools.py` | 1255 | `from src.memory.elision import compress_context` | Bridge context compression |
| `tools.py` (agents) | 578 | `from src.memory.elision import get_elision_compressor` | Agent context compression |
| `vetka_mcp_bridge.py` | 1039 | `from src.memory.elision import compress_context` | MCP bridge compression |
| `llm_call_tool.py` | 372 | `from src.memory.elision import compress_context` | LLM context compression |

### Embedding Compression Usage

| File | Line | Function |
|------|------|----------|
| `shared_tools.py` | 1447 | `from src.memory.compression import MemoryCompression` |
| `vetka_mcp_bridge.py` | 1099 | `from src.memory.compression import MemoryCompression` |

---

## Naming Analysis

### ✅ CORRECT NAMING

1. **`ElisionCompressor`** - Primary class properly uses "ELISION" with full definition
   - File: `elision.py`
   - Definition: "Efficient Language-Independent Symbolic Inversion of Names"
   - Phase: 92
   - Status: ACTIVE

### ⚠️ INCORRECT/MISLEADING NAMING

1. **`MemoryCompression`** vs actual function (age-based embedding reduction)
   - Should be: `AdaptiveEmbeddingCompression` or `AgeBasedEmbeddingCompression`
   - Current name suggests general memory compression, but is specifically embedding-focused
   - **Recommendation:** Rename module to `adaptive_embedding_compression.py`

2. **`DEPCompression`** vs actual function (dependency graph top-k filtering)
   - Should be: `DependencyGraphPruning` or `DependencyCompression`
   - Name is correct but could be clearer
   - **Recommendation:** Keep as is, but improve docstring

3. **`compress_context()` in `engram_user_memory.py`** (line 579)
   - Currently: Naive string truncation
   - Should use: `get_elision_compressor().compress()`
   - **Recommendation:** Replace with actual ELISION call

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│         COMPRESSION PIPELINE (3-TIER)                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  TIER 1: JSON Keys/Paths (ELISION)                      │
│  ├─ ElisionCompressor.compress()                        │
│  ├─ 40-60% token savings                                │
│  └─ Reversible via legend                               │
│                                                          │
│  TIER 2: Embedding Dimensions (Age-Based)               │
│  ├─ MemoryCompression.compress_by_age()                 │
│  ├─ 768D → 384D → 256D → 64D                            │
│  └─ Quality degrades with age                           │
│                                                          │
│  TIER 3: Dependency Graph (Top-K)                       │
│  ├─ DEPCompression.compress_dep_graph()                 │
│  ├─ full → top_3 → top_1 → none                         │
│  └─ Lazy recompute on access                            │
│                                                          │
└─────────────────────────────────────────────────────────┘

Used By:
- JARVISPromptEnricher (model-agnostic enrichment)
- SharedTools (bridge context compression)
- VETKAMCPBridge (MCP tool compression)
- LLMCallTool (agent LLM context)
- BaseAgent tools (general agent context)
```

---

## Recommendations

### Priority 1: Clarify Naming

```diff
# src/memory/compression.py
- class MemoryCompression:
+ class AdaptiveEmbeddingCompression:
    """Age-based embedding dimensionality reduction"""

# src/memory/dep_compression.py (OPTIONAL)
- # Current name is acceptable but could be improved
+ # Consider: DependencyGraphPruning or DependencyCompression
```

### Priority 2: Replace Mock Implementation

```diff
# src/memory/engram_user_memory.py line 576-612
- def compress_context(content, ratio):
-     target_length = int(len(content) * ratio)
-     return content[:target_length] + "... [compressed]"

+ from src.memory.elision import get_elision_compressor
+
+ result = get_elision_compressor().compress(content, level=2)
+ return result.compressed
```

### Priority 3: Unified Module Organization

```
src/memory/
├── elision.py           # ✅ CORRECT - JSON compression
├── compression.py       # ⚠️ RENAME → adaptive_embedding_compression.py
├── dep_compression.py   # ✅ ACCEPTABLE - Dependency pruning
├── engram_user_memory.py # ⚠️ FIX - Replace mock compress_context()
└── __init__.py          # Export all three compression engines
```

---

## Phase & Status Summary

| Module | Phase | Status | Notes |
|--------|-------|--------|-------|
| `elision.py` | Phase 92, Phase 96 | ✅ ACTIVE | Fully implemented, used across codebase |
| `compression.py` | Phase 77.4, Phase 96 | ✅ ACTIVE | Age-based embedding, good design |
| `dep_compression.py` | Phase 77.5 | ✅ ACTIVE | Dependency pruning, lazy recompute ready |
| `jarvis_prompt_enricher.py` | Phase 76.3 + 92, Phase 98 | ✅ ACTIVE | ELISION integrated, FIX_98.2 applied |
| `engram_user_memory.py` | Mock | ⚠️ PARTIAL | Placeholder only, should use real ELISION |

---

## Scan Completion

**Total Mentions Found:** 25+ files with compression references
**Primary Modules:** 3 (ELISION, MemoryCompression, DEPCompression)
**Integration Points:** 5+ (jarvis, bridge, tools, mcp, llm_call)
**Naming Issues:** 2 modules need clarification
**Mock Implementations:** 1 (engram_user_memory)

**Conclusion:** ELISION is **properly named and actively used**. Secondary compression modules should have clearer names to avoid confusion with ELISION.

---

*Scan completed: 2026-01-31*
*Tools used: grep pattern matching + source code analysis*
*Context read: 5 lines per match, no full file reads (optimization)*
