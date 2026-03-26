# RECON: VETKA CUT Manual vs Test Coverage — Gap Analysis
**Date:** 2026-03-26
**Author:** Epsilon (QA Engineer 2)
**Task:** tb_1774498120_1
**Type:** Research (gap analysis)
**Status:** COMPLETE

---

## 0. Executive Summary

Cross-referenced VETKA_CUT_MANUAL.md (9 sections, 78% FCP7 compliance) against full test inventory (50+ pytest files, 43 Playwright E2E specs). Found **15 critical features with ZERO E2E coverage** despite being documented as IMPLEMENTED in the manual.

**Test inventory:** ~600 pytest tests (CUT domain), 43 E2E specs (~200 test cases)
**Coverage pattern:** Backend/store contracts are excellent (90%+). E2E coverage drops sharply for workflow-level features.

---

## 1. Top 15 Gaps — Zero E2E Coverage

| Rank | Manual § | Feature | pytest | E2E | Priority |
|------|----------|---------|--------|-----|----------|
| 1 | §2.3 | Media Import (Cmd+I, drag-drop) | test_import_media_flow.py | NONE | CRITICAL |
| 2 | §2.2 | Save/Autosave (Cmd+S, status bar) | test_cut_save_autosave_contract.py | NONE | CRITICAL |
| 3 | §2.1 | Welcome Screen / Project Open | test_cut_bootstrap_pipeline.py | NONE | HIGH |
| 4 | §2.7 | Sequence Settings Dialog | test_cut_wiring_verification.py (endpoint only) | NONE | HIGH |
| 5 | §2.8 | Multi-Timeline (create/switch/delete) | test_cut_multi_timeline_store.py | NONE | HIGH |
| 6 | §3.9 | Copy/Paste/Clipboard (Cmd+C/X/V) | test_cut_editing_operations.py | NONE | HIGH |
| 7 | §3.8 | Lift/Extract (; and ' hotkeys) | test_cut_editing_operations.py | NONE | HIGH |
| 8 | §5.12 | L-cut/J-cut (Alt+E / Alt+Shift+E) | test_fcp7_partial_contracts.py | NONE | HIGH |
| 9 | §6.3 | Audio Rubber Band (Option+click keyframe) | test_audio_rubber_band.py | NONE | HIGH |
| 10 | §6.10 | PULSE Analysis Trigger (Cmd+Shift+P) | test_cut_scope_ws.py (partial) | NONE | HIGH |
| 11 | §5.16 | BPM Markers on Timeline | NONE | NONE | HIGH |
| 12 | §7.6 | LUT Browser Panel | test_cut_color_pipeline.py | NONE | HIGH |
| 13 | §7.3 | Motion Controls Panel | test_cut_motion_effects.py | NONE | HIGH |
| 14 | §9.6 | Scene Detection (Cmd+D) | test_cut_wiring_verification.py (endpoint only) | NONE | HIGH |
| 15 | §9.3 | Screenplay/Logger Panel | test_screenplay_timing.py | NONE | HIGH |

---

## 2. Additional Gaps (Lower Priority)

| Manual § | Feature | Status | Note |
|----------|---------|--------|------|
| §1.7 | Backtick (`) maximize/restore panel | NO TESTS AT ALL | Simple hotkey, easy to add |
| §3.3 | Overwrite Edit (.) hotkey E2E | pytest only | WF3 partial in workflow spec |
| §3.4 | Replace Edit (F11) E2E | pytest only | Not wired yet (PLANNED) |
| §3.5 | Fit to Fill (Shift+F11) E2E | pytest only | PARTIAL implementation |
| §4.8 | Snap visual indicator (yellow line) | Known GAP in pytest | No visual regression test |
| §5.11 | Close Gap (Alt+Backspace) E2E | pytest only | |
| §7.5 | Color Correction wheels/curves E2E | CC1-3 partial | Wheel drag interaction untested |
| §7.7 | Video Scopes mode switching E2E | CC2-3 partial | Mode toggle not directly tested |
| §8.1 | Editorial export (FCPXML/EDL/OTIO) E2E | EXP1 tabs only | No actual export trigger test |
| §9.8 | Clip Context Menu full coverage | Basic smoke only | Speed/Duration, Properties untested |

---

## 3. Coverage by Manual Section

| Section | Title | pytest Files | E2E Specs | Coverage Grade |
|---------|-------|-------------|-----------|----------------|
| §1 | Getting Started | 5 (hotkeys, wiring, workspace) | 4 (layout, focus, hotkeys, edge cases) | B+ |
| §2 | Project & Media | 5 (bootstrap, codec, proxy, save, import) | 0 dedicated | D — zero E2E |
| §3 | Editing | 5 (editing ops, 3-point, effects) | 3 (workflow, undo, precision) | B |
| §4 | Trimming | 3 (trim ops, trim tools, JKL) | 3 (transitions/trim, timecode/trim, precision) | B |
| §5 | Timeline | 3 (multi-timeline, track header, timecode) | 3 (deep compliance, menus, interactions) | B- |
| §6 | Audio | 4 (audio engine, transitions, mixer, rubber band) | 1 (audio/effects/export) | C+ |
| §7 | Effects & Color | 6 (effects, motion, render, color, keyframes) | 4 (transitions/speed, keyframes, coverage sweep, context/effects) | B |
| §8 | Export & Delivery | 3 (export, render cancel, render speed) | 1 (export failure smoke) | C |
| §9 | Advanced | 3 (multicam, screenplay, PULSE) | 3 (multicam, PULSE, scene graph) | C+ |

---

## 4. What This Task Covers

Epsilon implements contract tests + Playwright E2E for gaps #2, #5, #6, #7:

| Gap | Deliverable |
|-----|-------------|
| §2.2 Save/Autosave | `cut_save_autosave_tdd.spec.cjs` — store FSM, Cmd+S mock, dirty tracking |
| §2.8 Multi-Timeline | `cut_multi_timeline_tdd.spec.cjs` — create/switch/remove/fork/snapshot |
| §3.9 Clipboard | `cut_clipboard_lift_extract_tdd.spec.cjs` — copy/cut/paste/paste-insert |
| §3.8 Lift/Extract | Same spec — lift (;) leaves gap, extract (') ripples |

Plus pytest contracts in `test_fcp7_partial_contracts.py` for all 4 features.

---

## 5. Recommendations for Commander

1. **Gamma should add data-testid** to: SaveIndicator, AutoMontagePanel buttons, TimelineInstancePanel tab rows, PulseInspector
2. **Alpha should prioritize** Media Import E2E (§2.3) — the #1 gap, user's first interaction
3. **Delta should guard** Editorial Export (§8.1) — OTIO/FCPXML are key differentiators
4. **Zeta should investigate** BPM Marker rendering test (§5.16) — PULSE output visibility

---

*Generated by Epsilon (QA Engineer 2) — Phase 198*
