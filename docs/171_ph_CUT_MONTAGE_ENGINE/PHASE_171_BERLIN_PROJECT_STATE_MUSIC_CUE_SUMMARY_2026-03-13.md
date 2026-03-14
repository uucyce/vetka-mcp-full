# Phase 171 Berlin Project-State Music Cue Summary

## Scope

Task:
- `tb_1773372827_6`

## Surface

`GET /api/cut/project-state` now carries:
- `music_sync_result`
- `music_cue_summary`
- `music_cues_ready`

## Summary shape

The compact summary intentionally keeps only montage-relevant fields:
- `track_label`
- `music_path`
- `primary_candidate`
- `cue_point_count`
- `phrase_count`
- `downbeat_count`
- `tempo_bpm`
- `tempo_confidence`
- `top_cues[]`

## Why summary exists

The montage engine acceptance lane does not need the full phrase grid in every browser assertion.

It only needs proof that:
- Punch is still the primary track
- cue density survived hydration
- the strongest cues are visible after reload

## Berlin fixture implication

The deterministic Berlin fixture now carries representative Punch cue data and exposes summary text suitable for acceptance smoke and montage review status text.
