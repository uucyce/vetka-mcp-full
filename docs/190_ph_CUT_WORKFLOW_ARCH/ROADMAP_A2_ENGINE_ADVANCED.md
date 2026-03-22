# STREAM A2: ENGINE ADVANCED — Detailed Sub-Roadmap

**Date:** 2026-03-22
**Agent:** Opus Alpha (Claude Code)
**Parent:** ROADMAP_A_ENGINE_DETAIL.md (ALL DONE)
**Focus:** Backend trim ops, multi-clip drag, undo UX, zoom polish

---

## Context

Roadmap A (13 tasks) is complete. Frontend trim tools (slip/slide/ripple/roll)
exist but two critical backend ops are stubs — slip_clip and ripple_trim.
Undo/redo backend is production-ready (100+ tests) but frontend hotkeys
call the API, not yet verified round-trip. Multi-select exists but
multi-clip drag is missing.

---

## Task Matrix

| ID | Task | Priority | Complexity | Deps | Status |
|----|------|----------|------------|------|--------|
| A2.1 | Backend: `slip_clip` op handler | P0 | LOW | none | PENDING |
| A2.2 | Backend: `ripple_trim` op handler | P0 | MEDIUM | none | PENDING |
| A2.3 | Verify undo/redo round-trip (⌘Z/⌘⇧Z) | P1 | LOW | none | PENDING |
| A2.4 | Multi-clip drag/move | P1 | HIGH | none | PENDING |
| A2.5 | Zoom to selection | P2 | LOW | none | PENDING |
| A2.6 | Smooth zoom animation | P3 | LOW | none | PENDING |
| A2.7 | Python reference tests for slip/ripple_trim | P0 | LOW | A2.1, A2.2 | PENDING |

---

## Detailed Specs

### A2.1: Backend `slip_clip` op handler (P0)

Frontend sends: `{op: 'slip_clip', clip_id: string, source_in: number}`

Backend must: find clip by ID, update `source_in` field only. No timeline
position or duration changes. This changes WHAT part of the source media
is shown, not WHERE or HOW LONG the clip appears.

**FCP7 ref:** Slip = hold clip in place, drag content left/right within
the clip window. Like moving film inside a fixed gate.

**File:** `src/api/routes/cut_routes.py` — add case in `_apply_timeline_ops()`

### A2.2: Backend `ripple_trim` op handler (P0)

Frontend sends: `{op: 'ripple_trim', clip_id: string, start_sec: number, duration_sec: number}`

Backend must:
1. Find clip by ID
2. Calculate delta = new_duration - old_duration (or start_sec change)
3. Update clip's start_sec and duration_sec
4. Shift ALL subsequent clips in the SAME lane by delta

**FCP7 ref:** Ripple = trim edge + everything after shifts to fill/make room.
Unlike basic trim which leaves gaps.

**File:** `src/api/routes/cut_routes.py` — add case in `_apply_timeline_ops()`

### A2.3: Verify undo/redo round-trip (P1)

CutEditorLayoutV2 already calls `POST /api/cut/undo` and `POST /api/cut/redo`
via hotkey handlers (⌘Z, ⌘⇧Z). Backend undo service is production-ready.
Need to verify:
- After an edit (move, trim, delete), ⌘Z restores previous state
- ⌘⇧Z re-applies the edit
- `refreshProjectState()` properly reloads from backend after undo

**Likely gap:** Frontend edits that don't go through backend (setLanes directly)
won't have undo entries. These need to be migrated to backend ops.

### A2.4: Multi-clip drag/move (P1)

Currently: drag moves single clip. `selectedClipIds` tracks multi-select
but drag handler only uses `dragState.clipId` (singular).

Need:
- On drag start with multiple selected: create drag ghost for all
- On drag end: emit `move_clip` op for each selected clip with same delta
- Snap should use primary clip (the one being dragged), others follow

### A2.5: Zoom to selection (P2)

When clips are selected, `\` should zoom/scroll to show all selected clips.
Calculate bounding box of selected clips → set zoom and scrollLeft.

### A2.6: Smooth zoom animation (P3)

Currently zoom is instant (step). Use `requestAnimationFrame` to animate
zoom changes over 150ms for smoother feel.

---

## Execution Order

```
Phase 1 (parallel, no deps):
  A2.1 — slip_clip backend (30min)
  A2.2 — ripple_trim backend (45min)

Phase 2 (after A2.1 + A2.2):
  A2.7 — Python reference tests
  A2.3 — Undo round-trip verification

Phase 3:
  A2.4 — Multi-clip drag (independent)

Phase 4:
  A2.5, A2.6 — Polish
```

---

## Owned Files

```
src/api/routes/cut_routes.py              — backend ops (A2.1, A2.2)
tests/test_*.py                           — reference tests (A2.7)
client/src/components/cut/TimelineTrackView.tsx  — multi-clip drag (A2.4)
client/src/store/useCutEditorStore.ts      — zoom helpers (A2.5, A2.6)
client/src/components/cut/CutEditorLayoutV2.tsx  — undo verify (A2.3)
```

---

*"Roadmap A gave CUT a skeleton. A2 gives it muscle memory."*
