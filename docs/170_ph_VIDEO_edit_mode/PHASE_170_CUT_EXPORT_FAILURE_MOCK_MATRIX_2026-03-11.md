# Phase 170 CUT Export Failure Mock Matrix

## Goal
Minimum route matrix for a browser smoke that proves CUT export failure handling without touching backend code.

## Required mocked routes
| Route | Method | Why mocked | Expected payload | Mock response |
| --- | --- | --- | --- | --- |
| `/api/cut/project-state` | `GET` | Hydrates `/cut` into a ready-enough NLE shell | query includes `project_id` and `sandbox_root` from page URL | `success: true`, empty lanes, empty bundles, project metadata |
| `/api/cut/export/premiere-xml` | `POST` | Premiere failure branch | `sandbox_root`, `project_id`, `fps` | `success: false`, `error.message` string |
| `/api/cut/export/fcpxml` | `POST` | FCPXML failure branch | `sandbox_root`, `project_id`, `fps` | `success: false`, `error.message` string |

## Response shape assumptions
### Project state
Keep the payload minimal but aligned with current CUT shell expectations:
- `success: true`
- `project.project_id`
- `timeline_state.timeline_id`
- `timeline_state.lanes: []`
- `selection`, bundle placeholders, `sync_surface`, `time_marker_bundle`, `recent_jobs`, `active_jobs`

### Export failures
The frontend currently reads JSON and branches on `data.success`.
Use this shape:

```json
{
  "success": false,
  "error": {
    "message": "human-readable failure reason"
  }
}
```

## Keep unmocked
- Browser console behavior should stay real so runtime errors surface naturally.
- Transport color state should come from the real component, not injected CSS.
- Do not mock unrelated CUT routes unless the page unexpectedly requests them.

## Notes for helper agents
- No selector changes are required for this lane.
- If the spec needs more routes, add them only after confirming the request log from the running page.
- This lane is safe for GPT-mini because it lives in `client/e2e` + docs only.
