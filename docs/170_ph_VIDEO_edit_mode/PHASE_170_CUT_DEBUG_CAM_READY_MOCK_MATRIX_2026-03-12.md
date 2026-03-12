# PHASE 170 — CUT Debug CAM Ready Mock Matrix

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
- `thumbnail_bundle.items[]` with one media item so `Selected Shot` resolves deterministically
- `time_marker_bundle.items[]`
- empty placeholders for `scene_graph`, `waveform_bundle`, `transcript_bundle`, `audio_sync_result`, `slice_bundle`, `timecode_sync_result`, `sync_surface`, `recent_jobs`, `active_jobs`
- readiness booleans can stay mixed; only `thumbnail_ready` and `time_markers_ready` matter for this smoke

## Selected-shot requirements
The chosen thumbnail item must expose:
- `item_id`
- `source_path`
- `modality`
- `duration_sec`

## CAM marker requirements
The hydrated refresh payload needs one active marker with:
- `marker_id`
- `kind: 'cam'`
- `media_path` equal to the selected thumbnail `source_path`
- `start_sec`, `end_sec`
- `status: 'active'`
- optional `text`
- `cam_payload.source`
- `cam_payload.status`
- `cam_payload.hint`

## Refresh sequence
- snapshot A: no matching CAM markers, so the card shows `cam markers: 0`
- snapshot B: one matching CAM marker, so the card shows `cam markers: 1` and the payload row
- repeated reads can keep returning snapshot B after refresh
