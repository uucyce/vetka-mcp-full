# PHASE 171 CUT Montage Engine Roadmap

**Created:** 2026-03-13
**Status:** planning
**Predecessor:** Phase 170 (VETKA CUT foundation — sync, timeline, scene graph)

## Starting point

Phase 171 does **not** start from a blank editor anymore.
By the end of Phase 170, CUT already has:
- primary NLE surface with source browser, preview, timeline, markers, trim/drag/scrub
- first-class Scene Graph viewport in CUT/NLE
- Berlin fixture lane with Punch track and reserved-port sandbox flow
- CUT-only human launcher and CUT-only app/dmg packaging gate
- music-sync -> marker bundle path and marker rendering in Scene Graph

## Vision
Phase 170 established the CUT foundation: sync pipeline (timecode → waveform → sync_surface → apply_sync_offset), timeline state machine, scene graph, music sync contract. Phase 171 takes this to a working montage engine: real workers, PULSE rhythm integration, and shell UX that lets editors act on sync + rhythm recommendations.

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

## Workstreams

### W1: Music Sync Worker
Build the actual worker that generates `cut_music_sync_result_v1` from audio tracks.

| Task | ID | Complexity | Description |
|------|----|------------|-------------|
| W1.1 | 171.1 | medium | `POST /api/cut/worker/music-sync-async` endpoint + job envelope |
| W1.2 | 171.2 | large | Onset detection + beat tracking (librosa/madmom) |
| W1.3 | 171.3 | medium | Phrase segmentation (intro/verse/chorus/drop/outro) |
| W1.4 | 171.4 | small | Cue point generation from beat grid + phrase boundaries |
| W1.5 | 171.5 | small | Integration tests with Berlin Punch track fixture |

### W2: PULSE Rhythm Bridge
Connect PULSE BPM/mood analysis to CUT timeline for implicit rhythm.

| Task | ID | Complexity | Description |
|------|----|------------|-------------|
| W2.1 | 171.6 | medium | `cut_rhythm_surface_v1` contract: merge music cues + PULSE scene-BPM |
| W2.2 | 171.7 | medium | PULSE adapter: extract BPM, energy, valence from video clips |
| W2.3 | 171.8 | small | rhythm_surface in project-state (parallel to sync_surface) |
| W2.4 | 171.9 | small | Tests for rhythm_surface generation and priority logic |

### W3: Cue → Marker Promotion
Let editors promote music/rhythm cue points into persistent timeline markers.

| Task | ID | Complexity | Description |
|------|----|------------|-------------|
| W3.1 | 171.10 | medium | `apply_promote_cues` timeline op: batch cue→marker conversion |
| W3.2 | 171.11 | small | Shell UI: cue overlay on timeline (read-only display) |
| W3.3 | 171.12 | small | Shell action: "Promote Selected Cues" button |
| W3.4 | 171.13 | small | Tests for promote op + marker persistence |

### W4: Shell UX Polish
Make sync + rhythm recommendations actionable in the editor.

| Task | ID | Complexity | Description |
|------|----|------------|-------------|
| W4.1 | 171.14 | medium | Sync status badges on timeline clips (synced/hint/unsynced) |
| W4.2 | 171.15 | medium | Lane sync_summary display in lane headers |
| W4.3 | 171.16 | small | Music summary panel in storyboard sidebar |
| W4.4 | 171.17 | medium | Context menu: "Apply Sync" + "Promote Cue" actions |
| W4.5 | 171.18 | small | Playwright E2E: sync badge visibility + apply flow |

### W5: Export Foundation
First steps toward getting CUT timelines out.

| Task | ID | Complexity | Description |
|------|----|------------|-------------|
| W5.1 | 171.19 | medium | `cut_export_v1` contract: OTIO/XML export schema |
| W5.2 | 171.20 | large | Timeline → OTIO conversion (clips, sync offsets, markers) |
| W5.3 | 171.21 | medium | `POST /api/cut/export/otio` endpoint |
| W5.4 | 171.22 | small | Export round-trip test (create → export → verify structure) |

## Immediate milestones

### M1
Roadmap + architecture freeze for the montage engine.

### M2
Montage state contract seeded and persisted in project state.

### M3
Berlin Punch track upgraded from fixture metadata to first-class music cue source.

### M4
Marker -> montage decision promotion path exists and is browser-testable.

## Priority Order
1. **W1 (Music Worker)** — enables real Berlin fixture end-to-end
2. **W3 (Cue Promotion)** — makes music analysis actionable
3. **W2 (PULSE Bridge)** — adds implicit rhythm
4. **W4 (Shell UX)** — editor productivity
5. **W5 (Export)** — gets work out of CUT

## Success Criteria
1. Berlin Punch track generates real beat grid + cue points via worker
2. PULSE provides BPM for video-only clips (no music track needed)
3. Editor can promote cue points to timeline markers
4. Sync badges show on timeline clips reflecting sync_hint status
5. At least 1 export format (OTIO) works end-to-end

## Constraints
- reserved ports remain mandatory:
  - human review `3011`
  - Codex54 sandbox `3211`
- no shared random Vite ports
- do not regress Phase 170 CUT review app/dmg lane
- keep Scene Graph as first-class viewport, not debug-only fallback

## Agent Assignment Guidance
- **Opus:** W1 (music worker), W2 (PULSE bridge), W5 (export) — backend heavy
- **Codex:** W4 (shell UX), W3.2/W3.3 (shell actions), W4.5 (Playwright) — frontend
- **Shared:** W3.1 (promote op is backend but needs shell wiring)

## Phase 170 inputs this roadmap depends on
- `docs/170_ph_VIDEO_edit_mode/PHASE_170_VETKA_CUT_ARCHITECTURE_2026-03-09.md`
- `docs/170_ph_VIDEO_edit_mode/PHASE_170_VETKA_CUT_ROADMAP_RECON_MARKERS_2026-03-09.md`
- `docs/170_ph_VIDEO_edit_mode/PHASE_170_CHECKPOINT_2026-03-13.md`
- `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_BERLIN_SAMPLE_FIXTURE_PLAN_2026-03-13.md`
- `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_PUNCH_TRACK_MUSIC_SYNC_NOTE_2026-03-13.md`
