# Phase 185: CUT Polish & Missing Wiring

**Goal:** Close all gaps between working backend and frontend. Every backend feature gets a UI surface. Berlin-ready stress test.

**Principle:** No new backend features. Wire what exists. Polish what's rough.

---

## Wave 1: Smart Assembly (backend exists, UI missing)

### 185.1: Scene Detection UI Panel
- **What:** Button in TransportBar or ProjectPanel: "Detect Scenes" → calls `POST /scene-detect-and-apply`
- **Shows:** Progress toast during detection, results auto-refresh timeline
- **Keyboard:** Cmd+D (detect scenes)
- **Files:** TransportBar.tsx (button + handler), cut_routes.py (already done)
- **Est:** 30 min

### 185.2: Montage Suggestions Panel
- **What:** New floating panel or tab in Inspector showing ranked clip suggestions
- **Backend:** `GET /montage/suggestions` returns scored clips with reasons
- **UI:** List of clips sorted by score, click → preview in Source Monitor
- **Action:** "Apply" button → `POST /pulse/auto-montage` → new versioned timeline
- **Files:** New MontagePanel.tsx, wire to usePanelSyncStore
- **Est:** 1.5 hours

### 185.3: Auto-Montage Modes (3 buttons)
- **What:** In MontagePanel or FooterActionBar: "Favorites Cut", "Script Cut", "Music Cut"
- **Each:** Creates new timeline tab (NEVER overwrites), populated by auto-montage
- **Backend:** Already parameterized in `/pulse/auto-montage` (mode: favorites|script|music)
- **Est:** 45 min

---

## Wave 2: Media Pipeline UI

### 185.4: Proxy Toggle
- **What:** Toggle switch per lane header or global in TransportBar
- **Behavior:** When ON → replace clip source_paths with proxy paths from `/proxy/path`
- **Visual:** Proxy badge on clip blocks ("P" icon)
- **Backend:** `POST /proxy/generate`, `GET /proxy/list`, `GET /proxy/path` — all working
- **Files:** TimelineTrackView.tsx (lane header toggle), useCutEditorStore (proxyMode state)
- **Est:** 1 hour

### 185.5: Sync Status Badges
- **What:** Visual badge on each clip showing sync status
- **States:** ✓ synced (green), ~ partial (yellow), ✗ no sync (gray), ↻ pending (blue spinner)
- **Data:** Already in `clip.sync.confidence` and `clip.sync.method`
- **Files:** TimelineTrackView.tsx (badge overlay on clip blocks)
- **Est:** 30 min

### 185.6: Transcript Overlay Wiring
- **What:** Verify TranscriptOverlay shows current speech during playback
- **Check:** Is transcript_bundle loaded? Does it sync with currentTime?
- **Fix:** Wire missing data fetch if needed
- **Est:** 30 min

---

## Wave 3: Editing Polish

### 185.7: Centralized Hotkey Registry
- **What:** Single `useHotkeys.ts` hook that registers ALL shortcuts
- **Motivation:** Currently 3 components have independent keydown listeners (TransportBar, TimelineTrackView, ProjectPanel)
- **Benefit:** No conflicts, discoverable via help modal, user-customizable later
- **Shortcuts to consolidate:** Space, J/K/L, S, I/O, M, C, Cmd+Z, Cmd+A, Cmd+I, Cmd+D, Delete, arrows, +/-
- **Files:** New hooks/useHotkeys.ts, refactor TransportBar + TimelineTrackView
- **Est:** 1.5 hours

### 185.8: Panel Layout Persistence
- **What:** Save panel sizes/positions to localStorage on resize
- **Load:** Restore on mount (default layout as fallback)
- **Files:** usePanelLayoutStore.ts (persist middleware), PanelGrid.tsx
- **Est:** 45 min

### 185.9: StorySpace3D Anchor
- **What:** StorySpace3D renders in Program Monitor area (not floating over timeline)
- **Behavior:** Toggle between "3D Story" and "Video Preview" in program monitor slot
- **Files:** CutEditorLayoutV2.tsx, PanelShell.tsx
- **Est:** 30 min

---

## Wave 4: Export & Interchange

### 185.10: EDL Export Implementation
- **What:** Implement `_build_edl_export()` (currently stub)
- **Format:** CMX 3600 EDL (industry standard)
- **Fields:** Event#, Reel, Track, TransType, CutType, SourceIn, SourceOut, RecordIn, RecordOut
- **Files:** New converters/edl_converter.py, wire in cut_routes.py
- **Est:** 1 hour

### 185.11: Export Panel UX
- **What:** Dropdown in TransportBar export area: PPro XML / FCPXML / EDL / OTIO / Batch
- **Currently:** Toggle between PPro and FCP only
- **After:** Full dropdown with all 5 formats
- **Files:** TransportBar.tsx (export section)
- **Est:** 30 min

---

## Wave 5: QA & Demo

### 185.12: Berlin Stress Test
- **What:** Run full pipeline on Berlin fixture: import → detect scenes → sync → montage → export
- **Validate:** Audio sync ±1 frame, scene boundaries correct, export imports clean in Premiere
- **Files:** tests/e2e/ (new), scripts/berlin_stress_test.py
- **Est:** 2 hours

### 185.13: Playwright E2E Tests
- **What:** 10 core flows: load CUT, import media, split clip, undo/redo, export, keyboard shortcuts
- **Files:** tests/e2e/test_cut_e2e.py
- **Est:** 3 hours

### 185.14: Error UX Pass
- **What:** Audit all API calls for error handling. Add toast notifications for failures.
- **Priority:** Import failures, export failures, sync failures, undo empty
- **Files:** All cut components (audit pass)
- **Est:** 1 hour

---

## Dependency Graph

```
Wave 1 (Assembly)     Wave 2 (Media)        Wave 3 (Polish)
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│ 185.1 Scene │     │ 185.4 Proxy  │     │ 185.7 Hotkeys    │
│ 185.2 Monte │     │ 185.5 Badges │     │ 185.8 Persist    │
│ 185.3 Modes │     │ 185.6 Trans  │     │ 185.9 StorySpace │
└──────┬──────┘     └──────┬───────┘     └────────┬─────────┘
       │                    │                       │
       └────────────┬───────┘                       │
                    │                               │
              Wave 4 (Export)                       │
              ┌──────────────┐                      │
              │ 185.10 EDL   │                      │
              │ 185.11 UX    │                      │
              └──────┬───────┘                      │
                     │                              │
                     └──────────┬───────────────────┘
                                │
                          Wave 5 (QA)
                    ┌───────────────────┐
                    │ 185.12 Berlin     │
                    │ 185.13 Playwright │
                    │ 185.14 Error UX   │
                    └───────────────────┘
```

Waves 1-3 are independent (can run in parallel).
Wave 4 depends on Waves 1-2 being wired.
Wave 5 is always last.

---

## Estimated Total: ~14 hours

| Wave | Tasks | Hours |
|------|-------|-------|
| Wave 1: Smart Assembly | 3 tasks | 2.75h |
| Wave 2: Media Pipeline | 3 tasks | 2h |
| Wave 3: Editing Polish | 3 tasks | 2.75h |
| Wave 4: Export | 2 tasks | 1.5h |
| Wave 5: QA & Demo | 3 tasks | 6h |
| **Total** | **14 tasks** | **~15h** |
