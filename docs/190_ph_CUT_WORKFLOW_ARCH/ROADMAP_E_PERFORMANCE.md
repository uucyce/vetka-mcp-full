# ROADMAP_E: Performance, Test Depth, Accessibility
**Author:** Epsilon (QA-2) | **Branch:** claude/cut-qa-2
**Date:** 2026-03-23 | **Status:** ACTIVE
**Refs:** FCP7 User Manual, CUT_Interface_Architecture_v1.docx

---

## 0. Current Baseline (2026-03-23)

### TDD Suite Status
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| timecode_trim | 2 | 6 | 0 | 8 |
| fcp7_menus_editing | 15 | 0 | 6 | 21 |
| audio_effects_export | 12 | 0 | 0 | 12 |
| keyframes_gaps | 4 | 0 | 0 | 4 |
| coverage_sweep | 6 | 0 | 0 | 6 |
| workflow_e2e | 2 | 0 | 0 | 2 |
| panel_focus | 6 | 0 | 0 | 6 |
| fcp7_precision_editing | 5 | 0 | 0 | 5 |
| fcp7_deep_compliance | 10 | 0 | 4 | 14 |
| layout_compliance | 13 | 0 | 0 | 13 |
| transitions_speed_trim | 14 | 0 | 0 | 14 |
| **TOTAL** | **89** | **6** | **10** | **105** |

### Known Regressions
- TC1-TC3: TimecodeField seek not firing after fill+Enter (post-merge)
- TRIM1/TRIM2/TRIM4: Expected TDD RED (mouse drag trim not implemented)

### Visual Audit (45 color violations)
- V1/V2: Dockview tab backgrounds navy blue (should be grey)
- V3: Unknown bright blue element rgb(59,130,246)
- V8: "Unsaved" label slightly yellowish

---

## 1. PERFORMANCE BASELINE (Pillar 1)

### E-PERF-1: Page Load Time
**Target:** < 2 seconds cold load, < 500ms hot reload
**Method:**
- Playwright `performance.timing` capture on /cut load
- Measure: navigationStart → DOMContentLoaded → full render
- Track bundle sizes per chunk (vite build --report)
**Spec file:** `e2e/cut_performance_load.spec.cjs`
**Priority:** P2

### E-PERF-2: Timeline Scroll FPS
**Target:** 60fps sustained during horizontal scroll
**Method:**
- Playwright scroll simulation + requestAnimationFrame counter
- 100 clips on timeline, measure frame drops during scroll
- Report: min/avg/max fps, jank count (frames > 16.7ms)
**Spec file:** `e2e/cut_performance_scroll.spec.cjs`
**Priority:** P1

### E-PERF-3: Playback Start Latency
**Target:** < 500ms from Space press to first frame
**Method:**
- Set currentTime, press Space, measure time to isPlaying=true
- With/without waveforms, with/without video decode
**Spec file:** `e2e/cut_performance_playback.spec.cjs`
**Priority:** P2

### E-PERF-4: Bundle Size Audit
**Target:** Main chunk < 500KB gzipped
**Method:**
- `vite build` + analyze output sizes
- Identify lazy-loadable panels (Color, Scopes, LUTs, 3D)
- Check tree-shaking effectiveness (unused dockview features)
**Deliverable:** `docs/RECON_BUNDLE_AUDIT.md`
**Priority:** P3

---

## 2. TEST DEPTH (Pillar 2)

### E-TEST-1: FCP7 Hotkey Coverage
**Source:** FCP7 User Manual shortcuts reference + CUT_HOTKEY_ARCHITECTURE.md
**Target:** 1 test per hotkey binding (both Premiere + FCP7 preset)
**Scope:**
```
Playback:     Space, J, K, L, ←, →, Shift←, Shift→
Marking:      I, O, X, Shift+I, Shift+O, Alt+I, Alt+O, Alt+X
Editing:      V, C, S (snap), N, B, Delete, Alt+Delete
Tools:        A(arrow), B(blade), H(hand), Z(zoom), S(slip), U(slide), R(ripple), N(roll)
Clipboard:    Cmd+Z, Cmd+Shift+Z, Cmd+C, Cmd+V, Cmd+X
Navigation:   Home, End, Up, Down, Cmd+K, Cmd+Shift+K
Panel Focus:  Shift+1..5
Workspace:    Alt+Shift+1..4
View:         Cmd+\, =, -, `(backtick)
```
**Spec file:** `e2e/cut_fcp7_hotkey_coverage_tdd.spec.cjs`
**Estimated:** ~60 specs
**Priority:** P1

### E-TEST-2: Panel Interaction Coverage
**Target:** Every panel has at least 3 interaction tests
**Panels:**
```
Project:     list/grid/DAG modes, search, import trigger
Script:      scene click → playhead, scroll sync
Inspector:   clip select → data update, field editing
Effects:     slider adjustment → store update, reset
Color:       wheel drag, lift/gamma/gain, RGB parade
Mixer:       fader drag, solo/mute, clipping indicator
Scopes:      waveform/vectorscope/histogram modes
Timeline:    clip drag, ruler click, track resize
```
**Spec file:** `e2e/cut_panel_interactions_tdd.spec.cjs`
**Estimated:** ~30 specs
**Priority:** P2

### E-TEST-3: Drag-and-Drop Scenarios
**Target:** All drag interactions tested
```
Timeline:    clip move (same track, cross-track)
Timeline:    clip reorder (swap positions)
Timeline:    media drop from Project Panel
Timeline:    clip edge trim (left/right handles)
Panels:      dockview panel rearrangement
Panels:      tab reorder within group
Markers:     marker drag on timeline
```
**Spec file:** `e2e/cut_drag_drop_tdd.spec.cjs`
**Estimated:** ~15 specs
**Priority:** P2

### E-TEST-4: Undo/Redo Coverage
**Target:** Every destructive operation has undo/redo test
```
Split:       Cmd+K → Cmd+Z (clip unsplits)
Delete:      Delete → Cmd+Z (clip restored)
Ripple Del:  Alt+Delete → Cmd+Z (clip + gap restored)
Trim:        ripple/roll → Cmd+Z (edges restored)
Move:        clip drag → Cmd+Z (original position)
Speed:       speed change → Cmd+Z (original speed)
Effects:     effect apply → Cmd+Z (effect removed)
```
**Spec file:** `e2e/cut_undo_redo_tdd.spec.cjs`
**Estimated:** ~15 specs
**Priority:** P1

---

## 3. QA BACKUP (Pillar 3)

### Review Matrix
| Delta reviews | Epsilon reviews |
|--------------|----------------|
| Alpha (Engine) | Gamma (UX) |
| Beta (Media) | Anyone unreviewed |

### Review Checklist (per PR)
1. Scope: only owned files touched?
2. Monochrome: zero non-grey colors (except markers)?
3. Store API: no breaking changes to shared state?
4. Tests: existing tests still pass?
5. data-testid: present on new interactive elements?
6. Dependencies: merge order correct?

### Visual Audit Cadence
- After every 3+ branch merges to main
- Full panel screenshot + DOM color scan
- Report to Commander

---

## 4. ACCESSIBILITY (Pillar 4)

### E-A11Y-1: Tab Navigation
**Target:** All panels reachable via Tab key
**Method:**
- Tab through entire UI, verify focus ring visible
- Shift+Tab reverses order
- Enter/Space activates focused element
**Spec file:** `e2e/cut_a11y_tab_nav.spec.cjs`
**Priority:** P3

### E-A11Y-2: Screen Reader Labels
**Target:** Every interactive element has aria-label or visible text
**Method:**
- Playwright `page.accessibility.snapshot()` audit
- Flag elements with role but no name
- Flag images without alt text
**Spec file:** `e2e/cut_a11y_labels.spec.cjs`
**Priority:** P3

### E-A11Y-3: High Contrast
**Target:** UI usable with forced-colors media query
**Method:**
- Test with `prefers-contrast: more` emulation
- Verify text meets WCAG AA contrast ratio (4.5:1)
**Priority:** P4

---

## 5. Execution Order

### Wave 1 (immediate)
- [ ] E-TEST-1: FCP7 hotkey coverage (60 specs) — foundation for everything
- [ ] E-TEST-4: Undo/redo coverage (15 specs) — catches regressions early
- [ ] E-PERF-2: Timeline scroll FPS baseline — sets performance bar

### Wave 2 (after Wave 1 green)
- [ ] E-TEST-2: Panel interactions (30 specs)
- [ ] E-PERF-1: Page load time
- [ ] E-PERF-3: Playback latency

### Wave 3 (ongoing)
- [ ] E-TEST-3: Drag-and-drop (15 specs)
- [ ] E-PERF-4: Bundle audit
- [ ] E-A11Y-1: Tab navigation
- [ ] E-A11Y-2: Screen reader labels

### Wave 4 (polish)
- [ ] E-A11Y-3: High contrast
- [ ] Performance regression CI gate

---

## 6. Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| TDD pass rate | 89/105 (85%) | 100/105+ (95%) |
| FCP7 hotkey coverage | ~20 keys tested | 60+ keys |
| Timeline scroll FPS | unmeasured | 60fps sustained |
| Page load time | unmeasured | < 2s cold |
| Playback start | unmeasured | < 500ms |
| Color violations | 45 | 0 (non-marker) |
| a11y audit score | unmeasured | 90%+ |
