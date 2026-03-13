# PHASE 171 CUT Montage Engine Roadmap

## Starting point

Phase 171 does **not** start from a blank editor anymore.
By the end of Phase 170, CUT already has:
- primary NLE surface with source browser, preview, timeline, markers, trim/drag/scrub
- first-class Scene Graph viewport in CUT/NLE
- Berlin fixture lane with Punch track and reserved-port sandbox flow
- CUT-only human launcher and CUT-only app/dmg packaging gate
- music-sync -> marker bundle path and marker rendering in Scene Graph

## What Phase 171 owns

Phase 171 is the transition from **editor shell + graph + markers** to a real **montage engine**.

The montage engine should answer:
1. which cues matter now,
2. how they map into editorial intent,
3. how they persist in project state,
4. how the editor promotes them into actual montage decisions.

## Core tracks

### 171.1 Montage state + persistence
- freeze `cut_montage_plan_v1` / equivalent state contract
- persist selected montage decisions in project state
- keep marker/cue provenance, confidence, and source bundle ids

### 171.2 Music cue engine
- formalize beat / phrase / energy cue result contract
- surface music summary in project-state
- support marker promotion from music cues into montage decisions

### 171.3 Multi-track sync engine
- formalize A/B cam alignment model beyond current clip sync
- preserve hard-sync vs meta-sync hierarchy
- expose alignment groups for editor actions

### 171.4 Editorial scoring / ranking
- rank cues from transcript, pause slices, music, sync, scene graph, notes
- produce decision-ready montage suggestions rather than raw worker blobs

### 171.5 Browser acceptance + Berlin fixture
- keep Berlin as the deterministic montage acceptance lane
- prove that music cues, markers, and promoted montage decisions survive reloads

## Immediate milestones

### M1
Roadmap + architecture freeze for the montage engine.

### M2
Montage state contract seeded and persisted in project state.

### M3
Berlin Punch track upgraded from fixture metadata to first-class music cue source.

### M4
Marker -> montage decision promotion path exists and is browser-testable.

## Constraints
- reserved ports remain mandatory:
  - human review `3011`
  - Codex54 sandbox `3211`
- no shared random Vite ports
- do not regress Phase 170 CUT review app/dmg lane
- keep Scene Graph as first-class viewport, not debug-only fallback

## Phase 170 inputs this roadmap depends on
- `docs/170_ph_VIDEO_edit_mode/PHASE_170_VETKA_CUT_ARCHITECTURE_2026-03-09.md`
- `docs/170_ph_VIDEO_edit_mode/PHASE_170_VETKA_CUT_ROADMAP_RECON_MARKERS_2026-03-09.md`
- `docs/170_ph_VIDEO_edit_mode/PHASE_170_CHECKPOINT_2026-03-13.md`
- `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_BERLIN_SAMPLE_FIXTURE_PLAN_2026-03-13.md`
- `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_PUNCH_TRACK_MUSIC_SYNC_NOTE_2026-03-13.md`
