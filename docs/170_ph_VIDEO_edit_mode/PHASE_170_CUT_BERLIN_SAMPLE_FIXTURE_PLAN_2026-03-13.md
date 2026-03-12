# PHASE 170 CUT Berlin Sample Fixture Plan (2026-03-13)

## Input material

Project root:
- `/Users/danilagulin/work/teletape_temp/berlin`

Music track:
- `/Users/danilagulin/work/teletape_temp/albom/250623_vanpticdanyana_berlin_Punch.m4a`

## Intent

Use this material as a high-value CUT sample because it already carries:
- sync of takes by audio
- frame/scene breakdown by scenario
- music-driven montage potential
- mixed media types: video + photo

## Target lanes

### MARKER_170.BERLIN.FIXTURE
Build a deterministic fixture/manifest for CUT bootstrap and browser review.

### MARKER_170.BERLIN.BOOTSTRAP
Validate bootstrap/project-state against a real mixed-media source tree.

### MARKER_170.BERLIN.MUSIC_SYNC
Map the Punch track into a CUT-oriented music sync lane, at minimum as roadmap/recon if runtime wiring is not done yet.

## Why this matters

This sample is better than a synthetic smoke-only fixture because it exercises the exact editorial promises CUT is aiming at: shots, scenes, audio alignment, and music-aware editing.

## Asset audit snapshot

Real tree audited on 2026-03-13 at `/Users/danilagulin/work/teletape_temp/berlin`.

### Top-level buckets
- `video_gen`: 152 files, almost entirely `.mp4` outputs
- `source_gh5`: 8 files, all `.mov` camera sources
- `scene_gen`: 135 mostly image assets with one `.zip`
- `boards`: 42 storyboard/reference stills
- `Img_gen_unsorted`: 171 generated stills
- `img_gen_sorted`: 65 sorted stills
- `heros_lor`: 265 hero reference images
- `style_lor`: 180 style reference images
- `prj`: 34 editorial project files (`.prproj`, `.aep`, `.prin`)
- root audio/docs: Punch track, one extra `.m4a`, and three scenario/grok markdown notes

### Totals
- media-heavy mixed source: `151 mp4`, `8 mov`, `2 m4a`, `734 png`, `72 jpg`, `11 jpeg`
- editorial/project metadata present: `21 prproj`, `12 aep`, `3 md`
- this is enough to justify a dedicated CUT fixture profile instead of a synthetic smoke-only tree

## CUT fixture manifest direction

### Proposed bootstrap profile
- profile id: `berlin_fixture_v1`
- sandbox hint: `codex54_cut_fixture_sandbox`
- reserved port: `3211`
- launch protocol: `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_LAUNCH_AND_PORT_PROTOCOL_2026-03-13.md`

### Manifest goals
- preserve top-level bucket identity so browser fixtures can say whether they are looking at `source_gh5`, `video_gen`, `boards`, or generated stills
- keep the Punch track explicitly marked as the primary music-sync candidate
- surface scenario docs and Premiere/After Effects project files as editorial guidance, not timeline media
- make mixed video/photo/audio counts deterministic enough for bootstrap and smoke tests

### Backend return path
- `POST /api/cut/bootstrap` should return `bootstrap.profile` when `bootstrap_profile=berlin_fixture_v1`
- persisted `bootstrap_state.profile` should carry the same launch metadata and manifest summary
- `GET /api/cut/project-state` should expose that profile through `bootstrap_state` without needing UI-specific changes
