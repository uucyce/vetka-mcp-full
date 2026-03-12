# Phase 170 CUT Wave 8 Marker Actions

## Goal
Continue browser-only CUT roadmap coverage in the debug shell, focusing on time-marker actions that already exist in the current tree. Stay in safe-zone only.

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

## Part F — Debug marker-actions lane

### F1
Create `client/e2e/cut_debug_marker_actions_smoke.spec.cjs`.
- Toggle into debug shell.
- Mock one selected storyboard item and time-marker endpoints.
- Verify `Favorite Selected`, `Comment Selected`, `CAM Selected`, and `Show All Markers` / `Show Active Only`.
- Verify marker creation hits `/api/cut/time-markers/apply` and marker lists hydrate after refresh.

### F2
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_MARKER_ACTIONS_RECON_2026-03-12.md`.
- Stable selectors and readiness anchors.
- Expected marker list labels and toggle text.

### F3
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_MARKER_ACTIONS_MOCK_MATRIX_2026-03-12.md`.
- Minimum `project-state` and `time-markers/apply` mock requirements.
- Which routes can stay unmocked.
