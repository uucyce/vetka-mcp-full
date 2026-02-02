# Task C1: Timeline Decay Visualization - Index

**Phase:** 108.2
**Date:** 2026-02-02
**Status:** ⚠️ PARTIAL - Requires Fix

---

## Quick Links

### 📋 Read First
- **[Quick Summary](TASK_C1_QUICK_SUMMARY.md)** - TL;DR, what works, what's broken, the fix
- **[Full Report](TASK_C1_TIMELINE_DECAY_REPORT.md)** - Complete verification, test cases, implementation guide

### 🎨 Visual Guides
- **[Flow Diagram](TIMELINE_DECAY_FLOW_DIAGRAM.txt)** - ASCII diagram showing data flow from backend to frontend

### 📚 Reference Docs
- **[Chat Positioning Usage](CHAT_POSITIONING_USAGE.md)** - How to use `calculate_chat_positions()` function
- **[Phase A Backend Report](PHASE_A_BACKEND_REPORT.md)** - Original backend implementation docs

---

## Document Purposes

### TASK_C1_QUICK_SUMMARY.md
**Purpose:** Get up to speed in 2 minutes
- Status overview
- What works vs. what's broken
- Quick fix guide
- Test checklist

**Read when:** You need to understand the task quickly

---

### TASK_C1_TIMELINE_DECAY_REPORT.md
**Purpose:** Complete technical verification report
- Section 1: Decay factor implementation (backend)
- Section 2: Opacity mapping (backend → frontend)
- Section 3: Frontend rendering
- Section 4: **Temporal Y-axis ordering (BROKEN)**
- Section 5: Detailed fix implementation
- Section 6: Optional enhancements
- Section 7: Test cases
- Section 8: Marker locations
- Section 9: Summary of findings

**Read when:**
- Implementing the fix
- Understanding why temporal ordering doesn't work
- Writing tests
- Debugging issues

---

### TIMELINE_DECAY_FLOW_DIAGRAM.txt
**Purpose:** Visual representation of data flow
- Current implementation flow
- Missing integration points
- After-fix flow
- Visual comparison (before/after)
- Verification scenarios

**Read when:**
- Need to understand architecture
- Explaining to others
- Debugging integration issues

---

### CHAT_POSITIONING_USAGE.md
**Purpose:** API documentation for positioning functions
- `calculate_decay_factor()` reference
- `calculate_chat_positions()` reference
- Integration examples
- Test cases

**Read when:**
- Using the positioning functions
- Need parameter details
- Writing integration code

---

## Key Findings

### ✅ What Works
1. **Backend decay calculation** (`calculate_decay_factor`)
   - Location: `knowledge_layout.py:2239-2265`
   - Marker: `MARKER_108_CHAT_DECAY`
   - Formula: `max(0, 1 - hours_since_activity / 168)`
   - Output: 0.0 to 1.0

2. **Opacity mapping** (decay → visual opacity)
   - Location: `tree_routes.py:606`
   - Formula: `opacity = 0.7 + (decay_factor * 0.3)`
   - Range: 0.7 (old) to 1.0 (recent)

3. **Frontend opacity rendering**
   - Location: `FileCard.tsx:348-353`
   - Marker: `MARKER_108_CHAT_CARD`
   - Implementation: `ctx.globalAlpha = chatOpacity`

### ❌ What's Broken
1. **Temporal Y-axis ordering NOT implemented**
   - `calculate_chat_positions()` function exists but is NOT called
   - Tree routes uses static Y offset (-5)
   - All chats appear at same Y level regardless of timestamp

---

## Implementation Status

| Component | Status | Location | Marker |
|-----------|--------|----------|--------|
| Decay calculation | ✅ Working | knowledge_layout.py:2239 | MARKER_108_CHAT_DECAY |
| Chat positioning logic | ✅ Exists, ❌ Not used | knowledge_layout.py:2268 | MARKER_108_CHAT_POSITION |
| Opacity mapping | ✅ Working | tree_routes.py:606 | - |
| Frontend rendering | ✅ Working | FileCard.tsx:348 | MARKER_108_CHAT_CARD |
| Temporal Y-axis | ❌ NOT implemented | tree_routes.py:572-575 | Missing: MARKER_108_TIMELINE_DECAY |

---

## Fix Requirements

### Primary Goal
Integrate `calculate_chat_positions()` into `tree_routes.py` to enable temporal Y-axis ordering.

### Files to Modify
1. `/src/api/routes/tree_routes.py` (lines 520-627)

### Changes Required
1. Import `calculate_chat_positions` from knowledge_layout
2. Build `file_positions` dict from existing nodes
3. Prepare `chats_to_position` list with parsed timestamps
4. Call `calculate_chat_positions()`
5. Use returned positions instead of static offsets
6. Add `MARKER_108_TIMELINE_DECAY` marker

### Expected Outcome
- Older chats appear at lower Y coordinates
- Newer chats appear at higher Y coordinates
- Opacity decay still works (0.7 - 1.0)
- Multiple chats from same file stagger in X-axis

---

## Code Locations

### Backend
- **Decay calculation:** `/src/layout/knowledge_layout.py:2239-2265`
- **Positioning function:** `/src/layout/knowledge_layout.py:2268-2417`

### API
- **Tree endpoint:** `/src/api/routes/tree_routes.py:520-627`
- **Opacity mapping:** `/src/api/routes/tree_routes.py:606`

### Frontend
- **Chat rendering:** `/client/src/components/canvas/FileCard.tsx:345-410`
- **Opacity application:** `/client/src/components/canvas/FileCard.tsx:348-353`

---

## Markers

### Existing Markers
```
MARKER_108_CHAT_DECAY     knowledge_layout.py:2243 (decay calculation)
MARKER_108_CHAT_POSITION  knowledge_layout.py:2278 (positioning function)
MARKER_108_CHAT_CARD      FileCard.tsx:345        (chat rendering)
```

### Missing Marker
```
MARKER_108_TIMELINE_DECAY tree_routes.py          (should be added at integration point)
```

---

## Test Plan

### Unit Tests
1. Test `calculate_decay_factor()` with various timestamps
2. Test `calculate_chat_positions()` with sample data
3. Verify temporal Y ordering (older < newer)
4. Verify X-axis staggering for multiple chats

### Integration Tests
1. Verify API returns correct opacity values
2. Verify API returns temporally ordered Y coordinates
3. Test with edge cases (no chats, single chat, many chats)

### Visual Tests
1. Open VETKA with chats of different ages
2. Verify visual order matches temporal order
3. Verify opacity decreases with age
4. Verify multiple chats from same file are staggered

---

## Timeline

### Current Phase
**Task C1:** Timeline decay visualization (Phase 108.2)

### Estimated Time
- **Reading documentation:** 30 minutes
- **Implementing fix:** 1 hour
- **Testing:** 30 minutes
- **Total:** 2 hours

---

## Next Steps

1. Read [Quick Summary](TASK_C1_QUICK_SUMMARY.md) for overview
2. Read [Full Report](TASK_C1_TIMELINE_DECAY_REPORT.md) Section 5 for implementation details
3. Apply fix to `tree_routes.py`
4. Add `MARKER_108_TIMELINE_DECAY` marker
5. Test temporal ordering visually
6. Run unit tests
7. Mark task complete

---

## Related Tasks

- **Task A:** Backend chat positioning (COMPLETE)
- **Task B:** Frontend chat rendering (COMPLETE)
- **Task C1:** Timeline decay visualization (THIS TASK)
- **Task C2:** Artifact progress visualization (FUTURE)

---

**Last Updated:** 2026-02-02
**Phase:** 108.2
**Task:** C1 - Timeline Decay Visualization
