# Search Markers Index - Phase 95

**Date**: 2026-01-26
**Created by**: HAIKU-MARKERS-SEARCH-2
**Total Markers Found**: 11
**Backend Bugs**: 3
**Frontend TODOs**: 8

---

## Quick Reference

| Status | Count | Priority |
|--------|-------|----------|
| 🔴 Open Bugs | 3 | HIGH |
| 🟡 Frontend TODOs | 8 | MEDIUM |
| ✅ Completed | 2 | DONE |
| 📋 Documented | 11 | TRACKED |

---

## Python Backend Markers

### Critical Bugs in `src/search/hybrid_search.py`

| Bug ID | Line | Function | Description | Severity | Status |
|--------|------|----------|-------------|----------|--------|
| BUG_95.1_MODE_NONE | 264 | `search()` | When no results found, sets mode="none" instead of preserving requested_mode | 🔴 HIGH | OPEN |
| BUG_95.2_KEYWORD_EMPTY | 403 | `_keyword_search()` | Weaviate BM25 collection mapping returns 0 results - possible schema mismatch | 🔴 HIGH | OPEN |
| BUG_95.3_FILENAME_SCROLL | 453 | `_filename_search()` | Qdrant filename filter with type='scanned_file' finds 0 entries - payload filter broken | 🔴 HIGH | OPEN |

---

## Frontend TODOs (TypeScript/React)

### From HAIKU_MARKERS_2_SEARCH_UI.md

| TODO ID | File | Line | Component | Description | Status |
|---------|------|------|-----------|-------------|--------|
| TODO_SEARCH_UI_1 | UnifiedSearchBar.tsx | ~623 | CAM Suggestions | Add CAM context memory suggestions below search input - backend ready, UI missing | OPEN |
| TODO_SEARCH_UI_2 | UnifiedSearchBar.tsx | ~650 | Context Prefix | Context prefix selector (vetka/, web/, file/, cloud/, social/) - only vetka/ tested | OPEN |
| TODO_SEARCH_UI_3 | UnifiedSearchBar.tsx | ~825 | Mode Indicator | Show visual indicator of which search mode was used (HYB/SEM/KEY/FILE) | OPEN |
| TODO_SEARCH_UI_4 | UnifiedSearchBar.tsx | ~890 | Sort Direction | Sort direction toggle (↑↓) integration with Qdrant/Weaviate source indicators unclear | OPEN |
| TODO_SEARCH_UI_5 | UnifiedSearchBar.tsx | ~956 | Sort Dropdown | Sort dropdown (date/size/type) handlers need source-aware filtering | OPEN |
| TODO_SEARCH_UI_6 | UnifiedSearchBar.tsx | ~1040 | Source Badges | Add source badges [Qdrant], [Weaviate], [Hybrid] to results display | OPEN |
| TODO_SEARCH_UI_7 | useSearch.ts | ~88 | CAM Polling | Add CAM suggestions polling/subscription to hook | OPEN |
| TODO_SEARCH_UI_8 | useSearch.ts | ~104 | Mode Tracking | Track actual search mode used in response - expose for UI indicators | OPEN |

---

## Search Architecture Overview

### Core Search Stack

```
Frontend (React)
  ├─ UnifiedSearchBar.tsx (search UI)
  ├─ useSearch.ts hook (search logic + WebSocket)
  └─ ChatPanel.tsx (search integration)
       ↓
API Routes (FastAPI)
  ├─ /api/search/hybrid (Phase 68 - RRF fusion)
  ├─ /api/search/semantic (vector similarity)
  ├─ /api/search/weaviate (BM25 keyword)
  └─ /api/scanner/* (index management)
       ↓
Search Service (Python)
  ├─ HybridSearchService (coordinator)
  ├─ RRF Fusion Engine (rrf_fusion.py)
  ├─ Backend 1: Qdrant (semantic search)
  └─ Backend 2: Weaviate (keyword BM25)
```

---

## Bug Details & Root Causes

### BUG_95.1_MODE_NONE

**Location**: `src/search/hybrid_search.py:264`

**Code**:
```python
if len(results_lists) > 1:
    fused = weighted_rrf(results_lists, weights, k=RRF_K, top_n=limit)
    actual_mode = "hybrid"
elif len(results_lists) == 1:
    fused = results_lists[0][:limit]
    actual_mode = sources_used[0] if sources_used else mode
else:
    fused = []
    # BUG_95.1_MODE_NONE: Should preserve requested mode, not set "none" when no results
    actual_mode = "none"
```

**Problem**: When no results found from any backend, `actual_mode` is hardcoded to "none". This loses the user's requested mode preference and confuses the frontend.

**Impact**: UI cannot retry with different search mode because mode info is lost.

**Fix Needed**: Replace `"none"` with the requested `mode` parameter.

---

### BUG_95.2_KEYWORD_EMPTY

**Location**: `src/search/hybrid_search.py:403`

**Code**:
```python
# Execute BM25 search
results = self.weaviate.bm25_search(
    collection=collection, query=query, limit=limit
)
# BUG_95.2_KEYWORD_EMPTY: Weaviate BM25 returns 0 - check collection mapping
```

**Problem**: Weaviate BM25 search consistently returns 0 results. Likely cause: collection schema mismatch between Qdrant and Weaviate indices.

**Impact**: "keyword" and "hybrid" modes fall back to semantic-only search, losing BM25 benefits.

**Investigation Needed**:
- Verify Weaviate collection schema (VetkaLeaf vs other names)
- Check if file indexing is reaching Weaviate (check `file_watcher.py` for Weaviate emit)
- Test BM25 query directly via Weaviate GraphQL

---

### BUG_95.3_FILENAME_SCROLL

**Location**: `src/search/hybrid_search.py:453`

**Code**:
```python
# Use Qdrant scroll with filter for filename matching
results = self.qdrant.search_by_filename(
    filename_pattern=query, limit=limit
)
# BUG_95.3_FILENAME_SCROLL: type='scanned_file' filter finds 0 entries
```

**Problem**: Qdrant filename search returns 0 results. Issue likely in `qdrant_client.py` implementation of `search_by_filename()`.

**Impact**: "filename" search mode doesn't work - users cannot search by exact filename.

**Investigation Needed**:
- Check Qdrant payload schema (what's the actual field name for node_type?)
- Verify filter syntax: `{"type": {"equals": "scanned_file"}}` vs other formats
- Test scroll + filter directly via Qdrant client

---

## TODO Priorities

### Phase 1: Quick Wins (Display-Only, 2-3 hours)

These can be implemented without backend changes:

1. **TODO_SEARCH_UI_6**: Add Source Badges (30 min)
   - Display [Qdrant], [Weaviate], or [Hybrid] next to results
   - Use `searchResponse.sources` field already in API response
   - File: `UnifiedSearchBar.tsx` line ~1040

2. **TODO_SEARCH_UI_3**: Add Search Mode Indicator (30 min)
   - Show "(Semantic)" or "(Keyword)" or "(Hybrid)" near result count
   - Use `searchResponse.mode` field already in API response
   - File: `UnifiedSearchBar.tsx` line ~825

3. **TODO_SEARCH_UI_8**: Expose Mode in useSearch Hook (15 min)
   - Already tracking mode internally (line 106)
   - Just needs return value exposure
   - File: `useSearch.ts` line ~104 - PARTIALLY DONE

### Phase 2: Medium Features (4-6 hours)

Require backend work but are high-impact:

4. **TODO_SEARCH_UI_1**: CAM Suggestions Integration (4-6 hours)
   - Create `/api/cam/suggestions` endpoint
   - Fetch from `cam_engine.py`
   - Display top 3 tool suggestions below search bar
   - Files: `useSearch.ts` + `UnifiedSearchBar.tsx`

5. **TODO_SEARCH_UI_7**: CAM Polling in Hook (2 hours)
   - Add subscription to `/api/cam/suggestions`
   - Update suggestions when query changes
   - File: `useSearch.ts` line ~88

### Phase 3: Polish (1-2 hours)

Enhanced functionality:

6. **TODO_SEARCH_UI_5**: Smart Sort Options (1 hour)
   - Pass sort direction to API
   - Implement source-aware filtering
   - File: `UnifiedSearchBar.tsx` line ~956

7. **TODO_SEARCH_UI_2**: Complete Context Prefix (1 hour)
   - Test `/file/`, `/web/`, `/cloud/` endpoints
   - Add backend routing if needed
   - File: `UnifiedSearchBar.tsx` line ~650

8. **TODO_SEARCH_UI_4**: Sort Direction Integration (30 min)
   - Wire sort direction toggle to API params
   - File: `UnifiedSearchBar.tsx` line ~890

---

## Current Implementation Status

### What's Working ✅

| Component | Status | Notes |
|-----------|--------|-------|
| Hybrid Search API | ✅ WORKING | RRF fusion implemented, Phase 68 complete |
| Semantic Search (Qdrant) | ✅ WORKING | Vector embeddings, ~0.3s latency |
| WebSocket Results | ✅ WORKING | Real-time result delivery via Socket.IO |
| useSearch Hook | ✅ WORKING | Debouncing, mode switching, pagination |
| Search Result Display | ✅ WORKING | Results render with metadata |
| Cache Layer | ✅ WORKING | 5-min TTL on hybrid search results |

### What's Partially Working ⚠️

| Component | Status | Issue |
|-----------|--------|-------|
| Weaviate BM25 | ⚠️ BROKEN | Returns 0 results (BUG_95.2) |
| Filename Search | ⚠️ BROKEN | Returns 0 results (BUG_95.3) |
| Mode Fallback | ⚠️ BROKEN | Shows "none" mode (BUG_95.1) |
| Mode Display | ⚠️ MISSING | UI doesn't show which mode was used |
| Source Badges | ⚠️ MISSING | API has source data, UI doesn't display |
| CAM Suggestions | ⚠️ MISSING | Backend ready, UI not implemented |

### What's Not Started ❌

| Component | Status | Effort |
|-----------|--------|--------|
| Context Prefix Routing | ❌ TODO | /file/, /web/, /cloud/ endpoints |
| Sort Direction Params | ❌ TODO | Send to API, implement filtering |
| Smart Sort Options | ❌ TODO | Source-aware sorting logic |

---

## Files Involved

### Backend (Python)

```
src/search/
├── hybrid_search.py (521 lines) ← 3 BUGs here
├── rrf_fusion.py (261 lines) ✅ Working
└── __init__.py

src/api/routes/
└── semantic_routes.py (958 lines)
    ├── GET /api/search/hybrid ✅
    ├── GET /api/search/semantic ✅
    └── POST /api/search/weaviate ⚠️ (returns 0)

src/memory/
├── qdrant_client.py - search_by_filename() ⚠️
└── weaviate_helper.py - bm25_search() ⚠️
```

### Frontend (TypeScript/React)

```
client/src/
├── components/search/
│   └── UnifiedSearchBar.tsx (1182 lines) ← 6 TODOs here
├── hooks/
│   └── useSearch.ts (253 lines) ← 2 TODOs here
├── components/chat/
│   ├── ChatPanel.tsx ✅
│   └── MessageInput.tsx ✅
└── types/
    └── chat.ts (SearchResult interface)
```

---

## Testing Recommendations

### Unit Tests to Add

```python
# tests/test_hybrid_search.py
def test_search_preserves_mode_when_empty():
    """BUG_95.1: Should return requested_mode, not 'none'"""
    result = await search("impossible_xyz_query", mode="semantic")
    assert result["requested_mode"] == "semantic"
    assert result["mode"] != "none"  # FAILS TODAY

def test_keyword_search_returns_results():
    """BUG_95.2: Weaviate should return results"""
    result = await search("authentication", mode="keyword")
    assert len(result["results"]) > 0  # FAILS TODAY

def test_filename_search_returns_results():
    """BUG_95.3: Filename mode should find files"""
    result = await search("test", mode="filename")
    assert len(result["results"]) > 0  # FAILS TODAY
```

### Integration Tests to Add

```typescript
// tests/useSearch.integration.test.ts
describe("useSearch", () => {
  test("displays search mode in results", () => {
    // TODO_SEARCH_UI_3: Needs mode display in UI
  });

  test("shows source badges", () => {
    // TODO_SEARCH_UI_6: Needs badge rendering
  });

  test("fetches CAM suggestions", () => {
    // TODO_SEARCH_UI_1: Needs endpoint + polling
  });
});
```

---

## Dependency Map

```
Frontend useSearch Hook
    ↓ (via WebSocket)
API search_routes.py
    ↓
HybridSearchService.search()
    ├─ _semantic_search() → Qdrant ✅
    ├─ _keyword_search() → Weaviate ⚠️ BUG_95.2
    ├─ _filename_search() → Qdrant ⚠️ BUG_95.3
    └─ weighted_rrf() → Fusion ✅
         Returns:
         ├─ results[]
         ├─ mode: actual mode used ⚠️ BUG_95.1
         ├─ sources: ["qdrant", "weaviate"]
         └─ explanation

Frontend UnifiedSearchBar
    ↓ (receives results)
    ├─ Display results ✅
    ├─ Display mode ❌ TODO_SEARCH_UI_3
    ├─ Display sources ❌ TODO_SEARCH_UI_6
    └─ CAM suggestions ❌ TODO_SEARCH_UI_1
```

---

## Marker Cross-Reference

### By Priority

**Blocking Issues** (Fix first):
- BUG_95.1_MODE_NONE (1 hour fix)
- BUG_95.2_KEYWORD_EMPTY (2-4 hours investigation)
- BUG_95.3_FILENAME_SCROLL (1-2 hours investigation)

**Quick Wins** (Next):
- TODO_SEARCH_UI_6 (30 min, high visibility)
- TODO_SEARCH_UI_3 (30 min, high visibility)
- TODO_SEARCH_UI_8 (15 min, enabler)

**Medium Features** (Then):
- TODO_SEARCH_UI_1 (4-6 hours, high impact)
- TODO_SEARCH_UI_7 (2 hours, depends on #1)

**Polish** (Last):
- TODO_SEARCH_UI_2, TODO_SEARCH_UI_4, TODO_SEARCH_UI_5

---

## Implementation Checklist

### Bug Fixes
- [ ] Fix BUG_95.1: Change `actual_mode = "none"` → `actual_mode = mode`
- [ ] Fix BUG_95.2: Debug Weaviate collection schema and BM25 search
- [ ] Fix BUG_95.3: Debug Qdrant filename search filter syntax
- [ ] Run tests to verify all three bugs fixed
- [ ] Commit changes with test coverage

### Frontend Phase 1 (Display)
- [ ] Implement source badges (TODO_SEARCH_UI_6)
- [ ] Implement mode indicator (TODO_SEARCH_UI_3)
- [ ] Expose mode in useSearch return (TODO_SEARCH_UI_8)
- [ ] Update UnifiedSearchBar to use mode field
- [ ] Test in dev environment

### Frontend Phase 2 (CAM)
- [ ] Create `/api/cam/suggestions` endpoint
- [ ] Implement CAM polling in useSearch (TODO_SEARCH_UI_7)
- [ ] Render CAM suggestions in UnifiedSearchBar (TODO_SEARCH_UI_1)
- [ ] Test suggestion accuracy

### Frontend Phase 3 (Polish)
- [ ] Implement sort options (TODO_SEARCH_UI_5)
- [ ] Implement sort direction (TODO_SEARCH_UI_4)
- [ ] Complete context prefix routing (TODO_SEARCH_UI_2)
- [ ] Integration test all features

---

## References

### Documentation Files
- `docs/95_ph/HAIKU_MARKERS_2_SEARCH_UI.md` - Original marker definitions
- `docs/95_ph/PHASE_95_SEARCH_UI_COMPLETION.txt` - Status tracking
- `docs/95_ph/SEARCH_UI_QUICK_REFERENCE.md` - Quick reference

### Code Files
- `/src/search/hybrid_search.py` - Main search service (3 bugs)
- `/client/src/components/search/UnifiedSearchBar.tsx` - Main search UI (6 TODOs)
- `/client/src/hooks/useSearch.ts` - Search logic hook (2 TODOs)
- `/src/api/routes/semantic_routes.py` - API endpoints (958 lines)

### Related Issues
- Phase 68: RRF Fusion implementation
- Phase 69: Rescan/reindex system
- Phase 83: Scanner stop flag system

---

## Summary

**Total Markers**: 11 (3 backend bugs + 8 frontend TODOs)

**Estimated Fix Time**:
- Bugs: 4-8 hours (investigation + testing)
- Quick Wins: 1.5 hours
- CAM Integration: 6-8 hours
- Polish Features: 2-3 hours
- **Total: 13.5-22 hours** of development time

**Blocking**: None currently, all are enhancements except the 3 bugs which degrade search quality.

**Recommended Order**:
1. Fix all 3 bugs (test thoroughly)
2. Implement quick wins (source badges, mode display)
3. Add CAM integration
4. Polish with sort options

---

**Status**: ✅ Index complete - all search markers tracked and prioritized
