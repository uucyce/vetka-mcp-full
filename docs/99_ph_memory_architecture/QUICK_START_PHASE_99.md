# Phase 99 Quick Start

## TL;DR

Three new components for VETKA memory:

1. **STM Buffer** — Last 5-10 interactions with decay
2. **MGC Cache** — RAM → Qdrant → JSON hierarchy
3. **MemoryProxy** — Rate limiting, no vicious cycles

---

## Implementation Order

```
Phase 99.1: STM Buffer
├── src/memory/stm_buffer.py (NEW)
├── workflow.py: add stm_buffer to state
├── langgraph_nodes.py: update after HOPE
└── cam_agent.py: surprise → STM

Phase 99.2: MGC Cache
├── src/memory/mgc_cache.py (NEW)
├── qdrant_client.py: route through MGC
└── embedding_pipeline.py: use MGC

Phase 99.3: MemoryProxy
├── src/memory/memory_proxy.py (NEW)
└── wrap all memory operations

Phase 99.4: Frontend (optional)
├── useStore.ts: mirror STM
└── STMVisualization.tsx (NEW)
```

---

## Key Concepts

### STM (Short-Term Memory)
```python
# Recent items with decay
stm = STMBuffer(max_size=10, decay_rate=0.1)
stm.add(STMEntry(content="...", source="user"))
context = stm.get_context(max_items=5)  # sorted by weight
```

### MGC (Multi-Generational Cache)
```python
# Automatic tier management
mgc = MGCCache(gen0_max=100)
await mgc.set("key", value)      # → Gen 0 (RAM)
result = await mgc.get("key")    # checks Gen 0 → Gen 1 → Gen 2
```

### MemoryProxy
```python
# Prevents overload
proxy = MemoryProxy(max_concurrent=10, rate_limit=100)
result = await proxy.execute("key", some_async_func, args)
```

---

## Integration Points

| Component | Integrates With |
|-----------|-----------------|
| STM | HOPE, CAM, LangGraph state |
| MGC | Qdrant, JSON files, embedding pipeline |
| MemoryProxy | All memory operations |

---

## Markers

All new files should have:
```python
"""
@status: active
@phase: 99
@depends: ...
@used_by: ...
"""
```

---

## Test Commands

```bash
# Run Phase 99 tests
pytest tests/test_stm_buffer.py -v
pytest tests/test_mgc_cache.py -v

# Integration test
pytest tests/test_phase99_integration.py -v
```

---

**Ready for implementation!**
