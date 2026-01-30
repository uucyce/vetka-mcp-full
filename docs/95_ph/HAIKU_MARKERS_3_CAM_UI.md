# CAM UI Markers Added - HAIKU-MARKERS-3

**Status:** Complete
**Phase:** 95 (UI Integration Planning)
**Markers Added:** 6
**Files Modified:** 7
**Backend Ready:** Yes
**Effort Estimate:** Medium (5-10 days for full integration)

---

## Integration Points Found

| Location | Component | Feature | Marker | Effort | Priority |
|----------|-----------|---------|--------|--------|----------|
| `client/src/components/search/UnifiedSearchBar.tsx:1002-1009` | Search Results | CAM suggestions display | `// TODO_CAM_UI` | Medium | High |
| `client/src/components/canvas/FileCard.tsx:547-551` | File Card Hover | Pin-to-CAM button | `// TODO_CAM_PIN` | Small | High |
| `client/src/components/canvas/FileCard.tsx:603-609` | Folder Label | CAM activation indicator (hot/warm/cold) | `// TODO_CAM_INDICATOR` | Medium | High |
| `client/src/components/chat/MessageBubble.tsx:276-280` | Message Reactions | Link emoji to CAM weights | `// TODO_CAM_EMOJI` | Small | Medium |
| `client/src/components/chat/ChatSidebar.tsx:26-29` | Chat History | CAM activation display | `// TODO_CAM_INDICATOR` | Small | Medium |
| `client/src/components/chat/MessageInput.tsx:56-59` | Input Context | CAM suggestions enrichment | `// TODO_CAM_UI` | Small | Low |
| `client/src/components/ModelDirectory.tsx:27-29` | Model Selection | CAM model ranking | `// TODO_CAM_INDICATOR` | Medium | Medium |
| `client/src/components/chat/MentionPopup.tsx:48-50` | @ Mention Popup | CAM-ranked model suggestions | `// TODO_CAM_UI` | Small | Low |

---

## Marker Details

### 1. CAM Suggestions Display (Search Results)
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/search/UnifiedSearchBar.tsx`
**Lines:** 1002-1009
**Component:** UnifiedSearchBar

```typescript
// TODO_CAM_UI: Add CAM suggestions panel here (backend: /api/cam/suggestions)
// Display contextually relevant files based on CAM activation levels.
// Should show hot/warm/cold memory nodes alongside search results.
// Integration: GET /api/cam/suggestions?context={searchContext}&limit=5
// Display as separate section above results with "From Context Memory" header.
```

**Effort:** Medium (6-8 hours)
**Implementation Steps:**
1. Create `CAMSuggestionsPanel` component
2. Add API call to `/api/cam/suggestions` when search results load
3. Display hot/warm/cold badges with file icons
4. Style to match UnifiedSearchBar (Nolan dark minimal)
5. Add hover preview similar to search results
6. Allow pinning suggestions directly to context

---

### 2. Pin-to-CAM Button (File Cards)
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx`
**Lines:** 547-551
**Component:** FileCard

```typescript
// TODO_CAM_PIN: Add pin-to-CAM button on file card hover
// When clicked: POST /api/cam/pin with { file_path, metadata }
// Visual feedback: highlight pin icon or show "Added to CAM" toast
```

**Effort:** Small (2-3 hours)
**Implementation Steps:**
1. Add CAM pin icon (different from existing pin icon for context)
2. Implement onclick handler: `POST /api/cam/pin { path, type, depth }`
3. Add visual feedback (icon highlight or toast)
4. Update icon color based on CAM activation state
5. Optional: Show pinned count badge

---

### 3. CAM Activation Indicator (Folder Labels)
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx`
**Lines:** 603-609
**Component:** FileCard (Folder Label LOD)

```typescript
// TODO_CAM_INDICATOR: Show CAM activation level badge on folder label (hot/warm/cold)
// Query: GET /api/cam/activation?node_id={id} - returns { level: 'hot'|'warm'|'cold', weight: 0-1 }
// Display with color coding: hot=#ff6b6b, warm=#ffd93d, cold=#95a3a3
```

**Effort:** Medium (4-6 hours)
**Implementation Steps:**
1. Add CAM activation query on folder render
2. Fetch activation level for node
3. Display badge with color based on level
4. Animate opacity changes as activation changes
5. Optional: Show weight percentage (0.0-1.0)

---

### 4. Emoji Reactions → CAM Weight Boost
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/MessageBubble.tsx`
**Lines:** 276-280
**Component:** MessageBubble

```typescript
// TODO_CAM_EMOJI: Link emoji reactions to CAM weight boost
// When reaction added: POST /api/cam/reaction { message_id, emoji, weight: 0.1 }
// Use emoji→weight mapping: 👍=0.2, ❤️=0.3, 🔥=0.25, 💡=0.15, 🤔=0.1, 👎=-0.2
```

**Effort:** Small (2-3 hours)
**Implementation Steps:**
1. Enhance `handleReaction` to send CAM weight data
2. Create emoji→weight mapping constant
3. POST to `/api/cam/reaction` on reaction add/remove
4. Visual feedback (show weight value briefly)
5. Track reaction history in CAM

---

### 5. CAM Activation in Chat Sidebar
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatSidebar.tsx`
**Lines:** 26-29
**Component:** ChatSidebar

```typescript
// TODO_CAM_INDICATOR: Add CAM activation field to Chat interface
cam_activation?: 'hot' | 'warm' | 'cold';  // Show memory priority in sidebar
```

**Effort:** Small (2-3 hours)
**Implementation Steps:**
1. Fetch CAM activation status when loading chats
2. Display activation badge next to chat name
3. Sort chats by activation level (optional)
4. Add tooltip showing activation weight
5. Color code badges (hot/warm/cold)

---

### 6. CAM Context Enrichment in Message Input
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/MessageInput.tsx`
**Lines:** 56-59
**Component:** MessageInput

```typescript
// TODO_CAM_UI: Pass CAM context suggestions to enrich input hints
cam_suggestions?: string[];  // Show hot/warm files in placeholder or autocomplete
```

**Effort:** Small (2-3 hours)
**Implementation Steps:**
1. Accept `cam_suggestions` prop
2. Update placeholder to show hot files hint
3. Add autocomplete suggestions from CAM
4. Display with low opacity/faded style
5. Allow quick insertion with tab/enter

---

### 7. CAM Model Ranking (Model Directory)
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/ModelDirectory.tsx`
**Lines:** 27-29
**Component:** ModelDirectory

```typescript
// TODO_CAM_INDICATOR: Add CAM relevance ranking from backend
cam_score?: number;  // 0.0-1.0 from GET /api/cam/model-rank?model_id=...
```

**Effort:** Medium (4-6 hours)
**Implementation Steps:**
1. Fetch CAM scores for models on load
2. Sort/highlight by CAM relevance
3. Display score badge on model card
4. Show "Based on conversation context" label
5. Optional: Animate score updates

---

### 8. CAM-Ranked Models in Mention Popup
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/MentionPopup.tsx`
**Lines:** 48-50
**Component:** MentionPopup

```typescript
// TODO_CAM_UI: Add CAM-ranked model suggestions in mention popup
cam_ranked_models?: Array<{ id: string; name: string; cam_score: number }>;
```

**Effort:** Small (2-3 hours)
**Implementation Steps:**
1. Display top 3-5 CAM-ranked models first
2. Show relevance scores
3. Add "Recommended based on context" label
4. Maintain user-typed models below suggestions
5. Allow quick selection with arrow keys

---

## Backend Endpoints Available

### Core CAM API Endpoints

```
GET /api/cam/suggestions
  Query params: context={search_context}, limit={number}
  Response: { suggestions: [{ id, name, path, cam_score, level }] }
  Purpose: Fetch context-aware file suggestions

POST /api/cam/pin
  Body: { file_path, metadata, type, depth }
  Response: { success, node_id, weight }
  Purpose: Pin file to CAM with metadata

GET /api/cam/activation
  Query params: node_id={id}
  Response: { level: 'hot'|'warm'|'cold', weight: 0.0-1.0 }
  Purpose: Check CAM activation state of node

POST /api/cam/reaction
  Body: { message_id, emoji, weight }
  Response: { success, updated_weight }
  Purpose: Link emoji reactions to CAM weight boost

GET /api/cam/model-rank
  Query params: model_id={id}
  Response: { model_id, cam_score: 0.0-1.0, rank }
  Purpose: Get CAM relevance score for model

GET /api/cam/activation?chat_id={id}
  Query params: chat_id={id}
  Response: { chat_id, level: 'hot'|'warm'|'cold' }
  Purpose: Get CAM status of chat in history
```

### Backend Implementation References
- **CAM Engine:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/cam_engine.py`
- **CAM Integration:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/services/cam_integration.py`
- **CAM Metrics:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/monitoring/cam_metrics.py`
- **Semantic Routes:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/semantic_routes.py` (foundation for new CAM routes)

### Recommended Route File
Create new file: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/cam_routes.py`

---

## Implementation Priority

### Phase 1 (High Priority - 1-2 weeks)
1. **CAM suggestions display** in search results (High visibility, frequently used)
2. **Pin-to-CAM button** on file cards (Core feature, enables CAM population)
3. **Emoji → CAM weight** in message reactions (Easy win, engagement metric)

### Phase 2 (Medium Priority - 2-3 weeks)
4. **CAM activation indicator** on folders (Visual feedback, improves understanding)
5. **CAM status in chat sidebar** (Organization, helps navigation)
6. **CAM model ranking** in directory (Context awareness, improves UX)

### Phase 3 (Low Priority - 3-4 weeks)
7. **CAM context enrichment** in input (Polish feature, nice-to-have)
8. **CAM suggestions in mention popup** (Edge case, low usage)

---

## Color Palette (Nolan Style - Grayscale)

| Level | Color | RGB | Usage |
|-------|-------|-----|-------|
| Hot | #ff6b6b | Red-ish | High activation, frequently used |
| Warm | #ffd93d | Yellow-ish | Medium activation, moderately used |
| Cold | #95a3a3 | Gray | Low activation, rarely used |
| Badge | #4a9eff | Blue | Primary accent for badges |
| Inactive | #555555 | Medium gray | Default state |

**Note:** Keep all colors desaturated to match Nolan aesthetic. Can use opacity for variations.

---

## Testing Checklist

### Unit Tests Needed
- [ ] CAM suggestions API response parsing
- [ ] Emoji → weight mapping accuracy
- [ ] Activation level classification (hot/warm/cold)
- [ ] Pin/unpin state management

### Integration Tests Needed
- [ ] Search results + CAM suggestions display together
- [ ] File card with CAM pin button
- [ ] Message bubble reactions updating CAM
- [ ] Chat sidebar refresh with CAM status
- [ ] Model directory sorting by CAM score

### E2E Tests Needed
- [ ] User pins file → appears in suggestions
- [ ] User reacts with emoji → CAM weight updates
- [ ] Switching chats shows correct CAM activation
- [ ] Model selection influenced by CAM ranking
- [ ] Folder label updates with activation changes

---

## Performance Considerations

### API Call Optimization
- **Batch suggestions:** Combine multiple CAM queries into single request
- **Caching:** Cache CAM scores with 5-minute TTL
- **Lazy loading:** Load activation status on hover (not on render)
- **Debouncing:** Throttle activation updates to 1s intervals

### Frontend Performance
- **Memoization:** Use React.memo for CAM status badges
- **Lazy components:** Code-split CAMSuggestionsPanel
- **State management:** Use zustand store for CAM state (already have useStore)
- **Rendering:** Virtual scroll for large suggestion lists

---

## Known Limitations

1. **No real-time sync:** CAM updates not pushed to UI (polling only)
2. **No conflict resolution:** Multiple pinning sources not handled
3. **No rollback:** No way to undo CAM operations through UI
4. **Limited emoji mapping:** Only 6 quick reactions supported
5. **No offline mode:** All CAM operations require backend connectivity

---

## Future Enhancements

1. **CAM visualization:** 3D tree showing hot/warm/cold nodes
2. **Export CAM state:** Download/backup CAM activation data
3. **Import CAM:** Load pre-trained CAM from files
4. **Collaborative CAM:** Merge CAM from multiple users
5. **CAM presets:** Save/load CAM configurations for different workflows
6. **Predictive suggestions:** Suggest next likely files based on CAM trajectory
7. **CAM decay:** Show files that are becoming cold

---

## File Changes Summary

### Files Modified (7)

| File | Changes | Lines |
|------|---------|-------|
| UnifiedSearchBar.tsx | Added CAM suggestions marker | 1002-1009 |
| FileCard.tsx | Added CAM pin + indicator markers | 547-551, 603-609 |
| MessageBubble.tsx | Added emoji→CAM weight marker | 276-280 |
| ChatSidebar.tsx | Added CAM activation interface field | 26-29 |
| MessageInput.tsx | Added CAM suggestions prop | 56-59 |
| ModelDirectory.tsx | Added CAM score field to Model interface | 27-29 |
| MentionPopup.tsx | Added CAM ranked models prop | 48-50 |

### Files Ready for Creation

| File | Purpose | Lines |
|------|---------|-------|
| cam_routes.py | New API routes for CAM endpoints | ~300 |
| CAMSuggestionsPanel.tsx | New component for suggestions display | ~150 |
| useCAS.ts | New hook for CAM API calls | ~100 |
| cam_utils.ts | Helper functions (emoji mapping, colors) | ~50 |

---

## Next Steps (After Marker Placement)

1. **Create backend routes:** `src/api/routes/cam_routes.py`
2. **Implement CAMSuggestionsPanel:** React component for suggestions display
3. **Create useCAS hook:** Centralized CAM API calls
4. **Add colors/utils:** Nolan-style color helpers
5. **Integrate with existing components:** Update each marked component
6. **Test CAM workflows:** User pinning → suggestions appearing
7. **Performance optimization:** Caching and batching
8. **UI/UX polish:** Animations, tooltips, feedback

---

## Marker Reference

All markers follow pattern: `// TODO_CAM_TYPE: Description`

**Types:**
- `TODO_CAM_UI` - UI integration point (display suggestions, context)
- `TODO_CAM_PIN` - Pinning functionality (add/remove from CAM)
- `TODO_CAM_INDICATOR` - Show CAM status (hot/warm/cold badge)
- `TODO_CAM_EMOJI` - Link to emoji/reaction system

---

## Questions for Team

1. Should CAM suggestions replace or supplement existing search results?
2. Do we want real-time CAM updates or periodic polling?
3. Should emoji reactions count equally or have different weights?
4. Should model ranking affect @mentions or just display?
5. Should we persist CAM state across sessions?

---

**Created by:** HAIKU-MARKERS-3
**Date:** 2026-01-26
**Status:** Ready for implementation
**Next Phase:** Backend route implementation (Phase 96)
