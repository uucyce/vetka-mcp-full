# Phase 170 CUT Debug Marker Actions Mock Matrix

## Goal
Minimum route matrix for a browser smoke that verifies selected-shot marker actions and marker visibility toggles in the CUT debug shell.

## Required mocked routes
| Route | Method | Why mocked | Expected request shape | Mock response |
| --- | --- | --- | --- | --- |
| `/api/cut/project-state` | `GET` | Hydrates the selected-shot panel and marker groups | query includes `sandbox_root` and `project_id` | one ready project-state with thumbnail, timeline clip, and marker bundle |
| `/api/cut/time-markers/apply` | `POST` | Handles all create actions under test | `op: create`, `media_path`, `kind`, `start_sec`, `end_sec`, `score`, optional `text`, optional `cam_payload` | `success: true` |

## Minimum project-state shape
The `project-state` payload must include enough data to make selected-shot marker actions available:
- `project.project_id`
- one `timeline_state.lanes[]` clip whose `source_path` matches the selected thumbnail
- one `thumbnail_bundle.items[]` item so a selected shot is auto-hydrated
- `time_marker_bundle.items[]` with:
  - one active favorite marker
  - one archived comment marker for toggle coverage
- `runtime_ready: true`
- `graph_ready: true`
- `thumbnail_ready: true`
- `time_markers_ready: true`

## Expected time-marker payloads
### Favorite Selected
- `op: 'create'`
- `kind: 'favorite'`
- empty `text`
- `context_slice` present

### Comment Selected
- `op: 'create'`
- `kind: 'comment'`
- prompt-derived `text`
- `context_slice` present

### CAM Selected
- `op: 'create'`
- `kind: 'cam'`
- prompt-derived `text`
- `cam_payload.source: 'cut_shell'`
- `cam_payload.hint` mirrors the prompt value
- `cam_payload.status: 'placeholder'`

## Mutable state expectations
On each successful create:
- append a new active marker into `time_marker_bundle.items[]`
- keep `media_path` bound to the selected shot
- for the CAM marker, populate `cam_payload` so the `CAM Ready` card changes state

## Optional routes that can stay unmocked
- `/api/**` catch-all may return `{ "success": true }` for unrelated requests
- sync routes are not required in this lane
- export routes are not required in this lane
- worker routes are not required in this lane

## Keep unmocked
- actual local `showActiveMarkersOnly` toggle behavior
- prompt dialogs themselves
- runtime error overlay and `vetka_last_runtime_error` sentinel
