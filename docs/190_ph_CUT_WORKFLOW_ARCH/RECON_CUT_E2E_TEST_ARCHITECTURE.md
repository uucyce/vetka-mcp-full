# RECON: CUT NLE — E2E Test Architecture
**Date:** 2026-03-20
**Author:** OPUS-D (QA/Test Architect)
**Task:** tb_1773987881_33
**Type:** Research (no code)
**Status:** COMPLETE

---

## 0. Executive Summary

CUT NLE has **388 backend tests** (37 files) — excellent coverage. Frontend has **23 Playwright smoke specs** in `client/e2e/` but **zero component-level tests**. UI is growing fast (40 components, 3 parallel streams), creating a widening gap between backend confidence and frontend risk.

**Recommendation:** Dedicated QA-agent using Chrome DevTools MCP for E2E regression, complemented by Playwright specs written inline by stream agents (A/B/C) for their own features.

---

## 1. Current Test Landscape

### 1.1 Backend (Strong)

| Category | Files | Tests | Quality |
|----------|-------|-------|---------|
| API endpoints (Phase 170) | 24 | 117 | High — TestClient + tmp_path isolation |
| FFmpeg/Export (Phase 172) | 4 | 58 | High — synthetic signal data |
| Advanced features (Phase 173) | 6 | 129 | High — class-based, multi-scenario |
| Root tests (codecs, render, triple-write) | 3 | 84 | High — round-trip serialization |
| **Total** | **37** | **388** | **Production-grade** |

**Patterns established:**
- `_make_client()` → FastAPI TestClient per test
- `_bootstrap_sandbox(tmp_path)` → isolated filesystem
- `_wait_for_job()` → async job polling
- MARKER comments link tests to phase docs
- `pytest.ini`: `asyncio_mode = auto`, 24 custom markers

### 1.2 Frontend E2E (Exists but Thin)

**23 Playwright specs** in `client/e2e/`:
```
cut_nle_interactions_smoke.spec.cjs
cut_playback_reliability_smoke.spec.cjs
cut_nle_export_failure_smoke.spec.cjs
cut_berlin_music_markers_smoke.spec.cjs
cut_scene_graph_node_click_smoke.spec.cjs
cut_scene_graph_edge_filter_minicard_smoke.spec.cjs
cut_debug_timeline_surface_smoke.spec.cjs
cut_debug_sync_actions_smoke.spec.cjs
cut_debug_worker_outputs_smoke.spec.cjs
cut_debug_marker_actions_smoke.spec.cjs
cut_debug_inspector_questions_smoke.spec.cjs
cut_debug_cam_ready_smoke.spec.cjs
cut_debug_storyboard_strip_smoke.spec.cjs
cut_debug_worker_actions_smoke.spec.cjs
cut_debug_worker_queue_smoke.spec.cjs
cut_debug_scene_graph_surface_smoke.spec.cjs
cut_debug_sync_hints_smoke.spec.cjs
cut_berlin_fixture_smoke.spec.cjs
cut_berlin_music_acceptance.spec.cjs
cut_scene_graph_loaded_review.spec.cjs
... (3 more)
```

**Gaps:** No component-level tests (`.test.tsx`/`.spec.tsx`). No systematic regression suite. Smoke tests cover debug views, not NLE editing workflows.

### 1.3 Test Selectors Available

**data-testid attributes already in components:**

| Selector | Component | Usage |
|----------|-----------|-------|
| `cut-timeline-track-view` | TimelineTrackView | Main timeline container |
| `cut-timeline-ruler` | TimelineTrackView | Time ruler |
| `cut-timeline-lane-${id}` | TimelineTrackView | Per-lane (dynamic) |
| `cut-timeline-clip-${id}` | TimelineTrackView | Per-clip (dynamic) |
| `cut-marker-draft` | TimelineTrackView | Marker creation draft |
| `cut-marker-draft-create` | TimelineTrackView | Create marker button |
| `cut-clip-context-menu` | TimelineTrackView | Right-click menu |
| `cut-transport-bar` | TransportBar | Transport controls (deprecated) |
| `cut-undo-button` | TransportBar | Undo action |
| `cut-redo-button` | TransportBar | Redo action |
| `cut-scene-detect-button` | TransportBar | Scene detect trigger |
| `cut-undo-toast` | TransportBar | Undo notification |
| `timeline-tab-bar` | TimelineTabBar | Multi-timeline tabs |

**Missing:** No `aria-label` attributes. No testids on monitors, panels, modals, dockview tabs. **Stream agents must add testids as they build features.**

---

## 2. Tool Capabilities: Chrome DevTools MCP

### 2.1 Available Actions (29 tools)

| Category | Tools | E2E Relevance |
|----------|-------|---------------|
| **Input** | `click`, `fill`, `fill_form`, `type_text`, `hover`, `drag`, `press_key`, `handle_dialog`, `upload_file` | Timeline clip drag, hotkey simulation, export dialog form fill, media import |
| **Navigation** | `navigate_page`, `new_page`, `select_page`, `close_page`, `list_pages`, `wait_for` | App load, route navigation, async operation wait |
| **DOM/Debug** | `take_screenshot`, `take_snapshot`, `evaluate_script`, `list_console_messages`, `get_console_message`, `lighthouse_audit` | Visual regression, Zustand state inspection, error detection |
| **Network** | `list_network_requests`, `get_network_request` | API call verification, render job polling |
| **Performance** | `performance_start_trace`, `performance_stop_trace`, `performance_analyze_insight`, `take_memory_snapshot` | Timeline scroll perf, memory leak detection |
| **Emulation** | `emulate`, `resize_page` | Responsive layout, viewport size testing |

### 2.2 Key Capabilities for CUT

```
✅ click — select clips, switch panels, press buttons
✅ press_key — hotkey testing (Space, JKL, ⌘K, I/O, M/N/F)
✅ drag — clip move, trim handles, panel resize
✅ take_screenshot — visual regression after each operation
✅ evaluate_script — read Zustand store state directly:
   window.__ZUSTAND_STORE__.getState().currentTime
   window.__ZUSTAND_STORE__.getState().selectedClipIds
✅ wait_for — async renders, export jobs, scene detection
✅ list_console_messages — catch React errors, warnings
✅ take_snapshot — DOM structure for selector verification
```

### 2.3 Setup

```bash
# Chrome with debug port (persistent profile for auth)
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.chrome-debug-profile"

# MCP registration
claude mcp add --transport stdio chrome-devtools -- \
  npx -y chrome-devtools-mcp@latest --browserUrl=http://127.0.0.1:9222
```

---

## 3. E2E Test Architecture

### 3.1 Three-Layer Testing Pyramid

```
                    ╱╲
                   ╱  ╲
                  ╱ E2E╲         ← Chrome DevTools MCP (QA-agent)
                 ╱──────╲          Critical user flows, visual regression
                ╱        ╲         ~20 scenarios, run after each merge
               ╱Integration╲    ← Playwright (stream agents)
              ╱──────────────╲     Per-feature specs, data-testid based
             ╱                ╲    ~50 specs, run on feature branch
            ╱   Backend Unit   ╲ ← pytest (existing, 388 tests)
           ╱────────────────────╲  API + service + algorithm
          ╱                      ╲ Run on every commit
         ╱────────────────────────╲
```

### 3.2 State Inspection Strategy

**Problem:** E2E tests need to verify internal state (Zustand), not just DOM.

**Solution:** Expose store getter on `window` in dev mode:

```typescript
// In CutStandalone.tsx or app entry, dev-only:
if (process.env.NODE_ENV === 'development') {
  (window as any).__CUT_STORE__ = useCutEditorStore;
  (window as any).__SYNC_STORE__ = usePanelSyncStore;
  (window as any).__DOCK_STORE__ = useDockviewStore;
}
```

**Usage from Chrome DevTools MCP:**
```
evaluate_script("window.__CUT_STORE__.getState().currentTime")
evaluate_script("window.__CUT_STORE__.getState().selectedClipIds")
evaluate_script("window.__CUT_STORE__.getState().timelines.get('tl_cut-00').lanes.length")
```

### 3.3 Test Data Strategy

| Approach | When | How |
|----------|------|-----|
| **Fixture project** | Full E2E flows | Pre-built project with 3 scenes, 6 clips, 2 timelines. Load via `/cut/bootstrap-async` |
| **Empty project** | Panel/layout tests | Fresh bootstrap, verify empty state |
| **Berlin fixture** | Music/sync tests | Existing `cut_berlin_*` fixture data |
| **Store injection** | Isolated component tests | `evaluate_script` to set specific store state |

### 3.4 Selector Strategy

**Priority order for element targeting:**

1. `data-testid="cut-*"` — preferred, explicit, stable
2. `[role="..."]` + aria attributes — accessible, semantic
3. CSS class `.dv-*` — dockview panels (framework-specific but stable)
4. DOM structure — last resort, fragile

**Required testid additions (stream agents must add):**

| Component | Needed testid | Stream |
|-----------|---------------|--------|
| VideoPreview (source) | `cut-source-monitor` | A |
| VideoPreview (program) | `cut-program-monitor` | A |
| MonitorTransport | `cut-transport-source`, `cut-transport-program` | A |
| ExportDialog | `cut-export-dialog`, `cut-export-submit` | B |
| AudioMixer | `cut-audio-mixer` | B |
| DockviewLayout | `cut-dockview-root` | C |
| HotkeyEditor | `cut-hotkey-editor` | C |
| WorkspacePresets | `cut-workspace-presets` | C |
| ProjectSettings | `cut-project-settings` | A |
| SaveIndicator | `cut-save-indicator` | A |
| Each dockview panel | `cut-panel-{name}` | C |

---

## 4. Critical E2E Scenarios

### 4.1 Tier 1 — MVP Gate (Must Pass Before Ship)

| # | Scenario | Steps | Verify | Stream |
|---|----------|-------|--------|--------|
| E1 | **Project Bootstrap** | Navigate → import media → wait for bootstrap job | Timeline has lanes + clips; DAG has nodes; Source monitor shows first clip | A |
| E2 | **Timeline Playback** | Click play (Space) → wait 3s → pause | `currentTime` advanced; Program Monitor frame changed; transport shows timecode | A |
| E3 | **JKL Shuttle** | Press L (play) → L again (2x) → K (stop) → J (reverse) | Speed progression 1→2; stop; reverse plays backward | A |
| E4 | **Split at Playhead** | Seek to 5s → ⌘K | Clip at playhead split into two; clip count +1; split point at 5s | A |
| E5 | **Save & Reload** | ⌘S → wait for save indicator → reload page → verify state | All clips, markers, zoom, playhead position restored. No data loss | A |
| E6 | **Export Master** | Open ExportDialog → select H.264/1080p → click Export → wait | Render job completes; file exists; no console errors | B |
| E7 | **Hotkey Preset Switch** | Open HotkeyEditor → switch Premiere→FCP7 → press B | FCP7 maps B to Razor tool; Premiere maps B differently; verify tool state changes | C |
| E8 | **Panel Docking** | Drag panel to new zone → verify layout → switch workspace preset → verify restore | Panel moves; preset saves; restore returns to original layout | C |

### 4.2 Tier 2 — Core Editing (Run After Each Merge)

| # | Scenario | Steps | Verify |
|---|----------|-------|--------|
| E9 | **Insert/Overwrite** | Mark I/O on source clip → press , (insert) | Clip inserted at playhead; downstream clips rippled |
| E10 | **Ripple Delete** | Select clip → ⌥Delete | Clip removed; gap closed; downstream clips shifted left |
| E11 | **Multi-Select** | ⌘+click 3 clips → Delete | All 3 removed; `selectedClipIds.length === 0` |
| E12 | **Undo/Redo Chain** | Split → Delete → ⌘Z → ⌘Z → ⌘⇧Z | State reverts step by step; redo re-applies |
| E13 | **Source/Program Split** | Click DAG node → verify Source shows clip; click timeline → verify Program shows timeline | Two monitors show different feeds |
| E14 | **Panel Focus** | Click Source → press I → verify sourceMarkIn set; click Program → press I → verify sequenceMarkIn set | Marks are panel-scoped |
| E15 | **Track Lock/Mute/Solo** | Click lock icon on V1 → try to edit clip on V1 | Edit rejected; locked track prevents modifications |
| E16 | **Navigate Edit Points** | Press ↓ (next edit) → ↓ → ↑ (prev edit) | Playhead jumps to clip boundaries |
| E17 | **Context Menu** | Right-click clip → select "Split" | Context menu appears with options; split executes |
| E18 | **Zoom & Scroll** | Scroll zoom to 200% → pan left → verify clips still visible | Zoom changes; scroll position preserved; clips rendered correctly |

### 4.3 Tier 3 — Media Pipeline (Run After Stream B Merges)

| # | Scenario | Steps | Verify |
|---|----------|-------|--------|
| E19 | **Codec Detection** | Import ProRes + H.264 + DNxHD files | Each file shows correct codec info in ClipInspector |
| E20 | **Export Formats** | Export as XML → Export as FCPXML → Export as EDL | All 3 files generated; valid format headers |
| E21 | **Social Presets** | Export → Publish tab → select YouTube preset | Resolution auto-set to 1080p; codec to H.264; aspect 16:9 |
| E22 | **Audio Waveforms** | Import audio file → verify waveform on timeline clip | WaveformCanvas renders; amplitude data visible |
| E23 | **Sequence Settings** | Open SequenceSettings → change to 23.976fps → close | Store updated; timeline ruler reflects new fps |

### 4.4 Tier 4 — Multi-Timeline & Advanced (Run After Phase 198)

| # | Scenario | Steps | Verify |
|---|----------|-------|--------|
| E24 | **Create Timeline Version** | Click [+] tab → name "cut-02" | New tab appears; empty timeline; previous tab intact |
| E25 | **Switch Active Timeline** | Click tab cut-00 → click tab cut-01 | Program Monitor switches feed; playhead independent |
| E26 | **Close Active Timeline** | Close active tab → verify fallback | Most recently focused tab becomes active; no crash |
| E27 | **Auto-Montage** | Click AutoMontage → select "Favorites" → wait | NEW timeline created (cut-NN); excludes negative markers; uses favorites |
| E28 | **Marker Projection** | Add Favorite marker on source clip → check both timelines | Marker appears on ALL timelines containing that clip |

---

## 5. Regression Suite Design

### 5.1 Suite Tiers & Triggers

| Suite | Scenarios | Trigger | Duration Target | Runner |
|-------|-----------|---------|-----------------|--------|
| **Smoke** | E1, E2, E5, E6 | Every merge to main | < 2 min | QA-agent |
| **Core** | E1–E18 | After Stream A/C merges | < 8 min | QA-agent |
| **Full** | E1–E28 | Before release / weekly | < 15 min | QA-agent |
| **Visual** | Screenshots of all panels | After CSS/layout changes | < 5 min | QA-agent |

### 5.2 Regression Run Protocol

```
1. QA-agent receives trigger (merge event or manual)
2. navigate_page → http://localhost:3001/cut
3. wait_for → [data-testid="cut-timeline-track-view"] visible
4. take_screenshot → "baseline_load.png"
5. Execute scenario sequence (Smoke/Core/Full)
6. After each scenario:
   a. take_screenshot → "{scenario_id}_{step}.png"
   b. list_console_messages → check for errors/warnings
   c. evaluate_script → verify store state assertions
7. Generate report: PASS/FAIL per scenario + screenshots
8. If FAIL: capture DOM snapshot + console + network log
```

### 5.3 Failure Triage

| Signal | Action |
|--------|--------|
| Console error (React) | Flag to stream owner by component |
| API 500 | Flag to Stream B (backend) |
| Visual diff > threshold | Flag to Stream C (layout/UX) |
| Store state mismatch | Flag to Stream A (wiring) |
| Timeout (no response) | Check if dev server running; retry once |

---

## 6. Architectural Contracts — Automated Verification

These are invariants that E2E tests must enforce. Violation = test MUST fail.

### 6.1 Data Integrity

| Contract | Verification Method |
|----------|-------------------|
| **No Set<> in serializable state** | `evaluate_script`: check `JSON.parse(JSON.stringify(store))` round-trips losslessly |
| **Unified marker pool** | `evaluate_script`: `store.markers` is single array; no per-timeline copies |
| **Active timeline fallback** | Close all tabs → app doesn't crash; Program Monitor shows black |
| **Timeline = path through DAG** | Each `ClipUsageNode` references valid `MediaNode` in DAG |

### 6.2 Interaction Contracts

| Contract | Verification Method |
|----------|-------------------|
| **Hotkeys panel-scoped** | Focus Source → I sets sourceMarkIn; Focus Program → I sets sequenceMarkIn |
| **JKL progressive speed** | L×1=1x, L×2=2x, L×3=4x, K=stop |
| **Source ≠ Program** | After any action, Source and Program monitor never show same feed |
| **Auto-montage creates NEW timeline** | Count timelines before/after; new ID; old timelines unchanged |
| **Undo is atomic** | ⌘Z after compound op reverts entire op, not partial |

### 6.3 Layout Contracts

| Contract | Verification Method |
|----------|-------------------|
| **Dockview persistence** | Save layout → reload → `evaluate_script` dockview API → same panel config |
| **Workspace preset restore** | Apply "editing" preset → switch to "color" → switch back → panels match original |
| **Panel focus visual** | Click panel → screenshot → focused panel has border (#4A9EFF) |

---

## 7. QA-Agent Recommendation

### 7.1 Architecture: Dedicated QA-Agent (OPUS-D)

```
                 ┌──────────────────┐
                 │  Architect-Cmd   │
                 │  (merge trigger) │
                 └────────┬─────────┘
                          │ "run regression"
                          ▼
                 ┌──────────────────┐
                 │    OPUS-D        │
                 │   QA-Agent       │
                 │                  │
                 │ Tools:           │
                 │ • Chrome MCP     │
                 │ • evaluate_script│
                 │ • screenshot     │
                 │ • press_key      │
                 │ • click/drag     │
                 │ • wait_for       │
                 └────────┬─────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
         ┌─────────┐ ┌─────────┐ ┌─────────┐
         │ Stream A │ │ Stream B │ │ Stream C │
         │ (engine) │ │ (media)  │ │  (UX)    │
         │          │ │          │ │          │
         │ Owns:    │ │ Owns:    │ │ Owns:    │
         │ Playwright│ │ Playwright│ │ Playwright│
         │ per-feat │ │ per-feat │ │ per-feat │
         └─────────┘ └─────────┘ └─────────┘
```

### 7.2 Responsibility Split

| Responsibility | Owner | Tool |
|---------------|-------|------|
| Write feature Playwright specs | Stream agent (A/B/C) | Playwright |
| Add `data-testid` to new components | Stream agent (A/B/C) | Code |
| Run regression after merge | QA-agent (OPUS-D) | Chrome DevTools MCP |
| Visual regression screenshots | QA-agent (OPUS-D) | Chrome DevTools MCP |
| Triage failures → assign to stream | QA-agent (OPUS-D) | Task board |
| Store state invariant checks | QA-agent (OPUS-D) | evaluate_script |
| Performance profiling | QA-agent (OPUS-D) | performance_* tools |

### 7.3 Why Dedicated QA-Agent (Not Distributed)

| Factor | Dedicated QA-agent | Distributed (per-stream) |
|--------|-------------------|--------------------------|
| Cross-stream regressions | ✅ Catches interactions | ❌ Each stream blind to others |
| Consistent test quality | ✅ One standard | ❌ Three different approaches |
| Merge-point validation | ✅ Runs full suite at merge | ❌ Each stream tests own code |
| Context overhead | ✅ Specialized, focused | ❌ Distracts from feature work |
| Visual regression | ✅ Centralized baseline | ❌ Who owns the baseline? |

### 7.4 QA-Agent Task Protocol

```
1. Claim task from task board (phase_type: test)
2. Start Chrome in debug mode
3. Navigate to CUT app
4. Execute regression suite (Smoke/Core/Full based on trigger)
5. For each scenario:
   a. Setup: navigate, load fixture, set store state
   b. Act: click, press_key, drag (simulating user)
   c. Assert: evaluate_script for state, screenshot for visual
   d. Teardown: reload page (clean state)
6. Generate report (markdown with embedded screenshots)
7. If failures: create bug tasks on task board, assign to stream owner
8. Complete task with result summary
```

---

## 8. Required Infrastructure (Pre-Requisites)

Before QA-agent can run, stream agents must complete:

| Item | Owner | Priority | Status |
|------|-------|----------|--------|
| Expose Zustand stores on `window.__CUT_STORE__` (dev mode) | Stream A | 1-CRITICAL | NOT DONE |
| Add `data-testid` to monitors, panels, modals (see §3.4 table) | All streams | 1-CRITICAL | PARTIAL (13 exist) |
| Chrome DevTools MCP installed and configured | DevOps/Setup | 1-CRITICAL | NOT DONE |
| Fixture project data (3 scenes, 6 clips, 2 timelines) | Stream A | 2-HIGH | Partial (Berlin fixture exists) |
| Dev server stable on `localhost:3001` with hot reload | All | 1-CRITICAL | DONE |
| `data-testid` convention documented in CLAUDE.md or CUT_UNIFIED_VISION.md | Architect | 2-HIGH | NOT DONE |

---

## 9. Testid Convention

All CUT components MUST follow this naming:

```
data-testid="cut-{component}-{element}"

Examples:
  cut-timeline-track-view       — main timeline container
  cut-timeline-clip-{id}        — individual clip (dynamic)
  cut-source-monitor            — source video preview
  cut-program-monitor           — program video preview
  cut-export-dialog             — export modal
  cut-export-submit             — export submit button
  cut-panel-{name}              — dockview panel wrapper
  cut-hotkey-editor             — hotkey rebinding UI
  cut-save-indicator            — save status display
  cut-transport-source          — source monitor transport
  cut-transport-program         — program monitor transport
  cut-workspace-preset-{name}   — workspace preset button
  cut-context-menu-{action}     — context menu item
  cut-track-header-{lane_id}    — track header (lock/mute/solo)
```

**Rule:** Every interactive element that a user clicks, types into, or drags MUST have a `data-testid`. No exceptions for NLE-critical components.

---

## 10. Component Coverage Map

| Component (40 total) | LOC | Backend Tests | Playwright Specs | E2E Scenarios | Gap |
|----------------------|-----|---------------|-----------------|---------------|-----|
| TimelineTrackView | 1802 | ✅ (edit ops, undo) | ✅ (surface smoke) | E2–E4, E9–E12, E16–E18 | Need testids for track headers |
| VideoPreview | 376 | ✅ (player lab) | ✅ (playback smoke) | E2, E3, E13 | Need source/program split testid |
| ExportDialog | 616 | ✅ (export endpoints) | ✅ (export failure) | E6, E20, E21 | Need form field testids |
| ProjectPanel | 703 | ✅ (bootstrap, store) | — | E1 | Need import zone testid |
| DockviewLayout | 220 | — | — | E8 | Need panel zone testids |
| HotkeyEditor | 463 | — | — | E7 | Need action row testids |
| MonitorTransport | 202 | — | — | E2, E3 | Need feed-specific testids |
| ScriptPanel | 225 | ✅ (script parse) | — | E13 | Need chunk testids |
| DAGProjectPanel | 378 | ✅ (scene graph) | ✅ (node click, edge filter) | E13 | Need node testids |
| HistoryPanel | 225 | ✅ (undo/redo) | — | E12 | Need entry testids |
| AutoMontageMenu | 280 | ✅ (montage ranker) | ✅ (music acceptance) | E27 | Need mode button testids |
| ClipInspector | 268 | — | ✅ (inspector) | E19 | Need field testids |
| BPMTrack | 320 | — | — | — | Canvas — no testids needed |
| StorySpace3D | 482 | — | — | — | Three.js — screenshot only |
| ProjectSettings | 293 | — | — | E23 | Need field testids |
| SaveIndicator | 56 | ✅ (save) | — | E5 | Already small, need 1 testid |
| AudioLevelMeter | 209 | — | — | — | Canvas — visual only |
| TimelineTabBar | 162 | — | — | E24–E26 | Has testid |
| WorkspacePresets | 94 | — | — | E8 | Need preset button testids |
| CamelotWheel | 284 | — | — | — | SVG — screenshot only |
| PulseInspector | 329 | — | — | — | Read-only — low priority |
| Panel wrappers (10) | ~220 | — | — | E8 | Need container testids |

---

## 11. Risk Matrix

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Stream agents don't add testids | E2E tests can't find elements | HIGH | Add testid requirement to ROADMAP merge checklist |
| Chrome DevTools MCP flaky on macOS | False failures | MEDIUM | Retry once; fall back to Playwright |
| Store shape changes break evaluate_script | State assertions fail | MEDIUM | Version store access helpers; QA-agent reads types |
| 3 streams merge simultaneously | Regression conflicts | HIGH | QA-agent runs after EACH merge, not batched |
| Dockview DOM structure changes | Selectors break | LOW | Use `data-testid` over `.dv-*` classes |
| Timeline canvas rendering | Can't click pixel-precise | MEDIUM | Use store injection + evaluate_script for state, screenshot for visual |

---

## 12. Implementation Roadmap

### Phase 1: Foundation (Before Next Merge)
- [ ] Stream A: Expose stores on `window.__CUT_STORE__` (dev mode only)
- [ ] All streams: Add `data-testid` to new components (see §3.4)
- [ ] Setup: Install Chrome DevTools MCP

### Phase 2: Smoke Suite (After Merge Point 1)
- [ ] QA-agent: Implement E1 (bootstrap), E2 (playback), E5 (save/reload)
- [ ] QA-agent: Screenshot baseline for all panels

### Phase 3: Core Suite (After Merge Point 2)
- [ ] QA-agent: Implement E3–E4, E7–E18
- [ ] Stream agents: Write Playwright specs for their features

### Phase 4: Full Suite (After Merge Point 4 — MVP Gate)
- [ ] QA-agent: Implement E19–E28
- [ ] QA-agent: Performance profiling (timeline scroll, 100+ clips)
- [ ] Visual regression baseline established

---

## Appendix A: Component Hierarchy (Test Navigation)

```
CutEditorLayoutV2                          ← data-testid="cut-editor-root"
├── DockviewLayout                         ← data-testid="cut-dockview-root"
│   ├── TimelinePanel
│   │   ├── TimelineTrackView              ← data-testid="cut-timeline-track-view" ✅
│   │   │   ├── Ruler                      ← data-testid="cut-timeline-ruler" ✅
│   │   │   ├── Lane[]                     ← data-testid="cut-timeline-lane-{id}" ✅
│   │   │   │   └── Clip[]                 ← data-testid="cut-timeline-clip-{id}" ✅
│   │   │   └── ContextMenu                ← data-testid="cut-clip-context-menu" ✅
│   │   ├── TimelineToolbar
│   │   └── BPMTrack
│   ├── SourceMonitorPanel
│   │   ├── VideoPreview                   ← data-testid="cut-source-monitor" ⚠️ NEEDED
│   │   └── MonitorTransport               ← data-testid="cut-transport-source" ⚠️ NEEDED
│   ├── ProgramMonitorPanel
│   │   ├── VideoPreview                   ← data-testid="cut-program-monitor" ⚠️ NEEDED
│   │   └── MonitorTransport               ← data-testid="cut-transport-program" ⚠️ NEEDED
│   ├── ProjectPanelDock → ProjectPanel    ← data-testid="cut-panel-project" ⚠️ NEEDED
│   ├── ScriptPanelDock → ScriptPanel      ← data-testid="cut-panel-script" ⚠️ NEEDED
│   ├── GraphPanelDock → DAGProjectPanel   ← data-testid="cut-panel-graph" ⚠️ NEEDED
│   ├── InspectorPanelDock → PulseInspector
│   ├── ClipPanelDock → ClipInspector
│   ├── StorySpacePanelDock → StorySpace3D
│   └── HistoryPanelDock → HistoryPanel
├── ProjectSettings (modal)                ← data-testid="cut-project-settings" ⚠️ NEEDED
├── ExportDialog (modal)                   ← data-testid="cut-export-dialog" ⚠️ NEEDED
└── SaveIndicator                          ← data-testid="cut-save-indicator" ⚠️ NEEDED

✅ = exists    ⚠️ = must be added by stream agent
```

---

## Appendix B: Store State Assertions (evaluate_script Templates)

```javascript
// Playback state
window.__CUT_STORE__.getState().isPlaying            // boolean
window.__CUT_STORE__.getState().currentTime           // number (seconds)
window.__CUT_STORE__.getState().playbackRate           // 1, 2, 4, 8

// Selection
window.__CUT_STORE__.getState().selectedClipIds        // string[]
window.__CUT_STORE__.getState().selectedClipIds.length  // number

// Timeline
window.__CUT_STORE__.getState().lanes.length           // number of lanes
window.__CUT_STORE__.getState().lanes[0].clips.length  // clips in lane

// Marks
window.__CUT_STORE__.getState().sourceMarkIn           // number | null
window.__CUT_STORE__.getState().sequenceMarkIn         // number | null

// Focus
window.__CUT_STORE__.getState().focusedPanel           // string | null

// Sync
window.__SYNC_STORE__.getState().activeSceneId         // string | null
window.__SYNC_STORE__.getState().lastSyncSource        // 'script' | 'dag' | ...

// Dockview
window.__DOCK_STORE__.getState().getSavedPresets()      // string[]
```

---

*End of RECON. This document is the basis for CUT-QA task creation and QA-agent implementation.*
