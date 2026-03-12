# Phase 170 CUT Debug Runtime Flags Mock Matrix

## Goal
Minimum route matrix for a browser smoke that verifies `Project Overview` and `Runtime Flags` cards in CUT debug shell.

## Required mocked routes
| Route | Method | Why mocked | Expected request shape | Mock response |
| --- | --- | --- | --- | --- |
| `/api/cut/project-state` | `GET` | Hydrates overview/flags on load and refresh | query includes `sandbox_root` and `project_id` | project-state with `project` metadata and mixed readiness flags |

## Minimum project-state shape
Use a payload with:
- `project.project_id`
- `project.display_name`
- `project.source_path`
- readiness booleans:
  - `runtime_ready`
  - `graph_ready`
  - `waveform_ready`
  - `transcript_ready`
  - `thumbnail_ready`
  - `audio_sync_ready`
  - `slice_ready`
  - `timecode_sync_ready`
  - `sync_surface_ready`
  - `meta_sync_ready`
  - `time_markers_ready`
- minimal placeholder bundles and arrays for the rest of the shell

## Refresh behavior
A second mocked project-state response should change both:
- overview identity (`display_name`, `source_path`)
- several readiness booleans

This proves the card re-renders from refreshed server state rather than local cached text.

## Keep unmocked
- actual flag rendering in the debug shell
- refresh button behavior
- runtime error overlay and `vetka_last_runtime_error` sentinel
