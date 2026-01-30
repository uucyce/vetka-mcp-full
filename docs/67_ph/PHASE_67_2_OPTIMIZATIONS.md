# Phase 67.2: Context Assembly Optimizations

**Date:** 2026-01-18
**Commit:** `ee7ddb2`
**Status:** COMPLETED

---

## Summary

Оптимизации производительности для Phase 67 context assembly:

| Optimization | Before | After | Impact |
|-------------|--------|-------|--------|
| CAM Engine | New instance per call | Singleton | ~100ms saved per call |
| Qdrant queries | N queries for N files | 1 batch query | N-1 round trips saved |
| Relevance cache | None | LRU 100 entries | 0ms for repeated queries |
| Config | Hardcoded | Env variables | Runtime adjustable |

---

## Changes Made

### 1. `src/orchestration/cam_engine.py`

Added singleton pattern:

```python
# Line 753
_cam_engine_instance: Optional[VETKACAMEngine] = None

def get_cam_engine(memory_manager=None) -> Optional[VETKACAMEngine]:
    """Factory function - returns singleton CAM engine."""
    global _cam_engine_instance
    if _cam_engine_instance is None:
        _cam_engine_instance = VETKACAMEngine(memory_manager=memory_manager)
    return _cam_engine_instance

def reset_cam_engine():
    """Reset singleton for testing."""
    global _cam_engine_instance
    _cam_engine_instance = None
```

### 2. `src/api/handlers/message_utils.py`

#### Environment Variables (Line 44-48)

```python
QDRANT_WEIGHT = float(os.getenv("VETKA_QDRANT_WEIGHT", "0.7"))
CAM_WEIGHT = float(os.getenv("VETKA_CAM_WEIGHT", "0.3"))
MAX_CONTEXT_TOKENS = int(os.getenv("VETKA_MAX_CONTEXT_TOKENS", "4000"))
MAX_TOKENS_PER_FILE = int(os.getenv("VETKA_MAX_TOKENS_PER_FILE", "1000"))
VETKA_DEBUG_CONTEXT = os.getenv("VETKA_DEBUG_CONTEXT", "false").lower() == "true"
```

#### Cache (Line 50-54)

```python
_relevance_cache: Dict[str, List[Tuple[Dict, float]]] = {}
_cache_max_size = 100
_cache_hits = 0
_cache_misses = 0
```

#### New Functions

| Function | Line | Purpose |
|----------|------|---------|
| `_batch_get_qdrant_relevance()` | 171 | Single Qdrant query for all files |
| `_batch_get_cam_activations()` | 255 | Batch CAM scores |
| `_make_cache_key()` | 290 | MD5 hash of query + sorted paths |
| `clear_relevance_cache()` | 392 | Clear cache (for testing) |
| `get_cache_stats()` | 401 | Get hit/miss statistics |

#### Updated `_get_cam_activation()` (Line 223)

```python
def _get_cam_activation(file_path: str) -> float:
    # Phase 67.2: Use singleton instead of creating new instance
    from src.orchestration.cam_engine import get_cam_engine
    cam = get_cam_engine()  # ← Was: VETKACAMEngine()
    ...
```

---

## Performance Analysis

### Before Phase 67.2

```
For 5 pinned files with query "How does X work?":

1. get_embedding(query)              ~50ms
2. _get_qdrant_relevance(file1)      ~20ms
3. _get_qdrant_relevance(file2)      ~20ms
4. _get_qdrant_relevance(file3)      ~20ms
5. _get_qdrant_relevance(file4)      ~20ms
6. _get_qdrant_relevance(file5)      ~20ms
7. VETKACAMEngine() × 5              ~500ms (100ms each)
8. calculate_activation × 5          ~25ms
                                     ─────────
                                     ~675ms
```

### After Phase 67.2

```
First call (cache miss):

1. Check cache (miss)                ~0ms
2. get_embedding(query)              ~50ms
3. _batch_get_qdrant_relevance()     ~25ms (1 query)
4. _batch_get_cam_activations()      ~25ms (singleton)
5. Store in cache                    ~0ms
                                     ─────────
                                     ~100ms

Second call (cache hit):

1. Check cache (hit)                 ~0ms
                                     ─────────
                                     ~0ms
```

**Improvement:** ~575ms saved on first call, ~675ms on subsequent calls

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VETKA_QDRANT_WEIGHT` | `0.7` | Weight for Qdrant semantic similarity |
| `VETKA_CAM_WEIGHT` | `0.3` | Weight for CAM activation score |
| `VETKA_MAX_CONTEXT_TOKENS` | `4000` | Total token budget for context |
| `VETKA_MAX_TOKENS_PER_FILE` | `1000` | Token limit per file |
| `VETKA_DEBUG_CONTEXT` | `false` | Show debug info in context XML |

### Usage

```bash
# Adjust weights for more semantic relevance
export VETKA_QDRANT_WEIGHT=0.8
export VETKA_CAM_WEIGHT=0.2

# Increase context budget
export VETKA_MAX_CONTEXT_TOKENS=8000

# Enable debug mode
export VETKA_DEBUG_CONTEXT=true
```

---

## Debug Mode Output

When `VETKA_DEBUG_CONTEXT=true`:

```xml
<pinned_context>
User has pinned 8 file(s). Included 5 most relevant file(s) for context (~3200 tokens).
(Files ranked by semantic relevance to user query. Showing top 5 of 8.)

<pinned_file path="src/api/handlers/message_utils.py" name="message_utils.py" relevance="0.85">
...
</pinned_file>
...
</pinned_context>

<context_debug>
Query: How does context building work?
Ranking:
  1. message_utils.py - relevance=0.850
  2. qdrant_client.py - relevance=0.720
  3. cam_engine.py - relevance=0.680
  4. user_message_handler.py - relevance=0.550
  5. __init__.py - relevance=0.420
Weights: qdrant=0.7, cam=0.3
Cache: 50.0% hit rate (1 hits, 1 misses)
</context_debug>
```

---

## Cache API

```python
from src.api.handlers.message_utils import (
    clear_relevance_cache,
    get_cache_stats
)

# Get statistics
stats = get_cache_stats()
# {'size': 5, 'max_size': 100, 'hits': 10, 'misses': 5, 'hit_rate': '66.7%'}

# Clear cache
clear_relevance_cache()
```

---

## Tests Passed

```
✅ Test 1: Config defaults correct (0.7, 0.3, 4000, 1000)
✅ Test 2: _estimate_tokens works
✅ Test 3: _smart_truncate works
✅ Test 4: _make_cache_key consistent (sorted paths)
✅ Test 5: Cache functions work
✅ Test 6: build_pinned_context handles empty list
✅ Test 7: Signature correct with config defaults
✅ Test 8: CAM singleton works (cam1 is cam2)
✅ Integration: Cache hit rate 50% after 2 calls
```

---

## Backward Compatibility

- All existing function signatures preserved
- Default values unchanged (just sourced from env vars)
- No breaking changes to `build_pinned_context()` API

---

## Files Modified

| File | Changes |
|------|---------|
| `src/orchestration/cam_engine.py` | +38 lines (singleton) |
| `src/api/handlers/message_utils.py` | +150 lines (batch, cache, config) |

---

## Git

```bash
git log --oneline -1
# ee7ddb2 Phase 67.2: Context assembly optimizations
```
