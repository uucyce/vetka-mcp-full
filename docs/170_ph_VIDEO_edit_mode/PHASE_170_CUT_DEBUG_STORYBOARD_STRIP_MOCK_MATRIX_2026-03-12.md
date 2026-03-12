# PHASE 170 — CUT Debug Storyboard Strip Mock Matrix

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
- `thumbnail_bundle.items[]`
- `slice_bundle.items[]` or `transcript_bundle.items[]` so marker windows stay deterministic
- optional `sync_surface.items[]` for badge coverage
- empty placeholders for `scene_graph`, `waveform_bundle`, `audio_sync_result`, `timecode_sync_result`, `time_marker_bundle`, `recent_jobs`, `active_jobs`

## Thumbnail item requirements
Each storyboard item under test should expose:
- `item_id`
- `source_path`
- `modality`
- `duration_sec`
- optional `poster_url`
- optional `source_url`

## Refresh sequence
- snapshot A: `thumbnail_bundle.items[]` empty, so the strip shows `No thumbnails yet. Run thumbnail build.`
- snapshot B: at least two thumbnails, with one sync badge and deterministic marker windows
- repeated reads can keep returning snapshot B after refresh

## Expected visible behaviors
- `Open Preview` links exist for hydrated cards
- `Select Shot` on the second card updates `Selected Shot` to that filename
- the right panel should reflect that card's `marker window`, `slice source`, and `recommended sync`
