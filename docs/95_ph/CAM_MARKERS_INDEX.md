# CAM UI Markers - Quick Index

**Complete marker placement reference for CAM UI integration**

---

## All Markers (8 Total)

### MARKER 1: CAM Suggestions Display
**Component:** UnifiedSearchBar
**File:** `client/src/components/search/UnifiedSearchBar.tsx`
**Lines:** 1002-1009
**Type:** `TODO_CAM_UI`
**Severity:** High

```
Location: Search results section, above results list
Feature: Display contextually relevant files from CAM
Backend: GET /api/cam/suggestions?context={searchContext}&limit=5
```

---

### MARKER 2: CAM Pin Button
**Component:** FileCard
**File:** `client/src/components/canvas/FileCard.tsx`
**Lines:** 547-551
**Type:** `TODO_CAM_PIN`
**Severity:** High

```
Location: File card hover preview
Feature: Pin file to CAM with metadata
Backend: POST /api/cam/pin { file_path, metadata }
```

---

### MARKER 3: CAM Activation Indicator (Folders)
**Component:** FileCard
**File:** `client/src/components/canvas/FileCard.tsx`
**Lines:** 603-609
**Type:** `TODO_CAM_INDICATOR`
**Severity:** High

```
Location: Folder label display in 3D tree view
Feature: Show hot/warm/cold activation level
Backend: GET /api/cam/activation?node_id={id}
Colors: hot=#ff6b6b, warm=#ffd93d, cold=#95a3a3
```

---

### MARKER 4: Emoji Reactions to CAM Weight
**Component:** MessageBubble
**File:** `client/src/components/chat/MessageBubble.tsx`
**Lines:** 276-280
**Type:** `TODO_CAM_EMOJI`
**Severity:** Medium

```
Location: Emoji reaction buttons in message footer
Feature: Link emoji reactions to CAM weight boost
Backend: POST /api/cam/reaction { message_id, emoji, weight }
Mapping: 👍=0.2, ❤️=0.3, 🔥=0.25, 💡=0.15, 🤔=0.1, 👎=-0.2
```

---

### MARKER 5: CAM Status in Chat Sidebar
**Component:** ChatSidebar
**File:** `client/src/components/chat/ChatSidebar.tsx`
**Lines:** 26-29
**Type:** `TODO_CAM_INDICATOR`
**Severity:** Medium

```
Location: Chat history sidebar items
Feature: Display CAM activation status next to chat name
Backend: GET /api/cam/activation?chat_id={id}
Display: Badge with hot/warm/cold color coding
```

---

### MARKER 6: CAM Suggestions in Input
**Component:** MessageInput
**File:** `client/src/components/chat/MessageInput.tsx`
**Lines:** 56-59
**Type:** `TODO_CAM_UI`
**Severity:** Low

```
Location: Message input component props
Feature: Enrich input hints with CAM suggestions
Integration: Show hot/warm files in placeholder or autocomplete
```

---

### MARKER 7: CAM Model Ranking
**Component:** ModelDirectory
**File:** `client/src/components/ModelDirectory.tsx`
**Lines:** 27-29
**Type:** `TODO_CAM_INDICATOR`
**Severity:** Medium

```
Location: Model interface definition
Feature: Add CAM relevance score to model selection
Backend: GET /api/cam/model-rank?model_id={id}
Display: Score badge, sort by relevance
```

---

### MARKER 8: CAM-Ranked Models in Mention Popup
**Component:** MentionPopup
**File:** `client/src/components/chat/MentionPopup.tsx`
**Lines:** 48-50
**Type:** `TODO_CAM_UI`
**Severity:** Low

```
Location: @ mention popup component props
Feature: Show top CAM-ranked models in mention suggestions
Integration: Display top 3-5 with relevance scores
```

---

## Quick Search

### By Component
- **FileCard:** 2 markers (pin, indicator)
- **UnifiedSearchBar:** 1 marker
- **MessageBubble:** 1 marker
- **ChatSidebar:** 1 marker
- **MessageInput:** 1 marker
- **ModelDirectory:** 1 marker
- **MentionPopup:** 1 marker

### By Marker Type
- **TODO_CAM_UI (3):** Markers 1, 6, 8
- **TODO_CAM_PIN (1):** Marker 2
- **TODO_CAM_INDICATOR (4):** Markers 3, 5, 7, + 1 in ModelDirectory

### By Priority
- **High (3):** Markers 1, 2, 3
- **Medium (3):** Markers 4, 5, 7
- **Low (2):** Markers 6, 8

### By Backend Endpoint
| Endpoint | Marker |
|----------|--------|
| GET /api/cam/suggestions | 1 |
| POST /api/cam/pin | 2 |
| GET /api/cam/activation | 3, 5 |
| POST /api/cam/reaction | 4 |
| GET /api/cam/model-rank | 7 |

---

## Implementation Workflow

### Phase 1: Foundation (Days 1-3)
```
1. Create cam_routes.py with stub endpoints
2. Implement GET /api/cam/suggestions
3. Implement POST /api/cam/pin
4. Test with curl/Postman
```

### Phase 2: Frontend Components (Days 4-7)
```
5. Implement Marker 1 (search suggestions panel)
6. Implement Marker 2 (pin button)
7. Create useCAS hook for API calls
8. Add test fixtures
```

### Phase 3: Indicators (Days 8-10)
```
9. Implement Marker 3 (folder badge)
10. Implement Marker 5 (sidebar status)
11. Implement Marker 7 (model ranking)
12. Add color palette utilities
```

### Phase 4: Polish (Days 11-14)
```
13. Implement Marker 4 (emoji reactions)
14. Implement Marker 6 (input hints)
15. Implement Marker 8 (mention popup)
16. Performance optimization
```

---

## Testing Checklist

- [ ] All 8 markers found and documented
- [ ] Files edited without breaking existing code
- [ ] Backend endpoint stubs created
- [ ] Frontend components compile without errors
- [ ] API calls return expected responses
- [ ] Visual indicators display correctly
- [ ] Performance under load (1000+ nodes)
- [ ] Mobile responsive testing
- [ ] Keyboard accessibility
- [ ] Graceful degradation (backend down)

---

## Git Workflow

```bash
# Branch for each marker group
git checkout -b feature/cam-ui-markers

# Commit by marker
git commit -m "MARKER_1: Add CAM suggestions display to search"
git commit -m "MARKER_2_3: Add pin button and activation indicator to FileCard"
git commit -m "MARKER_4: Link emoji reactions to CAM weights"

# Final PR
git push origin feature/cam-ui-markers
```

---

## References

- **Full Documentation:** `/docs/95_ph/HAIKU_MARKERS_3_CAM_UI.md`
- **CAM Engine:** `src/orchestration/cam_engine.py`
- **CAM Integration:** `src/orchestration/services/cam_integration.py`
- **Existing Routes:** `src/api/routes/` directory

---

**Created:** 2026-01-26
**Status:** Ready for Implementation
**Estimated Effort:** 10-14 days (2 weeks)
