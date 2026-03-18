# CUT NLE — Unified Vision
**Date:** 2026-03-19
**Sources:** CUT_TARGET_ARCHITECTURE.md, CUT_DATA_MODEL.md, CUT_COGNITIVE_MODEL.md, ROADMAP_CUT_FULL.md, CUT_HOTKEY_ARCHITECTURE.md, RECON_192_ARCH_VS_CODE_2026-03-18.md
**Purpose:** ONE document that defines ALL panels, ALL functions, ALL hotkeys. Single source of truth.
**Status:** CANONICAL — replaces scattered definitions across 6 docs

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
│  │ [DAG]     │  │  ├──────────────┤  │  ├────────────────┤  │
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
│  │ V1: ▓▓▓▓│▓▓▓▓▓│▓▓▓│▓▓▓▓▓│▓▓▓▓▓│▓▓▓               │    │
│  │ V2:      ▓▓▓│▓▓▓▓▓│▓▓▓▓│                           │    │
│  │ A1: ░░░░│░░░░░│░░░│░░░░░│░░░░░│░░░                 │    │
│  │ A2:    ░░░░│░░░░░│░░░░│                              │    │
│  │ BPM: ● ● ●● ● ●●● ● ● ●● ●                        │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Panel Registry

| # | Panel | Component | Tab Group | Function | Mounted |
|---|-------|-----------|-----------|----------|---------|
| 1 | **Project Panel** | `ProjectPanel.tsx` | Navigation | Media bin: all files, bins, import, search | YES |
| 2 | **Script Panel** | `ScriptPanel.tsx` | Navigation | Screenplay as clickable scene chunks + teleprompter | YES |
| 3 | **DAG Project** | `DAGProjectPanel.tsx` | Navigation | Multiverse graph: script spine + media + lore | YES |
| 4 | **PulseInspector** | `PulseInspector.tsx` | Analysis | PULSE metadata for selected scene: Camelot, energy, pendulum, McKee | Tab (restore) |
| 5 | **ClipInspector** | `ClipInspector.tsx` | Analysis | Selected clip properties: file, timing, sync, waveform, transcript | Tab (restore) |
| 6 | **StorySpace3D** | `StorySpace3D.tsx` | Analysis | 3D narrative space: Camelot wheel + McKee triangle + scene trajectory | Tab (restore) |
| 7 | **Source Monitor** | `VideoPreview.tsx` feed=source | — | Raw clip from DAG/Project click. IN/OUT marking. | YES |
| 8 | **Program Monitor** | `VideoPreview.tsx` feed=program | — | Timeline playback result. | YES |
| 9 | **Monitor Transport** | `MonitorTransport.tsx` | Embedded | Scrubber + timecode + play/JKL + IN/OUT (Source only) | YES (×2) |
| 10 | **Timeline Track View** | `TimelineTrackView.tsx` | — | Horizontal timeline: tracks, clips, ruler, playhead, drag, trim | YES |
| 11 | **Timeline Tab Bar** | `TimelineTabBar.tsx` | — | Multi-version tabs: [cut-00] [cut-01] [+] | YES |
| 12 | **Timeline Toolbar** | `TimelineToolbar.tsx` | — | Snap toggle, zoom slider | YES |
| 13 | **BPM Track** | `BPMTrack.tsx` | — | Beat grid: audio(green), visual(blue), script(white), sync(orange) | YES |
| 14 | **Audio Level Meter** | `AudioLevelMeter.tsx` | Embedded in VideoPreview | Stereo VU meter | YES |
| 15 | **Transcript Overlay** | `TranscriptOverlay.tsx` | Embedded in VideoPreview | Subtitles at currentTime | YES |

### 1.3 Tab Groups

**Left column** has two tab groups stacked:

**Navigation tabs** (top):
- Project — media bin, файлы, импорт
- Script — сценарий как кликабельные блоки сцен
- DAG — граф фильма: script spine + media nodes + lore

**Analysis tabs** (bottom):
- Inspector — PULSE метадата выбранной сцены (Camelot, energy, McKee)
- Clip — свойства выбранного клипа (файл, timing, sync, waveform)
- StorySpace — 3D визуализация нарратива

**Связь:** Navigation и Analysis работают с одним `activeSceneId`. Кликнул сцену в Script → DAG подсвечивает ноду → Inspector показывает её PULSE данные → Clip показывает лучший take → StorySpace позиционирует точку.

### 1.4 Dead Components (to delete)
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
| Select clip → Source Monitor | Click | — (store: setSourceMedia) | WIRING GAP (goes to activeMediaPath, not sourceMediaPath) |
| Create new bin | ⌘/ | — | MISSING |
| Search/filter | ⌘F | — | MISSING |
| Delete item | Delete | — | MISSING |
| Reveal in Finder | ⇧H | — | MISSING |

### 2.2 Script Panel

| Function | Hotkey | Backend API | Status |
|----------|--------|-------------|--------|
| Parse script → scene chunks | — | POST /cut/script/parse | REAL |
| Click chunk → sync all panels | Click | syncFromScript() | REAL (but PanelSyncStore not bridged) |
| Teleprompter auto-scroll | — | — | REAL |
| Import .fountain/.fdx/.pdf/.docx | — | POST /cut/script/parse | MISSING (plain text only) |
| Manual drag-split chunks | Drag | — | MISSING |
| Lore tokens (clickable names) | Click on name | — | MISSING (Phase 7+) |

### 2.3 DAG Project Panel

| Function | Hotkey | Backend API | Status |
|----------|--------|-------------|--------|
| Fetch DAG for timeline | — | GET /cut/project/dag/{id} | REAL |
| Scene chunks as vertical spine | — | — | REAL |
| Video nodes LEFT, Audio RIGHT | — | — | REAL |
| Click node → Source Monitor | Click | syncFromDAG() → setSourceMedia() | WIRING GAP |
| Y-axis = chronology (START bottom) | — | — | BROKEN (START at top) |
| Flip Y toggle | — | — | MISSING |
| Lore nodes (characters, locations) | — | — | MISSING |
| Multiverse branches visualization | — | — | MISSING (Phase 7+) |
| Storylines (X-columns) | — | — | MISSING (Phase 7+) |
| Agent visualization (pulsing nodes) | — | — | MISSING (Phase 4+) |
| Active timelineId prop | — | — | BROKEN (hardcoded 'main') |

### 2.4 Source Monitor

| Function | Hotkey | Backend API | Status |
|----------|--------|-------------|--------|
| Show raw clip (from DAG/Project click) | — | — | WIRING GAP (same as Program) |
| Play/Pause | Space | — | REAL (but global, not panel-scoped) |
| JKL shuttle | J/K/L | — | SIMPLIFIED (±5s, not progressive) |
| Frame step | ←/→ | — | REAL |
| Mark IN | I | — | REAL |
| Mark OUT | O | — | REAL |
| Clear IN/OUT | ⌥I/⌥O/⌘⇧X | — | MISSING |
| Go to IN/OUT | ⇧I/⇧O | — | MISSING |
| Add favorite marker | M | POST /cut/time-markers/apply | REAL |
| Add negative marker | N | — | MISSING |
| Add comment marker | ⇧M | POST /cut/time-markers/apply | REAL |
| Insert to Timeline | , | POST /cut/timeline/apply | MISSING handler |
| Overwrite to Timeline | . | POST /cut/timeline/apply | MISSING handler |
| Match Frame | F | — | MISSING |
| 5-frame step | ⇧←/⇧→ | — | MISSING |

### 2.5 Program Monitor

| Function | Hotkey | Backend API | Status |
|----------|--------|-------------|--------|
| Show timeline playback | — | — | WIRING GAP (same feed as Source) |
| Play/Pause | Space | — | REAL |
| JKL shuttle | J/K/L | — | SIMPLIFIED |
| Frame step | ←/→ | — | REAL |
| Go to Start/End | Home/End | — | REAL |
| Cycle playback rate | — | — | REAL |

### 2.6 Timeline

| Function | Hotkey | Backend API | Status |
|----------|--------|-------------|--------|
| Select clip | Click | — | REAL |
| Move clip (drag) | Drag | POST /cut/timeline/apply | REAL |
| Trim clip edges | Drag edge | POST /cut/timeline/apply | REAL |
| Delete clip (leave gap) | Delete | POST /cut/timeline/apply remove_clip | REAL |
| Ripple Delete | ⌥Delete / ⇧Delete | POST /cut/timeline/apply | MISSING handler |
| Split at playhead | ⌘K / B | POST /cut/timeline/apply split_clip | MISSING handler |
| Ripple Trim Prev→Playhead | Q | POST /cut/timeline/apply | MISSING |
| Ripple Trim Next→Playhead | W | POST /cut/timeline/apply | MISSING |
| Navigate prev edit point | ↑ | — | MISSING |
| Navigate next edit point | ↓ | — | MISSING |
| Nudge clip ±1 frame | ⌥←/⌥→ | — | MISSING handler |
| Nudge clip ±5 frames | ⌥⇧←/⌥⇧→ | — | MISSING |
| Snap toggle | S | — | REAL |
| Zoom in/out | =/- | — | REAL |
| Zoom to fit | \ | — | MISSING |
| Selection tool | V / A | — | MISSING handler |
| Razor tool | C / B | — | MISSING handler |
| Scene detection | ⌘D | POST /cut/scene-detect-and-apply | REAL |
| Create new timeline version | Tab bar [+] | — | REAL |
| Parallel timeline (stacked) | — | — | MISSING |
| Undo | ⌘Z | POST /cut/undo | REAL |
| Redo | ⌘⇧Z | POST /cut/redo | REAL |
| Copy/Paste | ⌘C/⌘V | — | MISSING handler |
| Select All | ⌘A | — | MISSING handler |

### 2.7 Inspector (PulseInspector)

| Function | Hotkey | Backend API | Status |
|----------|--------|-------------|--------|
| Show PULSE metadata for scene | — | — | REAL (component exists) |
| Camelot key + mini wheel | — | — | REAL |
| Energy profile | — | — | REAL |
| Pendulum position | — | — | REAL |
| Dramatic function | — | — | REAL |
| McKee triangle position | — | — | REAL |
| **Mounted in layout** | — | — | **NO — returns null** |

### 2.8 Clip Inspector

| Function | Hotkey | Backend API | Status |
|----------|--------|-------------|--------|
| Show clip properties | — | — | REAL (component exists) |
| Filename, timing, sync | — | — | REAL |
| Waveform mini | — | — | REAL |
| Transcript excerpt | — | — | REAL |
| Marker list for clip | — | — | REAL |
| **Mounted in layout** | — | — | **NO — removed** |

### 2.9 StorySpace3D

| Function | Hotkey | Backend API | Status |
|----------|--------|-------------|--------|
| Camelot wheel (horizontal) | — | — | REAL (component exists) |
| McKee triangle (vertical) | — | — | REAL |
| Scene dots (color=pendulum, size=energy) | — | — | REAL |
| Trajectory lines between scenes | — | — | REAL |
| Click dot → sync to scene | Click | syncFromStorySpace() | REAL |
| Orbit controls (3D rotation) | Drag | — | REAL |
| **Mounted in layout** | — | — | **NO — removed** |

### 2.10 Auto-Montage (no panel yet)

| Function | Hotkey | Backend API | Status |
|----------|--------|-------------|--------|
| Favorites Cut | — | POST /cut/pulse/auto-montage | Backend REAL, UI MISSING |
| Script Cut | — | POST /cut/pulse/auto-montage | Backend REAL, UI MISSING |
| Music Cut | — | POST /cut/pulse/auto-montage | Backend REAL, UI MISSING |
| Progress indicator | — | — | MISSING |
| Result → new timeline tab | — | — | MISSING |
| Reverse dependency (alternatives) | — | — | MISSING |

### 2.11 Global Functions

| Function | Hotkey | Status |
|----------|--------|--------|
| Undo | ⌘Z | REAL |
| Redo | ⌘⇧Z | REAL |
| Import | ⌘I | REAL (stub — fires event) |
| Toggle NLE/Debug view | ⌘\ | REAL |
| Escape | Esc | MISSING handler |
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
| Marking (I/O) | Panel-scoped | Source: marks source clip. Program: marks sequence position |
| Editing (Delete, ⌘K, Q/W) | Panel-scoped | Only works when Timeline focused |
| Tools (V, C, S) | Panel-scoped | Only works when Timeline focused |
| Clipboard (⌘Z, ⌘C/V) | Global | Works everywhere |
| Import (⌘I) | Global | Works everywhere |
| Panel switch (⇧1-5) | Global | Works everywhere |
| View toggle (⌘\) | Global | Works everywhere |

---

## 4. Store Architecture

### 4.1 Three Stores

```
useCutEditorStore      — master state: playback, timeline, clips, media, zoom
usePanelSyncStore      — cross-panel sync matrix (who notifies whom)
usePanelLayoutStore    — panel modes, dock positions, grid sizes
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

// Routing:
Click in Project/DAG → setSourceMedia()
Timeline playback → setProgramMedia()
Click script line → setSourceMedia(linked raw) + setProgramMedia(jump to time)
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

---

## 7. Hotkey Summary Score

| Category | Implemented | Total | Score |
|----------|------------|-------|-------|
| Playback (Space, JKL, ←→, Home/End) | 9 | 12 | 75% |
| Marking (I/O, M, ⇧M) | 4 | 9 | 44% |
| Editing (Delete, ⌘Z, ⌘⇧Z) | 3 | 12 | 25% |
| Tools (S snap) | 1 | 5 | 20% |
| Navigation (zoom ±) | 2 | 6 | 33% |
| **TOTAL** | **19** | **44** | **43%** |

Premiere Tier 1 (cannot ship without): **6/12 = 50%**

---

## 8. Implementation Priority

```
WAVE 1 — WIRING (fix broken connections, write zero new features)
  W1.1  PanelSyncStore → EditorStore bridge
  W1.2  Panel Focus system + wire useCutHotkeys to NLE
  W1.3  Source/Program feed split (store + VideoPreview prop)
  W1.4  DAG timelineId prop + restore Inspector/Clip/StorySpace as tabs

WAVE 2 — DIRECTION + LABELS
  W2.1  DAG Y-axis flip (START bottom)
  W2.2  Source Monitor label fix

WAVE 3 — TIER 1 EDITING HOTKEYS (minimum for editing)
  HK-B1  Split at playhead (⌘K) + Ripple Delete (⌥Delete)
  HK-B2  Insert/Overwrite (,/.) + Navigate edits (↑/↓)
  HK-C   JKL Progressive Shuttle + 5-frame step + Clear In/Out
  HK-D   Tool State Machine (V/C/H/Z) + Razor click

WAVE 4 — MISSING UI
  W4.1  Auto-Montage UI (3 buttons + progress)
  W4.2  Parallel Timelines (stacked dual view)
  W4.3  Favorite markers: N key + MM double-tap

WAVE 5 — DATA MODEL ALIGNMENT
  W5.1  Taxonomy naming reconciliation (code vs doc)
  W5.2  has_media edge creation
  W5.3  LoreNode implementation

WAVE 6 — LOGGER ENRICHMENT
  W6.1  Scene-material linking (clips → SCN_XX)
  W6.2  Shot scale auto-detection
  W6.3  Screenplay import (.fountain, .fdx)

WAVE 7 — FUTURE
  W7.1  Documentary mode
  W7.2  Interactive lore tokens
  W7.3  Multiverse DAG UI
  W7.4  Storylines (X-columns)
  W7.5  Bridge layer (Circuit A ↔ Circuit B)
```

---

## 9. Conflicts Resolved

| Issue | Source A | Source B | Resolution |
|-------|---------|---------|------------|
| Layout: Inspector position | CUT_TARGET_ARCHITECTURE §8.1: "under Source Monitor" | User feedback: "these panels must not block monitors" | **Tab in left column** (Analysis tabs group) |
| Layout: StorySpace position | CUT_TARGET_ARCHITECTURE §8.1: "mini in Program corner" | User feedback: same | **Tab in left column** (Analysis tabs group) |
| Hotkeys: Phase ordering | ROADMAP Phase 6: "JKL shuttle" | CUT_HOTKEY_ARCHITECTURE Phase C | **No conflict** — hotkey doc is a detail of roadmap Phase 6 |
| Hotkeys: scope | ROADMAP Phase 6.0: "context-aware focus" | CUT_HOTKEY_ARCHITECTURE §5.1: "focusedPanel in store" | **Same concept**, hotkey doc has implementation spec |
| DAG Y-axis | CUT_TARGET_ARCHITECTURE §2.2: "bottom=START" | RECON_192: "code has START at top" | **Fix code** to match architecture |
| Taxonomy naming | CUT_DATA_MODEL: ScriptChunkNode, MediaNode | Code: scene_chunk, asset, note | **Reconcile in Wave 5** |

---

## 10. References

| Document | Role |
|----------|------|
| **This document** | Single source of truth: panels, functions, hotkeys |
| CUT_TARGET_ARCHITECTURE.md | Deep architecture: DAG model, routing, BPM, markers |
| CUT_DATA_MODEL.md | Node/Edge type schemas |
| CUT_COGNITIVE_MODEL.md | UX rationale: 5 cognitive layers, 3 spaces |
| CUT_HOTKEY_ARCHITECTURE.md | Hotkey contract: Premiere reference, panel scope, JKL spec |
| ROADMAP_CUT_FULL.md | Implementation phases with per-task granularity |
| RECON_192_ARCH_VS_CODE_2026-03-18.md | Code audit: what's real vs what's on paper |
