# STM Unification Plan — Phase 119.2

## Problem (Kimi K2.5 Audit + Grok 4.1 Analysis)

Triple STM duplication found:

| Location | Type | Structure | Eviction |
|----------|------|-----------|----------|
| `src/memory/stm_buffer.py` | STMBuffer (PRIMARY) | deque(maxlen), decay+surprise | LRU + decay |
| `src/orchestration/agent_pipeline.py:134` | `self.stm` list (DUPLICATE) | list, append/pop(0) | FIFO O(n) |
| `src/orchestration/orchestrator_with_elisya.py` | ElisyaState (third system) | dict-based | Manual |

## Proposed Solution (Grok 4.1 Verified)

**Bridge pipeline STM → STMBuffer via MemoryProxy sync wrapper.**

### Step 1: Replace pipeline list with STMBuffer singleton
```python
# agent_pipeline.py
from src.memory import get_stm_buffer, get_memory_proxy
self.stm = get_memory_proxy(get_stm_buffer())  # Sync wrapper
```

### Step 2: Add MGC eviction hook
```python
# stm_buffer.py: evict() -> MGC Gen1/Gen2
async def evict(self):
    if len(self.deque) > self.maxlen:
        evicted = self.deque.popleft()
        await self.mgc.set(f"stm:{evicted['id']}", evicted)
```

### Step 3: MemoryProxy sync/async bridge
```python
# memory_proxy.py already exists (Phase 99)
stm_proxy = get_memory_proxy(get_stm_buffer())
context = stm_proxy.get_recent_sync(5)  # Sync call
```

### Step 4: Backward-compatible self.stm property
Pipeline code continues using `self.stm.append()` and `self.stm[-3:]` syntax via property proxy.

## Files to Modify (4 files, ~80 lines)

| File | Changes |
|------|---------|
| `src/memory/stm_buffer.py` | MGC eviction hook |
| `src/orchestration/agent_pipeline.py` | list → STMBuffer singleton |
| `src/memory/memory_proxy.py` | Sync wrappers |
| `src/memory/__init__.py` | Export updates |

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Async in sync pipeline | MemoryProxy (sync facade) |
| Qdrant overload | RateLimitExceeded in Proxy |
| Data loss | Gen2 JSON fallback |

## Prerequisites (Done in Phase 118.8)
- STMConfig dataclass with env vars
- Thread-safe singletons
- Pipeline constants extracted
- Adaptive STM window + ELISION level

## Effort: LOW (1-2 hours). No breaking changes.
