# STREAM A3: TIMELINE UX POLISH — Detailed Sub-Roadmap

**Date:** 2026-03-22
**Agent:** Opus Alpha (Claude Code)
**Parent:** ROADMAP_A2_ENGINE_ADVANCED.md (ALL DONE)
**Focus:** Zoom gestures, marker UX, track height, waveform control

---

## Context

CUT's marker system is unique — not just editorial markers (favorite/comment)
but PULSE analysis markers: `bpm_audio` (rhythm beats), `bpm_visual` (cut points),
`bpm_script` (scene transitions), `sync_point` (multi-source sync).

Currently BPM markers render in BPMTrack.tsx (dot grid), but NOT on the main
timeline. Editors need to see beats ON the clips to cut rhythmically.

Snap system works but doesn't snap to marker end_sec. Zoom has Cmd+Wheel
but no pinch-to-zoom. Per-track waveform control is missing (global only).

---

## Task Matrix

| ID | Task | Priority | Complexity | Status |
|----|------|----------|------------|--------|
| A3.1 | BPM markers on timeline tracks | P1 | MEDIUM | PENDING |
| A3.2 | Marker filter/visibility toggle | P2 | LOW | PENDING |
| A3.3 | Pinch-to-zoom + zoom center at cursor | P2 | LOW | PENDING |
| A3.4 | Per-track waveform toggle | P2 | LOW | PENDING |
| A3.5 | Track height min/max constraints | P3 | LOW | PENDING |
| A3.6 | Snap to marker end_sec | P3 | LOW | PENDING |

---

## Detailed Specs

### A3.1: BPM Markers on Timeline Tracks (P1)

**The killer feature.** PULSE generates beat markers: audio beats (green),
visual cut points (blue), script scene transitions (white), sync points (orange).
Currently only visible in BPMTrack.tsx as a dot grid below timeline.

**Goal:** Render BPM markers as thin vertical lines INSIDE each track lane,
so editors can see beats overlaid on clips and cut to rhythm.

**Implementation:**
- Filter `markers` by BPM kinds: `bpm_audio`, `bpm_visual`, `bpm_script`, `sync_point`
- Render as 1px vertical lines inside lane content area (same as playhead but thinner)
- Colors: audio=#22c55e, visual=#4a9eff, script=#fff, sync=#f59e0b
- Opacity: based on `score` field (0-1) — stronger beats more visible
- Only render when zoom > 30 (avoid clutter at low zoom)

**Marker data:**
```typescript
// Already in store as markers: TimeMarker[]
// BPM markers have: kind, start_sec, score (0-1), source_engine
```

**Files:** TimelineTrackView.tsx (rendering), useCutEditorStore.ts (no changes)

### A3.2: Marker Filter/Visibility Toggle (P2)

Add per-kind visibility toggles to timeline toolbar or marker legend.
Store: `visibleMarkerKinds: Set<string>` (default: all visible).
Filter markers before rendering.

### A3.3: Pinch-to-Zoom + Zoom Center at Cursor (P2)

Current: Cmd+Wheel zooms but doesn't center on cursor position.
Target: trackpad pinch gesture + zoom centers on mouse X position.

**Implementation:**
- Listen for `gesturestart`/`gesturechange` events (Safari) OR
  detect `ctrlKey + wheel` (Chrome trackpad pinch emulation)
- Calculate cursor time = `(clientX - rect.left + scrollLeft) / zoom`
- After zoom: `scrollLeft = cursorTime * newZoom - (clientX - rect.left)`

### A3.4: Per-Track Waveform Toggle (P2)

Add eye-like toggle per audio lane to show/hide waveform.
Store: extend `hiddenLanes` concept or add `waveformLanes: Set<string>`.

### A3.5: Track Height Min/Max Constraints (P3)

Enforce minimum 20px, maximum 200px per lane.
Clamp in `setTrackHeight` and `setTrackHeightForLane`.

### A3.6: Snap to Marker end_sec (P3)

Currently snap only uses `marker.start_sec`. Add `marker.end_sec` to
snap candidates pool for range markers.

---

## Execution Order

```
Phase 1:
  A3.1 — BPM markers on timeline (biggest visual impact)

Phase 2 (parallel):
  A3.2 — Marker filter
  A3.3 — Pinch zoom
  A3.4 — Per-track waveform

Phase 3:
  A3.5 — Height constraints
  A3.6 — Snap to end_sec
```

---

*"The rhythm is already in the data. Now make it visible."*
