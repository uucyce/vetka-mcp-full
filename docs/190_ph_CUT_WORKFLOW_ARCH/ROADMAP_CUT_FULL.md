# CUT Full Roadmap v2
# From current state to shipping NLE product

> **NOTE:** For current feature status verified from code, see **[docs/VETKA_CUT_MANUAL.md](../VETKA_CUT_MANUAL.md)**.
> This roadmap defines WHAT to build. The manual shows WHAT IS BUILT.

**Date:** 2026-03-19
**Basis:** CUT_UNIFIED_VISION.md v2 (canonical source of truth)
**Audience:** Any agent (including Ollama 8B). Each task is self-contained.
**Status:** CANONICAL v2 — supersedes all previous roadmaps

### Mandatory references for EVERY CUT task

| Document | Purpose |
|----------|---------|
| `docs/190_ph_CUT_WORKFLOW_ARCH/CUT_UNIFIED_VISION.md` | Single source of truth: panels, functions, hotkeys, contracts |
| `docs/190_ph_CUT_WORKFLOW_ARCH/CUT_TARGET_ARCHITECTURE.md` | Deep architecture: DAG model, routing, BPM, markers |
| `docs/190_ph_CUT_WORKFLOW_ARCH/CUT_DATA_MODEL.md` | Node/Edge type schemas |
| `docs/190_ph_CUT_WORKFLOW_ARCH/ROADMAP_CUT_FULL.md` | This file — implementation plan |

---

## Current State Summary

### Frontend: 22 components, ~8500 lines
- Layout (CutEditorLayoutV2) — working
- Timeline (TimelineTrackView, 1687 lines) — working
- VideoPreview — working but NO source/program split
- ScriptPanel, DAGProjectPanel, ProjectPanel — working
- StorySpace3D, PulseInspector, ClipInspector — components exist, NOT mounted
- 3 Zustand stores (EditorStore, PanelSyncStore, PanelLayoutStore) — working but disconnected

### Backend: 22 Python files, ~16000 lines
- cut_routes.py (7818 lines) — all CUT API endpoints (monolith)
- PULSE pipeline (conductor, critics, camelot, montage) — fully working
- Export (Premiere XML, FCPXML, EDL, SRT) — fully working
- Undo/redo (cut_undo_redo.py) — working
- Proxy generation (cut_proxy_worker.py) — working

### Key gaps
- Source ≠ Program monitor (broken — same feed)
- PanelSyncStore → EditorStore bridge missing
- No panel focus system
- No track controls (lock/mute/solo/target)
- No context menu (right-click)
- No save/autosave
- No selection model beyond single clip
- No master render/export dialog
- Inspector/Clip/StorySpace not mounted in layout

---

## WAVE 0: UI CLEANUP
**Goal:** Remove dead code, fix layout structure.
**Can run PARALLEL with Wave 1.**

### CUT-W0.1: Delete legacy files
- Delete `CutEditorLayout.tsx` (799 lines) — replaced by V2
- Delete `SourceBrowser.tsx` (540 lines) — replaced by ProjectPanel
- Verify: `grep -r "CutEditorLayout\b" client/src/` and `grep -r "SourceBrowser" client/src/`
- **Files:** `client/src/components/cut/CutEditorLayout.tsx`, `SourceBrowser.tsx`
- **Complexity:** low
- **Status:** done_worktree (CUT-0.1)

### CUT-W0.2: Remove duplicate Program Monitor from layout
- In `CutEditorLayoutV2.tsx`: right_top renders extra Program Monitor
- Fix: ensure exactly ONE Source Monitor (left) and ONE Program Monitor (right)
- **Files:** `CutEditorLayoutV2.tsx`
- **Complexity:** medium
- **Status:** done_worktree (CUT-0.2)

### CUT-W0.3: TransportBar → MonitorTransport + TimelineToolbar
- Split monolithic TransportBar.tsx (671 lines) into:
  - `MonitorTransport.tsx` (~150 lines) — scrubber + timecode + play/JKL + IN/OUT, embedded under each monitor
  - `TimelineToolbar.tsx` (~50 lines) — snap toggle + zoom slider + linked selection toggle
- Delete export buttons, speed display, "Scenes" button from toolbar
- **Files:** `TransportBar.tsx` (delete), create `MonitorTransport.tsx`, `TimelineToolbar.tsx`
- **Complexity:** high
- **Status:** done_worktree (CUT-0.3)

### CUT-W0.4: StorySpace 3D — remove from timeline area
- Move from floating-over-timeline to tab in Analysis group (left column)
- **Files:** `CutEditorLayoutV2.tsx`, `StorySpace3D.tsx`
- **Complexity:** low
- **Status:** done_worktree (CUT-0.4)

### CUT-W0.5: Restore Inspector/Clip/StorySpace as tabs
- Mount PulseInspector, ClipInspector, StorySpace3D as tabs in Analysis tab group
- Currently these components return null or are not imported
- **Files:** `CutEditorLayoutV2.tsx`, `PulseInspector.tsx`, `ClipInspector.tsx`, `StorySpace3D.tsx`
- **Complexity:** medium

---

## WAVE 1: WIRING (fix broken connections)
**Goal:** Connect stores, split feeds, add focus. Zero new features.
**This is the MOST CRITICAL wave — everything else depends on it.**

### CUT-W1.1: PanelSyncStore → EditorStore bridge
- **Problem:** PanelSyncStore writes (from Script/DAG/StorySpace clicks) never reach EditorStore (which VideoPreview/Timeline read)
- **Fix:** Subscribe EditorStore to PanelSyncStore changes:
  - `selectedAssetPath` → `setSourceMedia()`
  - `activeSceneId` → timeline scroll + DAG highlight
- **Files:** `useCutEditorStore.ts`, `usePanelSyncStore.ts`
- **Complexity:** medium

### CUT-W1.2: Panel Focus system
- Add to `useCutEditorStore.ts`:
  ```typescript
  focusedPanel: 'source' | 'program' | 'timeline' | 'project' | 'script' | 'dag' | null
  setFocusedPanel: (panel) => void
  ```
- Each panel: `onMouseDown={() => setFocusedPanel('timeline')}`
- Visual: focused panel gets `border: 1px solid #4A9EFF`
- Wire hotkey scope: playback commands → focused monitor. Editing → only when timeline focused.
- **Files:** `useCutEditorStore.ts`, all panel components, `useCutHotkeys.ts`
- **Complexity:** medium

### CUT-W1.3: Source/Program feed split
- Add to `useCutEditorStore.ts`:
  ```typescript
  sourceMediaPath: string | null
  programMediaPath: string | null
  setSourceMedia: (path) => void
  setProgramMedia: (path) => void
  ```
- VideoPreview: accept `feed: 'source' | 'program'` prop
  - `feed='source'` → reads `sourceMediaPath`
  - `feed='program'` → reads `programMediaPath`
- Layout: `<VideoPreview feed="source" />` left, `<VideoPreview feed="program" />` right
- **Files:** `useCutEditorStore.ts`, `VideoPreview.tsx`, `CutEditorLayoutV2.tsx`
- **Complexity:** medium

### CUT-W1.4: Separate Source marks and Sequence marks
- Add to store:
  ```typescript
  sourceMarkIn: number | null
  sourceMarkOut: number | null
  sequenceMarkIn: number | null
  sequenceMarkOut: number | null
  ```
- `I` key: if focused=source → sourceMarkIn. If focused=program → sequenceMarkIn.
- `O` key: same logic.
- Display: IN/OUT indicators on MonitorTransport reflect the correct pair.
- **Files:** `useCutEditorStore.ts`, `MonitorTransport.tsx`, hotkey handler
- **Complexity:** medium

---

## WAVE 2: TRACK CONTROLS + DIRECTION
**Goal:** Track headers, source patching, DAG direction fix.
**Depends on:** Wave 1 (store split done)

### CUT-W2.1: Track header controls (lock/mute/solo/enable/target)
- Each track header (left of timeline) gets:
  - Lock icon (padlock SVG, monochrome white)
  - Mute icon (M SVG)
  - Solo icon (S SVG)
  - Enable/Disable (eye SVG, video tracks only)
  - Target indicator (dot, for insert/overwrite destination)
- Add to `Track` interface in store:
  ```typescript
  locked: boolean; muted: boolean; solo: boolean; enabled: boolean; targeted: boolean
  ```
- Visual style: monochrome white SVG, 16x16, stroke only, 1.5px. Active = filled, inactive = outline.
- **Files:** `TimelineTrackView.tsx` (track header area), `useCutEditorStore.ts`, new SVG icons
- **Complexity:** high

### CUT-W2.2: Source patching / destination targeting
- When user presses Insert (,) or Overwrite (.):
  - Source clip V channel → targeted V track
  - Source clip A channel → targeted A track
- Visual: patch indicator connecting source channel labels to destination track headers
- **Files:** `useCutEditorStore.ts`, `TimelineTrackView.tsx`, hotkey handler
- **Complexity:** high
- **Depends on:** CUT-W2.1 (track targeting exists)

### CUT-W2.3: DAG Y-axis flip (START bottom)
- Fix DAGProjectPanel: Y-axis = film chronology, bottom = START, top = END
- Add Flip Y toggle button (view option only)
- Fix hardcoded 'main' timelineId
- **Files:** `DAGProjectPanel.tsx`
- **Complexity:** medium
- **Status:** done_worktree (CUT-2.2, partial)

### CUT-W2.4: Source Monitor label fix
- Ensure Source and Program monitors have clear, consistent labels
- "SOURCE" and "PROGRAM" in top-left corner of each monitor
- **Files:** `CutEditorLayoutV2.tsx` or `VideoPreview.tsx`
- **Complexity:** low

---

## WAVE 3: TIER 1 EDITING HOTKEYS
**Goal:** Minimum editing functionality. Without these, it's not an NLE.
**Depends on:** Wave 1 (focus system), Wave 2 (track targeting)

### CUT-W3.1: Split at playhead (⌘K) + Ripple Delete (⌥Delete)
- Split: find clip(s) under playhead on targeted tracks → split into two clips
- Ripple Delete: delete selected clip(s) → close gap by shifting subsequent clips
- Backend: POST /cut/timeline/apply with action=split_clip / ripple_delete
- **Files:** hotkey handler, `TimelineTrackView.tsx`, `cut_routes.py`
- **Complexity:** medium

### CUT-W3.2: Insert/Overwrite (,/.) with track targeting
- Insert (,): insert source clip at playhead → push everything after right
- Overwrite (.): overwrite at playhead → no ripple, clips get covered
- Must respect track targeting from W2.2
- Source clip range = sourceMarkIn → sourceMarkOut
- **Files:** hotkey handler, `cut_routes.py`
- **Complexity:** high
- **Depends on:** CUT-W2.2

### CUT-W3.3: Navigate edit points (↑/↓)
- ↑ = jump playhead to previous edit point (cut between clips)
- ↓ = jump playhead to next edit point
- **Files:** hotkey handler, `useCutEditorStore.ts`
- **Complexity:** low

### CUT-W3.4: JKL Progressive Shuttle
- J = reverse playback (1x). JJ = 2x reverse. JJJ = 4x.
- K = pause.
- L = forward playback (1x). LL = 2x. LLL = 4x.
- K+J = slow reverse. K+L = slow forward.
- Must be panel-scoped: controls whichever monitor has focus.
- **Files:** hotkey handler, `VideoPreview.tsx`
- **Complexity:** medium

### CUT-W3.5: 5-frame step + Clear In/Out
- ⇧← / ⇧→ = step 5 frames
- ⌥I = clear IN point. ⌥O = clear OUT point. ⌘⇧X = clear both.
- **Files:** hotkey handler
- **Complexity:** low

### CUT-W3.6: Tool State Machine (V/C selection)
- V = Selection tool (default): click to select, drag to move
- C = Razor tool: click on clip to split at click position
- Visual: cursor changes based on active tool
- Store: `activeTool: 'selection' | 'razor' | 'hand' | 'zoom'`
- **Files:** `useCutEditorStore.ts`, `TimelineTrackView.tsx`, hotkey handler
- **Complexity:** medium

### CUT-W3.7: Selection model
- Single select: Click
- Multi-select: ⌘Click (toggle add/remove), ⇧Click (range)
- Linked selection: toggle via 🔗 button in TimelineToolbar (default ON)
- When ON: click video → also select synced audio
- Select All: ⌘A
- Store: `selectedClipIds: string[]`, `linkedSelection: boolean`
- **Files:** `TimelineTrackView.tsx`, `useCutEditorStore.ts` or new `useSelectionStore.ts`
- **Complexity:** medium

---

## WAVE 4: CONTEXT MENU + SAVE + PROJECT SETTINGS
**Goal:** Right-click actions, persistence, project configuration.
**Depends on:** Wave 3 (editing works)

### CUT-W4.1: Context menu — Timeline clips
- Right-click on clip → popup menu:
  - Cut / Copy / Paste / Delete / Ripple Delete
  - Split at Playhead
  - Unlink / Relink
  - Enable / Disable
  - Open in Source / Reveal in Project / Reveal in DAG
  - Make Subclip / Replace with Alternate / Show Scene Alternatives
  - Add Marker / Add Negative Marker / Properties
- Style: dark popup, monochrome icons, keyboard shortcut hints right-aligned
- **Files:** new `ContextMenu.tsx`, `TimelineTrackView.tsx` (right-click handler)
- **Complexity:** medium

### CUT-W4.2: Context menu — DAG nodes + Project items
- DAG node right-click: Open in Source, Add to Timeline, Mark Favorite/Rejected, Edit Lore, Properties
- Project item right-click: Open in Source, Reveal in Finder, Rename, Delete, Create Subclip, Create Bin, Import
- **Files:** `ContextMenu.tsx`, `DAGProjectPanel.tsx`, `ProjectPanel.tsx`
- **Complexity:** medium

### CUT-W4.3: Save / Save As / Autosave
- ⌘S = Save project state to `project.vetka-cut.json`
- ⌘⇧S = Save As (new project directory)
- Autosave: every 2 minutes to `{project}/.autosave/`
- Recovery: on load, check for newer autosave → prompt "Recover?"
- **Files:** `useCutEditorStore.ts` (serialize), backend endpoint, project loader
- **Complexity:** high

### CUT-W4.4: History Panel
- New component `HistoryPanel.tsx` in Analysis tab group
- Shows ordered list of all edit operations (from undo stack)
- Click entry → revert to that state
- Entries above current = grayed (redo-able)
- **Files:** new `HistoryPanel.tsx`, `CutEditorLayoutV2.tsx`, `cut_undo_redo.py`
- **Complexity:** medium

### CUT-W4.5: Project settings dialog
- Framerate: 23.976 / 24 / 25 / 29.97 / 30 / etc.
- Timecode format: HH:MM:SS:FF or HH:MM:SS.ms
- Drop frame: on/off (for 29.97/59.94)
- Start timecode: default 00:00:00:00
- Audio: sample rate, bit depth
- Wire timecode display to use project framerate everywhere
- **Files:** new `ProjectSettings.tsx`, `useCutEditorStore.ts`
- **Complexity:** medium

---

## WAVE 5: MISSING UI FEATURES
**Goal:** Auto-montage UI, parallel timelines, markers, project panel modes.
**Depends on:** Wave 2 (track controls), Wave 4 (save works)

### CUT-W5.1: Auto-Montage UI
- Three buttons/menu items: "PULSE: Favorites Cut / Script Cut / Music Cut"
- POST /cut/pulse/auto-montage → new timeline → new tab
- Progress indicator (progress bar or pulsing nodes on DAG)
- Backend: `pulse_auto_montage.py` — 100% ready
- **Files:** new `AutoMontagePanel.tsx` or menu, `TimelineTabBar.tsx`
- **Complexity:** medium

### CUT-W5.2: Parallel Timelines (stacked view)
- Two TimelineTrackView rendered simultaneously (stacked vertically)
- Only one active (★) at a time. Program Monitor follows active.
- Click on non-active → it becomes active (swap).
- Synced playhead between both.
- Store: `parallelTimelineId: string | null`
- **Files:** `CutEditorLayoutV2.tsx`, `useCutEditorStore.ts`, `TimelineTabBar.tsx`
- **Complexity:** high

### CUT-W5.3: Favorite markers: N key + ⇧M comment
- N = standard marker, semantics=negative
- ⇧M = marker + open comment text input popup
- MM (double-tap M) = alias for ⇧M
- Backend: markers already work, need semantic subtype field
- **Files:** hotkey handler, `useCutEditorStore.ts` (TimeMarker type update)
- **Complexity:** low

### CUT-W5.4: Project Panel view modes
- Add mode switcher: [List] [Grid] [DAG]
- List: current file list view (already works)
- Grid: thumbnail grid (new)
- DAG: show DAG view (uses existing DAGProjectPanel logic, disabled if graph not built)
- **Files:** `ProjectPanel.tsx`
- **Complexity:** medium

---

## WAVE 6: EXPORT / DELIVER
**Goal:** Full export pipeline including master render and crossposting.
**Depends on:** Wave 4 (save works, project settings exist)

### CUT-W6.1: Master render dialog
- Export current timeline as video file
- Options: codec (ProRes/H.264/H.265/DNxHD), resolution, quality
- Progress bar during render
- Backend: FFmpeg-based renderer
- **Files:** new `ExportDialog.tsx`, new backend endpoint
- **Complexity:** high

### CUT-W6.2: Export selection / audio stems
- Export only IN/OUT range (from sequence marks)
- Export individual audio tracks as separate files
- **Files:** `ExportDialog.tsx`, backend
- **Complexity:** medium

### CUT-W6.3: Crosspost presets
- Platform-aware delivery: YouTube, Instagram, TikTok, Vimeo
- Auto-reformat: aspect ratio, codec, duration per platform
- Batch export to multiple platforms
- **Files:** new `PublishPanel.tsx`, backend presets
- **Complexity:** high

### CUT-W6.4: OTIO / AAF export
- OpenTimelineIO export for broad NLE compatibility
- AAF export for Avid interchange
- **Files:** new converters in `converters/`
- **Complexity:** medium

---

## WAVE 7: DATA MODEL ALIGNMENT
**Goal:** Reconcile code naming with architecture docs.
**Can run PARALLEL with Waves 5-6.**

### CUT-W7.1: Taxonomy naming reconciliation
- Code uses: `scene_chunk`, `asset`, `note`
- Architecture docs use: `ScriptChunkNode`, `MediaNode`, `LoreNode`
- Reconcile: update code OR docs to match
- **Files:** `cut_scene_graph_taxonomy.py`, data model docs
- **Complexity:** medium

### CUT-W7.2: has_media edge creation
- When clips are linked to scene nodes, create `has_media` edges in DAG
- **Files:** `cut_project_store.py`, `cut_scene_graph_taxonomy.py`
- **Complexity:** low

### CUT-W7.3: LoreNode implementation
- Character, Location, Item nodes in DAG
- Created from script analysis (CAPS names = characters, INT./EXT. = locations)
- Edges: `mentions` (SceneChunk → LoreNode)
- **Files:** `cut_scene_graph_taxonomy.py`, `cut_project_store.py`, `DAGProjectPanel.tsx`
- **Complexity:** medium

---

## WAVE 8: LOGGER ENRICHMENT
**Goal:** DAG grows flesh — real media data enriches the graph.
**Depends on:** Wave 7 (data model aligned)

### CUT-W8.1: Scene-material linking
- Clips → SCN_XX nodes via transcript similarity or manual drag
- Algorithm: clip transcript (Whisper) → embedding similarity with scene text
- **Files:** `cut_project_store.py`, backend endpoint
- **Complexity:** high

### CUT-W8.2: Shot scale auto-detection
- Vision model detects CU/MCU/MS/WS/EWS per clip
- Fields: `shot_scale_auto`, `shot_scale_manual` (override), `shot_scale_confidence`
- **Files:** new `shot_scale_detector.py`, clip metadata
- **Complexity:** high

### CUT-W8.3: Screenplay import (.fountain, .fdx)
- Fountain parser: plain text conventions → SceneChunks
- FDX parser: Final Draft XML `<Scene>` tags → SceneChunks
- DOCX: pandoc → plain text → screenplay_timing.py
- **Files:** new parsers in `src/services/`
- **Complexity:** medium

### CUT-W8.4: Linked media behavior (link/unlink)
- Video + synced audio clips linked by default
- Unlink: right-click → Unlink (or ⌘L)
- Relink: select both → right-click → Link
- When linked: move/trim/delete affects both
- **Files:** `TimelineTrackView.tsx`, `useCutEditorStore.ts`
- **Complexity:** medium

---

## WAVE 9: AUDIO
**Goal:** Professional audio support.
**Depends on:** Wave 2 (track controls), Wave 8 (linked media)

### CUT-W9.1: Basic audio mixer panel
- Per-track: volume fader, pan knob, mute, solo, VU meter
- Master bus: volume fader, VU meter
- **Files:** new `AudioMixer.tsx`
- **Complexity:** high

### CUT-W9.2: Record VO / narration
- Record voiceover directly into timeline from microphone
- ADR recording with cue playback
- **Files:** new `RecordPanel.tsx`, Web Audio API
- **Complexity:** high

### CUT-W9.3: Audio transitions
- Crossfade between adjacent audio clips (default transition)
- Configurable fade curves
- **Files:** `TimelineTrackView.tsx`, backend
- **Complexity:** medium

---

## WAVE 10: FUTURE / GENERATIVE (not MVP)

### CUT-W10.1: Documentary mode
Import media → auto-transcribe → AI generates scene descriptions → Script panel content.
Reverse pipeline: footage → reconstructed script → DAG.

### CUT-W10.2: Interactive lore tokens
Words in screenplay = clickable hyperlinks. ANNA → character node. CAFE → location node.
Click token → show character DAG branch.

### CUT-W10.3: Multiverse DAG UI
Branch visualization: script drafts, montage variants, material branches.
Merge logic: scene heading match + semantic similarity.

### CUT-W10.4: Storylines (X-columns / partiture)
Script spine in center + storyline branches per X axis.
Character arcs, parallel plotlines as side columns.

### CUT-W10.5: Bridge layer (Circuit A ↔ Circuit B)
Bidirectional translation: symbolic ↔ learned/JEPA.
JEPA prediction error → BPM markers. Editorial constraints → latent space search.

### CUT-W10.6: Effects node graph
DaVinci Fusion-style node graph for color correction + transitions + compositing.

### CUT-W10.7: Keyboard customization UI
Settings dialog for rebinding all hotkeys.
Presets: Premiere Pro, FCP 7, Avid, Custom.

### CUT-W10.8: Proxy workflow toggle
Toggle proxy mode on/off. Edit with lightweight 720p H.264 proxies, export with originals.

---

## Dependency Graph

```
Wave 0 (cleanup) ─────────────────────────────────────────┐
     │ parallel                                             │
Wave 1 (wiring) ──→ Wave 2 (tracks + direction) ──┐       │
                                                    │       │
                    Wave 3 (editing hotkeys) ←──────┤       │
                         │                          │       │
                         ▼                          │       │
                    Wave 4 (context + save) ───────┤       │
                         │                          │       │
                         ▼                          ▼       │
                    Wave 5 (missing UI) ←──────────┘       │
                         │                                  │
                         ▼                                  │
                    Wave 6 (export/deliver) ←───────────────┘
                         │
Wave 7 (data model) ─────┤  (can run parallel with 5-6)
                         │
                         ▼
                    Wave 8 (logger enrichment)
                         │
                         ▼
                    Wave 9 (audio)
                         │
                         ▼
                    Wave 10 (future / generative)
```

---

## Task Naming Convention

All tasks on TaskBoard for CUT use prefix: `CUT-W{wave}.{number}`

Examples:
- `CUT-W1.1: PanelSyncStore → EditorStore bridge`
- `CUT-W3.4: JKL Progressive Shuttle`
- `CUT-W6.1: Master render dialog`

**project_id:** `CUT`

---

## Notes for Small Models (Ollama 8B)

Each task in this roadmap:
- **Files** listed explicitly
- **Interface/dataclass** defined inline
- **Algorithm** step-by-step
- **Dependencies** listed (what must be done BEFORE)
- **Complexity** rated (low/medium/high)

When slicing into TaskBoard tasks: each numbered item = 1 task on the board.
