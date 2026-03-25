# ROADMAP A4: PULSE Integration — Engine × Frontend Wiring
**Author:** Alpha-3 (Opus) | **Date:** 2026-03-24
**Status:** ACTIVE — awaiting Commander approval
**Domain:** Alpha (engine store/hotkeys) + Gamma (panel mount/UI) + Beta (backend verify)

---

## Problem Statement

PULSE backend is **90% complete** (4,190 lines across 8 services):
- `pulse_conductor.py` (457L) — orchestrator
- `pulse_camelot_engine.py` (320L) — harmonic wheel
- `pulse_cinema_matrix.py` (704L) — narrative DNA map (McKee + Itten + Camelot)
- `pulse_auto_montage.py` (669L) — 3-mode auto-edit
- `pulse_script_analyzer.py` (286L) — screenplay parser
- `pulse_energy_critics.py` (481L) — motion/audio energy
- `pulse_timeline_bridge.py` (387L) — clip enrichment
- `pulse_story_space.py` (615L) — 3D narrative viz

**But frontend has ZERO integration:**
- PulseInspector.tsx — exists, NOT mounted
- StorySpace3D.tsx — exists, NOT mounted
- AutoMontagePanel.tsx — exists but NO wiring to `POST /cut/pulse/auto-montage`
- CamelotWheel.tsx — exists, NOT accessible from main layout
- No "Run PULSE Analysis" button anywhere

---

## Phase 1: Mount Existing Components (Gamma, 2-3 hours)

| Task | Owner | File | Description |
|------|-------|------|-------------|
| A4.1 | Gamma | DockviewLayout.tsx | Mount PulseInspector in Analysis tab group |
| A4.2 | Gamma | DockviewLayout.tsx | Mount StorySpace3D in Analysis tab group |
| A4.3 | Gamma | DockviewLayout.tsx | Mount CamelotWheel as subtab of PulseInspector |

**Contract:** After Phase 1, user can open Analysis tabs and see PULSE metadata for selected scene.

---

## Phase 2: Auto-Montage UI (Gamma + Alpha, 3-4 hours)

| Task | Owner | File | Description |
|------|-------|------|-------------|
| A4.4 | Gamma | AutoMontagePanel.tsx | Wire 3 mode buttons → `POST /cut/pulse/auto-montage` |
| A4.5 | Alpha | useCutEditorStore.ts | `runAutoMontage(mode)` store action → API call → new timeline tab |
| A4.6 | Alpha | CutEditorLayoutV2.tsx | Handle montage result → create new timeline version tab |
| A4.7 | Gamma | AutoMontagePanel.tsx | Progress indicator during montage (SocketIO or polling) |

**Contract:** User clicks "Favorites Cut" → backend runs → new timeline tab appears with auto-assembled sequence.

**API Contract:**
```
POST /cut/pulse/auto-montage
Body: { sandbox_root, project_id, timeline_id, mode: "favorites"|"script"|"music" }
Response: { success, timeline_label, clips: MontageClip[], diagnostics }
```

---

## Phase 3: PULSE Analysis Trigger (Alpha + Beta, 2 hours)

| Task | Owner | File | Description |
|------|-------|------|-------------|
| A4.8 | Alpha | useCutEditorStore.ts | `runPulseAnalysis()` action → `POST /cut/pulse/analyze` |
| A4.9 | Beta | cut_routes.py | Verify `/cut/pulse/analyze` endpoint returns PulseScore per scene |
| A4.10 | Alpha | CutEditorLayoutV2.tsx | Hotkey `Cmd+Shift+P` → run PULSE analysis |

**Contract:** User presses Cmd+Shift+P → PULSE analyzes all scenes → PulseInspector shows results.

---

## Phase 4: Engine Store — Undo Completeness (Alpha, 3-4 hours)

5 editing actions bypass `applyTimelineOps()` → no undo:

| Task | Owner | Action | Current | Fix |
|------|-------|--------|---------|-----|
| A4.11 | Alpha | splitClip (local-first) | `setLanes()` direct | Keep local-first BUT also send to backend for undo entry |
| A4.12 | Alpha | addDefaultTransition | `setLanes()` direct | Route through `applyTimelineOps` |
| A4.13 | Alpha | pasteAttributes | direct mutation | Route through `applyTimelineOps` |
| A4.14 | Alpha | splitEditLCut | direct mutation | Route through `applyTimelineOps` |
| A4.15 | Alpha | splitEditJCut | direct mutation | Route through `applyTimelineOps` |

**Contract:** Cmd+Z undoes ALL editing operations, not just some.

---

## Phase 5: Source/Program Video Split (Alpha + Gamma, 4-6 hours)

| Task | Owner | File | Description |
|------|-------|------|-------------|
| A4.16 | Alpha | useCutEditorStore.ts | Ensure `sourceCurrentTime`, `seekSource`, `playSource`, `pauseSource` are fully independent |
| A4.17 | Alpha | CutEditorLayoutV2.tsx | Wire `feed` prop routing for VideoPreview instances |
| A4.18 | Gamma | VideoPreview.tsx | Respect `feed` prop — source reads source state, program reads program state |

**Contract:** Source Monitor shows raw clip. Program Monitor shows timeline playback. Independent seek/play.

---

## Priority Order

```
P0 (blocking user):
  Phase 4 (undo) — user can't trust Cmd+Z
  Phase 5 (source/program split) — both monitors show same thing

P1 (blocking PULSE):
  Phase 1 (mount components) — 2 hours, massive perceived value
  Phase 2 (auto-montage UI) — THE killer feature

P2 (deepening):
  Phase 3 (PULSE trigger) — analysis on demand
```

---

## Dependencies

- **Backend bootstrap must work** — `CutBootstrapRequest.timeline_id` bug blocks all E2E testing
- **Waveform/thumbnail backend** — needed for visual feedback in auto-montage results
- **Scene detection** — `POST /cut/scene-detect-and-apply` must return scene boundaries for PULSE to analyze

---

*"The conductor wrote the score. Now build the orchestra pit."*
