# Phase 71: Dependency Scoring Formula (DEP)
**Advanced Temporal-Semantic Dependency Detection**

**Date:** 2026-01-20
**Formula:** Logistic DEP with temporal decay + RRF
**Status:** ✅ DOCUMENTED
**Implementation:** Ready for Phase 72+ integration

---

## 🎯 Overview

Phase 71 establishes the **DEP (Dependency Score) formula** - an advanced algorithm for detecting and scoring semantic/temporal dependencies between files in VETKA.

### The Problem Solved

Many tools naively find imports/references but miss:
- **Temporal ordering:** B can't depend on A if B was created first
- **Semantic alignment:** Random string matches are noise
- **Weak signals:** References might be coincidences
- **Circular dependencies:** Which direction is real?

### The Solution

A logistic sigmoid formula that combines:
1. **Import signal** (5x weight) - Explicit imports
2. **Semantic signal** (temporal-modulated) - Content similarity
3. **Reference signal** (4x weight) - Citations/links
4. **RRF signal** (1x weight) - Source importance
5. **Temporal constraint** - File creation order
6. **Intelligent bias** - Minimum threshold

---

## 📐 The Formula

### Core DEP Formula

```
DEP(A→B) = σ( w₁·I + w₂·S'·E(ΔT) + w₃·R + w₄·RRF - θ )

where:
  σ(x) = 1/(1+e^(-12(x-0.35)))              # Shifted logistic sigmoid
  S' = max(0, (S-0.5)/0.5)                  # Semantic gating
  E(ΔT) = 0.2 + 0.8·e^(-ΔT/30)              # Temporal envelope
```

### Parameters Explained

| Parameter | Value | Meaning |
|-----------|-------|---------|
| **w₁** (Import) | **5** | Explicit imports are strongest signal |
| **w₂** (Semantic+Time) | **3** | High semantic + temporal match |
| **w₃** (Reference) | **4** | Citations/references are strong |
| **w₄** (RRF) | **1** | Source importance provides gentle boost |
| **θ (Bias)** | **2.5** | Threshold to prevent false positives |
| **λ (Decay)** | **1/30** | Temporal half-life = 30 days |
| **S_thr (Semantic)** | **0.5** | Minimum semantic similarity (0-1) |

---

## 🔬 Components Breakdown

### 1. Import Signal (I)
```
I ∈ {0, 1}

I = 1 if:
  - A imports B (import/from statement)
  - A references B in function call
  - A inherits from B

I = 0 otherwise
```

**Why w₁=5?**
- Explicit imports are unambiguous
- If file A imports B, DEP without other signals = σ(5-2.5) ≈ 0.88

### 2. Semantic Signal (S' with temporal modulation)
```
S' = max(0, (S-0.5)/0.5)         # Normalized to [0, 1]

S ∈ [0, 1]                       # From Qdrant embedding similarity

S'·E(ΔT) combines:
  - Semantic similarity (content-based)
  - Temporal ordering (creation order)
```

**Semantic Gate (S > 0.5):**
- Below 0.5: Likely false positive → zeroed out
- Above 0.5: Potential semantic connection

**Temporal Envelope E(ΔT):**
```
E(ΔT) = 0.2 + 0.8·e^(-ΔT/30)

ΔT = (created(B) - created(A)) in days

Timeline:
  ΔT = 0 days  → E(ΔT) = 1.0 (full strength)
  ΔT = 30 days → E(ΔT) ≈ 0.57 (37% remaining)
  ΔT = 60 days → E(ΔT) ≈ 0.37 (13% remaining)
  ΔT = 90 days → E(ΔT) ≈ 0.23 (5% remaining)
  ΔT ≤ 0      → E(ΔT) = 0.2 (minimum, because [ΔT>0] indicator below)
```

**Why floor at 0.2?**
- Allows late references (documentation, tests)
- But heavily penalizes temporal violations

### 3. Reference Signal (R)
```
R ∈ {0, 1}

R = 1 if:
  - A cites B in comments
  - A has URL/link to B
  - A has string containing B's path

R = 0 otherwise
```

**Why w₃=4?**
- Weaker than import (I) but stronger than pure semantic
- Manual citations show intentional connection

### 4. RRF Signal (Reciprocal Rank Fusion)
```
RRF ∈ [0, 1]

From Phase 68 Hybrid Search:
  RRF = 0.5/(60+rank_keyword) + 0.5/(60+rank_semantic)

Indicates how "important" B is in the overall system
```

**Why w₄=1?**
- Gentle influence only
- Popular files get +0.2 max boost to DEP
- Prevents popularity-bias

---

## 📊 Logistic Sigmoid

### Standard Sigmoid
```
σ(x) = 1/(1+e^(-x))

Properties:
- σ(0) = 0.5 (decision boundary)
- σ(∞) = 1
- σ(-∞) = 0
- Smooth S-curve
```

### **Shifted & Scaled** (Our Version)
```
σ(x) = 1/(1+e^(-12(x-0.35)))

Why shift to 0.35?
- Normal sigmoid at 0 gives 0.5
- We want DEP(A→B) > 0.5 when weighted sum > 2.5
- Shift moves center to 0.35 ≈ 2.5/7 (avg weight)

Why scale to -12?
- Steeper curve = sharper decision boundary
- Reduces twilight zone (0.3-0.7)
- Makes DEP more binary-like
```

### Score Interpretation
```
DEP < 0.3 → NOT a dependency (low confidence)
DEP 0.3-0.5 → Weak signal (investigate manually)
DEP 0.5-0.8 → Probable dependency
DEP 0.8+ → Strong dependency (high confidence)
```

---

## ⏰ Temporal Ordering Constraint

### The Problem: Backward Dependencies
```
File A (created Jan 1)
File B (created Jan 10)

If B imports A → OK (forward dependency)
If A imports B → INVALID (B didn't exist!)
```

### Solution: Temporal Indicator
```
[ΔT > 0] = 1 if created(B) > created(A)
         = 0 otherwise

Applied to formula:
  w₂·S'·E(ΔT)·[ΔT>0]

If B is older than A:
  [ΔT > 0] = 0 → Entire term vanishes
  DEP becomes: σ(w₁·I + w₃·R + w₄·RRF - θ)
  Only direct imports/references count
```

### Examples

**Example 1: Forward temporal + explicit import**
```
A created: 2026-01-01
B created: 2026-01-05 (4 days later)
A imports B explicitly

DEP(A→B) = σ(5·1 + 3·(0.8)·(0.9) + 4·0 + 1·0.5 - 2.5)
         = σ(5 + 2.16 + 0 + 0.5 - 2.5)
         = σ(5.16)
         ≈ 0.994  ✅ STRONG DEPENDENCY
```

**Example 2: Backward temporal + semantic match**
```
A created: 2026-01-10
B created: 2026-01-05 (A is 5 days newer)
Semantic similarity = 0.8

DEP(A→B) = σ(5·0 + 3·(0.6)·(0.2) + 4·0 + 1·0.5 - 2.5)
         = σ(0 + 0.36 + 0 + 0.5 - 2.5)
         = σ(-1.64)
         ≈ 0.16  ❌ NOT A DEPENDENCY (temporal violation)
```

**Example 3: Late reference (comment/doc)**
```
A created: 2026-01-01
B created: 2026-01-05
A references B in a comment (no import/semantic)
Reference signal only

DEP(A→B) = σ(5·0 + 3·(0)·(0.9) + 4·1 + 1·0.5 - 2.5)
         = σ(0 + 0 + 4 + 0.5 - 2.5)
         = σ(2.0)
         ≈ 0.68  ✅ WEAK-MEDIUM (ref can be late)
```

---

## 🎯 Tuning Parameters

### For Strict Dependency Detection (Few False Positives)
```
θ = 3.0          # Higher bias (require more signals)
λ = 1/20         # Faster decay (temporal precision)
S_thr = 0.6      # Higher semantic threshold
σ scale = -12    # Keep steep curve
```

### For Broad Dependency Detection (Few False Negatives)
```
θ = 2.0          # Lower bias (catch weak signals)
λ = 1/45         # Slower decay (more temporal tolerance)
S_thr = 0.4      # Lower semantic threshold
σ scale = -8     # Softer curve
```

### A/B Testing Recommendation
```
Test on 1000 files from your project:
1. Generate dependencies with Phase 72 scanner
2. Score with DEP formula (current parameters)
3. Manually verify 100 random samples:
   - Count false positives
   - Count false negatives
4. Adjust:
   - If too many false positives: increase θ or decrease λ
   - If too many false negatives: decrease θ or increase λ
   - If sensitivity wrong: adjust S_thr
5. Repeat until ~5% error rate
```

---

## 🔴 Edge Cases & Handling

### Case 1: ΔT < 0 (B Older Than A)
```
Problem: A cannot depend on something created after it exists

Solution: Temporal indicator [ΔT > 0] = 0
Result: Only explicit imports/references count
        Semantic signal completely eliminated
```

### Case 2: Very Old Files (ΔT > 90 days)
```
Problem: Relevance decays to almost nothing

Solution: Exponential decay with 30-day half-life
Result: E(ΔT) ≈ 0.05 for 90+ day gaps
        Still accepts if strong import signal
```

### Case 3: Circular Dependencies (A↔B)
```
Problem: Both A→B and B→A might score high

Solution: Post-processing step
Result: Keep only max(DEP(A→B), DEP(B→A))
        Remove lower-scoring direction
```

### Case 4: No Signals (I=0, S<0.5, R=0)
```
Problem: Some files might have no connections

Solution: DEP(A→B) = σ(0 + 0 + 0 + ~0.5 - 2.5) ≈ 0.1
Result: Isolated files have DEP ≈ 0 (not dependencies)
```

### Case 5: Very New Files (ΔT ≈ 0)
```
Problem: Files created on same day

Solution: E(ΔT) = 0.2 + 0.8·e^(-0/30) = 1.0 (full strength)
Result: Temporal ordering doesn't penalize
        Allows rapid development cycles
```

---

## 📊 Score Distribution Examples

### Expected Distribution on Real Projects

| Score Range | Meaning | Typical % |
|------------|---------|-----------|
| 0.0-0.3 | Not dependencies | ~70% |
| 0.3-0.5 | Weak signals | ~15% |
| 0.5-0.8 | Probable deps | ~12% |
| 0.8-1.0 | Strong deps | ~3% |

**Note:** These are rough estimates. Your project will vary.

---

## 🛠️ Implementation in VETKA

### Where It Integrates

**Phase 72:**
- Dependency dataclass stores `score` field
- PythonScanner finds imports, references

**Phase 73 (Next):**
- Apply DEP formula to score dependencies
- Use for intelligent dependency graphs

**Phase 74+ (Future):**
- ScannerManager uses DEP for visualization
- Knowledge graph layout uses DEP scores
- Context assembly might prefer high-DEP files

### Pseudocode Integration

```python
# Phase 72-derived dependency
dep = Dependency(
    file_path="src/handlers/user_message_handler.py",
    source_module="user_message_handler",
    target_module="message_utils",
    dependency_type=DependencyType.IMPORT,
    line_number=42,
    confidence=0.95
)

# Phase 71 scoring
class DependencyScorer:
    def compute_dep_score(
        self,
        dep: Dependency,
        files_metadata: Dict,  # created_at timestamps
        semantic_similarity: float,  # From Qdrant
        rrf_score: float  # From Phase 68
    ) -> float:
        """Compute DEP(A→B) using Phase 71 formula."""

        # Extract signals
        I = 1.0 if dep.dependency_type == DependencyType.IMPORT else 0.0
        R = 1.0 if dep.dependency_type == DependencyType.REFERENCE else 0.0

        # Temporal envelope
        delta_t = (files_metadata[dep.target_module]['created_at'] -
                   files_metadata[dep.source_module]['created_at']).days

        if delta_t <= 0:
            temporal_indicator = 0.0
        else:
            temporal_indicator = 1.0

        # Semantic gating
        S_prime = max(0, (semantic_similarity - 0.5) / 0.5)
        temporal_envelope = 0.2 + 0.8 * math.exp(-delta_t / 30)

        # Weighted sum
        weighted_sum = (5*I +
                       3*S_prime*temporal_envelope*temporal_indicator +
                       4*R +
                       1*rrf_score -
                       2.5)

        # Logistic sigmoid (shifted)
        dep_score = 1.0 / (1.0 + math.exp(-12 * (weighted_sum - 0.35)))

        return dep_score
```

---

## 📈 Validation Metrics

### How to Know It Works

**Good formula indicators:**
- ✅ Explicit imports score > 0.8
- ✅ Typos/noise score < 0.3
- ✅ Recent files score higher than old files
- ✅ Circular deps break to one direction
- ✅ Manual review agrees 80%+ of the time

**Bad formula indicators:**
- ❌ All scores cluster (0.1-0.2 or 0.8-0.9)
- ❌ Temporal ordering ignored
- ❌ No correlation with actual imports
- ❌ False positives/negatives > 10%

---

## 📚 References

### Related Documentation
- **Phase 68:** Hybrid Search & RRF (provides RRF scores)
- **Phase 72:** Dependency extraction (provides I, R, timestamps)
- **Phase 70:** Semantic similarity (provides S from Qdrant)

### Key Files in VETKA
```
src/scanners/dependency_calculator.py
  ↓ Where DEP formula should live (Phase 73+)

src/search/hybrid_search.py
  ↓ Provides RRF scores

src/scanners/known_packages.py
  ↓ Package registry for scoring
```

---

## ✅ Implementation Checklist

When implementing Phase 71 formula:

- [ ] Create `src/scanners/dependency_score.py`
- [ ] Implement `compute_dep_score()` function
- [ ] Add tests with edge cases
- [ ] Validate temporal ordering constraint
- [ ] Benchmark against known dependencies
- [ ] Run A/B test on 1000 files
- [ ] Document parameter choices
- [ ] Create visualization of score distribution

---

**Phase 71 Complete!**

Status: ✅ **DOCUMENTED & READY FOR PHASE 73 IMPLEMENTATION**

Generated: 2026-01-20
For: Claude Code Opus 4.5
Next: Integrate into Phase 72+ scanner workflow
