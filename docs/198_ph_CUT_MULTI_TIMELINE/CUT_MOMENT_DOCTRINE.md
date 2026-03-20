# CUT Moment Doctrine
**Date:** 2026-03-20
**Status:** Canonical — all marker/moment logic must follow this document
**Extends:** PHASE_170_COGNITIVE_TIME_MARKERS_CONTRACT_2026-03-09.md

## Core Principle

> **The unit of editing is not a second. It is a MOMENT.**

A moment is a semantic interval bounded by one of:
- **Cut-to-cut** — from one edit point (splice) to the next
- **Pause-to-pause** — from one speech silence to the next
- **Beat-to-beat** — from one strong musical beat (downbeat) to the next

When a user presses M at timecode 00:01:23.500, CUT does NOT place a point marker at that second.
CUT **auto-detects the moment** containing that timecode and marks the entire interval.

The moment is the atomic unit across the entire CUT system:
- Timeline selection
- Favorite/negative marking
- PULSE analysis
- Auto-montage
- Export

## Hotkey Actions

### M — Mark Moment (single press)

**What it does:** Creates a full, visible `kind: 'moment'` marker on the timeline.
This is a MARKER ON STEROIDS — a standard NLE marker upgraded with auto-detection of boundaries.

**What the user sees:**
1. Presses M at any timecode
2. CUT auto-detects the moment containing that timecode (see Boundary Detection Stack below)
3. The entire moment interval highlights on the timeline — start_sec to end_sec
4. A marker appears with full visual presence: colored region, label, draggable edges
5. The moment is immediately selectable, exportable, usable in montage

**This is NOT a silent/invisible mark.** It is the most visible, most informative marker type.
It answers: "What is happening HERE?" — and shows the full extent of "here".

**Boundary detection (priority order):**
1. If timeline has edit points (cuts/splices) → moment = current clip boundaries
2. If PULSE has analyzed audio → moment = pause-to-pause interval (energy_pause + transcript_pause hybrid)
3. If PULSE has analyzed music → moment = strong beat to strong beat (downbeat boundaries)
4. Fallback (no analysis available) → moment = narrow window ±0.5s around playhead

**The user does NOT choose the boundary method.** CUT picks the best available automatically.
Multiple boundary sources can be combined (hybrid merge, see cut_audio_intel_eval.py).

### MM — Comment on Moment (double press / long press)

**What it does:** Same as M (full marker with auto-detected boundaries) + opens text input.

**Behavior:**
1. First M creates the moment marker (same as single M — full visual presence)
2. Second M (or long press) opens text input overlay on that moment
3. Creates `kind: 'comment'` marker with same `start_sec` / `end_sec`
4. Comment text stored in `text` field
5. Supports threading via `comment_thread_id`

**Key difference:** M = marker (visual, no text), MM = marker + annotation (text input).

### F — Favorite Moment

**What it does:** Marks the current moment as favorite.

**Behavior:**
1. Detects moment boundaries (same logic as M)
2. Creates `kind: 'favorite'` marker
3. Scope: **source-level** — the favorite is attached to `media_path`, not `timeline_id`
4. Therefore: visible on ALL timelines containing this clip
5. Score: default 1.0 (highest importance)

**Relationship to M:** M and F are the same entity conceptually — both mark a moment.
F = M + `kind: 'favorite'` + source scope. They share boundary detection logic.

### N — Negative Moment

**What it does:** Marks the current moment as negative (bad take, unusable footage, flawed audio).

**Behavior:**
1. Detects moment boundaries (same logic as M)
2. Creates `kind: 'negative'` marker
3. Scope: **source-level** (like favorite — attached to media, not timeline)
4. Score: 0.0 (lowest importance)
5. PULSE auto-montage EXCLUDES moments with negative markers
6. Visual: red tint / strikethrough on clip in timeline

**Use cases:**
- Bad audio (wind noise, mic bump, clipping)
- Bad take (actor flubbed, camera shake)
- Technical defect (focus miss, exposure blow)
- "Kill this" — editor decisively rejects a moment

**Why this matters:** Without N, the editor must mentally remember bad moments.
With N, PULSE knows what to skip automatically. Negative is as important as favorite.

## Moment Boundary Detection Stack

The system uses three complementary methods, already partially implemented:

### 1. Energy Pause Detection (`energy_pause_v1`)
- Source: `src/services/cut_audio_intel_eval.py` → `derive_pause_windows_from_silence()`
- Method: RMS energy envelope (20ms frames), silence threshold ≤ 0.08
- Minimum silence: 250ms
- Creates boundaries at silence → speech transitions
- Confidence: 0.82

### 2. Transcript Pause Detection (`transcript_pause_v1`)
- Source: `src/services/cut_audio_intel_eval.py` → `transcript_pause_merge()`
- Method: Whisper transcription segments, gap threshold ≤ 0.35s
- Max window: 6 seconds
- Creates boundaries at natural speech pauses
- Confidence: 0.88

### 3. Hybrid Merge (`hybrid`)
- Source: `src/services/cut_audio_intel_eval.py` → `hybrid_merge_slices()`
- Combines methods 1+2, merges overlapping windows within 0.15s
- Takes best confidence from either
- Primary method for moment detection

### 4. Beat Detection (PULSE BPM) — TO BE INTEGRATED
- Source: PULSE audio analysis → `bpm_audio` markers
- Method: onset detection, downbeat identification
- Creates boundaries at strong musical beats
- For music-driven content (music videos, trailers, rhythmic editing)
- NOT YET connected to moment boundary detection — needs wiring

### 5. Edit Point Detection (Cut-to-Cut) — SIMPLEST
- Source: Timeline lane data (clip boundaries)
- Method: `clip.startTime` and `clip.startTime + clip.duration` of current clip
- No analysis needed — boundaries are explicit in timeline
- Highest priority when available (user already made edit decisions)

## Interaction with PULSE BPM System

PULSE generates 4 types of analytical markers:

| PULSE Kind | What it detects | Moment boundary? |
|-----------|----------------|------------------|
| `bpm_audio` | Musical beats / onset | Yes — strong beats define moment boundaries for music content |
| `bpm_visual` | Visual cuts / scene changes | Yes — these ARE edit points (cut-to-cut) |
| `bpm_script` | Narrative events / dramatic beats | No — these overlay ON moments, don't define boundaries |
| `sync_point` | 2-3 sources coincide ±2 frames | No — these are computed FROM moments, not boundaries |

**Bold/sync markers** appear when 2+ BPM sources align within ±2 frames.
These are COMPUTED from moment boundaries, not the other way around.

## Interaction with Auto-Montage

Auto-montage modes use moment markers as primary input:

| Mode | Source markers | Logic |
|------|---------------|-------|
| `favorites` | `kind: 'favorite'` moments | Include ONLY favorited moments |
| `script` | `kind: 'bpm_script'` events | Build timeline from narrative beats |
| `music` | `kind: 'sync_point'` + `bpm_audio` | Cut on musical sync points |

**Negative exclusion rule:** In ALL modes, moments with `kind: 'negative'` are EXCLUDED.
This is the primary purpose of N — automatic exclusion from generated timelines.

## Multi-Timeline Implications (Phase 198)

Per CUT_MULTI_INSTANCE doctrine (RECON_FCP7_MULTI_INSTANCE_TIMELINES.md):

- M (moment) and MM (comment) are **timeline-scoped** — `timeline_id` set
- F (favorite) and N (negative) are **source-scoped** — `media_path` set, no `timeline_id`
- Source-scoped markers project onto ALL timelines containing that clip
- Timeline-scoped markers visible only on their timeline

**Example flow:**
1. Editor watches source in Source Monitor, presses F → favorite on source
2. Opens Timeline A, drags clip in → favorite visible on clip
3. Opens Timeline B, same clip → SAME favorite visible (not copied — projected)
4. Editor presses M on Timeline A at 00:05:00 → moment marker on Timeline A only
5. Timeline B does NOT show this M — it's timeline-scoped

## SRT Transport

Moments export to SRT for external sharing (player lab, review tools):

```srt
1
00:01:23,000 --> 00:01:26,500
{favorite:} Great reaction shot

2
00:02:10,200 --> 00:02:11,800
{negative:} Audio clipping - unusable

3
00:03:45,100 --> 00:03:48,300
{comment:thread_abc123} Tighten this pause
```

Format: `{kind:thread_id} text`

## Kind Enum (Complete)

```typescript
type MarkerKind =
  // Editorial (user-created)
  | 'moment'       // M — full marker with auto-detected moment boundaries
  | 'favorite'     // F — favorite moment (source-scoped)
  | 'negative'     // N — negative moment (source-scoped, excludes from montage)
  | 'comment'      // MM — comment on moment (with text)
  | 'cam'          // CAM system auto-mark
  | 'insight'      // AI insight annotation
  | 'chat'         // Chat thread attachment

  // PULSE analytical (auto-generated)
  | 'bpm_audio'    // Audio beat detection
  | 'bpm_visual'   // Visual cut detection
  | 'bpm_script'   // Script/narrative event
  | 'sync_point'   // Multi-source synchronization (bold marker)
```

**Total: 11 kinds** (9 existing + `moment` + `negative`)

## Migration Notes

### From Phase 170 contract:
- `favorite` → unchanged, but now explicitly source-scoped
- `comment` → triggered by MM (double press), not M
- `cam`, `insight`, `chat` → unchanged

### New in this doctrine:
- `moment` kind — M single press, silent mark
- `negative` kind — N press, exclusion mark
- Moment boundary auto-detection as core behavior
- Beat-to-beat boundaries (PULSE BPM integration)
- Explicit M/MM/F/N hotkey contract

### Code changes needed:
1. Add `'moment'` and `'negative'` to `MarkerKind` union in `useCutEditorStore.ts`
2. Add `'negative'` color to TimelineTrackView marker colors (red: `#ef4444`)
3. Add `'moment'` color to TimelineTrackView marker colors (white: `#e5e7eb`)
4. Wire M/MM/F/N keyboard shortcuts in CUT panel
5. Connect PULSE beat detection to moment boundary resolution
6. Add negative exclusion filter to auto-montage logic
7. Update SRT bridge to handle `moment` and `negative` kinds

## Markers
1. `MARKER_198.MOMENT_DOCTRINE` — this document
2. `MARKER_198.MOMENT_M` — M hotkey implementation
3. `MARKER_198.MOMENT_MM` — MM comment implementation
4. `MARKER_198.MOMENT_F` — F favorite (already exists as MARKER_170)
5. `MARKER_198.MOMENT_N` — N negative implementation
6. `MARKER_198.MOMENT_BOUNDARY_STACK` — boundary detection priority
