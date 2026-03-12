# Phase 170 CUT Debug Marker Archive and Focus Mock Matrix

## Goal
Minimum route matrix for a browser smoke that verifies marker focus, archive, and global visibility toggles in the CUT debug shell.

## Required mocked routes
| Route | Method | Why mocked | Expected request shape | Mock response |
| --- | --- | --- | --- | --- |
| `/api/cut/project-state` | `GET` | Hydrates selected-shot marker cards and global marker cards | query includes `sandbox_root` and `project_id` | ready project-state with thumbnail, timeline clip, and marker bundle |
| `/api/cut/timeline/apply` | `POST` | Handles `Focus Marker In Timeline` | `ops[0].op = set_selection`, `ops[1].op = set_view` | `success: true`, `timeline_state` |
| `/api/cut/time-markers/apply` | `POST` | Handles `Archive Marker` | `op: archive`, `marker_id` | `success: true` |

## Minimum marker bundle shape
Use one marker bundle with at least:
- one active selected-shot marker that can be focused and archived
- one active CAM marker so active global count is greater than zero after archive
- one archived comment marker to test `Show All Global Markers`

Each marker should include:
- `marker_id`
- `kind`
- `media_path`
- `start_sec`
- `end_sec`
- `status`
- optional `text`
- optional `context_slice`

## Expected payloads
### Focus Marker In Timeline
- two ops in one `/api/cut/timeline/apply` request
- `set_selection` chooses the selected clip and scene
- `set_view` carries:
  - `active_lane_id`
  - `scroll_sec` equal to the marker start
  - `zoom: 1.5`

### Archive Marker
- one `/api/cut/time-markers/apply` request
- `op: 'archive'`
- `marker_id` of the clicked global marker

## Mutable state expectations
After archive succeeds:
- mutate the targeted marker status to `archived`
- allow the next `/api/cut/project-state` refresh to hide it again under active-only mode

## Keep unmocked
- local selected/global marker visibility toggles
- runtime status rendering
- runtime error overlay and `vetka_last_runtime_error` sentinel
