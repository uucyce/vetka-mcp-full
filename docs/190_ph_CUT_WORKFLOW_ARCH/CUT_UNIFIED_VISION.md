# CUT NLE — Unified Vision v2
**Date:** 2026-03-19 (updated)
**Sources:** CUT_TARGET_ARCHITECTURE.md, CUT_DATA_MODEL.md, CUT_COGNITIVE_MODEL.md, ROADMAP_CUT_FULL.md, CUT_HOTKEY_ARCHITECTURE.md, RECON_192_ARCH_VS_CODE_2026-03-18.md, ChatGPT NLE review 2026-03-19
**Purpose:** ONE document that defines ALL panels, ALL functions, ALL hotkeys, ALL NLE baseline contracts. Single source of truth.
**Status:** CANONICAL v2 — replaces scattered definitions across 6+ docs

---

## 0. Constitution

> **CUT is not a timeline editor. CUT is a narrative graph navigator.**
> **The editor navigates narrative intent through the DAG of possibilities.**

Three cognitive spaces, one system:
```
NARRATIVE SPACE (Script)    — what to tell
MEDIA SPACE (DAG)           — what material exists
TEMPORAL SPACE (Timeline)   — how to tell it
```

In traditional NLE: script, project bin, timeline = three disconnected worlds.
In CUT: script = spine of DAG = projected to timeline. One ontology.

**Design goal:** Premiere Pro on steroids — editor recognizes familiar NLE, discovers graph superpowers gradually.

---

## 1. Panels — Complete Inventory

### 1.1 Panel Map

```
                            CUT NLE LAYOUT

┌─────────────────┬────────────────────┬──────────────────────┐
│                 │                    │                      │
│   LEFT COLUMN   │   SOURCE MONITOR   │  PROGRAM MONITOR     │
│                 │                    │                      │
│  ┌───────────┐  │  ┌──────────────┐  │  ┌────────────────┐  │
│  │ Navigation│  │  │              │  │  │                │  │
│  │ Tabs:     │  │  │  Video       │  │  │  Video         │  │
│  │           │  │  │  Preview     │  │  │  Preview       │  │
│  │ [Project] │  │  │  (raw clip)  │  │  │  (timeline)    │  │
│  │ [Script]  │  │  │              │  │  │                │  │
│  │ [Graph]   │  │  ├──────────────┤  │  ├────────────────┤  │
│  │           │  │  │  Monitor     │  │  │  Monitor       │  │
│  │ Analysis  │  │  │  Transport   │  │  │  Transport     │  │
│  │ Tabs:     │  │  │  + IN/OUT    │  │  │                │  │
│  │           │  │  └──────────────┘  │  └────────────────┘  │
│  │ [Inspect] │  │                    │                      │
│  │ [Clip]    │  │                    │                      │
│  │ [Story3D] │  │                    │                      │
│  └───────────┘  │                    │                      │
├─────────────────┴────────────────────┴──────────────────────┤
│                                                             │
│  TIMELINE (full width)                                      │
│  [cut-00] [cut-01 ★] [cut-02] [+]     Snap  Zoom───────    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 🔒 M S │  V1: ▓▓▓▓│▓▓▓▓▓│▓▓▓│▓▓▓▓▓│▓▓▓▓▓│▓▓▓     │    │
│  │ 🔒 M S │  V2:      ▓▓▓│▓▓▓▓▓│▓▓▓▓│                 │    │
│  │ 🔒 M S │  A1: ░░░░│░░░░░│░░░│░░░░░│░░░░░│░░░       │    │
│  │ 🔒 M S │  A2:    ░░░░│░░░░░│░░░░│                    │    │
│  │         │  BPM: ● ● ●● ● ●●● ● ● ●● ●              │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
    Track header: 🔒=lock, M=mute, S=solo (monochrome SVG icons)
```

### 1.2 Panel Registry

| # | Panel | Component | Tab Group | Function | Mounted |
|---|-------|-----------|-----------|----------|---------|
| 1 | **Project Panel** | `ProjectPanel.tsx` | Navigation | Media bin: list/grid/DAG modes. Import, search, bins | YES |
| 2 | **Script Panel** | `ScriptPanel.tsx` | Navigation | Screenplay as clickable scene chunks + teleprompter | YES |
| 3 | **Graph** | `DAGProjectPanel.tsx` | Navigation | Multiverse graph: script spine + media + lore | YES |
| 4 | **PulseInspector** | `PulseInspector.tsx` | Analysis | PULSE metadata: Camelot, energy, pendulum, McKee | Tab (restore) |
| 5 | **ClipInspector** | `ClipInspector.tsx` | Analysis | Selected clip properties: file, timing, sync, waveform | Tab (restore) |
| 6 | **StorySpace3D** | `StorySpace3D.tsx` | Analysis | 3D narrative space: Camelot wheel + McKee triangle | Tab (restore) |
| 7 | **Source Monitor** | `VideoPreview.tsx` feed=source | — | Raw clip from DAG/Project click. IN/OUT marking | YES |
| 8 | **Program Monitor** | `VideoPreview.tsx` feed=program | — | Active timeline playback result | YES |
| 9 | **Monitor Transport** | `MonitorTransport.tsx` | Embedded | Scrubber + timecode + play/JKL + IN/OUT (Source only) | YES (x2) |
| 10 | **Timeline Track View** | `TimelineTrackView.tsx` | — | Horizontal timeline: tracks, clips, ruler, playhead, drag, trim | YES |
| 11 | **Timeline Tab Bar** | `TimelineTabBar.tsx` | — | Multi-version tabs: [cut-00] [cut-01] [+] | YES |
| 12 | **Timeline Toolbar** | `TimelineToolbar.tsx` | — | Snap toggle, zoom slider, linked selection toggle | YES |
| 13 | **BPM Track** | `BPMTrack.tsx` | — | Beat grid: audio(green), visual(blue), script(white), sync(orange) | YES |
| 14 | **Audio Level Meter** | `AudioLevelMeter.tsx` | Embedded | Stereo VU meter | YES |
| 15 | **Transcript Overlay** | `TranscriptOverlay.tsx` | Embedded | Subtitles at currentTime | YES |
| 16 | **History Panel** | `HistoryPanel.tsx` | Analysis | Visual undo/redo history list | MISSING |

### 1.3 Tab Groups

**Left column** has two tab groups stacked:

**Navigation tabs** (top):
- **Project** — media bin with modes: [List] [Grid] [DAG]. DAG mode requires graph build step
- **Script** — screenplay as clickable scene chunks
- **Graph** — multiverse graph: script spine + media nodes + lore

**Analysis tabs** (bottom):
- **Inspector** — PULSE metadata for selected scene (Camelot, energy, McKee)
- **Clip** — selected clip properties (file, timing, sync, waveform)
- **StorySpace** — 3D narrative visualization
- **History** — visual undo/redo list (like Photoshop History panel)

**Naming rule:** UI names stay familiar (Project, Script, Graph, Inspector). Architecture names stay precise (DAG Project, Script Spine, Multiverse). No synonyms in labels.

**Project vs Graph distinction:**
- **Project panel DAG mode** = lightweight file browser in graph layout (bins as clusters)
- **Graph tab** = full multiverse view with script spine, media nodes, lore, storylines
- Different scope, not duplication

### 1.4 Project Panel View Modes

```
Project Panel — single panel, multiple representations:

[List]  [Grid]  [DAG]

List mode   — file list with metadata (default, always available)
Grid mode   — thumbnails (always available)
DAG mode    — graph view (requires script import or logger pass)
              If structure not built: shows "Build Graph" button
```

DAG mode becomes available after script import or media bootstrap. This is normal UX — not a hidden feature.

### 1.5 Dead Components (to delete)
| Component | Reason |
|-----------|--------|
| `CutEditorLayout.tsx` | Legacy, replaced by V2 |
| `SourceBrowser.tsx` | Legacy, replaced by ProjectPanel |
| `TransportBar.tsx` | Replaced by MonitorTransport + TimelineToolbar |

---

## 2. Functions — by Panel

### 2.1 Project Panel

| Function | Hotkey | Backend API | Status |
|----------|--------|-------------|--------|
| Import media | ⌘I | POST /cut/bootstrap-async | REAL |
| Select clip → Source Monitor | Click | setSourceMedia() | WIRING GAP |
| Create new bin | ⌘/ | — | MISSING |
| Search/filter | ⌘F | — | MISSING |
| Delete item | Delete | — | MISSING |
| Reveal in Finder | ⇧H | — | MISSING |
| View mode: List/Grid/DAG | — | — | MISSING (List only) |

### 2.2 Script Panel

| Function | Hotkey | Backend API | Status |
|----------|--------|-------------|--------|
| Parse script → scene chunks | — | POST /cut/script/parse | REAL |
| Click chunk → sync all panels | Click | syncFromScript() | REAL (bridge gap) |
| Teleprompter auto-scroll | — | — | REAL |
| Import .fountain/.fdx/.pdf/.docx | — | POST /cut/script/parse | MISSING (plain text only) |
| Manual drag-split chunks | Drag | — | MISSING |
| Lore tokens (clickable names) | Click on name | — | MISSING (future) |

### 2.3 Graph Panel (DAG Project)

| Function | Hotkey | Backend API | Status |
|----------|--------|-------------|--------|
| Fetch DAG for timeline | — | GET /cut/project/dag/{id} | REAL |
| Scene chunks as vertical spine | — | — | REAL |
| Video nodes LEFT, Audio RIGHT | — | — | REAL |
| Click node → Source Monitor | Click | syncFromDAG() → setSourceMedia() | WIRING GAP |
| Y-axis = chronology (START bottom) | — | — | BROKEN (START at top) |
| Flip Y toggle | — | — | MISSING |
| Lore nodes (characters, locations) | — | — | MISSING |
| Agent visualization (pulsing nodes) | — | — | MISSING (future) |
| Active timelineId prop | — | — | BROKEN (hardcoded 'main') |

### 2.4 Source Monitor

| Function | Hotkey | Backend API | Status |
|----------|--------|-------------|--------|
| Show raw clip (from DAG/Project click) | — | — | WIRING GAP (same as Program) |
| Play/Pause | Space | — | REAL (but global, not panel-scoped) |
| JKL shuttle | J/K/L | — | SIMPLIFIED (±5s, not progressive) |
| Frame step | ←/→ | — | REAL |
| Mark IN (source) | I | — | REAL |
| Mark OUT (source) | O | — | REAL |
| Clear IN/OUT | ⌥I/⌥O/⌘⇧X | — | MISSING |
| Go to IN/OUT | ⇧I/⇧O | — | MISSING |
| Add positive marker | M | POST /cut/time-markers/apply | REAL |
| Add negative marker | N | — | MISSING |
| Add comment marker | ⇧M | POST /cut/time-markers/apply | REAL |
| Insert to Timeline | , | POST /cut/timeline/apply | MISSING handler |
| Overwrite to Timeline | . | POST /cut/timeline/apply | MISSING handler |
| Match Frame | F | — | MISSING |
| 5-frame step | ⇧←/⇧→ | — | MISSING |

### 2.5 Program Monitor

| Function | Hotkey | Backend API | Status |
|----------|--------|-------------|--------|
| Show active timeline playback | — | — | WIRING GAP (same feed as Source) |
| Play/Pause | Space | — | REAL |
| JKL shuttle | J/K/L | — | SIMPLIFIED |
| Frame step | ←/→ | — | REAL |
| Go to Start/End | Home/End | — | REAL |
| Mark IN (sequence) | I | — | MISSING (separate from source marks) |
| Mark OUT (sequence) | O | — | MISSING (separate from source marks) |
| Cycle playback rate | — | — | REAL |

### 2.6 Timeline

| Function | Hotkey | Backend API | Status |
|----------|--------|-------------|--------|
| Select clip | Click | — | REAL |
| Multi-select | ⇧Click / ⌘Click | — | MISSING |
| Range select (marquee) | Drag on empty area | — | MISSING |
| Select all clips in scene | — | — | MISSING |
| Move clip (drag) | Drag | POST /cut/timeline/apply | REAL |
| Trim clip edges | Drag edge | POST /cut/timeline/apply | REAL |
| Delete clip (leave gap) | Delete | POST /cut/timeline/apply | REAL |
| Ripple Delete | ⌥Delete / ⇧Delete | POST /cut/timeline/apply | MISSING handler |
| Split at playhead | ⌘K / B | POST /cut/timeline/apply | MISSING handler |
| Ripple Trim Prev→Playhead | Q | POST /cut/timeline/apply | MISSING |
| Ripple Trim Next→Playhead | W | POST /cut/timeline/apply | MISSING |
| Navigate prev edit point | ↑ | — | MISSING |
| Navigate next edit point | ↓ | — | MISSING |
| Nudge clip ±1 frame | ⌥←/⌥→ | — | MISSING |
| Nudge clip ±5 frames | ⌥⇧←/⌥⇧→ | — | MISSING |
| Snap toggle | S | — | REAL |
| Zoom in/out | =/- | — | REAL |
| Zoom to fit | \ | — | MISSING |
| Selection tool | V / A | — | MISSING |
| Razor tool | C / B | — | MISSING |
| Hand tool (pan) | H | — | MISSING |
| Zoom tool | Z | — | MISSING |
| Scene detection | ⌘D | POST /cut/scene-detect-and-apply | REAL |
| Create new timeline version | Tab bar [+] | — | REAL |
| Parallel timeline (stacked) | — | — | MISSING |
| Undo | ⌘Z | POST /cut/undo | REAL |
| Redo | ⌘⇧Z | POST /cut/redo | REAL |
| Copy/Paste | ⌘C/⌘V | — | MISSING |
| Select All | ⌘A | — | MISSING |

### 2.7 Inspector (PulseInspector)

| Function | Status |
|----------|--------|
| PULSE metadata for scene: Camelot, energy, pendulum, McKee | REAL (component exists) |
| **Mounted in layout** | **NO — returns null** |

### 2.8 Clip Inspector

| Function | Status |
|----------|--------|
| Clip properties: file, timing, sync, waveform, transcript | REAL (component exists) |
| **Mounted in layout** | **NO — removed** |

### 2.9 StorySpace3D

| Function | Status |
|----------|--------|
| Camelot wheel + McKee triangle + scene trajectory | REAL (component exists) |
| **Mounted in layout** | **NO — removed** |

### 2.10 Auto-Montage (no panel yet)

| Function | Backend API | Status |
|----------|-------------|--------|
| Favorites Cut | POST /cut/pulse/auto-montage | Backend REAL, UI MISSING |
| Script Cut | POST /cut/pulse/auto-montage | Backend REAL, UI MISSING |
| Music Cut | POST /cut/pulse/auto-montage | Backend REAL, UI MISSING |
| Progress indicator | — | MISSING |
| Result → new timeline tab | — | MISSING |
| Reverse dependency (alternatives) | — | MISSING |

### 2.11 Global Functions

| Function | Hotkey | Status |
|----------|--------|--------|
| Undo | ⌘Z | REAL |
| Redo | ⌘⇧Z | REAL |
| Import | ⌘I | REAL |
| Save | ⌘S | MISSING |
| Save As | ⌘⇧S | MISSING |
| Toggle NLE/Debug view | ⌘\ | REAL |
| Escape (deselect/cancel) | Esc | MISSING |
| Focus Project Panel | ⇧1 | MISSING |
| Focus Source Monitor | ⇧2 | MISSING |
| Focus Timeline | ⇧3 | MISSING |
| Focus Program Monitor | ⇧4 | MISSING |
| Focus Inspector | ⇧5 | MISSING |

---

## 3. Panel Focus System

### 3.1 Concept

Premiere Pro: hotkeys are panel-scoped. JKL controls whichever monitor has focus. Delete only works when Timeline is focused.

Our current state: ALL hotkeys are global (document-level listener). No focus concept.

### 3.2 Specification

```typescript
// useCutEditorStore.ts
focusedPanel: 'source' | 'program' | 'timeline' | 'project' | 'script' | 'dag' | null

// Each panel component:
onMouseDown={() => setFocusedPanel('timeline')}

// Visual: focused panel gets subtle highlight border
// CSS: border: 1px solid #4A9EFF (only on focused panel)
```

### 3.3 Scope Rules

| Hotkey Group | Scope | Behavior |
|-------------|-------|----------|
| Playback (Space, JKL, ←→) | Panel-scoped | Controls Source or Program depending on focus |
| Marking (I/O) | Panel-scoped | Source: source marks. Program: sequence marks |
| Editing (Delete, ⌘K, Q/W) | Panel-scoped | Only works when Timeline focused |
| Tools (V, C, S) | Panel-scoped | Only works when Timeline focused |
| Clipboard (⌘Z, ⌘C/V) | Global | Works everywhere |
| Import/Save (⌘I, ⌘S) | Global | Works everywhere |
| Panel switch (⇧1-5) | Global | Works everywhere |
| View toggle (⌘\) | Global | Works everywhere |

---

## 4. Store Architecture

### 4.1 Four Stores

```
useCutEditorStore      — master state: playback, timeline, clips, media, zoom, focus
usePanelSyncStore      — cross-panel sync matrix (who notifies whom)
usePanelLayoutStore    — panel modes, dock positions, grid sizes
useSelectionStore      — selection state: selectedClips, selectionMode, linkedSelection
```

### 4.2 Critical Wiring Gaps

```
usePanelSyncStore ──────────── ISLAND ──────────── useCutEditorStore
     ↑ writes                                          ↑ reads
  ScriptPanel                                       VideoPreview
  DAGProjectPanel                                   TimelineTrackView
  StorySpace3D                                      MonitorTransport

  BRIDGE NEEDED:
  usePanelSyncStore.selectedAssetPath → useCutEditorStore.setSourceMedia()
  usePanelSyncStore.activeSceneId → timeline scroll + DAG highlight
```

### 4.3 Source/Program Split (missing)

```typescript
// Current (broken):
activeMediaPath: string | null    // both monitors read this

// Target:
sourceMediaPath: string | null    // Source Monitor reads this
programMediaPath: string | null   // Program Monitor reads this

// Source marks (IN/OUT for raw clip in Source Monitor):
sourceMarkIn: number | null
sourceMarkOut: number | null

// Sequence marks (IN/OUT for timeline position in Program Monitor):
sequenceMarkIn: number | null
sequenceMarkOut: number | null

// Routing:
Click in Project/DAG → setSourceMedia()
Timeline playback → setProgramMedia()
Click script line → setSourceMedia(linked raw) + setProgramMedia(jump to time)
```

**Rule:** Source marks and sequence marks are SEPARATE state fields. `I` key sets whichever is in focus.

### 4.4 Playhead Contract

```typescript
// Timeline playhead = master clock. Program Monitor follows it.
currentTime: number          // seconds, master playhead position
playheadSource: 'timeline'   // always timeline in current architecture

// Source Monitor has its OWN playback position (independent):
sourceCurrentTime: number    // seconds, position within raw clip
```

**Rule:** Timeline playhead is the single source of truth for program output.

### 4.5 Clip vs Media Identity

```
MediaNode   = source file (one per imported file)
ClipUsageNode = instance on timeline (many per MediaNode)

clip_id ≠ media_id

One video file → many clip usages across timelines.
Undo/replace/relink operate on ClipUsageNode, not MediaNode.
```

---

## 5. Three-Level DAG Architecture

```
LEVEL 1 — SCRIPT SPINE
  Pure narrative structure. No media. Scene chunks with chronological order.
  SCN_01 → SCN_02 → SCN_03 → ... → SCN_N

LEVEL 2 — DAG PROJECT / LOGGER
  Scenes grow flesh: video takes, audio, lore, PULSE metadata.
  Each SCN_XX has: media nodes (LEFT=video, RIGHT=audio), lore nodes, analysis.

LEVEL 3 — TIMELINE PROJECTIONS
  Timelines = horizontal paths through the DAG.
  cut-00: Logger assembly. cut-01: PULSE rough cut. cut-02: Editor manual.
  DAG never disappears — it remains the source for all versions.
```

**Multiverse:** All script drafts, all montage variants, all material branches coexist in one DAG. Timeline = chosen path through this graph.

---

## 6. Routing Table

| User Action | Source Monitor | Program Monitor | DAG | Script | Timeline |
|-------------|--------------|-----------------|-----|--------|----------|
| Click clip in Project | Shows clip | — | — | — | — |
| Click node in DAG | Shows linked media | — | Highlights node | Scrolls to scene | — |
| Click chunk in Script | Shows linked raw | Jumps to time | Highlights SCN | — | Scrolls to position |
| Playhead moves on Timeline | — | Updates playback | — | Auto-scroll | — |
| Click clip on Timeline | Shows source clip | — | Highlights source SCN | Scrolls to scene | Selects clip |
| Double-click clip | Loads for IN/OUT | — | — | — | — |

**Rule:** Program Monitor ALWAYS follows the active timeline. Only one timeline is active at a time.

---

## 7. Track Controls

### 7.1 Track Header Controls

Each track (V1, V2, A1, A2...) has a header on the left side with:

| Control | Icon | Function |
|---------|------|----------|
| Lock | padlock SVG | Prevent edits on this track |
| Mute | M SVG | Audio: silence. Video: hide from output |
| Solo | S SVG | Audio: solo playback. Video: solo visible |
| Enable/Disable | eye SVG | Toggle track visibility (video) / audibility (audio) |
| Target | dot indicator | This track receives insert/overwrite edits |

**Visual style:** Monochrome white SVG icons on dark background. Active = filled, inactive = outline. No color in icons.

**Insert/Overwrite fallback:** If no track is explicitly targeted, default destination = V1 + A1.

### 7.2 Source Patching / Destination Targeting

```
Source clip has: V (video) + A (audio channels)

Patching determines WHERE insert/overwrite lands:

Source V  → Target V1    (or V2, V3... user selects)
Source A  → Target A1    (or A2, A3...)

Visual: patch indicator on track header connects source channel to destination track.

Insert (,) / Overwrite (.) only affect targeted tracks.
```

### 7.3 Track State in Store

```typescript
// useCutEditorStore.ts
tracks: Track[]

interface Track {
  id: string
  type: 'video' | 'audio'
  label: string           // V1, V2, A1, A2...
  locked: boolean
  muted: boolean
  solo: boolean
  enabled: boolean
  targeted: boolean       // receives insert/overwrite
  height: number          // pixels
}
```

---

## 8. Selection Model

### 8.1 Selection Targets

Selection can target:

| Target | Trigger | Store field |
|--------|---------|-------------|
| Single clip | Click | selectedClipIds: [id] |
| Multiple clips | ⌘Click / ⇧Click | selectedClipIds: [id, id, ...] |
| Linked pair (video+audio) | Click (when linkedSelection=ON) | selectedClipIds: [videoId, audioId] |
| Range (marquee) | Drag on empty timeline area | selectedClipIds: [...all in rect] |
| All clips in scene | ⌘A (when scene selected) | selectedClipIds: [...scene clips] |
| Scene chunk | Click in Script/DAG | activeSceneId |
| Lore node | Click in DAG | activeLoreNodeId |

### 8.2 Linked Selection

```
Linked selection toggle (🔗 in Timeline Toolbar):

ON (default):  click video clip → also selects synced audio clip(s)
OFF:           click video clip → only video clip selected

Unlink: right-click → Unlink
Relink: select video + audio → right-click → Link
```

---

## 9. Context Menu (Right-Click)

### 9.1 Timeline Clip Context Menu

| Action | Hotkey equivalent |
|--------|------------------|
| Cut | ⌘X |
| Copy | ⌘C |
| Paste | ⌘V |
| Delete | Delete |
| Ripple Delete | ⌥Delete |
| — separator — | |
| Split at Playhead | ⌘K |
| Unlink / Relink | — |
| Enable / Disable | — |
| — separator — | |
| Open in Source Monitor | — |
| Reveal in Project | — |
| Reveal in DAG | — |
| — separator — | |
| Make Subclip | — |
| Replace with Alternate | — (shows DAG alternatives) |
| Show Scene Alternatives | — (from Multiverse) |
| — separator — | |
| Add Marker | M |
| Add Negative Marker | N |
| Properties (Inspector) | — |

### 9.2 DAG Node Context Menu

| Action |
|--------|
| Open in Source Monitor |
| Add to Timeline (Insert) |
| Add to Timeline (Overwrite) |
| Mark as Favorite |
| Mark as Rejected |
| Edit Lore |
| Show All Takes |
| Properties |

### 9.3 Project Panel Context Menu

| Action |
|--------|
| Open in Source Monitor |
| Reveal in Finder |
| Rename |
| Delete |
| Create Subclip |
| Create New Bin |
| Import Media |

---

## 10. Marker Architecture

### 10.1 Unified Marker Model

All markers share a base type with semantic subtypes:

```typescript
interface Marker {
  id: string
  time: number              // timecode in seconds
  type: 'standard'          // base type — ONE type for all
  semantics: 'positive' | 'negative' | 'note' | 'neutral'
  text: string | null       // optional comment
  color: string             // user-assigned or auto from semantics
  source: 'user' | 'pulse_auto'
  scope: 'clip' | 'timeline'  // clip-level or timeline ruler
}
```

**Hotkeys:**
- **M** = standard marker, semantics=positive (favorite moment)
- **N** = standard marker, semantics=negative (reject moment)
- **⇧M** = standard marker + open comment input
- **MM** (double-tap) = alias for ⇧M

**Semantic colors (defaults):**
- positive = green tint
- negative = red tint
- note = yellow tint
- neutral = white

### 10.2 Marker Layers on Timeline

| Layer | Position | Content |
|-------|----------|---------|
| Standard markers | Top ruler | User markers (any semantics) |
| BPM markers | Bottom BPM track | Auto: green(audio), blue(visual), white(script), orange(sync) |
| PULSE scene markers | Script + timeline | Auto: amber scene boundaries |

### 10.3 Export Formats

| Format | What | Status |
|--------|------|--------|
| Premiere XML (XMEML v5) | Standard markers | REAL |
| FCPXML v1.10 | Standard markers | REAL |
| EDL | Standard markers | REAL |
| SRT | Favorite markers (positive) | REAL |
| pulse_markers.json | BPM markers (internal) | REAL |
| pulse_scenes.json | Scene markers (internal) | REAL |

---

## 11. Save / Autosave / History

### 11.1 Three Persistence Layers

```
Timeline Version ≠ Project Save State ≠ Undo History

1. Undo/Redo stack     — in-memory, fast, 100 levels, local to session
2. History panel       — visible list of operations (like Photoshop)
3. Autosave snapshots  — periodic disk writes for crash recovery
4. Save / Save As      — explicit project state checkpoint
```

### 11.2 Save Contract

| Function | Hotkey | Behavior |
|----------|--------|----------|
| Save | ⌘S | Writes current project state to `project.vetka-cut.json` |
| Save As | ⌘⇧S | Creates new project directory with copy of all state |
| Autosave | — | Every 2 minutes, silent, to `{project}/.autosave/`. Keep last 20, delete older. |
| Recovery | — | On crash → prompt "Recover from autosave?" |

### 11.3 History Panel

```
History Panel (tab in Analysis group):
┌──────────────────────┐
│ ● Current State       │ ← green dot
│ ○ Trim clip A1:02     │
│ ○ Move clip V1:03     │
│ ○ Delete clip V2:01   │
│ ○ Split at 00:01:23   │
│ ○ Import media (5)    │
│ ○ Project Created     │ ← first entry
└──────────────────────┘

Click any entry → revert to that state.
Grayed entries above = redo-able future.

Action grouping: drag = 1 entry, trim = 1 entry, multi-select edit = 1 entry.
Without grouping, 100 undo levels fill up with noise.
```

### 11.4 What Gets Saved

```
project.vetka-cut.json contains:
  - timeline states (all cut-NN versions)
  - media references (paths, not copies)
  - markers (all types)
  - DAG structure (nodes, edges)
  - script chunks
  - PULSE analysis results
  - layout state (panel positions, sizes)
  - track settings (lock, mute, solo, target)
  - project metadata (framerate, timecode format)
```

---

## 12. Export / Deliver

### 12.1 Three Export Modes

```
1. MASTER EXPORT — final rendered file
   Formats: ProRes, H.264, H.265, DNxHD
   Options: resolution, codec, audio mix

2. EDITORIAL EXPORT — interchange with other NLE
   Formats: Premiere XML (XMEML v5), FCPXML v1.10, EDL, AAF, OTIO
   + SRT (markers/subtitles)
   + pulse_markers.json (BPM data)

3. PUBLISH / CROSSPOST — platform-aware delivery
   Presets: YouTube, Instagram, TikTok, Vimeo, Twitter/X
   Auto-reformat: aspect ratio, duration, codec per platform
   Batch: export to multiple platforms at once
```

### 12.2 Export Status

| Format | Backend | Status |
|--------|---------|--------|
| Premiere XML (XMEML v5) | premiere_xml_converter.py | REAL |
| FCPXML v1.10 | fcpxml_converter.py | REAL |
| EDL | cut_routes.py | REAL |
| SRT | pulse_srt_bridge.py | REAL |
| Master render (ProRes/H.264) | — | MISSING |
| AAF | — | MISSING |
| OTIO (OpenTimelineIO) | cut_routes.py /export/otio | REAL |
| Batch export | cut_routes.py /export/batch | REAL |
| Social presets | cut_routes.py /export/social-presets | REAL (backend, UI MISSING) |

### 12.3 Export UI

```
File → Export → Master...       (render dialog)
File → Export → Editorial...    (format picker)
File → Export → Publish...      (platform picker)
File → Export → Selection...    (export IN/OUT range only)
File → Export → Audio Stems...  (per-track audio export)

Naming: {project}_{timeline}_{date}_{version}.ext
Example: Berlin_cut-02_2026-03-19_v01.mov
```

---

## 13. Project Settings / Technical Contracts

### 13.1 Framerate

Every project has a master framerate. All timecodes are calculated from this.

```typescript
interface ProjectSettings {
  framerate: 23.976 | 24 | 25 | 29.97 | 30 | 48 | 50 | 59.94 | 60
  timecodeFormat: 'HH:MM:SS:FF' | 'HH:MM:SS.ms'  // FF = frames, ms = milliseconds
  timecodeDropFrame: boolean  // only for 29.97/59.94
  startTimecode: string       // default '00:00:00:00'
  audioSampleRate: 44100 | 48000 | 96000
  audioBitDepth: 16 | 24 | 32
}
```

**Default:** 24fps, non-drop frame, `HH:MM:SS:FF` display.

**Rule:** Timecode display everywhere uses the same format. MonitorTransport, Timeline ruler, markers — all show `HH:MM:SS:FF` (or `:ms` if configured).

### 13.2 Proxy Workflow

```
For heavy footage (4K+, RAW):
1. On import: generate lightweight proxies (720p H.264)
2. Edit with proxies (fast playback)
3. On export: relink to original media (full quality)

Proxy generation: cut_proxy_worker.py (FFmpeg, already exists)
Toggle: "Proxy Mode ON/OFF" in Project settings
```

### 13.3 Keyboard Customization

Hotkeys are customizable per user:

```
Settings → Keyboard Shortcuts
  Preset: [Premiere Pro] [FCP 7] [Avid] [Custom]
  Search: _______________

  Category: Editing
    Split at Playhead:   ⌘K  [change]
    Ripple Delete:       ⌥⌫  [change]
    ...
```

Stored in: `{project}/.vetka_cut/keybindings.json`
Default preset: Premiere Pro (macOS).

---

## 14. Linked Media Behavior

### 14.1 Rules

```
Video + synced audio clips are LINKED by default (from import/sync).

When linked:
  - Move video → audio moves with it
  - Trim video → audio trims with it
  - Delete video → audio deletes with it
  - Click video → both selected

Unlink: right-click → Unlink (or ⌘L toggle)
After unlink: video and audio move independently.
Relink: select both → right-click → Link
```

### 14.2 Source Monitor Behavior for Timeline Clips

```
Click on clip usage in timeline:
  → Source Monitor shows FULL source clip (not subclip)
  → IN/OUT markers show which portion is used in timeline
  → User can adjust IN/OUT, then apply back to timeline (Match Frame workflow)
```

---

## 15. Parallel Timelines

### 15.1 Contract

```
Two timelines visible simultaneously (stacked, not tabs):

┌────────────────────────────────────┐
│ TIMELINE 2: cut-01 (PULSE)         │  ← can be edited if made active
│ ░░░░│░░░░░│░░░│░░░░░│░░░░│░░░     │
├────────────────────────────────────┤
│ TIMELINE 1 ★: cut-02 (Manual)     │  ← currently active
│ ▓▓▓│▓▓▓▓▓│▓▓│▓▓▓▓▓│▓▓▓▓│▓▓      │
└────────────────────────────────────┘
```

### 15.2 Rules

- **Only one timeline is active at a time** (marked ★)
- **Program Monitor always follows the active timeline**
- **Both timelines are editable** — click to make active, then edit
- **Playhead is synced** between both timelines
- **CUT proposes a montage** → user edits it directly or copies to a new version
- No forced "reference mode" / "read-only" — both are first-class timelines

### 15.3 Diff View

Parallel stacked view IS the diff. No separate color overlay needed in MVP.
Visual comparison = rhythm, density, scene order, clip duration — best read by eye.

---

## 16. Audio

### 16.1 Current State

- VU meter: REAL (AudioLevelMeter.tsx)
- Per-track volume sliders: REAL (lane volume in timeline headers)
- Full mixer panel: NOT in MVP
- Audio waveforms on tracks: REAL (WaveformCanvas.tsx)

### 16.2 Audio Roadmap (post-MVP)

```
Phase A: Basic audio mixer panel
  - Per-track: volume fader, pan, mute, solo
  - Master bus: volume fader, VU meter

Phase B: Record / VO / ADR
  - Record voiceover directly into timeline
  - ADR recording with cue playback
  - Narration input for documentary workflow

Phase C: Audio effects
  - Per-track EQ, compression, reverb (node-based)
  - Audio transitions (crossfade)
```

---

## 17. Hotkey Summary Score

| Category | Implemented | Total | Score |
|----------|------------|-------|-------|
| Playback (Space, JKL, ←→, Home/End) | 9 | 12 | 75% |
| Marking (I/O, M, ⇧M) | 4 | 11 | 36% |
| Editing (Delete, ⌘Z, ⌘⇧Z) | 3 | 14 | 21% |
| Tools (S snap) | 1 | 5 | 20% |
| Navigation (zoom ±) | 2 | 8 | 25% |
| Project (⌘S, ⌘I) | 1 | 4 | 25% |
| **TOTAL** | **20** | **54** | **37%** |

Premiere Tier 1 (cannot ship without): **6/14 = 43%**

---

## 18. Implementation Priority (Waves)

```
WAVE 1 — WIRING (fix broken connections, zero new features)
  W1.1  PanelSyncStore → EditorStore bridge
  W1.2  Panel Focus system (focusedPanel in store + onMouseDown handlers)
  W1.3  Source/Program feed split (sourceMediaPath + programMediaPath)
  W1.4  Source marks vs Sequence marks (separate state fields)
  W1.5  DAG timelineId prop + restore Inspector/Clip/StorySpace as tabs

WAVE 2 — DIRECTION + LABELS + TRACK CONTROLS
  W2.1  DAG Y-axis flip (START bottom)
  W2.2  Source Monitor label fix
  W2.3  Track header controls (lock/mute/solo/enable, monochrome SVG)
  W2.4  Track targeting / source patching

WAVE 3 — TIER 1 EDITING HOTKEYS (minimum for editing)
  HK-B1  Split at playhead (⌘K) + Ripple Delete (⌥Delete)
  HK-B2  Insert/Overwrite (,/.) with track targeting
  HK-B3  Navigate edits (↑/↓)
  HK-C   JKL Progressive Shuttle + 5-frame step + Clear In/Out
  HK-D   Tool State Machine (V/C/H/Z) + Razor click
  HK-E   Selection model (multi-select, linked selection toggle)

WAVE 4 — CONTEXT + SAVE + SELECTION
  W4.1  Context menu (right-click) — timeline clips, DAG nodes, project items
  W4.2  Save / Save As / Autosave + project settings
  W4.3  History panel (visual undo list)
  W4.4  Project settings dialog (framerate, timecode format)

WAVE 5 — MISSING UI FEATURES
  W5.1  Auto-Montage UI (3 buttons + progress + result → new tab)
  W5.2  Parallel Timelines (stacked dual view)
  W5.3  Favorite markers: N key + ⇧M comment
  W5.4  Project Panel view modes (List/Grid/DAG switch)

WAVE 6 — EXPORT / DELIVER
  W6.1  Master render dialog (ProRes/H.264)
  W6.2  Export selection / audio stems
  W6.3  Crosspost presets (YouTube, Instagram, TikTok)
  W6.4  OTIO / AAF export

WAVE 7 — DATA MODEL ALIGNMENT
  W7.1  Taxonomy naming reconciliation (code vs doc)
  W7.2  has_media edge creation
  W7.3  LoreNode implementation

WAVE 8 — LOGGER ENRICHMENT
  W8.1  Scene-material linking (clips → SCN_XX)
  W8.2  Shot scale auto-detection
  W8.3  Screenplay import (.fountain, .fdx)
  W8.4  Linked media behavior (link/unlink)

WAVE 9 — AUDIO
  W9.1  Basic audio mixer panel
  W9.2  Record VO / narration
  W9.3  Audio transitions (crossfade)

WAVE 10 — FUTURE / GENERATIVE
  W10.1  Documentary mode (footage → reconstructed script)
  W10.2  Interactive lore tokens (clickable names in script)
  W10.3  Multiverse DAG UI (branch visualization)
  W10.4  Storylines (X-columns / partiture)
  W10.5  Bridge layer (Circuit A ↔ Circuit B)
  W10.6  Effects node graph
  W10.7  Keyboard customization UI
  W10.8  Proxy workflow toggle
```

---

## 19. Conflicts Resolved

| Issue | Source A | Source B | Resolution |
|-------|---------|---------|------------|
| Layout: Inspector position | TARGET_ARCH §8.1: "under Source Monitor" | User: "must not block monitors" | **Tab in left column** (Analysis tabs) |
| Layout: StorySpace position | TARGET_ARCH §8.1: "mini in Program corner" | User: same | **Tab in left column** (Analysis tabs) |
| DAG Y-axis | TARGET_ARCH §2.2: "bottom=START" | Code: "START at top" | **Fix code** to match architecture |
| Taxonomy naming | DATA_MODEL: ScriptChunkNode, MediaNode | Code: scene_chunk, asset, note | **Reconcile in Wave 7** |
| Marker architecture | Multiple marker types as separate entities | ChatGPT review: standard + semantic | **Unified: one base type + semantics subtype** |
| Project/DAG naming | Separate panels "Project" and "DAG Project" | User: "one panel, two modes" | **Project panel with List/Grid/DAG modes** + separate Graph tab |
| Timeline edit rights | "Reference timeline = read-only" | User: "both editable, one active" | **Both editable, only one active at a time** |
| Source vs Sequence marks | Single markIn/markOut | ChatGPT: must be separate | **Separate: sourceMarkIn/Out + sequenceMarkIn/Out** |

---

## 20. References

| Document | Role |
|----------|------|
| **This document** | Single source of truth: panels, functions, hotkeys, contracts |
| CUT_TARGET_ARCHITECTURE.md | Deep architecture: DAG model, routing, BPM, markers |
| CUT_DATA_MODEL.md | Node/Edge type schemas |
| CUT_COGNITIVE_MODEL.md | UX rationale: 5 cognitive layers, 3 spaces |
| CUT_HOTKEY_ARCHITECTURE.md | Hotkey contract: Premiere reference, panel scope, JKL spec |
| ROADMAP_CUT_FULL.md | Legacy roadmap (superseded by this doc's Wave plan) |
| RECON_192_ARCH_VS_CODE_2026-03-18.md | Code audit: what's real vs what's on paper |
