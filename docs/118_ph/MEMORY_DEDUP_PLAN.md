# MGC Deduplication Plan — Phase 119.1

## Problem (Kimi K2.5 Memory System Audit)

Triple MGC implementation found:

| Location | Class | Type | Notes |
|----------|-------|------|-------|
| `src/memory/mgc_cache.py` | MGCCache | PRIMARY | Async, 3-tier (RAM/Qdrant/JSON), asyncio.Lock |
| `src/memory/spiral_context_generator.py:91-156` | MGCGraphCache | DUPLICATE #1 | Sync, decay=0.05, pool_size=10 |
| `src/agents/arc_solver_agent.py:50-123` | MGCGraphCache | DUPLICATE #2 | Sync, deque, request pooling |

### Consequences
- Caches not synchronized — entries in one don't propagate to others
- Maintenance nightmare — bug fixes need 3x effort
- Memory waste — three separate Gen0 RAM stores

## Proposed Solution

### Step 1: Create MGCCacheSync wrapper (or use MemoryProxy)
```python
# Sync wrapper over async MGCCache for spiral_context and arc_solver
class MGCCacheSync:
    def __init__(self):
        self._cache = get_mgc_cache()  # Singleton

    def get(self, key):
        return asyncio.run(self._cache.get(key))

    def cascade(self, key, value):
        return asyncio.run(self._cache.cascade(key, value))
```

### Step 2: Replace MGCGraphCache in both files
```python
# spiral_context_generator.py
- from ... import MGCGraphCache
+ from src.memory import get_mgc_cache
  self.mgc = get_mgc_cache()  # Shared singleton

# arc_solver_agent.py — same pattern
```

### Step 3: Delete MGCGraphCache class from both files

## Files to Modify (4 files)

| File | Changes |
|------|---------|
| `src/memory/spiral_context_generator.py` | Remove MGCGraphCache (lines 91-156), use MGCCache |
| `src/agents/arc_solver_agent.py` | Remove MGCGraphCache (lines 50-123), use MGCCache |
| `src/memory/mgc_cache.py` | Add sync helpers or wrapper |
| `src/memory/__init__.py` | Export sync wrapper |

## Key Differences Between Implementations

| Feature | MGCCache (primary) | MGCGraphCache (dups) |
|---------|-------------------|---------------------|
| Gen0 max | 100 | 100 (same) |
| Promotion threshold | 3 accesses | 5 usages |
| Decay | None | 0.05/week |
| Thread safety | asyncio.Lock | None |
| JSON fallback | Yes (data/mgc_cache.json) | No |

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Async/sync mismatch | MEDIUM | MemoryProxy or MGCCacheSync wrapper |
| Different thresholds | LOW | Use primary MGCCache defaults |
| ARC solver perf | LOW | Request pooling via deque stays in ARC |

## Effort: MEDIUM (2-3 hours). Careful import verification needed.
