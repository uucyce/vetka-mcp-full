# Phase 171: CUT Montage Engine — Rhythm + Worker + Shell
**Created:** 2026-03-13
**Status:** planning
**Predecessor:** Phase 170 (VETKA CUT foundation — sync, timeline, scene graph)

## Vision
Phase 170 established the CUT foundation: sync pipeline (timecode → waveform → sync_surface → apply_sync_offset), timeline state machine, scene graph, music sync contract. Phase 171 takes this to a working montage engine: real workers, PULSE rhythm integration, and shell UX that lets editors act on sync + rhythm recommendations.

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

## Agent Assignment Guidance
- **Opus:** W1 (music worker), W2 (PULSE bridge), W5 (export) — backend heavy
- **Codex:** W4 (shell UX), W3.2/W3.3 (shell actions), W4.5 (Playwright) — frontend
- **Shared:** W3.1 (promote op is backend but needs shell wiring)
