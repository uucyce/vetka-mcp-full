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

## Workstream C — Integration & UX (Codex + Opus)

### 173.20 Player Lab Integration UI
- Import button in TransportBar / Source Browser → file picker for Player Lab JSON
- Calls existing `POST /api/cut/markers/import-player-lab`
- Show import preview: how many markers, types, timecodes
- After import → markers appear on timeline + toast "Imported 42 markers"
- Backend already exists (Phase 170), this is UI wiring

### 173.21 Media Import Panel
- "Import Media" button in Source Browser (left panel)
- Supports: drag-and-drop files, folder picker, URL paste
- On import → triggers bootstrap-async → shows progress
- After bootstrap: clips populate Source Browser with thumbnails
- Calls existing `POST /api/cut/bootstrap-async`
- Import history sidebar (recent imports)

### 173.22 Program Monitor (Preview Window)
- Right panel: dedicated Program Monitor (Premiere-style)
- Shows current playhead frame from active timeline
- Independent from Source Browser video preview
- Scope: waveform scope, vectorscope, histogram (future)
- Full-screen toggle (double-click or F key)
- Timecode overlay with frame-accurate display
- Mark In/Out directly on monitor

### 173.23 Dual Timeline — Assembly + Final Cut
- **Upper timeline:** Auto-montage assembly lane (synced, ranked clips from montage engine)
  - Read-only, auto-populated from montage suggestions + sync results
  - Clips color-coded by source: 🎵 music-aligned, ⏸ pause-cut, 📝 transcript-driven
  - Acts as a "palette" — user drags clips FROM here
- **Lower timeline:** Final Cut lane (user's edit)
  - Standard interactive timeline (all 173.x editing ops)
  - User drags/copies clips from upper → lower
  - This IS the export source
- Backend: `POST /api/cut/assembly-timeline/generate` — auto-build assembly from ranked montage decisions
- Store: `activeTimeline: 'assembly' | 'final'` toggle
- Drag-between: cross-timeline drag-and-drop with auto-ripple-insert

### 173.24 VETKA Chat + Agent Phonebook Window
- Floating MiniChat (from Phase 154 MiniChat component) embedded in CUT
- Agent phonebook panel: list of available agents with status (online/busy/offline)
  - Dragon teams (Bronze/Silver/Gold)
  - Codex agents
  - Grok researcher
- Direct chat with agents: "@dragon analyze this timeline for pacing"
- Chat context: current project_id + timeline_id auto-injected
- History: conversation per project, persisted

### 173.25 VETKA Core Memory + MCC TaskBoard Panel
- Panel in CUT sidebar: project memory view
  - Key decisions, architecture notes, montage preferences
  - Pulled from VETKA Qdrant knowledge base
- MCC TaskBoard mini-view (from Phase 154 MiniTasks)
  - Show tasks for current CUT project_id
  - Create/claim/complete tasks inline
  - Filter by phase, agent, status

### 173.26 Video Export + Social Cross-Post
- Export menu in TransportBar:
  - "Export Video" → FFmpeg render: final timeline → H.264/ProRes output
  - Resolution presets: 1080p, 4K, Instagram (1:1), TikTok (9:16), YouTube (16:9)
  - Progress bar with ETA
- Cross-post panel (after export):
  - One-click publish to: YouTube, Instagram, TikTok, Telegram, VK
  - Title, description, tags per platform
  - Thumbnail selector (from scene boundaries)
  - Schedule publish (now / date+time)
- Backend: `POST /api/cut/export/render-video-async` (FFmpeg render job)
- Backend: `POST /api/cut/export/cross-post` (social API integrations)

---

## Vision Horizon

| Task | Horizon | Notes |
|------|---------|-------|
| 173.1-173.6 | **Now** | Backend foundation — this session |
| 173.10-173.18 | **Now** | Core editing UX — Codex |
| 173.20-173.21 | **Next sprint** | Import/Player Lab — small but needed |
| 173.22-173.23 | **Next sprint** | Monitor + Dual Timeline — the killer feature |
| 173.24-173.25 | **Phase 174+** | VETKA integration — deep ecosystem |
| 173.26 | **Phase 175+** | Export + social — requires social API keys |

---

## Exit Criteria

- [ ] User can split, trim, delete, move clips with undo/redo
- [ ] Audio plays in sync with video across lanes
- [ ] Smart cut suggestions appear from montage engine
- [ ] Scenes auto-detected and visualized
- [ ] Media can be imported via UI (drag-and-drop / file picker)
- [ ] Player Lab markers importable with preview
- [ ] Program Monitor shows current frame independently
- [ ] Dual timeline: assembly palette → final cut drag workflow
- [ ] Export to Premiere/FCPXML includes all edits
- [ ] 90%+ test coverage on new endpoints
