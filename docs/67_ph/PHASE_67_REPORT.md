# Phase 67: CAM + Qdrant Integration into Context Assembly

**Date:** 2026-01-18
**Commit:** `3a53ca9`
**Status:** COMPLETED

---

## TL;DR

CAM Engine (840+ строк) и Qdrant client были полностью реализованы, но НЕ использовались для сборки контекста.
`build_pinned_context()` тупо читал файлы через `read()` — теперь подключены Qdrant semantic search + CAM activation scores.

---

## Что было сделано

### 1. Модифицированные файлы

| Файл | Изменения | Строк |
|------|-----------|-------|
| `src/api/handlers/message_utils.py` | Новые функции + обновлённая логика | +290 |
| `src/api/handlers/user_message_handler.py` | 4 call-sites обновлены | +4/-4 |

### 2. Новые функции в `message_utils.py`

```
src/api/handlers/message_utils.py
├── format_history_for_prompt()      # Без изменений
├── load_pinned_file_content()       # Без изменений
├── _estimate_tokens()               # NEW: ~4 chars per token
├── _smart_truncate()                # NEW: 60% head + 40% tail
├── _get_qdrant_relevance()          # NEW: Semantic search score
├── _get_cam_activation()            # NEW: CAM activation score
├── _rank_pinned_files()             # NEW: Weighted ranking
├── build_pinned_context()           # UPDATED: Smart selection
└── build_pinned_context_legacy()    # NEW: Fallback version
```

---

## Архитектура решения

### Data Flow

```
User Message
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  build_pinned_context(pinned_files, user_query=text)        │
└─────────────────────────────────────────────────────────────┘
    │
    ├──► _rank_pinned_files()
    │       │
    │       ├──► get_embedding(user_query)     ← EmbeddingService
    │       │
    │       ├──► _get_qdrant_relevance()       ← QdrantVetkaClient
    │       │       └── search_by_vector()
    │       │
    │       └──► _get_cam_activation()         ← VETKACAMEngine
    │               └── calculate_activation_score()
    │
    │   relevance = 0.7 * qdrant_score + 0.3 * cam_score
    │
    ├──► Sort by relevance (descending)
    │
    ├──► Select top N files (max_files=5)
    │
    ├──► _smart_truncate() each file
    │       └── Keep 60% head + 40% tail
    │
    └──► Build XML context with relevance tags
```

### Scoring Formula

```python
relevance_score = 0.7 * qdrant_similarity + 0.3 * cam_activation
```

- **Qdrant similarity (70%):** Semantic relevance to user query
- **CAM activation (30%):** Historical importance based on query history

---

## API Changes

### Before (Phase 61)

```python
def build_pinned_context(pinned_files: list, max_files: int = 10) -> str:
    # Simple read + char truncation at 3000 chars
```

### After (Phase 67)

```python
def build_pinned_context(
    pinned_files: list,
    user_query: str = "",           # NEW: For relevance ranking
    max_files: int = 5,             # CHANGED: 10 → 5
    max_tokens_per_file: int = 1000,# NEW: Token-based
    max_total_tokens: int = 4000    # NEW: Total budget
) -> str:
    # Smart selection + token-based truncation
```

### Backward Compatibility

- `user_query` has default value `""` — old calls work
- `build_pinned_context_legacy()` available for explicit fallback

---

## Call Sites Updated

### `user_message_handler.py`

| Line | Before | After |
|------|--------|-------|
| 259 | `build_pinned_context(pinned_files)` | `build_pinned_context(pinned_files, user_query=text)` |
| 392 | `build_pinned_context(pinned_files)` | `build_pinned_context(pinned_files, user_query=text)` |
| 619 | `build_pinned_context(pinned_files)` | `build_pinned_context(pinned_files, user_query=clean_text)` |
| 1295 | `build_pinned_context(pinned_files)` | `build_pinned_context(pinned_files, user_query=text)` |

---

## Smart Truncation Algorithm

```python
def _smart_truncate(content: str, max_tokens: int = 1000) -> str:
    max_chars = max_tokens * 4  # ~4 chars per token

    if len(content) <= max_chars:
        return content

    # Keep 60% from beginning, 40% from end
    head_chars = int(max_chars * 0.6)
    tail_chars = int(max_chars * 0.4)

    head = content[:head_chars]
    tail = content[-tail_chars:]

    return f"{head}\n\n... [truncated {len(content) - max_chars} chars] ...\n\n{tail}"
```

**Rationale:**
- Beginning: imports, class definitions, type declarations
- End: exports, main logic, entry points
- Middle: often less critical implementation details

---

## Fallback Behavior

```
┌─────────────────────────────────────────────────────────────┐
│                    Graceful Degradation                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Qdrant unavailable?                                        │
│    → qdrant_score = 0.5 (neutral)                          │
│                                                             │
│  Embedding service unavailable?                             │
│    → query_embedding = None                                 │
│    → Skip Qdrant search, use qdrant_score = 0.5            │
│                                                             │
│  CAM engine unavailable?                                    │
│    → cam_score = 0.5 (neutral)                             │
│                                                             │
│  All services down?                                         │
│    → All files get score 0.5                               │
│    → Original order preserved                               │
│    → Still applies smart truncation                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Output Format

### With Smart Selection

```xml
<pinned_context>
User has pinned 8 file(s). Included 5 most relevant file(s) for context (~3200 tokens).
(Files ranked by semantic relevance to user query. Showing top 5 of 8.)

<pinned_file path="src/api/handlers/message_utils.py" name="message_utils.py" relevance="0.85">
... file content ...
</pinned_file>

<pinned_file path="src/memory/qdrant_client.py" name="qdrant_client.py" relevance="0.72">
... file content ...
</pinned_file>

...
</pinned_context>
```

### Without Smart Selection (fallback)

```xml
<pinned_context>
User has pinned 3 file(s). Included 3 most relevant file(s) for context (~1500 tokens).

<pinned_file path="src/foo.py" name="foo.py">
... file content ...
</pinned_file>

...
</pinned_context>
```

---

## Logging

```python
logger = logging.getLogger("VETKA_CONTEXT")

# Success case
logger.info("[CONTEXT] Using smart selection: 5 files, 0.72 avg relevance")

# Fallback cases
logger.warning("[CONTEXT] Smart ranking failed, using fallback: {error}")
logger.debug("[CONTEXT] Qdrant relevance failed: {error}")
logger.debug("[CONTEXT] CAM activation failed: {error}")
logger.debug("[CONTEXT] Embedding failed: {error}")
```

---

## Dependencies

### Required (already exist)

```
src/memory/qdrant_client.py
├── get_qdrant_client() → QdrantVetkaClient
└── QdrantVetkaClient.search_by_vector()

src/orchestration/cam_engine.py
├── VETKACAMEngine
└── calculate_activation_score()

src/utils/embedding_service.py
├── get_embedding_service() → EmbeddingService
└── get_embedding() → List[float]
```

### Optional (graceful degradation)

- Qdrant server (localhost:6333)
- Ollama with embeddinggemma:300m model

---

## Testing

### Unit Tests Passed

```
✅ Test 1: _estimate_tokens works
✅ Test 2: _smart_truncate no-op for short content
✅ Test 3: _smart_truncate preserves head and tail
✅ Test 4: build_pinned_context handles empty list
✅ Test 5: build_pinned_context skips folders
✅ Test 6: build_pinned_context_legacy works
✅ Test 7: New signature has all Phase 67 parameters
```

### Integration Tests Passed

```
✅ Import from handlers package works
✅ build_pinned_context works without user_query (backward compat)
✅ build_pinned_context works with user_query
```

---

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | `build_pinned_context()` accepts `user_query` parameter | ✅ |
| 2 | Uses Qdrant for semantic search | ✅ |
| 3 | Uses CAM activation_score for ranking | ✅ |
| 4 | Fallback to legacy logic if services unavailable | ✅ |
| 5 | All existing tests pass | ✅ |
| 6 | Logging: `[CONTEXT] Using smart selection...` | ✅ |

---

## Files Structure

```
src/api/handlers/
├── __init__.py                    # Re-exports build_pinned_context
├── message_utils.py               # ← MODIFIED (Phase 67)
├── user_message_handler.py        # ← MODIFIED (4 call-sites)
├── chat_handler.py
├── streaming_handler.py
├── workflow_handler.py
└── handler_utils.py

src/memory/
└── qdrant_client.py               # Used by _get_qdrant_relevance()

src/orchestration/
└── cam_engine.py                  # Used by _get_cam_activation()

src/utils/
└── embedding_service.py           # Used by _rank_pinned_files()
```

---

## Git

```bash
git log --oneline -1
# 3a53ca9 Phase 67: Integrate CAM + Qdrant into context assembly

git remote -v
# origin  git@github.com:danilagoleen/vetka.git

git push origin main
# f85aae1..3a53ca9  main -> main
```

---

## Future Improvements

1. **Singleton CAM Engine** — Currently creates new instance per call
2. **Batch Qdrant queries** — Single query for all pinned files
3. **Cache relevance scores** — Avoid recomputation for same query
4. **Configurable weights** — Allow user to adjust Qdrant/CAM balance
5. **Streaming context** — Progressive loading for large file sets

---

## Author

Phase 67 implemented by Claude Opus 4.5
Date: 2026-01-18
