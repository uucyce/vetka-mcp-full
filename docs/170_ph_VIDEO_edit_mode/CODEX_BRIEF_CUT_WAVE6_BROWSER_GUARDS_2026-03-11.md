# Phase 170 CUT Wave 6 Browser Guards

## Goal
Add the next browser-only verification layer for CUT without touching shared NLE implementation files. This batch exists to keep parallel agents out of `TimelineTrackView`, `TransportBar`, `CutEditorLayout`, `CutStandalone`, `VideoPreview`, `AudioLevelMeter`, and backend worker code unless a follow-up task explicitly requires it.

## Safe edit zone
- `client/e2e/*.spec.cjs`
- `docs/170_ph_VIDEO_edit_mode/*.md`
- `data/task_board.json`

## Do not touch in Wave 6
- `client/src/components/cut/TimelineTrackView.tsx`
- `client/src/components/cut/TransportBar.tsx`
- `client/src/components/cut/CutEditorLayout.tsx`
- `client/src/CutStandalone.tsx`
- `client/src/components/cut/VideoPreview.tsx`
- `client/src/components/cut/AudioLevelMeter.tsx`
- `src/api/routes/cut_routes.py`
- `src/services/cut_project_store.py`

## Part C — Export guard lane
Focus on failure-path verification for the existing export UI.

### C1
Create `client/e2e/cut_nle_export_failure_smoke.spec.cjs`.
- Open `/cut` with mocked `project-state`.
- Mock both `/api/cut/export/premiere-xml` and `/api/cut/export/fcpxml` as failures.
- Verify request routing still follows the `PPro` / `FCP/DR` toggle.
- Verify the export button enters the red error state and does not crash the page.

### C2
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_EXPORT_FAILURE_SMOKE_RECON_2026-03-11.md`.
- Exact selectors.
- Expected error-state behavior.
- Timing notes around the 3-second reset.

### C3
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_EXPORT_FAILURE_MOCK_MATRIX_2026-03-11.md`.
- Minimum mocked routes.
- Success vs failure payload shape assumptions.
- Notes on what must stay unmocked.

## Part D — Debug shell worker lane
Focus on debug shell coverage only; no backend edits.

### D1
Create `client/e2e/cut_debug_worker_actions_smoke.spec.cjs`.
- Toggle from NLE into debug shell.
- Mock bootstrap and worker/job routes.
- Verify shell buttons trigger expected async endpoints.
- Verify status text transitions are visible and no runtime crash appears.

### D2
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_WORKER_SMOKE_RECON_2026-03-11.md`.
- Toggle path.
- Stable shell selectors.
- Expected worker action labels.

### D3
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_WORKER_MOCK_MATRIX_2026-03-11.md`.
- Route matrix for bootstrap, project-state refresh, worker start, and job polling.

## Suggested split
- Main Codex: Part C.
- Second Codex or GPT-mini: Part D docs first (`D2`, `D3`), then `D1`.

## Acceptance
- Relevant `npx playwright test ...` spec passes.
- No edits outside the safe zone.
- TaskBoard entry gets `result_summary` with exact artifact path.
