# Phase 173 — CUT Interactive Editor

> **Goal:** Turn CUT from "read-only viewer with export" → "interactive editor you can actually cut video in"
>
> **Prerequisite phases:** 170 (foundation), 171 (montage engine), 172 (backend backbone)
>
> **Two zones:** Backend (Opus) | Frontend (Codex)

---

## Architecture Decision

Phase 170-172 built the data layer: timeline state, workers, sync, export, scene detection.
Phase 171 added montage intelligence: music cues, rhythm surface, marker promotion.

**Phase 173 bridges the gap:** wire backend capabilities into interactive UI.

---

## Workstream A — Backend (Opus)

### 173.1 Undo/Redo Service
- `src/services/cut_undo_redo.py` — edit command stack
- Operations: add_clip, remove_clip, move_clip, trim_clip, split_clip, add_marker, remove_marker
- Each op = `(forward_patch, reverse_patch)` pair stored in stack
- Max stack depth: 100 (configurable)
- Persistence: `cut_runtime/state/undo_stack.json` (survives reload)
- API: `POST /api/cut/undo`, `POST /api/cut/redo`, `GET /api/cut/undo-stack` (depth + labels)

### 173.2 Ripple/Insert Edit Operations
- Extend `POST /api/cut/timeline/apply` with new op types:
  - `ripple_delete` — remove clip, shift all subsequent clips left
  - `insert_at` — insert clip at timecode, push subsequent clips right
  - `overwrite_at` — overwrite range, no shift
  - `split_at` — split clip at playhead into two clips
- Each op produces undo pair (173.1)
- Contract: `cut_timeline_op_v2` extends existing op schema

### 173.3 Scene Detection → Timeline Integration
- New endpoint: `POST /api/cut/scene-detect-and-apply`
- Uses `cut_scene_detector.py` (from 172.19) on source media
- Auto-creates clips at scene boundaries on a new lane
- Returns lane_id + clip_ids for UI to display
- Links scene graph nodes to created clips

### 173.4 Real-time Project State via WebSocket
- SocketIO channel: `cut:project-state-update`
- Emits on: any timeline/marker/montage mutation
- Payload: `{event_type, changed_keys[], timestamp, actor}`
- Enables multi-agent editing awareness (Codex A edits → Codex B sees)
- Debounce: 100ms (batch rapid edits)

### 173.5 Montage Decision Ranking Engine
- `src/services/cut_montage_ranker.py`
- Inputs: all cue sources (transcript, pause, music, scene, manual)
- Scoring: weighted confidence × recency × editorial_intent alignment
- Output: ranked `MontageDecision[]` with composite_score
- API: `GET /api/cut/montage/suggestions?limit=10`
- Powers "smart cut" — suggest where to cut based on all intelligence

### 173.6 Clip Proxy Generation Worker
- `POST /api/cut/worker/proxy-generate-async`
- FFmpeg transcode: source → 720p H.264 proxy (fast decode)
- Stores in `cut_storage/proxies/`
- Enables smooth playback of 4K+ sources
- Media proxy endpoint (172) serves proxy if available, else original

---

## Workstream B — Frontend (Codex)

### 173.10 Audio Playback Engine
- Wire Web Audio API to timeline playback
- AudioContext → source nodes per lane → GainNode (volume) → destination
- Respect mute/solo/volume from useCutEditorStore
- Sync audio currentTime with video element
- Audio scrub: play small buffer on seek/drag

### 173.11 Undo/Redo UI + Keyboard
- Cmd+Z / Cmd+Shift+Z wired to `POST /api/cut/undo` / `/redo`
- Undo stack indicator in TransportBar (count badge)
- Toast notification on undo/redo ("Undid: Remove clip_03")

### 173.12 Multi-Clip Selection + Bulk Ops
- Shift+Click range select, Cmd+Click toggle select
- Selected clips: highlight border, group drag
- Delete selection → ripple_delete batch
- Copy/Paste clips (Cmd+C/V) with offset

### 173.13 Clip Split at Playhead
- S key or Razor tool icon → split clip at current playhead
- Visual: blade cursor when razor active
- Uses `split_at` op from 173.2
- Undo-able (173.11)

### 173.14 Montage Suggestions Panel
- New sidebar panel or overlay: "Smart Cut Suggestions"
- Calls `GET /api/cut/montage/suggestions`
- Each suggestion: timecode, source (music/pause/transcript), score, preview
- Click suggestion → seek to timecode
- "Apply" → creates marker or split
- "Dismiss" → add to rejected decisions

### 173.15 Proxy Toggle + Quality Indicator
- UI toggle: "Proxy" / "Full Quality" in TransportBar
- Badge showing current playback resolution
- Auto-switch to proxy when timeline is playing, full on pause (optional)

### 173.16 Lane Volume Sliders
- Visual fader per lane in TimelineTrackView lane headers
- Drag to adjust, double-click to reset to 0dB
- Wired to laneVolumes in store + Web Audio GainNode

### 173.17 Scene Detection UI
- Button in TransportBar: "Detect Scenes"
- Calls 173.3 endpoint
- Shows progress (job polling)
- Results: new lane appears with auto-detected clips
- Color-coded by scene boundary confidence

### 173.18 Timeline Snap Improvements
- Snap to: clip edges, markers, playhead, beat grid (from music sync)
- Visual snap indicator (yellow line)
- Hold Alt to disable snap temporarily

---

## Test Strategy

| Zone | Test Type | Owner |
|------|-----------|-------|
| 173.1-173.6 | pytest unit + API | Opus |
| 173.10-173.18 | Playwright E2E + component | Codex |
| Integration | pytest + Playwright | Both |

---

## Priority Order

**Critical path (Codex blocked on these):**
1. 173.1 Undo/Redo Service ← Codex needs this for 173.11
2. 173.2 Ripple/Insert Ops ← Codex needs for 173.12, 173.13
3. 173.4 WebSocket updates ← Codex needs for reactive UI

**Parallel (Codex can start immediately):**
- 173.10 Audio Playback (no backend dependency)
- 173.16 Lane Volume Sliders (store already has data)
- 173.18 Timeline Snap (pure frontend)

**After backend ready:**
- 173.11 Undo/Redo UI (needs 173.1)
- 173.12 Multi-Clip (needs 173.2)
- 173.13 Clip Split (needs 173.2)
- 173.14 Montage Panel (needs 173.5)
- 173.15 Proxy Toggle (needs 173.6)
- 173.17 Scene Detection UI (needs 173.3)

---

## Exit Criteria

- [ ] User can split, trim, delete, move clips with undo/redo
- [ ] Audio plays in sync with video across lanes
- [ ] Smart cut suggestions appear from montage engine
- [ ] Scenes auto-detected and visualized
- [ ] Export to Premiere/FCPXML includes all edits
- [ ] 90%+ test coverage on new endpoints
