# PHASE 170 CUT Handoff Status
**Date:** 2026-03-11  
**Status:** hand-off snapshot after stream disconnect  
**Scope:** `VETKA CUT` worker/state/shell sync path

## Why this hand-off exists
The previous implementation stream disconnected after the CUT sync work advanced beyond the last plain-text checkpoint. This document fixes that gap and records the actual repo state so the next engineer starts from the tree, not from stale chat memory.

## Current verified state
1. `energy_pause_v1` is implemented as the first persisted worker-backed slice path.
2. `slice_bundle` is persisted in project state and is already consumed by the CUT shell.
3. `audio_sync_result` is persisted and already visible in the shell as sync hints.
4. `timecode_sync_result` is already implemented in the backend/store/project-state and surfaced in the shell.
5. `sync_surface` already exists as the first unified recommendation layer combining hard-sync outputs.

Verification run on current tree:
1. `pytest -q tests/phase170/test_cut_standalone_shell_contract.py` -> `2 passed, 1 warning`

Markers:
1. `MARKER_170.HANDOFF.CURRENT_TREE_VERIFIED`
2. `MARKER_170.HANDOFF.STREAM_DISCONNECT_RECOVERED`

## What was completed
### Worker + persistence
1. Added worker-backed pause slicing endpoint `POST /api/cut/worker/pause-slice-async` in [cut_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/cut_routes.py:2414).
2. Worker builds persisted `cut_slice_bundle_v1` using silence-aware / signal-proxy baseline logic in [cut_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/cut_routes.py:1848).
3. File-backed storage + validation for `slice_bundle`, `audio_sync_result`, and `timecode_sync_result` exists in [cut_project_store.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/cut_project_store.py:94), [cut_project_store.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/cut_project_store.py:225), and [cut_project_store.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/cut_project_store.py:544).
4. `project-state` now returns `audio_sync_result`, `slice_bundle`, `timecode_sync_result`, and derived `sync_surface` in [cut_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/cut_routes.py:2553).

Markers:
1. `MARKER_170.WORKER.PAUSE_SLICE_V1`
2. `MARKER_170.STORE.SLICE_BUNDLE_PERSISTED`
3. `MARKER_170.STORE.TIMECODE_SYNC_PERSISTED`
4. `MARKER_170.MCP.PROJECT_STATE_SYNC_SURFACE`

### Contracts + docs
1. `cut_slice_bundle_v1` contract was added in [cut_slice_bundle_v1.schema.json](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_slice_bundle_v1.schema.json:1).
2. Roadmap updated with sync hierarchy and `meta_sync` guardrail in [PHASE_170_VETKA_CUT_ROADMAP_RECON_MARKERS_2026-03-09.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/170_ph_VIDEO_edit_mode/PHASE_170_VETKA_CUT_ROADMAP_RECON_MARKERS_2026-03-09.md:75).
3. Architecture updated with `timecode -> waveform -> meta_sync` layering in [PHASE_170_VETKA_CUT_ARCHITECTURE_2026-03-09.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/170_ph_VIDEO_edit_mode/PHASE_170_VETKA_CUT_ARCHITECTURE_2026-03-09.md:78).
4. Slice implementation notes were written in [PHASE_170_P170_7_SLICE_SYNC_METHOD_BAKEOFF_IMPLEMENTATION_2026-03-11.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/170_ph_VIDEO_edit_mode/PHASE_170_P170_7_SLICE_SYNC_METHOD_BAKEOFF_IMPLEMENTATION_2026-03-11.md:1).

Markers:
1. `MARKER_170.CONTRACT.SLICE_BUNDLE_V1`
2. `MARKER_170.ARCH.SYNC_HIERARCHY`
3. `MARKER_170.INTEL.META_SYNC_GUARDRAIL`

### Shell integration
1. CUT shell now prefers `energy_pause_v1` windows, then transcript heuristic, then preview fallback in [CutStandalone.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/CutStandalone.tsx:129).
2. Shell exposes actions for `Build Pause Slices`, `Build Audio Sync`, and `Build Timecode Sync` and hydrates all returned bundles in [CutStandalone.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/CutStandalone.tsx:450).
3. `Selected Shot` and storyboard already show source/hint information for `slice_bundle`, `audio_sync_result`, and `timecode_sync_result` in [CutStandalone.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/CutStandalone.tsx:1058).
4. Shell already includes `sync_surface` and `apply_sync_offset` intent wiring in [CutStandalone.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/CutStandalone.tsx:676), and backend timeline patch handling for that op already exists in [cut_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/cut_routes.py:499).

Markers:
1. `MARKER_170.UI.SLICE_WINDOW_SOURCE_BINDING`
2. `MARKER_170.UI.SYNC_HINTS_VISIBLE`
3. `MARKER_170.UI.SYNC_SURFACE_VISIBLE`
4. `MARKER_170.UI.APPLY_SYNC_OFFSET_INTENT`

### Tests already covering this
1. Worker/store/schema/project-state coverage exists in [test_cut_pause_slice_worker_api.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/phase170/test_cut_pause_slice_worker_api.py:41), [test_cut_project_store.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/phase170/test_cut_project_store.py:100), [test_cut_project_state_api.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/phase170/test_cut_project_state_api.py:97), and [test_cut_contract_schemas.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/phase170/test_cut_contract_schemas.py:5).
2. Shell contract coverage for the CUT route, actions, queue, sync hints, and marker UI exists in [test_cut_standalone_shell_contract.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/phase170/test_cut_standalone_shell_contract.py:18).

Markers:
1. `MARKER_170.TEST.PAUSE_SLICE_WORKER`
2. `MARKER_170.TEST.CUT_PROJECT_STATE`
3. `MARKER_170.TEST.CUT_SHELL_SYNC_BINDING`

## Important correction to the previous chat state
The last plain-text checkpoint said the next step was to "introduce timecode sync contract/result next to audio_sync_result". That is already done in the current repo.

Current tree evidence:
1. `timecode_sync_result_path`, load/save, and validation already exist in [cut_project_store.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/cut_project_store.py:102).
2. `_run_cut_timecode_sync_job` and `POST /api/cut/worker/timecode-sync-async` already exist in [cut_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/cut_routes.py:1988) and [cut_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/cut_routes.py:2466).
3. Shell already reads `timecode_sync_result` and `sync_surface` in [CutStandalone.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/CutStandalone.tsx:452).

Marker:
1. `MARKER_170.HANDOFF.TIMECODE_STEP_ALREADY_DONE`

## What remains to do
### Immediate next slice
1. Add focused tests for `apply_sync_offset` so the existing backend op is covered as a first-class sync mutation path.
2. Bind `audio_sync_result` and `timecode_sync_result` to actual timeline lane decisions and shot-level actions so timeline state reflects recommended alignment, not just shell text.
3. Verify `sync_surface -> apply_sync_offset -> timeline_state` round-trip end to end, including `sync_groups` persistence.

Markers:
1. `MARKER_170.NEXT.APPLY_SYNC_OFFSET_TESTS`
2. `MARKER_170.NEXT.TIMELINE_SYNC_BINDING`
3. `MARKER_170.NEXT.SYNC_ROUNDTRIP_E2E`

### After that
1. Add `meta_sync` as proposal/refinement layer only after hard sync surfaces are stable.
2. Pull sync recommendations into storyboard and selected-shot actions more structurally, not just as hint labels.
3. Revisit media decode quality only if signal-proxy accuracy becomes the limiting factor for pause slices or waveform sync.

Markers:
1. `MARKER_170.NEXT.META_SYNC_PROPOSAL_ONLY`
2. `MARKER_170.NEXT.STORYBOARD_SYNC_ACTIONS`
3. `MARKER_170.NEXT.REAL_AUDIO_DECODE_GATE`

## Recommended hand-off starting point
If another engineer picks this up now, they should start here:
1. Treat `worker -> persisted state -> project-state -> shell` as established and do not rebuild it.
2. Start from tests plus UX binding around the existing backend execution of `apply_sync_offset` and its timeline-state mutation.
3. Keep `meta_sync` strictly secondary to `timecode` and `waveform`.
4. Do not spend time re-adding `timecode_sync`; verify and extend the existing implementation instead.

## Suggested next command set
1. Run `pytest -q tests/phase170/test_cut_project_state_api.py tests/phase170/test_cut_standalone_shell_contract.py`
2. Inspect `timeline/apply` handling in [cut_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/cut_routes.py:2709)
3. Add tests for `apply_sync_offset` mutation and `sync_groups` persistence
4. Add contract tests for `sync_surface` recommendation to timeline mutation round-trip
