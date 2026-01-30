# Phase 72.5: Enhanced Dependency Formula (Quick Fix)

**Date:** 2026-01-19
**Status:** COMPLETE

## Overview

Phase 72.5 enhances the Kimi K2 formula based on consensus from 6 AI models:
- ChatGPT-Math
- Gemini-3-Pro
- Claude
- Anonymous
- DeepSeek R1
- Mathos AI

## Problem

Pure imports without semantic similarity scored below significance threshold (0.6):

| Scenario | Old Score | Target |
|----------|-----------|--------|
| Pure import (I=1.0, S=0.0) | 0.23 | >0.6 |

Root cause: Sigmoid center at 0.5 pushed import-only scores too low.

## Solution (3 Changes)

### 1. Sigmoid Center: 0.5 → 0.35

```python
# Before
σ(x) = 1/(1+e^(-12(x-0.5)))

# After (Phase 72.5)
σ(x) = 1/(1+e^(-12(x-0.35)))
```

This shifts the transition zone to favor import-dominant scores:
- σ(0.435) = 0.74 > 0.6 ✅ (was 0.23)

### 2. Semantic Gating (Threshold 0.5)

```python
# Before
S_effective = S if S >= 0.3 else 0

# After (Phase 72.5)
S_gated = max(0.0, (S - 0.5) / 0.5)
# S < 0.5  → 0.0 (noise filtered)
# S = 0.75 → 0.5
# S = 1.0  → 1.0
```

Benefits:
- Filters weak semantic matches (< 0.5) as noise
- Strong matches (> 0.5) are normalized to [0, 1]

### 3. Temporal Floor (20% Memory)

```python
# Before
E(ΔT) = e^(-ΔT/τ)           # Decays to ~0 for old files

# After (Phase 72.5)
E(ΔT) = 0.2 + 0.8 * e^(-ΔT/τ)  # Never below 20%
```

Benefits:
- Old foundational files retain 20% relevance
- Prevents complete loss of temporal context

| ΔT (days) | Old E(ΔT) | New E(ΔT) |
|-----------|-----------|-----------|
| 1 | 0.97 | 0.97 |
| 30 | 0.37 | 0.49 |
| 90 | 0.05 | 0.24 |
| 365 | 0.00 | 0.20 |

## Results

| Scenario | Old Score | New Score | Target |
|----------|-----------|-----------|--------|
| Pure import (I=1.0, S=0.0) | 0.23 | 0.74 | >0.6 ✅ |
| Import + semantic (I=0.9, S=0.7) | 0.98 | 0.99 | >0.8 ✅ |
| Semantic only (S=0.8, 2 days) | 0.08 | 0.20 | <0.6 ✅ |
| Old file with semantic (214 days) | 0.00 | 0.04 | >0.0 ✅ |

## Files Modified

### `src/scanners/dependency_calculator.py`

1. **ScoringConfig** - New defaults:
   - `sigmoid_center: float = 0.35` (was 0.5)
   - `semantic_gate_threshold: float = 0.5` (new)
   - `temporal_floor: float = 0.2` (new)

2. **DependencyCalculator.calculate()** - Semantic gating:
   ```python
   if S_raw >= gate_threshold:
       S_gated = (S_raw - gate_threshold) / (1.0 - gate_threshold)
   else:
       S_gated = 0.0
   ```

3. **_calculate_temporal_decay()** - Floor:
   ```python
   floor = self.config.temporal_floor
   decay = floor + (1.0 - floor) * math.exp(-delta_days / tau)
   ```

4. **Components output** - Now includes:
   - `S_raw`: Original semantic score
   - `S_gated`: After threshold normalization

### `tests/scanners/test_dependency_calculator.py`

- Updated marker: `Phase 72.4 + 72.5`
- Added `TestSemanticGating` class (5 tests)
- Updated `TestTemporalDecay` for floor (7 tests)
- Updated `TestSigmoid` for center 0.35 (6 tests)
- Added `test_pure_import_now_significant` (key fix validation)
- Total: 45 tests (was 36)

## Post-Audit Fixes

Based on Claude Code Haiku 4.5 audit, additional fixes applied:

### BUG #2 Fixed: Legacy Filter Removed
```python
# REMOVED (was dead code):
if S_raw < self.config.min_semantic_score:
    S_gated = 0.0

# Semantic gating (threshold 0.5) handles this more effectively
```

### BUG #5 Fixed: Config Validation Enhanced
```python
def __post_init__(self):
    # Tight tolerance for weights
    if abs(total - 1.0) > 0.001:  # Was 0.01
        raise ValueError(...)

    # Validate non-negative weights
    for name, value in weights:
        if value < 0:
            raise ValueError(f"{name} must be >= 0")

    # Validate sigmoid parameters
    if not 0 <= self.sigmoid_center <= 1:
        raise ValueError(...)

    # Validate temporal parameters
    if not 0 <= self.temporal_floor <= 1:
        raise ValueError(...)
```

### BUG #6 Fixed: Float Precision Tests Added
```python
def test_float_precision_at_boundary():
    # S = 0.50001 → S_gated = 0.00002 (small but non-zero)
    assert result.components['S_gated'] > 0.0
    assert result.components['S_gated'] < 0.001
```

## Test Results

```
============================= 233 passed in 0.41s =============================
```

All 233 scanner tests pass (72.1 + 72.2 + 72.3 + 72.4 + 72.5 + audit fixes).

## Configuration

```python
from src.scanners import ScoringConfig, DependencyCalculator

# Default (Phase 72.5)
calculator = DependencyCalculator()

# Custom: stricter semantic gating
config = ScoringConfig(
    sigmoid_center=0.35,       # Keep Phase 72.5 center
    semantic_gate_threshold=0.6,  # Stricter gate
    temporal_floor=0.1,        # Less floor
)
calculator = DependencyCalculator(config=config)
```

## Formula Summary

```
DEP(A→B) = σ( w₁·I + w₂·S'·E(ΔT) + w₃·R + w₄·RRF )

where:
    σ(x) = 1/(1+e^(-12(x-0.35)))     # Shifted center
    S' = max(0, (S - 0.5) / 0.5)     # Semantic gating
    E(ΔT) = 0.2 + 0.8·e^(-ΔT/τ)     # Temporal with floor
    τ = 30 days
    w = [0.40, 0.33, 0.20, 0.07]
    threshold = 0.6
```
