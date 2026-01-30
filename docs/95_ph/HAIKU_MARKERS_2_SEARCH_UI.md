# HAIKU-MARKERS-2: Search UI Button Markers

**Mission**: Add TODO markers for broken/incomplete search UI buttons
**Date**: 2026-01-26
**Based on**: HAIKU-RECON-3 findings about "half working UI buttons"
**Scope**: Frontend search components in `/client/src/components/search/`

---

## Executive Summary

Based on HAIKU-RECON-3 audit, the following search UI components were identified as **partially working** or **missing handler implementations**:

- Sort options buttons (visible but handlers incomplete)
- CAM suggestion integration (backend ready, UI disconnected)
- Source indicators (no visual display)
- Context prefix selector (exists but flow unclear)
- Search mode indicators (results don't show which mode was used)

This document adds TODO markers to guide the implementation of these missing features.

---

## Broken/Incomplete Buttons Found

| Component | Button/Feature | Issue | Status | Marker Added |
|-----------|----------------|-------|--------|--------------|
| UnifiedSearchBar | Sort dropdown (relevance/name/type/date) | Handlers visible, logic unclear | ⚠️ PARTIAL | ✅ |
| UnifiedSearchBar | Sort direction toggle (↑↓) | Toggle works, integration unclear | ⚠️ PARTIAL | ✅ |
| UnifiedSearchBar | CAM suggestions | Button/UI missing entirely | ❌ MISSING | ✅ |
| UnifiedSearchBar | Source badges | No display of Qdrant/Weaviate source | ❌ MISSING | ✅ |
| UnifiedSearchBar | Mode indicator | Results don't show which search mode used | ❌ MISSING | ✅ |
| UnifiedSearchBar | Context prefix selector | Exists but selection unclear | ⚠️ PARTIAL | ✅ |
| useSearch Hook | Mode switching callback | Prop passed but integration unclear | ⚠️ PARTIAL | ✅ |

---

## Files Modified

### 1. `/client/src/components/search/UnifiedSearchBar.tsx`

**Location**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/search/UnifiedSearchBar.tsx`

**Markers Added**: 6 TODO markers

#### Marker 1: Sort Direction Toggle
**Line**: ~890
```
// TODO_SEARCH_UI: Sort direction toggle (↑↓) connects to setSortAscending
// but integration with Qdrant/Weaviate source indicators unclear
// connects to: backend filter_weights, source detection
```

#### Marker 2: Sort Dropdown Menu
**Line**: ~956
```
// TODO_SEARCH_UI: Sort dropdown renders but handlers for
// date/size/type sorting need source-aware filtering
// connects to: /api/search/hybrid with sort params
```

#### Marker 3: Search Mode Indicators
**Line**: ~825
```
// TODO_SEARCH_UI: Show visual indicator of which search mode was used
// in results (HYB vs SEM vs KEY vs FILE)
// connects to: searchResponse.mode, add badge to results
```

#### Marker 4: CAM Suggestion Integration
**Line**: ~623
```
// TODO_SEARCH_UI: Add CAM (Context-Aware Memory) suggestions below search input
// Backend ready (cam_engine.py) but UI integration missing
// connects to: /api/cam/suggestions endpoint + JARVIS hints
```

#### Marker 5: Source Indicator Badges
**Line**: ~1040
```
// TODO_SEARCH_UI: Add source badges [Qdrant], [Weaviate], [Hybrid] to results
// Backend returns source in response but not displayed in UI
// connects to: searchResponse.sources array
```

#### Marker 6: Context Prefix Selector Flow
**Line**: ~650
```
// TODO_SEARCH_UI: Context prefix selector (vetka/, web/, file/, cloud/, social/)
// Only vetka/ fully tested, others need backend routing
// connects to: context-specific search endpoints
```

---

### 2. `/client/src/hooks/useSearch.ts`

**Location**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/hooks/useSearch.ts`

**Markers Added**: 2 TODO markers

#### Marker 1: Search Mode Response Tracking
**Line**: ~104
```
// TODO_SEARCH_UI: Track actual search mode used in response
// Should expose mode metadata for UI indicators
// connects to: UnifiedSearchBar mode display badges
```

#### Marker 2: CAM Suggestions Fetch
**Line**: ~88
```
// TODO_SEARCH_UI: Add CAM suggestions polling/subscription
// Backend has CAM activation scores but hook doesn't fetch them
// connects to: /api/cam/suggestions or WebSocket event
```

---

## Implementation Roadmap

### Phase 1: Quick Wins (2-3 hours)
**These are cosmetic/display improvements that don't require backend changes**

1. **Add Source Badges** (30 min)
   - Display `[Qdrant]`, `[Weaviate]`, or `[Hybrid]` next to relevance score
   - Color code: Qdrant=#555 (gray), Weaviate=#888 (light gray), Hybrid=#6a8 (subtle teal)
   - File: `UnifiedSearchBar.tsx` line ~1040

2. **Add Search Mode Indicator** (30 min)
   - Show "(Semantic)" or "(Keyword)" or "(Hybrid)" near result count
   - Update when searchMode changes
   - File: `UnifiedSearchBar.tsx` line ~878

3. **Complete Context Prefix Support** (1 hour)
   - Test `/file/`, `/web/`, `/cloud/` endpoints
   - Add backend routing if needed
   - File: `UnifiedSearchBar.tsx` line ~650

### Phase 2: Medium Features (4-6 hours)
**These require backend communication but minimal new API design**

4. **CAM Suggestions Integration** (4-6 hours)
   - Create `/api/cam/suggestions` endpoint (if not exists)
   - Fetch CAM activation scores from `cam_engine.py`
   - Display as "CAM suggests" hints below search bar
   - Show top 3 suggested tools (pin_files, search_files, focus_node)
   - Files: `useSearch.ts` + `UnifiedSearchBar.tsx`

### Phase 3: Polish (1-2 hours)
**These enhance UX but are optional**

5. **Sort Options with Source Awareness** (1 hour)
   - When sorting by relevance, show source-aware scores
   - When sorting by name, preserve source grouping
   - File: `UnifiedSearchBar.tsx` line ~956

---

## API Endpoints Needed

### Existing ✅
- `/api/search/hybrid` - Already provides `source` field
- `/api/search/semantic` - Working
- `/api/search/weaviate` - Working

### Needed Implementation ⚠️
- `/api/cam/suggestions` - CAM activation scores for top results
  - Returns: `[{tool_name, activation_score, context_key}]`
  - Used by: useSearch hook

---

## Backend Integration Points

| Backend Component | Frontend Hook | Expected Response |
|-------------------|---------------|-------------------|
| `HybridSearchService` | `useSearch` | Already includes `source` field ✅ |
| `CAMEngine` | `useSearch` | Needs new `/api/cam/suggestions` endpoint |
| `semantic_routes.py` | `useSearch` | Has all search modes ✅ |
| `search_handlers.py` | Socket.IO | Emits `search_results` event ✅ |

---

## Files Summary

### Modified
1. **`/client/src/components/search/UnifiedSearchBar.tsx`**
   - 6 TODO markers added
   - No code changes (markers only)
   - Lines: ~623, ~650, ~825, ~890, ~956, ~1040

2. **`/client/src/hooks/useSearch.ts`**
   - 2 TODO markers added
   - No code changes (markers only)
   - Lines: ~88, ~104

### Unchanged (Fully Working)
- `ChatPanel.tsx` - Search integration working ✅
- `MessageInput.tsx` - Voice + search working ✅

---

## Next Steps for Implementation

### For HAIKU-MARKERS-2 Follow-up
1. Implement source badges (quick win)
2. Add search mode indicator
3. Create `/api/cam/suggestions` endpoint
4. Integrate CAM suggestions into useSearch hook

### For Full Feature Completion
- See HAIKU-RECON-3 section 14 "Recommendations" for detailed roadmap
- CAM integration is highest priority (4-6 hours, high impact)
- All other features are 1-2 hours each

---

## Quality Checklist

- [x] All broken/incomplete buttons identified
- [x] Markers added to source code
- [x] Backend integration points mapped
- [x] Implementation roadmap provided
- [x] API endpoints specified
- [x] Effort estimates included
- [x] No code changes made (markers only)

---

## References

- **HAIKU-RECON-3**: `/docs/95_ph/HAIKU_RECON_3_SEARCH_MEMORY.md` - Full audit report
- **UnifiedSearchBar**: `/client/src/components/search/UnifiedSearchBar.tsx` - Main search UI (1182 lines)
- **useSearch Hook**: `/client/src/hooks/useSearch.ts` - Search logic (253 lines)
- **CAM Engine**: `/src/orchestration/cam_engine.py` - Context memory backend (1312 lines)
- **HybridSearchService**: `/src/search/hybrid_search.py` - Search coordinator (521 lines)

---

## Status

**COMPLETE**: All search UI buttons marked with TODO comments for implementation guidance.

**Next Phase**: HAIKU-MARKERS-3 will implement these markers in order of priority.
