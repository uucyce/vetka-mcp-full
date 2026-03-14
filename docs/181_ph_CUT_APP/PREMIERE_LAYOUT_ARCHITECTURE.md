# VETKA CUT — Window Architecture: IKEA-Premiere

**Phase:** 181.3
**Status:** DRAFT v3
**Date:** 2026-03-14

---

## 0. Constitution (Architecture Doc §0)

> **"CUT не ищет единственно верный монтаж. CUT исследует множество допустимых монтажей под разные цели, аудитории и контексты."**

---

## 1. Philosophy: Free Windows, Not Fixed Zones

### Premiere = free windows
Premiere Pro has **windows**, not "columns" or fixed zones. Any window can be:
- **Docked** in any position relative to other windows
- **Tabbed** inside another window (drag window title → onto another window)
- **Floating** independently (drag out of dock)
- **Fullscreen** (double-click title bar, or ` key)
- **Separate OS window** (for multi-monitor)
- **Minimized** to a dock bar

Users arrange whatever windows they want, however they want. There is no fixed "3-column" or "2-column" layout. There is only a **default arrangement** that users can completely rearrange.

### DaVinci ≠ our model
DaVinci has fixed "pages" (Edit, Color, Fusion, Fairlight). We do NOT do this. Every window is always available, like Premiere.

### VETKA additions to Premiere model:
- **Mini mode** — any window can be collapsed to a compact overlay (like StorySpace 3D mini)
- **DAG view** — any list window can switch to node graph view (Project list ↔ DAG)
- **PULSE integration** — metadata columns include Camelot key, energy, pendulum, etc.

---

## 2. Window Catalog

### 2.1 Source Monitor
- Opens on **double-click** on a clip in Project window
- Shows raw clip preview with In/Out point controls
- Standard NLE: **left side** by default (source = left, output = right)
- Can be anywhere — user decides

### 2.2 Program Monitor
- Shows **timeline playback** output
- Standard NLE: **right side** by default
- StorySpace 3D lives as mini overlay in corner
- Transport controls (play, JKL shuttle, frame step, timecode)

### 2.3 Project Window (the core)
This is the most important window. It's where all imported media lives.

**Two views (toggle):**

#### List View (default) — like Premiere's Project panel
An Excel-like table with metadata columns:

| Column | Source | Description |
|---|---|---|
| Name | filesystem | Clip filename |
| Duration | ffprobe | Media duration |
| Media Start/End | ffprobe | Timecode range |
| Video Info | ffprobe | Resolution, codec (e.g. "4K H.265") |
| Audio Info | ffprobe | Sample rate, channels |
| Frame Rate | ffprobe | fps |
| Date | filesystem | Creation/modification date |
| In / Out | editor | Set by user in Source Monitor |
| Media Type | scan | Video, Audio, Image, Document |
| Tag / Label | editor | Color-coded labels |
| **Camelot Key** | PULSE | e.g. "8A" (VETKA-specific) |
| **Energy** | PULSE | 0-100% |
| **Pendulum** | PULSE | -1..+1 |
| **Dramatic Function** | PULSE | accent_cut, hold, etc. |
| **Script Link** | script analysis | Which scene/line this clip serves |
| **Linked Files** | DAG edges | Related clips, takes, versions |
| **Sync Status** | sync engine | Synced/unsynced, method, confidence |

Columns are sortable, reorderable, hideable — exactly like Premiere.

#### DAG View — VETKA unique
Same data, visualized as a node graph:
- Nodes = clips, grouped by clusters (Characters, Locations, Takes, Music, SFX, etc.)
- Edges = relationships (same scene, same character, sync pair, etc.)
- Click node → opens in Source Monitor
- MCC has ready-made extractors: list ↔ DAG ↔ Excel ↔ Markdown

**Toggle button** in Project window header: `[☰ List] [◈ DAG]`

### 2.4 Script Window
- Screenplay text or auto-transcript
- Y-axis = time (vertical, chat-like)
- Click line → Source Monitor shows linked material
- BPM dots: green (audio), blue (visual), white (script)
- Can be tabbed with Project or Inspector

### 2.5 Inspector / Properties Window
- PULSE data for selected clip/scene
- Camelot wheel, energy, pendulum visualization
- Clip metadata (resolution, codec, fps)
- Like Premiere's Properties panel (v25.0+)

### 2.6 Timeline Window
- X-axis = time (horizontal, standard NLE)
- Tracks: V1, V2... (video), A1, A2... (audio)
- BPM track at bottom (green/blue/white/orange dots)
- Timeline tabs for versions (Main, cut-01, cut-02...)
- **~35% of screen height** by default
- Track height: pinch-to-zoom or Shift+drag
- Mute/Solo: **single button click** (not toggle/slider)

### 2.7 StorySpace 3D
- Analytical vectorscope for narrative
- Default: mini overlay inside Program Monitor
- Can expand to full window

### 2.8 Node Graph / Effects (future)
- DaVinci Fusion-style node editor
- Color correction, transitions, PULSE-driven effects

---

## 3. Import Flow

Import happens **inside the Project window**:

1. **Drag & drop** folder/files into Project window
2. **Cmd+I** keyboard shortcut → path input / file dialog
3. **Double-click** empty area in Project window
4. **File > Import** menu (future)

### Backend flow:
```
User provides path → POST /api/cut/bootstrap-async
  → Auto-creates sandbox if missing
  → Scans files (ffprobe, classify by extension)
  → Builds project.vetka-cut.json
  → refreshProjectState() → Project window populates
```

### After import:
- Import UI collapses to compact "+" button
- Clips appear in list/DAG view with all metadata columns
- Click clip → opens in Source Monitor

---

## 4. Window Management Implementation

### 4.1 PanelShell (existing, needs extension)
Each window is wrapped in `PanelShell` which provides:
- Title bar with tab/detach/close/fullscreen buttons
- Drag handle for floating
- Tab bar when multiple panels are stacked
- Drop zones when another panel is dragged over

### 4.2 Window modes
```typescript
type PanelMode =
  | 'docked'     // in a layout zone
  | 'tab'        // stacked as tab inside another window
  | 'floating'   // independent floating window
  | 'mini'       // compact overlay
  | 'minimized'; // collapsed to dock bar
```

### 4.3 Default arrangement
The system ships with a sensible default that users can rearrange:
```typescript
const DEFAULT_ARRANGEMENT = [
  { id: 'source_monitor',  mode: 'docked',   position: 'left_top' },
  { id: 'project',         mode: 'docked',   position: 'left_bottom' },
  { id: 'program_monitor', mode: 'docked',   position: 'right_top' },
  { id: 'inspector',       mode: 'docked',   position: 'right_bottom' },
  { id: 'script',          mode: 'tab',      tabParent: 'inspector' },
  { id: 'dag_project',     mode: 'tab',      tabParent: 'inspector' },
  { id: 'timeline',        mode: 'docked',   position: 'bottom' },
  { id: 'story_space_3d',  mode: 'mini',     miniParent: 'program_monitor' },
];
```

But user can completely rearrange by dragging windows. Layout persists per project.

---

## 5. Codec & Resolution Support

All standard production codecs must work:

| Category | Formats |
|---|---|
| Camera codecs | H.264, H.265/HEVC, ProRes (422/4444), DNxHD/DNxHR, RED R3D, BRAW |
| Containers | MOV, MP4, MXF, AVI, MKV |
| Audio | WAV, AIFF, MP3, AAC, FLAC, M4A |
| Images | JPEG, PNG, TIFF, EXR, DPX, BMP |
| Documents | MD, TXT, PDF, SRT, VTT |
| Projects | FCP XML, AAF, EDL, OTIO |

Resolution support: SD through 8K. Frame rates: 23.976, 24, 25, 29.97, 30, 48, 50, 59.94, 60, 120.

---

## 6. Export & Cross-Posting (future)

### Export modes:
- **Premiere Pro XML** (FCP XML / xmeml v4)
- **OpenTimelineIO** (.otio) → universal exchange
- **EDL** → legacy NLE
- **AAF** → Avid
- **Direct render** → H.264/H.265/ProRes with presets

### Social media cross-posting:
- YouTube (with chapters from markers)
- Instagram/Reels (aspect ratio presets: 9:16, 1:1, 4:5)
- TikTok
- Telegram
- VK
- Twitter/X

### VETKA Lab Player integration:
- Time markers via SRT export/import
- Comment system (timecoded notes)
- Shareable review links
- Viewer-side favorite markers → feed back into PULSE

---

## 7. What Changed from v1 → v3

| v1 (wrong) | v3 (correct) |
|---|---|
| "3-column layout" | **Free windows**, default arrangement |
| "Source Browser" (right) | **Project window** (left), opens Source Monitor on double-click |
| Fixed zones like DaVinci | **Premiere-style** free docking + tabs |
| "Columns" = layout zones | **Columns** = metadata fields inside Project window list view |
| 180px timeline | **~35% screen** timeline |
| No fullscreen | **Any window fullscreen** |
| No multi-monitor | **Detachable to OS windows** |
| Toggle switches for Mute | **Single button click** |
