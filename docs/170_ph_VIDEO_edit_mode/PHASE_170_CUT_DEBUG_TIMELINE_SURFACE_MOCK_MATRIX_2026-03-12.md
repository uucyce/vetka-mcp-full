# PHASE 170 — CUT Debug Timeline Surface Mock Matrix

## Routes
| Route | Method | Why it is needed | Minimum mock behavior |
| --- | --- | --- | --- |
| `/api/cut/project-state` | `GET` | Initial hydration, refresh after action | Return `success: true` plus a valid CUT project-state payload |
| `/api/cut/timeline/apply` | `POST` | `Select First Clip` action under test | Capture `set_selection` / `set_view`, mutate in-memory selection, return `{ "success": true }` |
| `/api/*` fallback | `GET/POST` | Defensive catch-all for unrelated calls | Return `{ "success": true }` |

## Minimum project-state shape
- `success: true`
- `schema_version: 'cut_project_state_v1'`
- `project.project_id`, `project.display_name`, `project.sandbox_root`, `project.state`
- `timeline_state.timeline_id`
- `timeline_state.selection.clip_ids[]`
- `timeline_state.lanes[]` with at least one lane and two clips for readability
- empty placeholders for `scene_graph`, `waveform_bundle`, `transcript_bundle`, `thumbnail_bundle`, `audio_sync_result`, `slice_bundle`, `timecode_sync_result`, `sync_surface`, `time_marker_bundle`, `recent_jobs`, `active_jobs`

## Lane / clip item requirements
Each lane should expose:
- `lane_id`
- `lane_type`
- `clips[]`

Each clip should expose:
- `clip_id`
- `source_path`
- `start_sec`
- `duration_sec`

## Refresh sequence
- snapshot A: `runtime_ready: false`, no lanes needed, empty-state message visible
- snapshot B: `runtime_ready: true`, lanes visible, no selected clip yet
- snapshot C: same lanes, but `timeline_state.selection.clip_ids[]` contains the first clip after `/api/cut/timeline/apply`
- repeated reads can keep returning snapshot C after the action refresh
