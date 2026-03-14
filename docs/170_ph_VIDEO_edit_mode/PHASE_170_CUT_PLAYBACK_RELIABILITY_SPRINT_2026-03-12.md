# PHASE 170 — CUT Playback Reliability Sprint

> **Owner:** Opus
> **Goal:** "User opens project, selects clip, sees preview, play/pause/seek work, timeline selection and preview don't diverge"
> **Date:** 2026-03-12
> **Scope:** VideoPreview, CutEditorLayout, useCutEditorStore, e2e smoke tests
> **Do NOT touch:** CutStandalone.tsx (Codex Scene Graph territory), Scene Graph packages

---

## Current State (Recon)

### What Works
- HTML5 `<video>` element with RAF sync loop (VideoPreview.tsx:194 lines)
- Two-way store sync: store.currentTime ↔ video.currentTime (150ms deadband)
- TransportBar: play/pause/seek/rate/mark-in-out
- AudioLevelMeter: Web Audio API VU meter (canvas-based)
- TranscriptOverlay: marker-driven subtitles
- media-proxy endpoint: sandbox-isolated file serving with MIME detection
- CutEditorLayout: Premiere-style 3-panel (source browser | preview | inspector) + timeline

### Critical Gaps

| # | Gap | Impact | Priority |
|---|-----|--------|----------|
| G1 | No `onError` on `<video>` | Bad/missing media = silent black frame, user confused | P0 |
| G2 | No active media switching reliability | Race conditions when clicking clips fast | P0 |
| G3 | No playback e2e smoke test | Zero coverage of core user flow | P0 |
| G4 | Single timeline (`timelineId: 'main'`) | User wants multi-timeline tabs (2-3 simultaneous) | P1 |
| G5 | No source monitor vs program monitor | NLE standard: source=raw clip, program=timeline output | P1 |
| G6 | Sets don't serialize (mutedLanes/soloLanes) | State lost on persist/reload | P2 |
| G7 | No codec/format validation | Unsupported formats fail silently | P2 |
| G8 | Poster matching requires exact source_path | Slight path mismatch = no poster = black frame | P2 |

---

## Architecture: Multi-Timeline Support

User requirement: multiple timelines in tabs, 2-3 visible simultaneously.

### Current (single timeline)
```
useCutEditorStore
  └── timelineId: 'main'
  └── lanes: TimelineLane[]
  └── currentTime: number
  └── selectedClipId: string | null
```

### Target (multi-timeline)
```
useCutEditorStore
  └── timelines: Map<string, TimelineState>
  │     ├── 'main' → { lanes, currentTime, selectedClipId, zoom, scrollLeft, ... }
  │     ├── 'alt-1' → { lanes, currentTime, ... }
  │     └── 'alt-2' → { lanes, currentTime, ... }
  └── activeTimelineId: string  (which one drives the program monitor)
  └── visibleTimelineIds: string[]  (which tabs are open / visible)
  └── focusedTimelineId: string  (which one has keyboard focus)
```

### Timeline Tab Behavior
- Tabs bar above timeline area shows open timelines
- Click tab → sets focusedTimelineId
- "New Timeline" button → creates empty timeline
- Each timeline has independent: lanes, currentTime, zoom, scrollLeft, selection
- Program monitor follows `activeTimelineId` (marked with ▶ badge)
- User can split view: 2-3 timelines stacked vertically

### Migration Path
- Phase A: Extract `TimelineState` interface from flat store fields
- Phase B: Wrap in `Map<string, TimelineState>` with activeTimelineId
- Phase C: TimelineTrackView accepts `timelineId` prop instead of reading flat store
- Phase D: Timeline tabs UI (simple tab bar + split view toggle)

---

## Task Breakdown

### Wave A: Error Handling & Media Reliability (P0)

**A1 (research):** Audit all media error paths
- Map every place where media can fail (proxy 404, codec unsupported, CORS, empty path)
- Document expected user-visible behavior for each failure mode
- Check VideoArtifactPlayer.tsx for patterns to reuse (it has quality scaling, BroadcastChannel)

**A2 (build):** Add `onError` handler to VideoPreview
- Display error state overlay (icon + message) instead of silent black frame
- Handle: network error, decode error, source not supported
- Add `mediaError` state field to useCutEditorStore
- Clear error on successful media switch

**A3 (build):** Harden media switching
- Debounce rapid clip clicks (prevent race conditions)
- Cancel pending loads when new media selected
- Show loading indicator during media load
- Validate activeMediaPath before proxy call

**A4 (test):** Playback smoke e2e test
- `cut_playback_reliability_smoke.spec.cjs`
- Scenarios: load project → click clip → verify preview → play/pause → seek → switch clip → error state

### Wave B: Multi-Timeline Foundation (P1)

**B1 (research):** Design TimelineState extraction
- Define `TimelineState` interface (lanes, currentTime, zoom, scrollLeft, selection, muted, solo)
- Plan migration from flat store to `Map<timelineId, TimelineState>`
- Identify all components that need `timelineId` prop
- Document backward-compat strategy (default 'main' timeline)

**B2 (build):** Extract TimelineState interface + activeTimelineId
- Create `TimelineState` type
- Add `timelines: Record<string, TimelineState>` to store
- Add `activeTimelineId`, `visibleTimelineIds`, `focusedTimelineId`
- Keep backward-compat getters for existing components (transitional)

**B3 (build):** Timeline tabs UI
- Tab bar component above timeline area
- New Timeline / Close / Rename
- Active timeline badge (▶)
- Click tab = set focused
- Drag to reorder (stretch: split view for 2-3 stacked)

**B4 (test):** Multi-timeline contract test
- Verify store supports multiple timelines
- Verify switching active timeline updates program monitor
- Verify independent state per timeline

### Wave C: Source Monitor vs Program Monitor (P1)

**C1 (research):** Design dual-monitor layout
- Source monitor: shows raw clip from source browser
- Program monitor: shows timeline playback output
- How to split VideoPreview area (toggle or side-by-side?)
- Which store fields drive which monitor?

**C2 (build):** Implement dual-monitor
- `SourceMonitor.tsx` — reads `activeMediaPath` directly, independent playhead
- `ProgramMonitor.tsx` — reads `activeTimelineId` playback state
- Layout toggle: single monitor ↔ dual monitor (like Premiere Pro)

**C3 (test):** Dual-monitor smoke test

### Wave D: Serialization & Polish (P2)

**D1 (build):** Fix Set serialization
- Convert `mutedLanes`/`soloLanes` from `Set<string>` to `string[]` in store
- Or add Zustand persist middleware with Set↔Array transform

**D2 (build):** Poster matching resilience
- Fuzzy path matching (normalize slashes, strip sandbox prefix)
- Fallback: generate poster from first video frame if no thumbnail

**D3 (build):** Codec/format pre-validation
- Check file extension before loading
- Display "unsupported format" message for non-web-playable files
- Suggest proxy transcoding for .mxf, .r3d, .braw etc.

---

## Files in Scope

| File | Role | Touch Policy |
|------|------|-------------|
| `client/src/components/cut/VideoPreview.tsx` | Primary target | Opus owns |
| `client/src/components/cut/CutEditorLayout.tsx` | Layout changes for dual-monitor | Opus owns |
| `client/src/store/useCutEditorStore.ts` | Multi-timeline state | Opus owns |
| `client/src/components/cut/TransportBar.tsx` | May need timeline-aware updates | Opus owns |
| `client/src/components/cut/TimelineTrackView.tsx` | Needs timelineId prop | Opus owns |
| `client/e2e/cut_playback_*.spec.cjs` | New e2e tests | Opus owns |
| `client/src/CutStandalone.tsx` | READ ONLY (Codex territory) | DO NOT EDIT |

---

## Coordination with Codex

- Codex continues Scene Graph micro-batches in CutStandalone.tsx
- Opus works in VideoPreview, CutEditorLayout, store, e2e — NO overlap
- Messages via task board `result_summary` fields
- If Opus needs CutStandalone bridge data → read only, leave MARKER note for Codex
