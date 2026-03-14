# Phase 170 CUT Wave 7 Sync Actions

## Goal
Keep moving through the CUT roadmap using browser-only verification in the debug shell. This batch stays out of shared implementation files and focuses on sync/timeline actions already exposed by the shell UI.

## Safe edit zone
- `client/e2e/*.spec.cjs`
- `docs/170_ph_VIDEO_edit_mode/*.md`
- `data/task_board.json`

## Do not touch
- `client/src/CutStandalone.tsx`
- `client/src/components/cut/TimelineTrackView.tsx`
- `client/src/components/cut/TransportBar.tsx`
- `client/src/components/cut/CutEditorLayout.tsx`
- backend CUT routes and stores

## Part E — Debug sync-action lane

### E1
Create `client/e2e/cut_debug_sync_actions_smoke.spec.cjs`.
- Toggle into debug shell.
- Mock a hydrated project-state with one selected storyboard item and one `sync_surface` recommendation.
- Verify `Sync Timeline Selection`, `Apply Selected Sync`, and `Apply All Syncs` hit `/api/cut/timeline/apply`.
- Verify status text and sync hints update without runtime crash.

### E2
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_SYNC_ACTIONS_RECON_2026-03-12.md`.
- Stable selectors and text anchors.
- Which selected-shot panel text proves the lane is ready.

### E3
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_SYNC_ACTIONS_MOCK_MATRIX_2026-03-12.md`.
- Minimum `project-state` shape.
- Required `timeline/apply` payload expectations.
- Any optional routes that can stay unmocked.

## Acceptance
- Relevant Playwright spec passes.
- No edits outside the safe zone.
- TaskBoard entries carry exact artifact paths in `result_summary`.
