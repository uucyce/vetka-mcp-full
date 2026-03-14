# PHASE 170 cut_timeline_state_v1 Draft
**Date:** 2026-03-09  
**Status:** first draft  
**Scope:** lightweight editorial state contract separate from `cut_project_v1`

## Goal
Define the first dedicated timeline state object for `VETKA CUT` without overloading `cut_project_v1`.

## Marker
- `MARKER_170.CONTRACT.CUT_TIMELINE_STATE_V1`

## Why separate from cut_project_v1
`cut_project_v1` stores stable project identity and runtime roots.
`cut_timeline_state_v1` stores volatile editorial state.

This split keeps:
1. project persistence stable,
2. timeline iteration fast,
3. async editorial updates isolated.

## Required fields
1. `schema_version`
2. `project_id`
3. `timeline_id`
4. `revision`
5. `fps`
6. `lanes`
7. `selection`
8. `view`
9. `updated_at`

## Lane model (V1)
Lanes stay aligned with existing media concepts:
1. `video_main`
2. `audio_sync`
3. `take_alt_y`
4. optional future lanes only as additive fields

## Proposed shape
```json
{
  "schema_version": "cut_timeline_state_v1",
  "project_id": "cut_demo_1234abcd",
  "timeline_id": "main",
  "revision": 1,
  "fps": 25,
  "lanes": [
    {
      "lane_id": "video_main",
      "lane_type": "video_main",
      "clips": [
        {
          "clip_id": "clip_001",
          "record_id": "record_001",
          "scene_id": "scene_01",
          "take_id": "take_a",
          "start_sec": 0.0,
          "duration_sec": 4.2,
          "source_path": "/abs/path/clip.mp4"
        }
      ]
    }
  ],
  "selection": {
    "clip_ids": ["clip_001"],
    "scene_ids": ["scene_01"]
  },
  "view": {
    "zoom": 1.0,
    "scroll_sec": 0.0,
    "active_lane_id": "video_main"
  },
  "updated_at": "2026-03-09T12:00:00Z"
}
```

## Mapping notes
1. `record_id`, `scene_id`, `take_id` should map cleanly to `vetka_montage_sheet_v1`
2. lane semantics should remain aligned with `media_chunks_v1.timeline_lane`
3. future scene graph references should stay outside V1 unless additive

## V1 non-goals
1. no keyframes
2. no effects graph
3. no multicam Z-mode state
4. no full undo history
5. no embedded semantic links payloads

## Follow-up
After this draft:
1. freeze `cut_timeline_state_v1` schema
2. define persistence file path
3. define relation to `cut_scene_graph_v1`
