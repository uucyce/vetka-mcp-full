# Phase 170 CUT Interaction Mock Matrix

## Required mocked routes
| Route | Method | Used by | Minimal response / behavior |
| --- | --- | --- | --- |
| `/api/cut/project-state` | `GET` | `CutStandalone` initial hydration and post-action refreshes | Return `success: true`, `project`, `runtime_ready: true`, `timeline_state.timeline_id`, at least one lane with clips, `thumbnail_bundle.items`, `sync_surface.items`, and `time_marker_bundle.items` |
| `/api/cut/time-markers/apply` | `POST` | Timeline marker draft create, transport hotkey marker create | Return `{ "success": true }` and mutate in-memory `time_marker_bundle.items` so the next `project-state` refresh shows the new marker |
| `/api/cut/timeline/apply` | `POST` | Optional context actions such as `Apply Sync`, `Remove Clip`, or future interaction expansion | Return `{ "success": true, "timeline_state": ... }`; current smoke only needs route availability, not state mutation |

## Supporting route
| Route | Method | Used by | Minimal response / behavior |
| --- | --- | --- | --- |
| `/api/cut/media-proxy` | `GET` | `VideoPreview` after clip selection/right click activates media | Safe stub is `204` with `video/mp4` content type; this keeps player requests from leaking to the real backend during smoke |

## Mock state payload requirements
### `project`
- `project_id`
- `display_name`
- `sandbox_root`
- `source_path`

### `timeline_state`
- `timeline_id: "main"`
- `selection: { clip_ids: [], scene_ids: [] }`
- `lanes[0].lane_id: "video_main"`
- `lanes[0].clips[]` with:
  - `clip_id`
  - `scene_id`
  - `start_sec`
  - `duration_sec`
  - `source_path`
  - optional `sync` payload if `Apply Sync` should show enabled semantics

### `thumbnail_bundle`
- `items[]` with `item_id`, `source_path`, `modality`, `duration_sec`
- Posters are optional for this smoke

### `sync_surface`
- At least one item matching the clip `source_path`
- `recommended_method` must be non-null to keep `Apply Sync` enabled in the context menu

### `time_marker_bundle`
- Start with `items: []`
- After marker create, append:
  - `marker_id`
  - `kind`
  - `media_path`
  - `start_sec`
  - `end_sec`
  - `text`
  - `status: "active"`
  - `score`

## Expected request pattern
1. Initial navigation triggers one `GET /api/cut/project-state`.
2. Ruler double click + create triggers one `POST /api/cut/time-markers/apply`, then one follow-up `GET /api/cut/project-state`.
3. `KeyM` hotkey marker create triggers one more `POST /api/cut/time-markers/apply`, then one more `GET /api/cut/project-state`.
4. `POST /api/cut/timeline/apply` should remain available for future assertions even if this smoke only opens the menu and does not invoke its actions.

## Why this matrix is enough
- Interaction smoke is frontend-heavy and only needs deterministic hydration plus marker persistence across refresh.
- Export, jobs, bootstrap, scene assembly, and worker endpoints are outside this lane and should stay out of the mock surface.
