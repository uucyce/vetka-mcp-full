# PHASE 170 Cognitive Time Markers Contract
**Date:** 2026-03-09  
**Status:** Contract draft frozen before implementation  
**Scope:** player-lab bridge + future `VETKA CUT` cognitive timeline markers

## Why this exists
We need one exact contract for:
- player-side moment actions,
- CUT timeline markers,
- CAM-linked cognitive moments,
- future comment threads on time ranges.

This prevents vague "favorite" logic and avoids redoing endpoints later.

## Core decision
There is no primary file-level favorite.

Primary unit is a `time marker` on a bounded media interval:
- one moment,
- one meaning,
- one score,
- optional context slice,
- optional CAM/chat payload.

## Canonical contracts
1. `cut_time_marker_v1`
2. `cut_time_marker_bundle_v1`
3. `cut_time_marker_apply_v1`

Files:
1. `docs/contracts/cut_time_marker_v1.schema.json`
2. `docs/contracts/cut_time_marker_bundle_v1.schema.json`
3. `docs/contracts/cut_time_marker_apply_v1.schema.json`

## Marker model
`cut_time_marker_v1` required core:
- `marker_id`
- `project_id`
- `timeline_id`
- `media_path`
- `kind`
- `start_sec`
- `end_sec`
- `score`
- `created_at`
- `updated_at`

Allowed `kind` values:
- `favorite`
- `comment`
- `cam`
- `insight`
- `chat`

Optional enrichment:
- `anchor_sec`
- `label`
- `text`
- `author`
- `context_slice`
- `cam_payload`
- `chat_thread_id`
- `comment_thread_id`
- `source_engine`
- `status`

## Behavior rules
### 1. Favorite means favorite moment
When user presses star:
- do not mark whole file,
- create `kind=favorite` marker for current time interval.

### 2. Smart slice is mandatory later, optional now
V1 creation rule:
- if no segmentation exists, use narrow default window around current time.

Recommended fallback:
- `start_sec = max(0, t - 0.5)`
- `end_sec = t + 0.5`
- `anchor_sec = t`

V2 creation rule:
- expand to pause-to-pause / silence-to-silence / speech chunk boundaries.

### 3. Comments are also markers
Frame.io-style comment should map to:
- `kind=comment`
- same time interval model
- optional `text`
- optional `comment_thread_id`

### 4. CAM markers are first-class
If CAM or another intelligence layer highlights a moment:
- store it as `kind=cam` or `kind=insight`
- attach `cam_payload`
- keep same timeline identity model as user comments/favorites

### 5. Ranking is moment-based
Media priority should be computed from moment markers, not file-level stars.

Bundle-level `ranking_summary` should later support:
- `marker_count`
- `favorite_count`
- `comment_count`
- `cam_count`
- `weighted_score`
- `media_rank`

## Exact endpoint recommendation for player sandbox
These can be implemented in player-lab now without pulling full CUT runtime.

### Write
1. `POST /api/player/markers/favorite`
2. `POST /api/player/markers/comment`
3. `POST /api/player/markers/cam`
4. `POST /api/player/markers`

### Read
1. `GET /api/player/markers`
2. `GET /api/player/markers/summary`

## Request shape recommendation
Minimum request payload:

```json
{
  "project_id": "cut_demo",
  "timeline_id": "main",
  "media_path": "/abs/path/video.mp4",
  "kind": "favorite",
  "anchor_sec": 42.18,
  "start_sec": 41.68,
  "end_sec": 42.68,
  "text": "",
  "author": "player_lab",
  "context_slice": null,
  "cam_payload": null
}
```

## What player-lab should prepare now
1. Player UI should create time-based markers, not file-level favorites.
2. Overlay toolbar should expose:
   - favorite moment,
   - comment moment,
   - future CAM marker hook.
3. Preview quality and minimal overlay UX can stay local to player-lab.
4. Marker payload shape should already match CUT contracts.
5. Player-lab does not need full CUT orchestration; it only needs the marker boundary and payload discipline.

## Short brief for player-lab Codex
I am from neighboring sandbox `VETKA CUT`.

`CUT = Contextual Unified Timeline` — editorial timeline over `VETKA Core`, where moments can be linked to CAM, chat, semantic context, and future montage logic.

Please prepare player-lab for this bridge:
- replace file-level favorite with time markers,
- add comment markers on time intervals,
- keep compact overlay toolbar and preview quality menu,
- add marker endpoints/contracts compatible with CUT,
- leave full CUT orchestration out of player-lab for now.

## Markers
1. `MARKER_170.INTEL.TIME_MARKERS_CAM_BRIDGE`
2. `MARKER_170.INTEL.COGNITIVE_TIME_MARKERS`
3. `MARKER_170.INTEL.MOMENT_RANKING`
4. `MARKER_170.MCP.TIME_MARKERS_V1`
5. `MARKER_170.CONTRACT.CUT_TIME_MARKER_V1`
