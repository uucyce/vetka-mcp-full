# Phase 170 CUT Wave 11 Inspector / Questions

## Goal
Continue CUT browser-only roadmap coverage in safe-zone, focusing on the Inspector / Questions card in the debug shell.

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

## Part I — Inspector / Questions lane

### I1
Create `client/e2e/cut_debug_inspector_questions_smoke.spec.cjs`.
- Toggle into debug shell.
- Mock `bootstrap_state.last_stats` with structured fallback question data.
- Verify the Inspector / Questions card renders JSON payload and updates after refresh.

### I2
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_INSPECTOR_QUESTIONS_RECON_2026-03-12.md`.
- Stable selectors and text anchors for the card.
- Expected visible JSON keys.

### I3
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_INSPECTOR_QUESTIONS_MOCK_MATRIX_2026-03-12.md`.
- Minimum `bootstrap_state.last_stats` shape.
- Required project-state mock behavior.
