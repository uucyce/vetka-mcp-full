# Phase 180 — VETKA CUT Interface Build
> **Date:** 2026-03-14 | **Author:** Opus (Architect)
> **Source of Truth:** `docs/besedii_google_drive_docs/PULSE-JEPA/VETKA_CUT_Interface_Architecture_v1.docx`
> **Prototypes:** `story_space_3d_camelot_mckee.html`, `vetka_cut_workspace_wireframe.html`
> **Backend ready:** 8 PULSE modules (3,521 lines), 20+ endpoints, 152 tests

---

## 0. What exists (Phase 170–179)

| Layer | Component | Lines | Status |
|-------|-----------|-------|--------|
| Backend | 8× `pulse_*.py` services | 3,521 | ✅ merged to main |
| Backend | 20+ `/api/cut/pulse/*` endpoints | in cut_routes.py | ✅ merged |
| Backend | `cut_montage_ranker.py` (7 signals) | ~400 | ✅ merged |
| Frontend | `CutEditorLayout.tsx` | 800 | ✅ basic 3-panel |
| Frontend | `TransportBar.tsx` | 683 | ✅ play/pause/JKL/M-key markers |
| Frontend | `TimelineTrackView.tsx` | 1,679 | ✅ horizontal tracks, clips, waveform, trim |
| Frontend | `VideoPreview.tsx` | 297 | ✅ playback |
| Frontend | `ClipInspector.tsx` | 268 | ✅ clip metadata |
| Frontend | `AudioLevelMeter.tsx` | 209 | ✅ levels |
| Frontend | `TimelineTabBar.tsx` | 118 | ✅ multiple timelines |
| Frontend | `TranscriptOverlay.tsx` | 101 | ✅ SRT overlay |
| Frontend | `WaveformCanvas.tsx` | 77 | ✅ waveform canvas |
| Store | `useCutEditorStore.ts` | ~600 | ✅ clips, lanes, playhead, markers |
| Tests | 6 test files (phase179/) | 2,584 | ✅ 152 passing |

## 1. What to build (Architecture doc → Roadmap)

Architecture doc defines **7 panel types**. Build order from Section 14:
> "Script panel + Timeline + Monitors (MVP). Then DAG project. Then PULSE integration. Then Story Space. Then Effects nodes."

Timeline + Monitors already exist. Current phase fills the remaining 4 panels + critical infrastructure.

---

## 2. Waves

### Wave 1 — Panel Infrastructure (Opus + Codex A)
> **Goal:** Swedish wardrobe — any panel as tab, docked, or floating window

### Wave 2 — Script Panel + BPM Track (Codex A + Codex B)
> **Goal:** The spine of VETKA CUT — script drives everything

### Wave 3 — Story Space 3D + Camelot Wheel (Codex B)
> **Goal:** 3D vectorscope for narrative analysis

### Wave 4 — PULSE Auto-Montage Engine (Opus)
> **Goal:** 3 montage modes — always new timeline, never overwrite

### Wave 5 — Panel Sync + DAG Project (Codex A + Opus)
> **Goal:** Click anywhere → everything syncs. Material DAG with clusters

### Wave 6 — Inspector + Polish (All)
> **Goal:** PULSE data in source monitor, visual rules compliance

---

## 3. Task Breakdown

### Wave 1 — Panel Infrastructure

| ID | Task | Agent | Priority | Docs |
|----|------|-------|----------|------|
| **180.1** | `usePanelLayoutStore` — Zustand store for panel dock/tab/float state. Types: `PanelId`, `PanelState('docked'|'tab'|'floating')`, `LayoutPreset`. Actions: `detach(id)`, `dock(id, position)`, `tabify(id, targetId)`, `saveLayout()`, `loadLayout()`. Persist to `layout_state.json` | **Opus** | P0 | Arch doc §1 "Swedish wardrobe", §3 "Default layout", §10 `dag/layout_state.json` |
| **180.2** | `PanelShell` — wrapper component. Title bar with tab/detach/close buttons. Drag handle. Renders children panel. Supports: tab mode (renders as tab inside PanelGroup), docked mode (fixed position in grid), floating mode (absolute positioned, draggable, resizable). Monochrome SVG icons per §11 | **Codex A** | P0 | Arch doc §1 rules, §11 "Visual design rules" |
| **180.3** | `PanelGrid` — CSS Grid layout matching §3 default: left col 220px, center flex, right col 280px, bottom strip 180px. Drag borders to resize. Receives panels from store | **Codex A** | P0 | Arch doc §3 "Default layout" table |
| **180.4** | Migrate existing panels: wrap `VideoPreview` → Program Monitor shell, `ClipInspector` → Source Monitor shell, `TimelineTrackView` → Timeline shell. Preserve all existing functionality | **Codex A** | P1 | Arch doc §2.3, §2.4, §2.5 |

### Wave 2 — Script Panel + BPM Track

| ID | Task | Agent | Priority | Docs |
|----|------|-------|----------|------|
| **180.5** | `ScriptPanel.tsx` — vertical Y-time panel. Lines with timecodes (`script-time` class). Click line → sync playhead + highlight in DAG + show in source monitor. Auto-scroll on playback (teleprompter mode). Documentary mode: auto-transcript as script. Tab bar: "Script" / "DAG project" | **Codex A** | P0 | Arch doc §2.1 "Script panel" table, wireframe `panel-script` div |
| **180.6** | Script BPM display — 3 colored dots in script panel: green (audio BPM), blue (visual BPM), white (script BPM). Formula: `script_bpm = event_count × 60`. Events = stage directions + dialogue changes + scene headers | **Codex A** | P1 | Arch doc §5.1 BPM sources table, §5.3 "Script BPM calculation" |
| **180.7** | `BPMTrack.tsx` — special track at bottom of timeline. Green dots = audio beats (`/api/cut/pulse/analyze-script`), blue dots = visual cuts (scene detection), white dots = script events, orange dots = all-sync (strong beat, ±2 frames tolerance). Canvas-based for performance | **Codex B** | P0 | Arch doc §2.5 "BPM track", §5.2 "Sync indicator", wireframe `.tl-row` BPM |
| **180.8** | Backend: `GET /api/cut/pulse/bpm-markers` — returns all 3 BPM sources as timestamped arrays + computed sync points (orange). Uses `pulse_conductor.py` fusion logic | **Opus** | P0 | Arch doc §5.1, §5.2. Backend: `pulse_conductor.py`, `pulse_timeline_bridge.py` |

### Wave 3 — Story Space 3D + Camelot Wheel

| ID | Task | Agent | Priority | Docs |
|----|------|-------|----------|------|
| **180.9** | `StorySpace3D.tsx` — Three.js component. Horizontal plane = Camelot wheel (12 keys as ring). Vertical = McKee triangle (Archplot top, Mini/Anti bottom corners). Film trajectory as animated path. Current scene = glowing dot. Click dot → sync all panels. Default: floating 120×80 mini-panel inside Program Monitor. Can detach to full panel | **Codex B** | P0 | Arch doc §2.6, prototype `story_space_3d_camelot_mckee.html` (full 3D reference), `pulse_story_space.py` backend |
| **180.10** | `CamelotWheel.tsx` — SVG/Canvas interactive key circle. 12 major + 12 minor keys. Current key highlighted. Compatible neighbors shown. Click key → filter by Camelot proximity. Used inside StorySpace3D and standalone in Inspector | **Codex B** | P1 | Arch doc §2.6, prototype colors `camelotColors` array, `pulse_camelot_engine.py` backend |
| **180.11** | Backend: `POST /api/cut/pulse/story-space-points` — returns `StorySpacePoint[]` for all scenes. Each point: `{scene_id, x, y, z, camelot_key, triangle_pos, pendulum, energy, label}`. Uses `pulse_story_space.py` compute methods | **Opus** | P0 | `pulse_story_space.py` `StorySpacePoint` class, Arch doc §2.6 |

### Wave 4 — PULSE Auto-Montage Engine

| ID | Task | Agent | Priority | Docs |
|----|------|-------|----------|------|
| **180.12** | `pulse_auto_montage.py` — 3 montage modes. (A) Favorite assembly: takes favorite markers → finds natural in/out boundaries → orders by script/time. (B) Script-driven: matches script scenes to material via similarity → cuts at BPM sync points. (C) Music-driven: analyzes music BPM/key/energy → matches clips to music sections via Camelot/mood. ALL modes create new timeline (`{project}_cut-{NN+1}`), NEVER overwrite | **Opus** | P0 | Arch doc §7 "PULSE auto-montage workflow" (all 3 subsections), §7.1 safety rule |
| **180.13** | `POST /api/cut/pulse/auto-montage` — REST endpoint. Params: `mode` (favorites/script/music), `source_timeline_id`, `options`. Returns new timeline ID + assembly report. Emits SocketIO progress events for agent visualization | **Opus** | P0 | Arch doc §7.2 three modes table, §7.3 agent visualization |
| **180.14** | Timeline versioning: auto-naming `{project}_cut-{NN}`. Old timelines become read-only. Extend `useCutEditorStore` with `createVersionedTimeline()`, `isReadOnly(timelineId)`. Extend `TimelineTabBar` to show version badges + lock icon on read-only | **Codex A** | P1 | Arch doc §2.5 "Versioning", §7.1 safety rule, §10 `timelines/` structure |

### Wave 5 — Panel Sync + DAG Project

| ID | Task | Agent | Priority | Docs |
|----|------|-------|----------|------|
| **180.15** | Panel sync protocol — central `usePanelSyncStore`: `activeSceneId`, `playheadSec`, `selectedAssetId`, `selectedScriptLine`. Actions map per §9 sync matrix. Every panel subscribes to relevant fields. Click in any panel → broadcasts to all others | **Opus** | P0 | Arch doc §9 "Panel synchronization" — full 7×7 sync matrix |
| **180.16** | `DAGProjectPanel.tsx` — ReactFlow-based. Material organized by clusters: Characters, Locations, Takes, Music, SFX, Graphics. Click node → source monitor shows asset. Nodes linked to active script line glow blue. Bidirectional linking with script. Y-time vertical (bottom=root, top=leaves) | **Codex A** | P1 | Arch doc §2.2 "DAG project panel", wireframe `panel-dag` div |
| **180.17** | Backend: `GET /api/cut/project/dag` — returns DAG node/edge structure from project assets. Clusters auto-detected from asset metadata. Linked state computed from script analysis. Uses existing scene graph + `pulse_script_analyzer.py` | **Opus** | P1 | Arch doc §2.2, §8 "DAG as universal view mode", §10 `dag/project_graph.json` |

### Wave 6 — Inspector + Polish

| ID | Task | Agent | Priority | Docs |
|----|------|-------|----------|------|
| **180.18** | `PulseInspector.tsx` — replaces basic ClipInspector. Shows PULSE data for selected clip: Camelot key, scale, pendulum, dramatic_function, energy_profile, BPM. Reads from `/api/cut/pulse/score/scene`. Below source monitor in right column | **Codex B** | P1 | Arch doc §2.4 "Inspector" row, wireframe Inspector section |
| **180.19** | Visual compliance audit — verify all components match §11 rules: bg #0D0D0D/#1A1A1A/#252525, text #E0E0E0/#888/#555, 0.5px borders #333, no gradients, no glow, 4px/2px corners, thin scrollbars, monospace for timecodes. Fix any deviations | **Codex B** | P2 | Arch doc §11 "Visual design rules" — full table |
| **180.20** | Marker system unification — 4 marker types (Standard, BPM, Favorite-time, PULSE scene) visible simultaneously on timeline. Standard = top ruler, BPM = bottom track, Favorite = on clip, PULSE scene = amber. Export: Standard→XML, Favorite→SRT, BPM→JSON | **Codex A** | P2 | Arch doc §6 "Marker system" — full marker table |
| **180.21** | `project.vetka-cut.json` schema — master project file per §10 structure. Init on project create. Save/load layout, timelines, markers, PULSE config. Backend route: `POST /api/cut/project/save`, `GET /api/cut/project/load` | **Opus** | P2 | Arch doc §10 "Project file structure" |

---

## 4. Agent Assignment Summary

### Opus (Backend + Architecture) — 7 tasks

| Wave | Tasks | Focus |
|------|-------|-------|
| W1 | 180.1 | Panel layout store (Zustand architecture) |
| W2 | 180.8 | BPM markers endpoint |
| W3 | 180.11 | StorySpace points endpoint |
| W4 | 180.12, 180.13 | **PULSE Auto-Montage engine** (the brain) |
| W5 | 180.15, 180.17 | Panel sync protocol + DAG project API |
| W6 | 180.21 | Project file schema |

### Codex A (Core UI panels) — 7 tasks

| Wave | Tasks | Focus |
|------|-------|-------|
| W1 | 180.2, 180.3, 180.4 | **Panel infrastructure** (PanelShell, PanelGrid, migration) |
| W2 | 180.5, 180.6 | **Script Panel** (the spine) |
| W4 | 180.14 | Timeline versioning |
| W5 | 180.16 | DAG Project panel |
| W6 | 180.20 | Marker unification |

### Codex B (PULSE visualization) — 5 tasks

| Wave | Tasks | Focus |
|------|-------|-------|
| W2 | 180.7 | BPM Track on timeline |
| W3 | 180.9, 180.10 | **StorySpace3D + CamelotWheel** (the wow factor) |
| W6 | 180.18, 180.19 | PulseInspector + visual polish |

---

## 5. Execution Order (dependency chain)

```
Wave 1: Opus 180.1 ──→ Codex A 180.2, 180.3 ──→ Codex A 180.4
         (store)        (shell + grid)            (migration)

Wave 2: Opus 180.8 ──→ Codex B 180.7     (BPM endpoint → BPM track)
         Codex A 180.5 ──→ 180.6          (Script panel → BPM dots)
         (180.5 and 180.8 can start in parallel)

Wave 3: Opus 180.11 ──→ Codex B 180.9    (StorySpace API → 3D component)
         Codex B 180.10                    (CamelotWheel — independent)

Wave 4: Opus 180.12 ──→ 180.13           (Engine → REST endpoint)
         Codex A 180.14                    (Timeline versioning — independent)

Wave 5: Opus 180.15 ──→ ALL panels wire sync
         Opus 180.17 ──→ Codex A 180.16   (DAG API → DAG panel)

Wave 6: All — polish, inspector, markers, project file
```

---

## 6. Key Reference Documents per Task

| Task | Primary Doc | Secondary |
|------|-------------|-----------|
| 180.1–180.4 | Arch doc §1, §3, §11 | — |
| 180.5–180.6 | Arch doc §2.1, §5.3 | wireframe `panel-script` |
| 180.7 | Arch doc §2.5, §5.1–5.2 | wireframe BPM track |
| 180.8 | `pulse_conductor.py`, `pulse_timeline_bridge.py` | Arch doc §5 |
| 180.9 | Prototype `story_space_3d_camelot_mckee.html` | `pulse_story_space.py`, Arch doc §2.6 |
| 180.10 | `pulse_camelot_engine.py` | Prototype camelotColors/Labels |
| 180.11 | `pulse_story_space.py` StorySpacePoint | Arch doc §2.6 |
| 180.12–180.13 | Arch doc §7 (all subsections) | `cut_montage_ranker.py`, `pulse_conductor.py` |
| 180.14 | Arch doc §2.5 Versioning, §7.1 | `TimelineTabBar.tsx` |
| 180.15 | Arch doc §9 sync matrix | `useCutEditorStore.ts` |
| 180.16 | Arch doc §2.2, §8 | wireframe `panel-dag` |
| 180.17 | Arch doc §2.2, §10 | `pulse_script_analyzer.py` |
| 180.18 | Arch doc §2.4 Inspector | wireframe Inspector section |
| 180.19 | Arch doc §11 full visual spec | — |
| 180.20 | Arch doc §6 marker table | `cut_marker_bundle_service.py` |
| 180.21 | Arch doc §10 project structure | — |

---

## 7. Visual Design Rules (§11 — mandatory for ALL agents)

```
Background:  #0D0D0D (root), #1A1A1A (panels), #252525 (surfaces)
Text:        #E0E0E0 (primary), #888 (secondary), #555 (disabled)
Icons:       Custom SVG only. Monochrome white. 16×16 / 24×24. Stroke 1.5px, no fill
Borders:     0.5px solid #333. Panel dividers = 2px #222
Video track: #85B7EB (blue)
Audio track: #5DCAA5 (green)
Buttons:     No library. Transparent bg, 0.5px border #444, hover #333, active scale(0.98)
Font:        JetBrains Mono (timecode), Inter/system (labels)
Corners:     4px panels, 2px buttons, 0px timeline elements
NO:          gradients, shadows, glow, blur, standard UI buttons, emojis
```

---

## 8. Test Strategy

| Wave | Tests | Runner |
|------|-------|--------|
| W1 | Store unit tests (panel state transitions) | Opus writes |
| W2 | BPM markers endpoint tests, Script BPM calculation | Opus writes |
| W3 | StorySpace points API tests | Opus writes |
| W4 | Auto-montage 3 modes × edge cases (empty, single scene, 100 scenes) | Opus writes |
| W5 | Panel sync integration tests | Opus writes |
| W6 | Visual regression (optional — Playwright) | Codex |

---

## 9. Success Criteria

- [ ] 7 panels rendered in PanelGrid with correct default positions
- [ ] Any panel detachable to floating window, dockable back
- [ ] Script panel drives playhead, DAG highlights, source monitor
- [ ] BPM track shows 3 sources + orange sync points
- [ ] StorySpace3D renders Camelot × McKee with film trajectory
- [ ] PULSE auto-montage creates new timeline (never overwrites)
- [ ] Click in any panel → all panels sync per §9 matrix
- [ ] All visual rules §11 pass audit
- [ ] 200+ tests passing (152 existing + new)
