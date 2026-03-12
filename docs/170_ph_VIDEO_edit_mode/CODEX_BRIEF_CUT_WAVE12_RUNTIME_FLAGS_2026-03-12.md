# Phase 170 CUT Wave 12 Runtime Flags / Project Overview

## Goal
Continue CUT browser-only roadmap coverage in safe-zone, focusing on Project Overview and Runtime Flags cards in the debug shell.

## Safe edit zone
- `client/e2e/*.spec.cjs`
- `docs/170_ph_VIDEO_edit_mode/*.md`
- `data/task_board.json`

## Do not touch
- `client/src/CutStandalone.tsx`
- `client/src/components/cut/TimelineTrackView.tsx`
- `client/src/components/cut/TransportBar.tsx`
- `client/src/components/cut/CutEditorLayout.tsx`
- backend CUT routes/store

## Part J — Overview / flags lane

### J1
Create `client/e2e/cut_debug_runtime_flags_smoke.spec.cjs`.
- Toggle into debug shell.
- Mock project-state with mixed readiness flags.
- Verify Project Overview text plus Runtime Flags card values.
- Refresh once and verify a changed readiness mix is rendered.

### J2
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_RUNTIME_FLAGS_RECON_2026-03-12.md`.
- Stable selectors and visible text anchors.
- Expected refresh behavior for flags.

### J3
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_RUNTIME_FLAGS_MOCK_MATRIX_2026-03-12.md`.
- Minimum project-state shape for overview + readiness flags.
- Required refresh behavior.
