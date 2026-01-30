# FIX_95.12: RRF Score Threshold Fix

**Date**: 2026-01-27
**Phase**: 95.12
**Status**: COMPLETED
**Root Cause Analysis**: Grok

## Problem Identified

Search results showed `filtered=100` meaning ALL results were being filtered out after RRF fusion.

Grok's analysis identified the issue:
> "Находит 400 сырых (semantic + keyword), фьюжит в 400 unique via RRF (k=60), возвращает 100...
> но потом 'Found 0 results... filtered=100'. Фильтрация по relevance threshold сбрасывает всё."

## Root Cause

**search_handlers.py** line 65 had:
```python
min_score = data.get('min_score', 0.3)  # Default 0.3
```

But RRF scores follow the formula: `weight / (k + rank)` where k=60

**Typical RRF score ranges:**
- Document at rank 1 in one source: `0.5 / (60 + 1) ≈ 0.0082`
- Document at rank 1 in BOTH sources: `0.5/61 + 0.5/61 ≈ 0.0164`
- Maximum possible: `2 * (1/61) ≈ 0.033`

So `min_score = 0.3` filters out **100% of all results** because RRF scores are in the 0.001-0.03 range, NOT 0-1!

## Solution

1. **Changed default threshold** from 0.3 to 0.005 (appropriate for RRF scores)
2. **Removed score normalization** that was incorrectly treating scores as 0-1
3. **Added display scaling** for UI (multiply by 30 to get 0-1 range)
4. **Added debug logging** for filtered results

## Files Modified

- `src/api/handlers/search_handlers.py`:
  - Line 64-66: Changed default min_score from 0.3 to 0.005
  - Line 119-130: Fixed relevance calculation, added debug logging
  - Line 132-139: Added display_relevance scaling and raw_score field

## Code Changes

Before:
```python
min_score = data.get('min_score', 0.3)  # Default 0.3 for broader results
...
score = r.get('rrf_score') or r.get('score') or 0
relevance = min(score, 1.0) if score <= 1.0 else score / 100  # Normalize
if relevance < min_score:  # 0.0164 < 0.3 → FILTERED!
    filtered_count += 1
```

After:
```python
min_score = data.get('min_score', 0.005)  # FIX_95.12: Appropriate for RRF
...
score = r.get('rrf_score') or r.get('score') or 0
relevance = score  # Keep raw score
if relevance < min_score:  # 0.0164 > 0.005 → PASSES!
    filtered_count += 1
...
display_relevance = min(relevance * 30, 1.0)  # Scale for UI
```

## Testing

Search for "3d" should now return results:
- Before: `Found 0 results... filtered=100`
- After: `Found ~100 results... filtered=0`

## Related

- FIX_95.10: BM25 field mapping
- FIX_95.11: Name field in keyword results
- Grok analysis on RRF fusion behavior
