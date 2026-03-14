# Codex Brief — Phase 173: CUT Interactive Editor (Frontend)

> **Phase:** 173 | **Owner:** Codex | **Backend:** Opus (bold-dubinsky worktree)
> **Goal:** Make CUT an interactive video editor. Right now it's 85% visualization — we need interactivity.

---

## YOUR ZONE: `client/src/components/cut/`

You own ALL frontend CUT components. Backend endpoints are being built by Opus in parallel.

---

## IMMEDIATE TASKS (no backend dependency)

### 173.10 Audio Playback Engine
**Files:** New `useAudioEngine.ts` hook + modify `CutEditorLayout.tsx`, `TimelineTrackView.tsx`

Wire Web Audio API to timeline:
```
AudioContext → per-lane MediaElementSourceNode → GainNode (volume) → destination
```

- Create audio elements for each lane's clips (use media-proxy URL)
- Sync audio `currentTime` with `useCutEditorStore.currentTime`
- Respect `mutedLanes`, `soloLanes`, `laneVolumes` from store
- Audio scrub: on seek/drag, play 200ms buffer at target position
- Cleanup: disconnect nodes on unmount

**Test:** Play a 2-lane timeline (video + audio_sync). Both tracks audible. Mute one → silence.

### 173.16 Lane Volume Sliders
**Files:** Modify `TimelineTrackView.tsx` lane headers

- Add vertical slider (0–100%) in each lane header
- Wire to `laneVolumes` in store
- Double-click → reset to 100% (0dB)
- Visual: thin slider, matches Premiere dark style

**Test:** Drag slider → volume changes in real-time via 173.10 audio engine.

### 173.18 Timeline Snap Improvements
**Files:** Modify `TimelineTrackView.tsx` snap logic

Current snap: clip edges only (5px threshold).
Add snap targets:
- Marker positions (from `markers` in store)
- Playhead position
- Beat grid (from `syncSurface.music_sync_result.beat_grid` if available)
- Other clip in/out points across lanes

Visual: yellow vertical line at snap point.
Hold `Alt` to temporarily disable snap.

**Test:** Drag clip near marker → snaps. Hold Alt → no snap.

---

## TASKS AFTER BACKEND READY

### 173.11 Undo/Redo UI + Keyboard
**Depends on:** 173.1 (backend undo service)
**Files:** Modify `TransportBar.tsx`, new keyboard handler

- `Cmd+Z` → `POST /api/cut/undo` → refresh project state
- `Cmd+Shift+Z` → `POST /api/cut/redo`
- Badge in TransportBar: undo stack depth count
- Toast on undo/redo: "Undid: Remove clip_03"

### 173.12 Multi-Clip Selection + Bulk Ops
**Depends on:** 173.2 (ripple/insert ops)
**Files:** Modify `TimelineTrackView.tsx`

- `Shift+Click` → range select (between current selection and clicked)
- `Cmd+Click` → toggle individual clip in selection
- Selected clips: highlighted border (blue outline)
- `Delete` on selection → batch `ripple_delete` call
- `Cmd+C` / `Cmd+V` → copy/paste clips with time offset
- Group drag: move all selected clips together

### 173.13 Clip Split at Playhead
**Depends on:** 173.2 (split_at op)
**Files:** Modify `TransportBar.tsx` (razor button), `TimelineTrackView.tsx` (split visual)

- `S` key or Razor tool button → split clip at playhead
- Visual: blade cursor (crosshair) when razor mode active
- After split: two clips replace original, both selected
- Undo-able via 173.11

### 173.14 Montage Suggestions Panel
**Depends on:** 173.5 (ranking engine API)
**Files:** New `MontageSuggestionsPanel.tsx`

- Sidebar panel (right side, below ClipInspector)
- Calls `GET /api/cut/montage/suggestions?limit=10`
- Each suggestion card:
  - Timecode badge
  - Source icon (🎵 music, ⏸ pause, 📝 transcript, 🎬 scene)
  - Confidence score bar (0-1)
  - "Apply" button → creates marker or split at timecode
  - "Dismiss" button → POST reject to montage state
- Click card → seek timeline to that timecode
- Auto-refresh when project state changes

### 173.15 Proxy Toggle
**Depends on:** 173.6 (proxy generation)
**Files:** Modify `TransportBar.tsx`, `VideoPreview.tsx`

- Toggle button: "HQ" / "Proxy" in TransportBar
- VideoPreview: switch media-proxy URL param `?prefer_proxy=1`
- Badge: show current resolution (1080p / 720p proxy)

### 173.17 Scene Detection UI
**Depends on:** 173.3 (scene detect endpoint)
**Files:** Modify `TransportBar.tsx` (button), new `SceneDetectProgress.tsx`

- Button in TransportBar: scissors icon + "Detect Scenes"
- Click → `POST /api/cut/scene-detect-and-apply`
- Show progress: job polling with % indicator
- On complete: new lane appears with auto-detected scene clips
- Each scene clip colored by boundary confidence (green = strong, yellow = weak)

---

## STORE EXTENSIONS NEEDED

Add to `useCutEditorStore.ts`:
```typescript
// 173.10 Audio
audioReady: boolean
setAudioReady: (ready: boolean) => void

// 173.12 Multi-select
selectedClipIds: Set<string>  // was: selectedClipId (single)
toggleClipSelection: (clipId: string) => void
rangeSelectClips: (fromId: string, toId: string) => void
clearSelection: () => void

// 173.13 Razor
razorMode: boolean
setRazorMode: (active: boolean) => void

// 173.14 Montage
montageSuggestions: MontageDecision[]
refreshSuggestions: () => Promise<void>

// 173.15 Proxy
preferProxy: boolean
toggleProxy: () => void

// 173.11 Undo
undoDepth: number
redoDepth: number
performUndo: () => Promise<void>
performRedo: () => Promise<void>
```

---

## API ENDPOINTS YOU'LL CALL

| Endpoint | Method | When |
|----------|--------|------|
| `/api/cut/undo` | POST | Cmd+Z |
| `/api/cut/redo` | POST | Cmd+Shift+Z |
| `/api/cut/undo-stack` | GET | Show depth badge |
| `/api/cut/timeline/apply` | POST | Split, delete, insert clips |
| `/api/cut/montage/suggestions` | GET | Montage panel refresh |
| `/api/cut/scene-detect-and-apply` | POST | Scene detect button |
| `/api/cut/worker/proxy-generate-async` | POST | Proxy generation |
| `/api/cut/job/{job_id}` | GET | Poll async jobs |
| `/api/cut/media-proxy` | GET | Video/audio playback |

---

## STYLE GUIDE (from Phase 170 audit)

- Dark theme (Premiere Pro parity)
- Monochrome SVG icons (no emoji)
- Colors: chrome neutral (gray), only clips/markers/VU get color
- 1px borders, tight spacing
- Fonts: system monospace for timecodes

---

## TASK BOARD IDS

Your tasks will be on the board. Use MCP protocol:
1. `mycelium_task_board action=claim task_id=<id> assigned_to=codex agent_type=codex`
2. Work
3. `vetka_git_commit message="phase173.XX: description [task:tb_xxxx]"`

**NEVER edit task_board.json directly.** Always use MCP tools.

---

## PRIORITY ORDER

1. 🟢 **173.10** Audio Playback (start NOW — no dependency)
2. 🟢 **173.16** Lane Volume Sliders (start NOW)
3. 🟢 **173.18** Timeline Snap (start NOW)
4. 🟡 **173.11** Undo/Redo UI (wait for backend 173.1)
5. 🟡 **173.12** Multi-Clip Select (wait for backend 173.2)
6. 🟡 **173.13** Clip Split (wait for backend 173.2)
7. 🟡 **173.14** Montage Panel (wait for backend 173.5)
8. 🟡 **173.17** Scene Detect UI (wait for backend 173.3)
9. 🔵 **173.15** Proxy Toggle (wait for backend 173.6)
