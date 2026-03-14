# Phase 170 CUT Wave 13 Sync Hints

## Goal
Continue CUT browser-only roadmap coverage in safe-zone, focusing on the `Sync Hints` card in the debug shell.

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

## Part K — Sync Hints lane

### K1
Create `client/e2e/cut_debug_sync_hints_smoke.spec.cjs`.
- Toggle into debug shell.
- Mock timecode sync, audio sync, and sync_surface items.
- Verify counts and representative card rows.
- Refresh once and verify changed counts or methods render.

### K2
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_SYNC_HINTS_RECON_2026-03-12.md`.
- Stable selectors and visible anchors for Sync Hints.
- Expected refresh behavior.

### K3
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_SYNC_HINTS_MOCK_MATRIX_2026-03-12.md`.
- Minimum project-state shape for timecode/audio/sync_surface items.
- Required refresh behavior.
