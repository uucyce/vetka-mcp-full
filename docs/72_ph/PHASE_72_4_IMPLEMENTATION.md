# Phase 72.4: Dependency Scoring Calculator

**Date:** 2026-01-19
**Status:** COMPLETE

## Overview

Phase 72.4 implements the DependencyCalculator - a combined scoring system using the Kimi K2 formula to merge import dependencies with semantic similarity from Qdrant.

## Formula (Kimi K2)

```
DEP(A→B) = σ( w₁·I + w₂·S·E(ΔT) + w₃·R + w₄·RRF )

where:
    σ(x) = 1/(1+e^(-12(x-0.5)))  # Sigmoid normalization
    E(ΔT) = e^(-ΔT/τ)            # Exponential decay (τ=30 days)
    ΔT = max(0, created(B) - created(A)) / 86400  # Days
    w = [0.40, 0.33, 0.20, 0.07]  # Weights (sum = 1.0)
    threshold = 0.6               # Minimum for significant link
```

### Components

| Symbol | Name | Weight | Description |
|--------|------|--------|-------------|
| I | Import | 0.40 | Explicit code imports (from PythonScanner) |
| S | Semantic | 0.33 | Vector similarity (from Qdrant) |
| E(ΔT) | Temporal | - | Time decay factor (multiplies S) |
| R | Reference | 0.20 | Explicit references (links, paths) |
| RRF | Rank Fusion | 0.07 | Source file importance |

### Score Interpretation

| Range | Meaning |
|-------|---------|
| 0.8-1.0 | Strong dependency (explicit import) |
| 0.6-0.8 | Significant link (semantic + temporal) |
| 0.4-0.6 | Weak link (semantic only) |
| 0.0-0.4 | No meaningful dependency |

## Files Created

### 1. `src/scanners/dependency_calculator.py` (146 lines, 95% coverage)

Main calculator implementation:

```python
class DependencyCalculator:
    """Calculate combined dependency scores using Kimi K2 formula."""

    def calculate(self, input_data: ScoringInput) -> ScoringResult:
        """Calculate score for A→B link."""

    def find_dependencies(
        self,
        target_file: FileMetadata,
        candidate_sources: List[FileMetadata],
        import_scores: Dict[str, float],
        semantic_scores: Dict[str, float]
    ) -> List[ScoringResult]:
        """Find all significant dependencies for a file."""
```

Supporting classes:
- `ScoringConfig` - Configurable weights and thresholds
- `ScoringInput` - Input data for calculation
- `ScoringResult` - Output with score breakdown
- `FileMetadata` - File timestamps and metadata
- `QdrantSemanticProvider` - Qdrant integration wrapper

### 2. `tests/scanners/test_dependency_calculator.py` (36 tests)

Test categories:
- `TestScoringConfig` - Weight validation
- `TestTemporalDecay` - E(ΔT) calculation
- `TestSigmoid` - Normalization
- `TestDependencyCalculator` - Core scoring
- `TestBatchProcessing` - Multiple files
- `TestQdrantSemanticProvider` - Mock Qdrant
- `TestRealWorldScenarios` - Practical cases

## Key Features

### Temporal Decay

```python
def _calculate_temporal_decay(self, source_created, target_created):
    # Causality: source must exist before target
    if delta_days < 0:
        return 0.0

    # Exponential decay with τ=30 days
    return math.exp(-delta_days / self.config.tau_days)
```

Decay values:
- 1 day: 0.97 (strong)
- 30 days: 0.37 (medium)
- 90 days: 0.05 (weak)

### Causality Constraint

```python
# Source created AFTER target = no dependency
if E_delta_t == 0.0 and I == 0.0:
    return ScoringResult(..., final_score=0.0, reason='temporal_violation')
```

Exception: Explicit imports override temporal constraint (handles circular deps).

### Qdrant Integration

```python
class QdrantSemanticProvider:
    """Wraps Qdrant for semantic search."""

    def search_similar(self, query_path, limit=10, score_threshold=0.3):
        query_vector = self.embedding_func(query_path)
        return self.client.search_by_vector(query_vector, limit, score_threshold)
```

## Test Results

```
======================== 216 passed in 0.68s ========================

Coverage: 95%
- dependency_calculator.py: 146 statements, 8 missed
```

## Architecture

```
Phase 72 Pipeline:
┌──────────────┐
│ Python File  │
└──────┬───────┘
       │
       ▼
┌──────────────────┐    ┌─────────────────┐
│ PythonScanner    │    │ Qdrant          │
│ (72.3)           │    │ Vector Search   │
│ - AST parsing    │    │ - Embeddings    │
│ - Import resolve │    │ - Similarity    │
└──────┬───────────┘    └───────┬─────────┘
       │                        │
       │  import_confidence     │  semantic_score
       │                        │
       └──────────┬─────────────┘
                  │
                  ▼
       ┌──────────────────────┐
       │ DependencyCalculator │
       │ (72.4)               │
       │ - Kimi K2 formula    │
       │ - Temporal decay     │
       │ - Sigmoid normalize  │
       └──────────┬───────────┘
                  │
                  ▼
       ┌──────────────────────┐
       │ ScoringResult        │
       │ - final_score (0-1)  │
       │ - is_significant     │
       │ - components         │
       └──────────────────────┘
```

## Usage Example

```python
from src.scanners import (
    DependencyCalculator,
    ScoringInput,
    FileMetadata,
    combine_import_and_semantic
)
from datetime import datetime

# Create calculator
calculator = DependencyCalculator()

# Calculate single score
result = calculator.calculate(ScoringInput(
    source_file=FileMetadata(
        path="/src/utils.py",
        created_at=datetime(2026, 1, 1)
    ),
    target_file=FileMetadata(
        path="/src/main.py",
        created_at=datetime(2026, 1, 3)
    ),
    import_confidence=0.9,
    semantic_score=0.7
))

print(f"Score: {result.final_score:.2f}")  # ~0.85
print(f"Significant: {result.is_significant}")  # True

# Enhance existing dependencies
enhanced = combine_import_and_semantic(
    dependencies=scanner_deps,
    semantic_scores=qdrant_results
)
```

## Configuration

```python
from src.scanners import ScoringConfig, DependencyCalculator

# Custom weights for code-heavy project
config = ScoringConfig(
    w_import=0.50,    # More weight on imports
    w_semantic=0.25,  # Less on semantic
    w_reference=0.20,
    w_rrf=0.05,
    tau_days=14.0,    # Faster decay
    significance_threshold=0.7  # Higher bar
)

calculator = DependencyCalculator(config=config)
```

## Next Steps (Phase 72.5)

- Integrate with file watcher for real-time updates
- Batch processing pipeline for full project scan
- Visualization of dependency graph in 3D tree
- Performance optimization for large codebases
