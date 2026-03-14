# Phase 170 CUT Multi-Track Sync Alignment Recon

## Scope

Task lane:
- `tb_1773400000_261`

Context:
- Berlin fixture uses Punch as the primary music reference
- CUT already has `audio_sync_result`, `timecode_sync_result`, `sync_surface`, and music markers

## Alignment problem

Multi-track montage alignment is not a single offset problem anymore once Punch becomes the editorial spine.

We now have three timing layers:
- track-level phrasing from `cut_music_sync_result_v1`
- clip-to-reference offsets from `cut_audio_sync_result_v1`
- deterministic camera offsets from `cut_timecode_sync_result_v1`

## Practical synthesis order

1. Timecode first
- if a clip has reliable timecode, use it as the base structural alignment

2. Audio sync second
- use waveform/audio sync to refine clips that share real audio with the reference track or camera mic

3. Music cues last
- apply music cue points as editorial anchors for montage timing, not as replacement sync offsets

## Why music cues stay separate

- `audio_sync_result` answers: "where does this clip align to a reference waveform?"
- `music_sync_result` answers: "where are the beats, phrases, and accent points on the editorial music spine?"
- overloading one result with the other would blur technical sync and editorial timing decisions

## Recommended project-state summary shape

Project-state does not need to dump full phrase grids into the UI by default. The useful compact summary is:
- track label
- cue count
- phrase count
- downbeat count
- tempo estimate
- top 2-3 cues by confidence

That is enough for CUT shells and browser smokes to verify montage readiness while leaving the full result on disk for deeper workflows.

## Next implementation step after this recon

1. expose `music_sync_result` + `music_cue_summary` in `project-state`
2. keep Berlin fixture hydrated with representative cue points from Punch
3. later add timeline actions that convert selected cue points into editorial markers or cut suggestions
