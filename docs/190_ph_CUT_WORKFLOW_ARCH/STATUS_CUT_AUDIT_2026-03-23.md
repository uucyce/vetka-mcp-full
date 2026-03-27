# CUT Project Audit — 2026-03-23
**Author:** Delta-3 (QA) | **Branch:** main | **Source:** Roadmaps + git + codebase scan

---

## Codebase Metrics

| Metric | Count |
|--------|-------|
| Total commits (all branches) | 1,657 |
| CUT-related commits | 720 |
| Commits on main | 1,356 |
| Unmerged (engine/media/ux/qa) | 3 / 2 / 5 / 8 |
| Python tests (pytest --co) | 6,437 |
| Python tests passing | 4,480 / 4,480 (100%) |
| E2E spec files (Playwright) | 41 |
| E2E test cases | ~650 |
| API endpoints (async handlers) | 107 (67 core + 26 media + 8 export + 6 render) |
| Backend services (cut_*.py) | 22 |
| UI components (components/cut/*.tsx) | 57 |
| Dockview panels (panels/) | 14 |
| Zustand store actions | 262 |
| Store LOC (useCutEditorStore.ts) | 1,419 |
| Hotkey actions wired | 79 unique |
| Hotkey bindings (Premiere/FCP7) | 80 / 78 |

---

## Stream A: Engine (Alpha)

**Roadmap:** ROADMAP_A_ENGINE_DETAIL.md | **Completion: 10/17 (59%)**

### DONE

| ID | Task | Evidence |
|----|------|----------|
| A1 | PanelSyncStore → EditorStore bridge | DockviewLayout.tsx wired |
| A2 | Panel focus system (focusedPanel + ACTION_SCOPE) | useCutHotkeys.ts:ACTION_SCOPE |
| A3 | Source/Program feed split | SourceMonitorPanel + ProgramMonitorPanel |
| A4 | Separate Source/Sequence marks | markIn/markOut per-context in store |
| A5 | Mount useCutHotkeys in NLE layout | CutEditorLayoutV2.tsx useEffect |
| A8 | Split at playhead + Ripple Delete | splitClip + rippleDelete handlers |
| A11 | 5-frame step + Clear In/Out | Shift+Arrow, Opt+X handlers |
| A12 | Tool State Machine (V/C/B/Z) | activeTool + 4 tool hotkeys |
| A16 | Project settings dialog | ProjectSettings panel |
| A17 | History Panel | HistoryPanelDock.tsx |

### DONE (this session, unmerged on cut-engine)

| Commit | Task | Fix |
|--------|------|-----|
| dd4f97cf | UNDO_COMPLETE_ALL | 11 ops routed through applyTimelineOps |
| 4aa488fb | CTRLV_FIX + K_CAPTURE | splitClip→Cmd+K, K key { capture: true } |

### REMAINING

| ID | Task | Priority | MVP Blocker |
|----|------|----------|-------------|
| **A15** | **Save / Save As / Autosave (Cmd+S)** | **CRITICAL** | **YES** |
| A6 | Track header controls (lock/mute/solo/target) | HIGH | no |
| A7 | Source patching / destination targeting | HIGH | no (blocked by A6) |
| A9 | Insert/Overwrite with targeting | HIGH | no (blocked by A7) |
| A10 | Navigate edit points (Up/Down) | HIGH | no |
| A13 | Context menu — Timeline clips | HIGH | no |
| A14 | Context menu — DAG/Project items | MEDIUM | no |

---

## Stream B: Media (Beta)

**Roadmap:** ROADMAP_B_MEDIA_DETAIL.md | **Completion: Backend 100%, Frontend 0/17 (0%)**

### DONE (Backend — 107 endpoints, 22 services)

| Area | Endpoints | Services |
|------|-----------|----------|
| Timeline CRUD | 67 | cut_project_store, cut_timeline_events, cut_undo_redo |
| Media/Proxy/Waveform | 26 | cut_proxy_worker, cut_ffmpeg_waveform, cut_codec_probe |
| Export/Presets | 8 | cut_render_engine |
| Render pipeline | 6 | cut_preview_decoder, cut_color_pipeline |
| Audio sync/analysis | — | cut_ffmpeg_audio_sync, cut_audio_engine, cut_audio_intel_eval |
| Scene detection | — | cut_scene_detector, cut_scene_graph_taxonomy |
| Montage/markers | — | cut_montage_ranker, cut_marker_bundle_service |
| Multicam sync | — | cut_multicam_sync (NEW) |
| Conform/relink | — | cut_conform (NEW) |

### DONE (this session, unmerged on cut-media)

| Commit | Task |
|--------|------|
| d0b3c569 | MARKER_B47: Media cache management + conform/relink (FCP7 Ch.44) |

### REMAINING (Frontend wiring)

| ID | Task | Priority | MVP Blocker |
|----|------|----------|-------------|
| **B3** | **Sequence Settings (framerate, resolution)** | **CRITICAL** | **YES** |
| **B5** | **Master Render Engine UI** | **CRITICAL** | **YES** |
| **B6** | **ExportDialog Rewrite** | **CRITICAL** | **YES** |
| B1 | FFprobe Codec Detection UI | CRITICAL | no |
| B1.5 | Maximum Codec/Container Coverage | CRITICAL | no |
| B2 | Proxy Generation Pipeline UI | CRITICAL | no |
| B4 | WebCodecs Decoder (ProRes/DNxHD) | HIGH | no |
| B7 | Crosspost Presets UI | MEDIUM | no |
| B8 | OTIO / AAF Export | MEDIUM | no |
| B9 | Effects System (video effects) | HIGH | no |
| B10 | Transitions System | MEDIUM | no |
| B11 | Clip Speed Control UI | HIGH | no |
| B12 | Motion Controls UI | MEDIUM | no |
| B13 | Audio Mixer Panel wiring | HIGH | no |
| B14 | Audio Transitions | MEDIUM | no |
| B15 | Audio Waveform Overlay | HIGH | no |
| B16 | Color Correction UI | MEDIUM | no |
| B17 | Export Selection + Audio Stems | MEDIUM | no |

---

## Stream C: UX (Gamma)

**Roadmap:** ROADMAP_C_UX_DETAIL.md | **Completion: 4/16 (25%)**

### DONE

| ID | Task | Evidence |
|----|------|----------|
| C1 | Merge dockview branch | DockviewLayout.tsx on main |
| C2 | Dark theme + panel styling | dockview-cut-theme.css (monochrome) |
| C3 | CutDockviewLayout replaces V2 | DockviewLayout is primary entry |
| C3+ | Monochrome sweep (#3b82f6 killed) | GAMMA-P1 task verified |

### DONE (this session, unmerged on cut-ux)

| Commit | Task |
|--------|------|
| 2c7863a8 | GAMMA-MN1: TimelineMiniMap (Premiere-style overview bar) |

### REMAINING

| ID | Task | Priority | MVP Blocker |
|----|------|----------|-------------|
| C4 | Panel Wrappers (Source, Program, Timeline, Project) | HIGH | no |
| C5 | Workspace Presets (Editing/Color/Audio) | MEDIUM | no |
| C6 | Hotkey Preset Selector | HIGH | no |
| C7 | Hotkey Editor (full rebinding UI) | HIGH | no |
| C8 | DAG Y-axis Flip + timelineId | HIGH | no |
| C9 | Mount Inspector/StorySpace/PULSE panels | HIGH | no |
| C10-C13 | Phase 198: Store refactor + multi-timeline | FUTURE | no |
| C14 | Auto-Montage UI | FUTURE | no |
| C15 | Project Panel view modes | FUTURE | no |
| C16 | Favorite Markers (N key + Shift+M) | FUTURE | no |

---

## Stream D: QA (Delta)

**Roadmap:** ROADMAP_D_QA_FORTRESS.md

### Current Baseline

| Suite | Pass | Fail | Skip/Fixme | Total |
|-------|------|------|------------|-------|
| Python backend | 4,480 | 0 | 1,860 | 6,340 |
| E2E Playwright (Delta-2) | 152 | 37 | 57 | 246 |

### QA Gate Verdicts (this session)

| Task | Agent | Verdict |
|------|-------|---------|
| tb_1774218077_6 | Gamma | PASS |
| tb_1774233252_15 | Delta | PASS |
| tb_1774242864_25 | Delta | PASS |
| tb_1774216127_1 | Delta | PASS |
| tb_1774231561_14 | Delta | PASS |
| tb_1774251471_1 | Alpha | PASS (Ctrl+V fix) |
| tb_1774251495_1 | Alpha | PASS (K capture) |

### Monochrome Audit

| Category | Violations | Status |
|----------|-----------|--------|
| Color correction | 0 | EXEMPT |
| Markers | 0 | EXEMPT |
| Music viz (Camelot/BPM) | 0 | EXEMPT |
| Audio metering | 0 | EXEMPT (functional) |
| **Real violations** | **3** | **FAIL** |

**Active violations:** DAGProjectPanel.tsx (#5DCAA5), ExportDialog.tsx (#1f1f2a x2)

---

## MVP Gate Status

**ROADMAP_CUT_MVP_PARALLEL.md — Merge Point 4**

| Blocker | Stream | Status | Fix |
|---------|--------|--------|-----|
| **A15: Save/Autosave** | Engine | **RED** | Alpha must implement Cmd+S |
| **B3: Sequence Settings** | Media | **RED** | Beta frontend wiring |
| **B5: Master Render UI** | Media | **RED** | Beta frontend wiring |
| **B6: ExportDialog Rewrite** | Media | **RED** | Beta frontend wiring |
| A3: Source/Program split | Engine | **GREEN** | Done |
| A5: Hotkeys working | Engine | **GREEN** | Done |
| A8: Split + Ripple Delete | Engine | **GREEN** | Done |
| C1: Dockview on main | UX | **GREEN** | Done |
| C2: Dark theme | UX | **GREEN** | Done |

**MVP Readiness: 5/9 gates GREEN (56%) — 4 CRITICAL blockers remain**

---

## Overall Summary

| Stream | Done | Remaining | % | MVP Blockers |
|--------|------|-----------|---|-------------|
| A: Engine | 10 (+2 unmerged) | 7 | 59% | 1 (Save) |
| B: Media backend | 107 endpoints, 22 services | — | 100% | — |
| B: Media frontend | 0 | 17 | 0% | 3 (Settings/Render/Export) |
| C: UX | 4 (+1 unmerged) | 12 | 25% | 0 |
| D: QA | 4,480 pass, 7 verdicts | ongoing | — | 0 |
| **Total MVP blockers** | | | | **4** |

**Bottom line:** Backend is complete. Frontend needs Save, Sequence Settings, Render UI, and Export rewrite before MVP deploy. Engine is 59% done, UX 25%. All blockers are frontend-side.
