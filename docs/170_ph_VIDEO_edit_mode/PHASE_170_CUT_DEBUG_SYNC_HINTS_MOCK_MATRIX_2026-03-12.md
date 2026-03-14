# Phase 170 CUT Debug Sync Hints Mock Matrix

## Goal
Minimum route matrix for a browser smoke that verifies the `Sync Hints` card in CUT debug shell.

## Required mocked routes
| Route | Method | Why mocked | Expected request shape | Mock response |
| --- | --- | --- | --- | --- |
| `/api/cut/project-state` | `GET` | Hydrates sync hint counts and rows on load and refresh | query includes `sandbox_root` and `project_id` | project-state with `timecode_sync_result`, `audio_sync_result`, and `sync_surface` |

## Minimum project-state shape
Use a payload with:
- `timecode_sync_result.items[]` containing one item with:
  - `source_path`
  - `reference_path`
  - `reference_timecode`
  - `source_timecode`
  - `detected_offset_sec`
  - `method`
- `audio_sync_result.items[]` containing one item with:
  - `source_path`
  - `reference_path`
  - `detected_offset_sec`
  - `confidence`
  - `method`
- `sync_surface.items[]` containing one item with:
  - `source_path`
  - `recommended_method`
  - `recommended_offset_sec`
  - `confidence`

## Refresh behavior
A second mocked project-state response should change one or more of:
- sync_surface count
- timecode source/reference labels
- audio sync method
- recommended sync method

This proves the card re-renders from refreshed project state.

## Keep unmocked
- actual sync hint row rendering
- refresh button behavior
- runtime error overlay and `vetka_last_runtime_error` sentinel
