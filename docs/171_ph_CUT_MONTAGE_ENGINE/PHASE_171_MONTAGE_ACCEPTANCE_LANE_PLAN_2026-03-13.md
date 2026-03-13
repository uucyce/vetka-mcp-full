# PHASE 171 Montage Acceptance Lane Plan (2026-03-13)

## Purpose

Define the deterministic acceptance lane for montage engine work so cue promotion and persistence can be proven against the Berlin fixture.

## Fixture

- source project: `/Users/danilagulin/work/teletape_temp/berlin`
- music track: `/Users/danilagulin/work/teletape_temp/albom/250623_vanpticdanyana_berlin_Punch.m4a`
- human review port: `3011`
- fixture sandbox port: `3211`

## Acceptance chain

1. bootstrap Berlin fixture
2. verify music cue source is present in project-state
3. create or reuse time markers from music/sync lane
4. promote marker into montage decision
5. reload project-state
6. verify montage decision survives reload with provenance intact

## Required assertions

- `music_cues_ready = true` when Punch-track cues exist
- `time_markers_ready = true` before promotion
- `montage_ready = true` after promotion
- accepted/rejected decisions preserve:
  - `cue_provenance_ids`
  - `source_bundle_id`
  - `source_bundle_revision`
  - `editorial_intent`

## Browser/test lanes

### Backend
- `tests/phase170/test_cut_time_marker_api.py`
- `tests/phase170/test_cut_project_state_api.py`

### Browser
- Berlin fixture smoke
- montage promotion smoke
- reload persistence smoke

## Ownership split

- Codex: montage promotion + persistence
- Codex54: Berlin cue summary + Berlin acceptance smoke

## Markers

- `MARKER_171.MONTAGE_ENGINE.ACCEPTANCE_LANE`
- `MARKER_171.MONTAGE_ENGINE.BERLIN_RELOAD_PROOF`
