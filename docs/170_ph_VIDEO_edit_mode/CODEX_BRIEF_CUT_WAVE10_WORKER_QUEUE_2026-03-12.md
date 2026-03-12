# Phase 170 CUT Wave 10 Worker Queue

## Goal
Continue CUT browser-only roadmap coverage in safe-zone, focusing on the debug-shell worker queue card and cancel flow already present in the current tree.

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

## Part H — Worker queue lane

### H1
Create `client/e2e/cut_debug_worker_queue_smoke.spec.cjs`.
- Toggle into debug shell.
- Mock one active job and one recent job in project-state.
- Verify queue card labels, Cancel Job request, and post-cancel refresh.
- Verify `/api/cut/job/{job_id}/cancel` is called and active/recent counts change.

### H2
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_WORKER_QUEUE_RECON_2026-03-12.md`.
- Stable selectors and text anchors for queue card.
- Expected status text for cancel flow.

### H3
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_WORKER_QUEUE_MOCK_MATRIX_2026-03-12.md`.
- Minimum project-state queue shape.
- Required cancel route mock.
- Which routes can remain unmocked.
