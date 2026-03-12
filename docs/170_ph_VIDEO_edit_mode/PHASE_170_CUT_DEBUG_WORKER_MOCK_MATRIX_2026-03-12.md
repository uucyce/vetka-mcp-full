# Phase 170 CUT Debug Worker Mock Matrix

## Goal
Minimum route matrix for a browser smoke that verifies debug-shell bootstrap and async worker actions in CUT.

## Required mocked routes
| Route | Method | Why mocked | Expected request shape | Mock response |
| --- | --- | --- | --- | --- |
| `/api/cut/bootstrap` | `POST` | Creates or opens the CUT project from shell inputs | `source_path`, `sandbox_root`, `project_name`, `mode`, `use_core_mirror`, `create_project_if_missing` | `success: true`, `project.project_id` |
| `/api/cut/project-state` | `GET` | Hydrates shell panels and worker outputs | query contains `sandbox_root` and `project_id` | full enough `cut_project_state_v1` payload |
| `/api/cut/scene-assembly-async` | `POST` | Starts scene assembly from shell | `sandbox_root`, `project_id`, `timeline_id`, `graph_id` | `success: true`, `job_id`, `job.state: running` |
| `/api/cut/worker/waveform-build-async` | `POST` | Starts waveform worker | `sandbox_root`, `project_id`, `bins`, `limit` | `success: true`, `job_id`, `job.state: running` |
| `/api/cut/worker/audio-sync-async` | `POST` | Starts audio sync worker | `sandbox_root`, `project_id`, `limit`, `sample_bytes`, `method` | `success: true`, `job_id`, `job.state: running` |
| `/api/cut/job/{job_id}` | `GET` | Polls completion in `waitForJob()` | path includes the created job id | `success: true`, `job.state: done` |

## Mutable state expectations
Use one in-memory project-state object and mutate it when a mocked job is polled as done.

### After bootstrap
- `project.project_id` is present
- `runtime_ready` stays `false`
- `timeline_state.lanes` may remain empty

### After scene assembly job completes
- `runtime_ready: true`
- `graph_ready: true`
- one `timeline_state.lanes[]`
- one `scene_graph.nodes[]`

### After waveform job completes
- `waveform_ready: true`
- `waveform_bundle.items.length = 1`

### After audio sync job completes
- `audio_sync_ready: true`
- `audio_sync_result.items.length = 1`

## Optional routes
- Catch-all `/api/**` fallback may return `{ "success": true }` for unrelated reads.
- `media-proxy` is not required for this shell-only lane.

## Keep unmocked
- Actual view-mode toggle behavior
- Status text rendering
- Runtime error overlay and `localStorage` crash sentinels

## Helper guidance
- This lane is safe for GPT-mini if it stays within `client/e2e`, `docs/170_ph_VIDEO_edit_mode`, and `data/task_board.json`.
- Do not edit `CutStandalone.tsx`; adapt the smoke to current UI labels instead.
