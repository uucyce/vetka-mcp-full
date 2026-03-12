# Phase 170 CUT Debug Worker Queue Mock Matrix

## Goal
Minimum route matrix for a browser smoke that verifies the debug-shell Worker Queue card and cancel flow.

## Required mocked routes
| Route | Method | Why mocked | Expected request shape | Mock response |
| --- | --- | --- | --- | --- |
| `/api/cut/project-state` | `GET` | Hydrates queue counts and job rows | query includes `sandbox_root` and `project_id` | project-state with one active job and one recent job |
| `/api/cut/job/{job_id}/cancel` | `POST` | Handles queue cancel action | path includes active job id | `success: true`, `job.state: cancelled` |

## Minimum queue shape in project-state
- `active_jobs` with one item:
  - `job_id`
  - `job_type`
  - `state`
  - `progress`
- `recent_jobs` with one item:
  - `job_id`
  - `job_type`
  - `state`
  - `progress`

Other project-state fields can remain minimal placeholders.

## Mutable state expectations
After cancel succeeds:
- remove the job from `active_jobs`
- prepend the same job into `recent_jobs`
- mutate its `state` to `cancelled`
- preserve the existing `progress` so the UI can show `cancelled · 42%`

## Keep unmocked
- actual queue card rendering
- local status text rendering
- runtime error overlay and `vetka_last_runtime_error` sentinel
