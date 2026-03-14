# PHASE 170 — CUT Debug Worker Outputs Mock Matrix

## Routes
| Route | Method | Why it is needed | Minimum mock behavior |
| --- | --- | --- | --- |
| `/api/cut/project-state` | `GET` | Initial hydration and refresh | Return `success: true` plus a valid CUT project-state payload |
| `/api/*` fallback | `GET/POST` | Defensive catch-all for unrelated calls | Return `{ "success": true }` |

## Minimum project-state shape
- `success: true`
- `schema_version: 'cut_project_state_v1'`
- `project.project_id`, `project.display_name`, `project.sandbox_root`, `project.state`
- `timeline_state.timeline_id`
- `waveform_bundle.items[]`
- `transcript_bundle.items[]`
- `thumbnail_bundle.items[]`
- `audio_sync_result.items[]`
- `slice_bundle.items[]`
- `timecode_sync_result.items[]`
- `time_marker_bundle.items[]`
- empty placeholders for `scene_graph`, `sync_surface`, `recent_jobs`, `active_jobs`

## Representative item fields
- waveform/transcript: `item_id`, `source_path`, optional `degraded_mode`, optional `degraded_reason`
- thumbnail: `item_id`, `source_path`, `duration_sec`
- audio sync: `item_id`, `source_path`, `detected_offset_sec`, `confidence`, `method`
- timecode sync: `item_id`, `source_path`, `reference_timecode`, `source_timecode`, `detected_offset_sec`, `fps`
- time marker: `marker_id` is enough for count coverage in this smoke

## Refresh sequence
- snapshot A: one item in each family and representative rows visible
- snapshot B: increased counts and changed representative rows to prove the card rehydrates from the new payload
- repeated reads can keep returning snapshot B after refresh
