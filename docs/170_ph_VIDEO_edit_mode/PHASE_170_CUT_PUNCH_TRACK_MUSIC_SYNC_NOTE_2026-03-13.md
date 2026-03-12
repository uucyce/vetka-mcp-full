# Phase 170 CUT Punch Track Music-Sync Note

## Input

- track: `/Users/danilagulin/work/teletape_temp/albom/250623_vanpticdanyana_berlin_Punch.m4a`
- mirrored source copy also exists inside `/Users/danilagulin/work/teletape_temp/berlin`
- fixture profile anchor: `berlin_fixture_v1`

## Why this track matters

- it is the clearest editorial music spine in the Berlin sample
- it sits next to mixed camera, generated video, stills, and project files
- it is the natural candidate for a CUT lane that goes beyond shot sync and starts informing montage timing

## Proposed CUT mapping

### Near-term
- treat Punch as a first-class `audio_sync` / music reference candidate during bootstrap profile planning
- keep it visible in fixture manifest as `music_track`
- let browser fixtures prove the track survives source-browser hydration in the isolated sandbox lane

### Next worker step
- add a dedicated async worker lane, tentatively `POST /api/cut/worker/music-sync-async`
- input:
  - `sandbox_root`
  - `project_id`
  - `music_path`
  - optional `reference_paths`
  - optional `bpm_hint`
- output:
  - beat grid
  - bar/phrase markers
  - high-energy regions
  - suggested montage cut points

## Contract direction

### New contract candidate
- `cut_music_sync_result_v1`

### Suggested shape
- `project_id`
- `music_path`
- `tempo`: bpm estimate + confidence
- `downbeats`: ordered timestamps
- `phrases`: sections with start/end, energy, label
- `cue_points`: recommended cut anchors
- `derived_from`: waveform/transient analysis method
- `generated_at`

### Existing contract reuse
- `cut_time_marker_bundle_v1` can carry promoted cue points once editorially accepted
- `cut_timeline_apply_v1` can consume accepted cue points as view/selection anchors before we support automatic rhythmic edits
- `cut_audio_sync_result_v1` remains clip-to-reference alignment, not music phrasing; do not overload it with beat-grid semantics

## Incremental implementation order

1. Fixture/bootstrap layer
- keep Punch pinned in `bootstrap.profile.music_track`

2. Analysis layer
- derive waveform + onset/beat candidates from the track

3. Surfacing layer
- expose music cue summary in `project-state`

4. Editing layer
- allow selected cue points to create `favorite` or `insight` markers, then later real montage ops

## Practical next tests

- backend: bootstrap/profile test proving Punch is selected as primary music candidate for `berlin_fixture_v1`
- backend: future contract test for `cut_music_sync_result_v1`
- browser: isolated Berlin fixture smoke asserting the Punch track appears in the reserved-port source browser lane
