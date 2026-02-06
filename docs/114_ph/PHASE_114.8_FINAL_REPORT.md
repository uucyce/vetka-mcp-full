# Phase 114.8: Async Pre-Fetch Semantic Search Before Stream
## Final Implementation Report

**Date:** 2026-02-06
**Status:** IMPLEMENTED ✅
**Commits:** Previous: 78bb8109, 993be677, 462ae5a4

---

## What Was Done

### FIX 114.8.1: Async Pre-Fetch in Stream Path
**File:** `src/api/handlers/user_message_handler.py`

**Problem:** Stream path (solo chat) had NO tool results. Phase 109.7 intentionally removed tools from streaming. Phase 114.7 added a "костыль" — static system prompt saying "you cannot execute tools directly, describe what you would use". Models got zero real data from codebase.

**Solution:** Async pre-fetch via `HybridSearchService.search()` BEFORE stream starts.

**Changes:**
1. **Helper function** `_format_search_results_for_stream()` — formats search results into readable markdown for system prompt injection (after line 56, before `register_user_message_handler`)
2. **Pre-fetch block** — `await hybrid.search(query=text[:200], limit=5, mode="hybrid")` inserted AFTER `save_chat_message`, BEFORE `build_model_prompt`. Non-blocking: errors caught, stream continues with empty context.
3. **System prompt replacement** — MARKER_114.7 static tool hint replaced with MARKER_114.8 conditional injection. If pre-fetch found results → real data injected. If not → fallback tool list.

**Flow:**
```
user sends message →
  build_pinned_context() →
  json_context() →
  save_chat_message() →
  [NEW] await hybrid.search(text) → prefetch_context →  ← PHASE 114.8
  build_model_prompt() →
  [REPLACED] stream_system_prompt with prefetch_context →  ← PHASE 114.8
  call_model_v2_stream(messages=[system+user]) →
  async for token: emit to UI
```

**Key insight (from Данила):** `handle_user_message` is `async def` — so `await hybrid.search()` works directly. No ThreadPoolExecutor/Flask sync issues. Phase 109.7 removed tools unnecessarily.

### FIX 114.8.2: HybridSearch Import Bug
**File:** `src/mcp/tools/llm_call_tool.py`

**Problem:** Line 354 imported `HybridSearch` — a class that DOES NOT EXIST. Line 355 created `HybridSearch()` — new instance every call instead of singleton.

**Fix:**
- `from src.search.hybrid_search import HybridSearch` → `from src.search.hybrid_search import get_hybrid_search`
- `search = HybridSearch()` → `search = get_hybrid_search()`
- `results = await search.search(...)` → `search_response = await search.search(...)` + `results = search_response.get("results", [])` (was treating Dict as List)

---

## Files Modified

| File | Changes |
|------|---------|
| `src/api/handlers/user_message_handler.py` | +helper function, +pre-fetch block, replaced stream_system_prompt |
| `src/mcp/tools/llm_call_tool.py` | Fixed import + singleton + results extraction |

## Verification Results

```
✅ Task 1: _format_search_results_for_stream() helper found
✅ Task 3: Pre-fetch logic with await hybrid.search() found
✅ Task 4: Stream system prompt replaced with conditional pre-fetch
✅ FIX 114.8.2: llm_call_tool.py import + results extraction fixed
✅ user_message_handler.py: Valid Python syntax
✅ llm_call_tool.py: Valid Python syntax
ALL CHECKS PASSED ✅
```

## Markers

| Marker | Location | Purpose |
|--------|----------|---------|
| `PHASE 114.8: PRE-FETCH TOOLS BEFORE STREAM` | user_message_handler.py | Pre-fetch block start |
| `END PHASE 114.8 PRE-FETCH` | user_message_handler.py | Pre-fetch block end |
| `MARKER_114.8_STREAM_PREFETCH` | user_message_handler.py | System prompt replacement |
| `FIX_114.8.2` | llm_call_tool.py | Import bug fix |

## What Grok Gets Now

**Before (Phase 114.7):**
```
System: "You cannot execute tools directly. Describe what tools you would use."
→ Grok describes hypothetical searches, zero real data
```

**After (Phase 114.8):**
```
System: "Pre-fetched Codebase Search Results:
### Result 1: `src/main.py` (score: 0.891)
[actual file content snippet]
### Result 2: `src/api/routes.py` (score: 0.754)
[actual file content snippet]
Reference them in your answer."
→ Grok references REAL codebase data in streaming response
```

## Rollback

Remove pre-fetch block + helper function + restore static prompt. No DB changes.
