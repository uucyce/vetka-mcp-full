# Phase 170 CUT Music-Sync Handoff
**Date:** 2026-03-13
**Status:** contract seeded, store + project-state wired, ready for worker implementation

## What was completed

### Contract (C10)
- `cut_music_sync_result_v1` schema at `docs/contracts/cut_music_sync_result_v1.schema.json`
- Fields: `tempo` (bpm + confidence + time_signature), `downbeats`, `phrases` (energy + label), `cue_points` (kind + strength), `derived_from`
- Store: `load_music_sync_result()` / `save_music_sync_result()` with full validation
- 11 contract tests in `tests/phase170/test_cut_music_sync_contract.py`

### Project-state surfacing (C11)
- `music_sync_result` returned in full from `/api/cut/project-state`
- `music_summary` compact lane: bpm, confidence, phrase count, high-energy count, cue kind breakdown
- `music_sync_ready` readiness flag

### Markers
- `MARKER_170.C10.MUSIC_SYNC_CONTRACT`
- `MARKER_170.C11.MUSIC_SUMMARY_LANE`

## How cue points should promote into CUT markers

### Promotion flow (next phase)
1. Music worker generates `cut_music_sync_result_v1` with `cue_points`
2. Shell displays cue points as overlay markers on timeline (read-only)
3. User selects cue points to promote → creates `cut_time_marker_v1` entries via existing `time-marker/apply` endpoint
4. Promoted markers persist in `time_marker_bundle` and survive session reload

### Cue point kinds → marker mappings
| cue_point.kind | Promoted marker kind | Visual |
|----------------|---------------------|--------|
| `downbeat` | `beat` | thin tick on beat track |
| `phrase_start` | `section` | section boundary |
| `phrase_end` | `section` | section boundary |
| `drop` | `highlight` | high-energy anchor |
| `transient` | `insight` | transient spike |
| `silence` | `pause` | silence gap |

### API sequence
```
POST /api/cut/time-marker/apply
{
  "sandbox_root": "...",
  "project_id": "...",
  "ops": [
    {
      "op": "add_marker",
      "time_sec": <cue_point.time_sec>,
      "kind": "<mapped_kind>",
      "label": "From music cue: <cue_point.kind>",
      "source": "music_sync_promote"
    }
  ]
}
```

## PULSE integration note

PULSE is the rhythmic analysis engine — even scenes without music have inherent rhythm (BPM) and mood (major/minor). PULSE provides:
- Scene-level BPM estimation from visual motion patterns
- Mood classification (energy, valence)
- Cut density and motion volatility metrics

The `cut_music_sync_result_v1` contract handles explicit music tracks. PULSE handles implicit scene rhythm. Both feed into CUT's montage timing decisions:
- Music cue points → hard cut anchors (high confidence)
- PULSE rhythm hints → soft cut suggestions (lower confidence, context-dependent)

### JEPA role in the chain
JEPA provides scene-level embeddings that inform:
1. **Scene similarity** — which clips belong together
2. **Semantic transitions** — where scene boundaries naturally occur
3. **Search reranking** — finding relevant media by content

JEPA embeddings feed into `sync_surface` and `scene_graph` but do NOT directly generate BPM or cue points. That's PULSE's domain.

## What remains

### Worker implementation (Phase 171+)
1. `POST /api/cut/worker/music-sync-async` — onset detection, beat tracking, phrase segmentation
2. Use librosa or madmom for beat/downbeat detection
3. Use spectral flux + onset strength for cue point generation
4. Store result via `store.save_music_sync_result()`

### Shell integration (Phase 171+)
1. Display music cue overlay on timeline (non-interactive first)
2. Add "Promote to Markers" action in music summary panel
3. Show BPM and phrase structure in storyboard view

### PULSE bridge (Phase 171+)
1. Feed PULSE rhythm features alongside music cue points
2. Merge PULSE scene-BPM with music-track BPM for hybrid rhythm surface
3. Expose combined rhythm_surface in project-state (similar to sync_surface pattern)
