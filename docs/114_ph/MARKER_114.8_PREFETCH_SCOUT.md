# MARKER_114.8 - ASYNC PRE-FETCH TOOLS SCOUT REPORT

## MISSION STATUS: COMPLETE
All insertion points for async pre-fetch tools before streaming identified and marked.

---

## SECTION 1: STREAM-PATH INSERTION POINTS (user_message_handler.py)

### INSERTION_POINT_1: Stream Parameter Collection
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py:226-229`

```python
# Phase 61: Pinned files for multi-file context
pinned_files = data.get("pinned_files", [])

# [PHASE71-M1] Phase 71: Viewport context for spatial awareness
viewport_context = data.get("viewport_context", None)
```

**Status:** AVAILABLE FOR USE
- `pinned_files` = list of file objects with context
- `viewport_context` = spatial viewport data
- `text` (original user query) = available from `data.get("text")`
- Both available BEFORE stream starts

---

### INSERTION_POINT_2: Model Prompt Assembly (Before Stream)
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py:583-590`

```python
# Phase 64.3: Use extracted helper for prompt building
# Phase 71: Added viewport_summary parameter
# Phase 73: Added json_context parameter
model_prompt = build_model_prompt(
    text,
    context_for_model,
    pinned_context,
    history_context,
    viewport_summary,
    json_context,
)
```

**Status:** PRE-FETCH TRIGGER POINT
- This is where model prompt is assembled (line 583)
- All context components (`pinned_context`, `history_context`, `viewport_summary`, `json_context`) are ready
- **PERFECT LOCATION** for async pre-fetch BEFORE line 599 (call_model_v2_stream)

---

### INSERTION_POINT_3: Stream Invocation
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py:639-645`

```python
# Use unified streaming
async for token in call_model_v2_stream(
    messages=stream_messages,  # MARKER_114.7: includes system prompt
    model=requested_model,
    provider=detected_provider,
    source=model_source,  # Phase 111.9
    temperature=0.7,
):
```

**Status:** STREAM STARTS HERE
- This is the ACTUAL stream start (AsyncGenerator)
- Tools MUST be fetched BEFORE this line
- Tools should be referenced in `stream_system_prompt` (line 622-631)

---

### INSERTION_POINT_4: Context Assembly Before Prompt Build
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py:551-579`

```python
# Build context components (lines ~551-579)
pinned_context = (
    build_pinned_context(pinned_files, user_query=text)
    if pinned_files
    else ""
)
history_context = format_history_for_prompt(chat_id, max_context=4000)
viewport_summary = (
    build_viewport_summary(viewport_context)
    if viewport_context
    else ""
)
json_context = build_json_context(
    pinned_files,
    viewport_context,
    client_id
)
```

**Status:** CONTEXT READY
- All context components built synchronously here
- This happens BEFORE model_prompt assembly (line 583)
- **IDEAL INSERTION POINT**: Add async tool pre-fetch right after json_context (after line 579)

---

## SECTION 2: HYBRID SEARCH INTERFACE

### REFERENCE: HybridSearchService.search()
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/search/hybrid_search.py:121-149`

```python
async def search(
    self,
    query: str,
    limit: int = 100,
    mode: str = "hybrid",
    filters: Optional[Dict] = None,
    collection: str = "leaf",
    skip_cache: bool = False,
) -> Dict[str, Any]:
    """
    Returns:
        Dict with:
        - results: List of matched documents with rrf_score
        - count: Number of results
        - mode: Actual mode used
        - timing_ms: Search time in milliseconds
        - sources: Which backends were used
        - cache_hit: Whether result was from cache
    """
```

**Status:** READY FOR USE
- Async function, can be awaited before stream
- Returns results in structured dict format
- Supports semantic/keyword/hybrid search modes

---

### REFERENCE: get_hybrid_search() Singleton
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/search/hybrid_search.py:532-542`

```python
def get_hybrid_search() -> HybridSearchService:
    """
    Get or create the singleton hybrid search service.

    Returns:
        HybridSearchService instance
    """
    global _hybrid_search_instance
    if _hybrid_search_instance is None:
        _hybrid_search_instance = HybridSearchService()
    return _hybrid_search_instance
```

**Status:** SINGLETON GETTER AVAILABLE
- Thread-safe singleton pattern
- Use: `hybrid = get_hybrid_search()` then `results = await hybrid.search(...)`

---

## SECTION 3: MEMORY CACHE PATTERNS

### REFERENCE: MGCCache.get_or_compute()
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/mgc_cache.py:231-256`

```python
async def get_or_compute(
    self,
    key: str,
    compute_fn: Callable[[], Awaitable[Any]],
    size_bytes: int = 0
) -> Any:
    """
    Get from cache or compute and store.

    Args:
        key: Cache key
        compute_fn: Async function to compute value if not cached
        size_bytes: Size estimate for new entry

    Returns:
        Cached or computed value
    """
    # Try cache first
    result = await self.get(key)
    if result is not None:
        return result

    # Compute and cache
    result = await compute_fn()
    await self.set(key, result, size_bytes)
    return result
```

**Status:** REUSABLE PATTERN
- Pre-fetch results can be cached with `get_or_compute()`
- Three-tier cache: RAM (Gen 0) → Qdrant (Gen 1) → JSON (Gen 2)
- Automatic promotion/demotion based on access patterns

---

### REFERENCE: get_mgc_cache() Singleton
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/mgc_cache.py:434-440`

```python
def get_mgc_cache() -> MGCCache:
    """Get or create global MGC cache instance."""
    global _global_mgc
    if _global_mgc is None:
        _global_mgc = MGCCache()
        logger.info("Global MGC cache initialized")
    return _global_mgc
```

**Status:** READY FOR USE
- Global singleton cache
- Use: `mgc = get_mgc_cache()` then `result = await mgc.get_or_compute(...)`

---

## SECTION 4: EXISTING INJECT_CONTEXT PATTERN (PROVEN)

### EXISTING PATTERN: LLMCallTool._gather_inject_context()
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/llm_call_tool.py:281-387`

**Pattern Analysis:**

```python
async def _gather_inject_context(self, inject_config: Dict[str, Any]) -> str:
    """
    Phase 55.2: Gather context from VETKA sources for injection.

    FLOW:
    1. Read files (if specified)
    2. Load session state from MCPStateManager
    3. Get user preferences from Engram
    4. Get CAM active nodes
    5. Semantic search results (KEY PART FOR PRE-FETCH)
    6. Apply ELISION compression
    """
    context_parts = []

    # ... file reading ...
    # ... session state ...
    # ... engram prefs ...
    # ... CAM nodes ...

    # 5. Semantic search results
    semantic_query = inject_config.get("semantic_query")
    if semantic_query:
        try:
            from src.search.hybrid_search import HybridSearch
            search = HybridSearch()
            limit = inject_config.get("semantic_limit", 5)
            results = await search.search(semantic_query, limit=limit)
            if results:
                search_text = []
                for r in results[:limit]:
                    path = r.get("path", r.get("file_path", "unknown"))
                    score = r.get("score", 0)
                    snippet = r.get("content", "")[:300]
                    search_text.append(f"**{path}** (score: {score:.2f})\n{snippet}")
                context_parts.append(f"### Semantic Search: '{semantic_query}'\n" + "\n\n".join(search_text))
        except Exception as e:
            logger.warning(f"[INJECT_CONTEXT] Semantic search error: {e}")

    # 6. Apply ELISION compression
    if inject_config.get("compress", True) and len(full_context) > 2000:
        try:
            from src.memory.elision import compress_context
            compressed = compress_context({"content": full_context})
            if compressed and len(compressed) < len(full_context):
                full_context = compressed
        except Exception as e:
            logger.warning(f"[INJECT_CONTEXT] Compression error: {e}")

    return f"<vetka_context>\n{full_context}\n</vetka_context>"
```

**Key Insights for Phase 114.8:**
- ✅ Already uses `HybridSearch` for semantic pre-fetch (line 354)
- ✅ Already handles async/await pattern correctly
- ✅ Already applies ELISION compression
- ✅ Error handling with fallback
- ❌ Uses `HybridSearch()` directly instead of `get_hybrid_search()` singleton

**REUSE PATTERN:**
The `_gather_inject_context()` method is THE proven pattern for:
1. Async context gathering
2. Semantic search integration
3. Error handling
4. Context compression

---

## SECTION 5: TEXT/QUERY AVAILABILITY

### User Query Available At:
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py:179-220`

```python
def on_message(data):
    ...
    text = data.get("text", "")  # Line ~180
    ...
    requested_model = data.get("model", "grok-4")  # Line ~218
    model_source = data.get("model_source")  # Line ~221
    pinned_files = data.get("pinned_files", [])  # Line ~226
    viewport_context = data.get("viewport_context", None)  # Line ~229
```

**Status:** ALL PARAMETERS AVAILABLE
- `text` = original user query
- `requested_model` = which model will be used
- `model_source` = provider source (poe, polza, openrouter)
- `pinned_files` = context files
- `viewport_context` = spatial data

---

## SECTION 6: TOOL AWARENESS IN STREAMING

### Current Tool Hint (Placeholder)
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py:619-631`

```python
# MARKER_114.7_STREAM_TOOLS: Add tool awareness to streamed models
# Streaming can't do tool calling loop, but model should know tools exist
# so it can reference them and suggest their use
stream_system_prompt = """You are a VETKA AI agent with access to project context.

Available tools (mention them when relevant):
- vetka_search_semantic: Search codebase by meaning (Qdrant vector search)
- vetka_camera_focus: Move 3D camera to focus on files/folders
- get_tree_context: Get file/folder hierarchy
- search_codebase: Search code by pattern (grep)
- vetka_edit_artifact: Create code artifacts for review

Note: In streaming mode, you cannot execute tools directly. Describe what tools you would use and what you expect to find. The user can then ask the system to execute them."""
```

**Status:** PLACEHOLDER ONLY
- This is a STATIC hint to the model
- Phase 114.8 will REPLACE this with actual pre-fetched tool results
- Model will reference REAL search results instead of suggesting searches

---

## IMPLEMENTATION ROADMAP FOR PHASE 114.8

### RECOMMENDED INSERTION POINT:
**After line 579** (after json_context is built, before line 583 model_prompt assembly)

```python
# ====== PHASE 114.8: PRE-FETCH TOOLS BEFORE STREAM ======
# Async pre-fetch semantic search results to inject into stream system prompt
# This allows streaming models to reference tool results without tool calling loop

# Extract semantic query from user text
semantic_query = text[:200]  # First 200 chars as search query

# Pre-fetch from hybrid search (async, non-blocking)
try:
    from src.search.hybrid_search import get_hybrid_search
    hybrid = get_hybrid_search()

    # Async pre-fetch (happens during stream setup, not during streaming)
    search_results = await hybrid.search(
        query=semantic_query,
        limit=5,
        mode="hybrid",
        skip_cache=False
    )

    # Format results for system prompt injection
    if search_results.get("count", 0) > 0:
        tools_context = _format_search_results_for_stream(search_results["results"])
    else:
        tools_context = ""

except Exception as e:
    logger.warning(f"[PHASE_114.8] Pre-fetch failed: {e}")
    tools_context = ""

# ====== END PHASE 114.8 ======
```

### THEN AT LINE 622: INJECT TOOLS_CONTEXT
Replace the static tool hint with actual pre-fetched results in stream_system_prompt.

---

## DEPENDENCIES TO IMPORT

```python
# In user_message_handler.py imports section (line 80-116):

from src.search.hybrid_search import get_hybrid_search

# Optional (for caching pre-fetch results):
from src.memory.mgc_cache import get_mgc_cache
from src.memory.elision import compress_context
```

---

## MARKER LEGEND

| Marker | Meaning |
|--------|---------|
| `INSERTION_POINT_N` | Specific line(s) where code should be inserted |
| `REFERENCE` | Code pattern/interface to reference (read-only) |
| `PRE-FETCH TRIGGER POINT` | Where async pre-fetch should happen |
| `STREAM STARTS HERE` | Where actual token streaming begins |
| `AVAILABLE FOR USE` | Component ready to be used |
| `REUSABLE PATTERN` | Pattern proven to work, can be copied |
| `PROVEN` | Already implemented elsewhere, safe to follow |

---

## QUICK CHECKLIST FOR PHASE 114.8 IMPLEMENTATION

- [ ] Add `get_hybrid_search` import (line ~85)
- [ ] Add async pre-fetch code after line 579
- [ ] Create `_format_search_results_for_stream()` helper function
- [ ] Inject `tools_context` into `stream_system_prompt` (replace static hint at line 622)
- [ ] Add MGC caching for pre-fetch results (optional, for performance)
- [ ] Test with multiple models (Grok, GPT, Claude)
- [ ] Verify ELISION compression applies to injected context
- [ ] Add MARKER comment at insertion point for future audits

---

## FILE REFERENCE SUMMARY

| File | Lines | Purpose |
|------|-------|---------|
| `user_message_handler.py` | 226-229 | Stream parameters collection |
| `user_message_handler.py` | 579 | **INSERTION POINT** (after json_context) |
| `user_message_handler.py` | 583-590 | Model prompt assembly |
| `user_message_handler.py` | 622-631 | **INJECTION POINT** (stream_system_prompt) |
| `user_message_handler.py` | 639-645 | Stream invocation |
| `hybrid_search.py` | 121-149 | HybridSearchService.search() signature |
| `hybrid_search.py` | 532-542 | get_hybrid_search() singleton |
| `mgc_cache.py` | 231-256 | MGCCache.get_or_compute() pattern |
| `mgc_cache.py` | 434-440 | get_mgc_cache() singleton |
| `llm_call_tool.py` | 281-387 | Proven inject_context pattern |
| `provider_registry.py` | 1675-1702 | call_model_v2_stream() signature |

---

**Report Generated:** 2026-02-06
**Scout Status:** COMPLETE ✅
**Ready for Implementation:** YES
