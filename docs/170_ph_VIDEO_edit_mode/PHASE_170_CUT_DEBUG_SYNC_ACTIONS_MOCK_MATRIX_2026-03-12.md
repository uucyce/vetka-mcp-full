# Phase 170 CUT Debug Sync Actions Mock Matrix

## Goal
Minimum route matrix for a browser smoke that verifies selected-shot sync actions in the CUT debug shell.

## Required mocked routes
| Route | Method | Why mocked | Expected request shape | Mock response |
| --- | --- | --- | --- | --- |
| `/api/cut/project-state` | `GET` | Hydrates the debug shell and selected-shot panel | query includes `sandbox_root` and `project_id` | one ready project-state object with thumbnail, timeline lane, audio sync item, and sync_surface item |
| `/api/cut/timeline/apply` | `POST` | Handles all three sync actions under test | `sandbox_root`, `project_id`, `timeline_id`, `author`, `ops[]` | `success: true`, `timeline_state` |

## Minimum project-state shape
The `project-state` payload must include enough data to make the selected-shot panel actionable:
- `project.project_id`
- `timeline_state.timeline_id`
- one `timeline_state.lanes[]` item with one clip
- one `thumbnail_bundle.items[]` item whose `source_path` matches the clip
- one `audio_sync_result.items[]` item for `sync hint:`
- one `sync_surface.items[]` item with `recommended_method` and `recommended_offset_sec`
- `runtime_ready: true`
- `graph_ready: true`
- `thumbnail_ready: true`
- `audio_sync_ready: true`
- `sync_surface_ready: true`

## Expected timeline/apply payloads
### Sync Timeline Selection
Expect two ops:
1. `set_selection`
2. `set_view`

Important fields:
- selected `clip_id`
- matching `scene_id`
- `active_lane_id`

### Apply Selected Sync
Expect one op:
- `apply_sync_offset`

Important fields:
- `clip_id`
- `offset_sec`
- `method`
- `confidence`
- `reference_path`
- `source: 'sync_surface'`
- `group_id`

### Apply All Syncs
Expect one or more `apply_sync_offset` ops packed into a single request.
For the smoke matrix, one actionable item is enough, so the request can still contain a single op.

## Optional routes that can stay unmocked
- `/api/**` catch-all can return `{ "success": true }` for unrelated requests
- worker routes are not required in this lane
- export routes are not required in this lane
- media proxy is not required in this lane

## Keep unmocked
- actual view-mode toggle behavior
- status text rendering
- local runtime error overlay and `vetka_last_runtime_error` sentinel
