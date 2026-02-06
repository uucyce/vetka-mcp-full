# Phase 114.8.1: MGC Cache Integration — Verification Report
## Haiku Scouts (5) → Sonnet Verification

**Date:** 2026-02-06
**Status:** VERIFIED ✅ Ready for implementation

---

## Scout Results Summary

### Scout 1: MGC Cache Interface
**EXACT signature of `get_or_compute()`:**
```python
async def get_or_compute(
    self,
    key: str,
    compute_fn: Callable[[], Awaitable[Any]],
    size_bytes: int = 0
) -> Any
```
- ❌ **NO `ttl` parameter** — Grok's code has `ttl=300` which will CRASH
- ✅ `size_bytes` is optional, defaults to 0
- ✅ `compute_fn` must be async callable with ZERO args
- ✅ Result is `await compute_fn()` — properly awaits

### Scout 2: Current Pre-fetch Code
- Lines 608-636: Pre-fetch block with `await hybrid.search()`
- Lines 677-694: `MARKER_114.8_STREAM_PREFETCH` with conditional injection
- Variables available: `text`, `chat_id`, `requested_model`, `prefetch_context`
- MGC integration point: WRAP the `hybrid.search()` call (line 618)

### Scout 3: inject_context Pattern
- `_gather_inject_context()` does NOT use MGC cache
- Uses direct singleton getters
- ELISION compression: only if `> 2000 chars`
- Error handling: try/except with `logger.warning()`, never raises

### Scout 4: MGC Usage in Codebase
- 7 files reference MGC, but user_message_handler.py has NO import
- Key naming: arbitrary strings, hashed to 16-char MD5
- `message_utils.py` uses MGC indirectly via `SpiralContextGenerator().mgc_cache`
- Test patterns confirm `await mgc.get_or_compute(key, async_fn)`

### Scout 5: Grok's Code Review
| Issue | Severity | Fix |
|-------|----------|-----|
| `ttl=300` — PARAMETER DOES NOT EXIST | 🔴 BLOCKING | Remove `ttl=` kwarg |
| Lambda compute_fn must return Awaitable | 🟡 HIGH | Use proper async function |
| `search_results.get("count")` may be None | 🟡 MEDIUM | Add isinstance check |

---

## Sonnet Verification

### Confirmed by reading actual code:
1. ✅ `mgc_cache.py:231-236` — exact signature matches Scout 1 report
2. ✅ `mgc_cache.py:254` — `result = await compute_fn()` — requires async
3. ✅ Current pre-fetch at lines 608-636 — clean, ready for MGC wrap
4. ✅ `chat_id` available in scope (from line ~552)

### Architecture Decision:
**INLINE MGC wrap** (not separate function) — follows the existing pattern in the pre-fetch block. No need for `_prefetch_tools_with_cache()` wrapper — keeps code co-located.

---

## Implementation Plan

### What Changes:
Replace direct `hybrid.search()` call with `mgc.get_or_compute()` wrapper.

### Exact Code (CORRECTED from Grok):
```python
# In pre-fetch block (lines 612-635):
prefetch_context = ""
try:
    from src.search.hybrid_search import get_hybrid_search
    from src.memory.mgc_cache import get_mgc_cache

    hybrid = get_hybrid_search()
    mgc = get_mgc_cache()
    semantic_query = text[:200] if text else "project overview"
    cache_key = f"stream_prefetch:{semantic_query[:100]}"

    async def _compute_search():
        return await hybrid.search(
            query=semantic_query,
            limit=5,
            mode="hybrid",
            collection="leaf",
            skip_cache=False,
        )

    search_response = await mgc.get_or_compute(
        key=cache_key,
        compute_fn=_compute_search,
        size_bytes=0,
    )

    if isinstance(search_response, dict) and search_response.get("count", 0) > 0:
        prefetch_context = _format_search_results_for_stream(
            search_response["results"]
        )
except Exception as prefetch_err:
    print(f"[PHASE_114.8] Pre-fetch failed: {prefetch_err}")
```

### Key Corrections vs Grok:
1. ❌ `ttl=300` → removed (parameter doesn't exist)
2. ❌ `lambda: fn()` → `async def _compute_search()` (proper async)
3. ❌ `chat_id` in cache key → `semantic_query[:100]` (query-based, not session-based — same query = same results regardless of chat)
4. ✅ `isinstance(search_response, dict)` safety check added
5. ✅ Inline pattern (no separate function)

---

## Files to Modify
| File | Change |
|------|--------|
| `src/api/handlers/user_message_handler.py:608-636` | Wrap hybrid.search() with MGC |

## Performance Impact
- Cache HIT: ~0ms (vs 50-100ms for hybrid search)
- Cache MISS: same as before (50-100ms)
- Repeat queries in same session: instant
- MGC Gen 0 (RAM): LRU eviction at 100 items
