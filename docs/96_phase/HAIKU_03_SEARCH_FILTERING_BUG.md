# HAIKU RECON 03: Search Filtering Bug Analysis

**Agent:** Haiku
**Date:** 2026-01-28
**Task:** Analyze why search returns 0 results with filtered=100

---

## SCORE RANGES BY SEARCH MODE

| Mode | Source | Raw Score Range | Formula | Notes |
|------|--------|-----------------|---------|-------|
| **Semantic** | Qdrant | 0.0-1.0 | Cosine similarity | `score_threshold=0.3` in search |
| **Keyword** | Weaviate BM25 | Variable | BM25 algorithm | Not standardized |
| **Hybrid** | RRF Fusion | 0.001-0.033 | `w/(k+rank)` with k=60 | **CRITICAL** |
| **Filename** | Qdrant filter | 0.5-1.0 | Position-based | 1.0 for first, then decreases |

---

## ROOT CAUSE: MIN_SCORE FILTERING

### The Problem

**File:** `src/api/handlers/search_handlers.py` (lines 59-67)

```python
# FIX_95.12: RRF scores are typically 0.001-0.03, not 0-1!
# Default 0.3 was filtering out 100% of results
# New default: 0.005 (allows most relevant results through)
min_score = data.get('min_score', 0.005)
```

**Old default:** `min_score = 0.3`
**Max RRF score:** `~0.033`
**Result:** 100% of results filtered out (0.033 < 0.3)

### RRF Score Calculation

With k=60, if document ranked #1 in both sources:
```
score = 0.5/(60+1) + 0.3/(60+1)
      = 0.5/61 + 0.3/61
      ≈ 0.00820 + 0.00492
      ≈ 0.0131
```

Maximum theoretical RRF score:
```
max_score = 2 * (1/(60+1)) ≈ 0.0328
```

---

## FILTERING CHAIN

```
Frontend request
    ↓
[search_handlers.py] handle_search_query
    ├─ min_score = 0.005 (default) or from params
    │
    ├─→ [hybrid_search.py] service.search()
    │       ├─ Parallel exec:
    │       │   ├─ _semantic_search() → Qdrant (scores: 0.3-1.0)
    │       │   └─ _keyword_search() → Weaviate BM25 (scores: variable)
    │       │
    │       └─ weighted_rrf() → RRF scores (0.001-0.033)
    │
    └─→ Format results
        ├─ if score < min_score (0.005): FILTER OUT
        ├─ raw_score = score (0.001-0.033)
        ├─ display_relevance = raw_score * 30 (capped at 1.0)
        └─ Emit: {results[], filtered_count}
```

---

## WHY FILTERED=100 HAPPENS

**Scenario:**
1. Frontend sends with old `min_score=0.3` (or uses old cached default)
2. Hybrid search returns RRF scores in range 0.001-0.033
3. Handler filters: `if relevance < 0.3: filtered_count += 1`
4. **All 100% results filtered** because `0.0131 < 0.3`

---

## CACHING ISSUE

**File:** `src/search/hybrid_search.py` (lines 47-48, 154-162)

```python
HYBRID_CACHE_TTL = 300  # 5 minutes
_hybrid_search_cache: Dict[str, Any] = {}

cache_key = f"hybrid:{query}:{limit}:{mode}:{hash(str(filters))}"
if not skip_cache and cache_key in _hybrid_search_cache:
    cached = _hybrid_search_cache[cache_key]
    if age < HYBRID_CACHE_TTL:
        return cached["result"]  # 0ms = cached!
```

**Problem:** Cache may return stale results with old score format

---

## BM25 WEAVIATE ISSUE

**Log observed:**
```
[KEYWORD] BM25 returned 0 results for '3в'. Weaviate collection 'VetkaLeaf' may be empty
```

**Possible causes:**
1. Weaviate not synced with Qdrant (COHERENCE_BYPASS markers)
2. Cyrillic query handling issue
3. VetkaLeaf collection actually empty

---

## FIX APPLIED (FIX_95.12)

**Location:** `src/api/handlers/search_handlers.py`

```python
# Lines 64-67: New default
min_score = data.get('min_score', 0.005)

# Lines 120-125: Filtering with debug
if relevance < min_score:
    filtered_count += 1
    if filtered_count <= 3:
        logger.debug(f"[SEARCH] Filtered: {path} (score={score:.6f} < min={min_score})")
    continue

# Lines 132-135: Scale for display
display_relevance = min(relevance * 30, 1.0)
```

---

## RECOMMENDED MODE-AWARE THRESHOLDS

```python
# BUG_96.1 fix: Different thresholds per mode
if mode == 'keyword':
    min_score = data.get('min_score', 0.0)  # BM25 scores vary widely
elif mode == 'hybrid':
    min_score = data.get('min_score', 0.005)  # RRF scores 0.001-0.03
elif mode == 'filename':
    min_score = data.get('min_score', 0.0)  # Filename has no scores
else:  # semantic
    min_score = data.get('min_score', 0.3)  # Cosine similarity 0-1
```

---

## FILES TO CHECK

| File | Issue | Change Needed |
|------|-------|---------------|
| `src/api/handlers/search_handlers.py` | BUG_96.1, BUG_96.2 | Mode-aware min_score |
| `src/search/hybrid_search.py` | BUG_96.3 | Debug filename matching |
| `src/memory/weaviate_helper.py` | BM25 empty | Check VetkaLeaf sync |
