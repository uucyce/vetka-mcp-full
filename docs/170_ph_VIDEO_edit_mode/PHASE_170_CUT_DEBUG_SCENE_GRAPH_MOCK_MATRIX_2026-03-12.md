# PHASE 170 - CUT Debug Scene Graph Surface Mock Matrix

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
- `scene_graph.nodes[]`
- empty placeholders for `waveform_bundle`, `transcript_bundle`, `thumbnail_bundle`, `audio_sync_result`, `slice_bundle`, `timecode_sync_result`, `sync_surface`, `time_marker_bundle`, `recent_jobs`, `active_jobs`

## Scene graph node fields
Each node under test should expose:
- `node_id`
- `node_type`
- `label`

## Refresh sequence
- snapshot A: `graph_ready: false`, so the card shows `Scene graph not ready.`
- snapshot B: `graph_ready: true` and `scene_graph.nodes[]` populated with representative `scene`, `take`, and `note` nodes
- repeated reads can keep returning snapshot B after refresh

## Architecture note
This smoke only freezes hydration and row rendering.
It does not attempt MCC DAG layout, clustering, or JEPA/PULSE overlays; those belong to the longer architecture chain anchored by `PHASE_170_CUT_SCENE_GRAPH_ARCHITECTURE_PLAN_2026-03-12.md`.
