# VETKA CUT Manual

**Version 1.0** | 2026-03-25 | VETKA AI Project

---

## Abstract

VETKA CUT is a non-linear video editor built from scratch on React 19 + FastAPI + FFmpeg, designed to replace commercial NLE workflows for independent film production. The architecture follows Final Cut Pro 7's editing paradigm — three-point editing, JKL shuttle, razor/ripple/roll/slip/slide trim tools — while extending it with AI-native features: PULSE music-driven editing, DAG scene graph, automatic scene detection, and Camelot harmonic path planning.

This manual is the **single source of truth** for VETKA CUT. It documents every feature from actual source code inspection, not from specifications or roadmaps. Each feature carries a status label (IMPLEMENTED, PARTIAL, or [PLANNED]) so the reader always knows what works today and what is coming.

As of version 1.0, VETKA CUT implements **78% of core FCP7 features** (28 of 36) with 82 keyboard shortcuts across two presets (FCP7 and Premiere Pro). The system supports 17+ export codecs, real-time video scopes via WebSocket, 3-way color correction with LUT support, and a dockview-based panel system with 22 draggable panels.

> **How to read status labels:**
> - **IMPLEMENTED** — code exists and is wired end-to-end
> - **PARTIAL** — code exists but incomplete (detail in description)
> - **[PLANNED Wx]** — not yet implemented, assigned to wave x
>
> **Replaces:** CUT_UNIFIED_VISION.md, ROADMAP_CUT_FULL.md, FCP7_COMPLIANCE_MATRIX, RECON_192, CUT_DATA_MODEL.md, Delta RECONs.

---

## Table of Contents

### Part I — Foundations
- [1. Getting Started](#section-1-getting-started) — Stack, launch, interface, workspace presets, keyboard shortcuts
- [2. Project & Media Management](#section-2-project-and-media-management) — Projects, import, bins, proxy, codecs, sequence settings

### Part II — Core Editing
- [3. Editing](#section-3-editing) — Three-point editing, insert/overwrite, razor, undo, selection, marks
- [4. Trimming Tools](#section-4-trimming-tools) — Selection, razor, ripple, roll, slip, slide, snap

### Part III — Timeline & Audio
- [5. Timeline](#section-5-timeline) — Lanes, multi-timeline, track targeting/locking, ruler, zoom, BPM markers
- [6. Audio](#section-6-audio) — Mixer, rubber band automation, playback, waveforms, scopes, PULSE analysis

### Part IV — Effects & Output
- [7. Effects & Color Correction](#section-7-effects--color-correction) — Transitions, motion, speed, color wheels, LUT, video scopes, keyframes
- [8. Export & Delivery](#section-8-export--delivery) — Master render, editorial export, publish presets, render pipeline

### Part V — Advanced
- [9. Advanced — VETKA CUT Exclusive Features](#section-9-advanced--vetka-cut-exclusive-features) — DAG, multicam, screenplay, PULSE, scene detection, Tauri desktop

### Appendices
- [Appendix A: Feature Coverage Summary](#appendix-a-feature-coverage-summary) — Wave coverage, FCP7 compliance %, missing features

> **Screenshots:** Sections marked with `[screenshot: description]` are placeholders for UI captures.
> Delta/Gamma agents add screenshots during UI test passes (see task `tb_screenshot_manual`).

---

## Section 1: Getting Started

### 1.1 What Is VETKA CUT

VETKA CUT is a non-linear video editor (NLE) built from scratch on a React + Python + FFmpeg stack. It is not a plugin or wrapper — it is a full editing environment intended to eventually replace commercial NLE workflows for the VETKA production pipeline.

**Tech stack (verified against source):**

| Layer | Technology |
|---|---|
| Frontend UI | React 19, TypeScript, Vite 5 |
| Panel docking | dockview-react 5.1.0 |
| State management | Zustand 4.5.2 |
| 3D / graph views | Three.js 0.170, @react-three/fiber, @xyflow/react |
| Backend API | FastAPI 0.120.0, Uvicorn 0.38.0 |
| Real-time events | Socket.IO (python-socketio 5.14.2) |
| Media analysis | FFprobe (system binary, via subprocess) |
| Proxy generation | FFmpeg (system binary, libx264 ultrafast) |
| AI / ML pipeline | numpy, scikit-learn, Whisper (MLX), OpenAI, Anthropic |

The desktop shell is Tauri 2.x (Rust + WebView). CUT can also run as a browser-based app on localhost.

**Differs from FCP7:** FCP7 was a 32-bit Cocoa application. VETKA CUT is a web-stack NLE running inside a native shell. The underlying architecture is closer to Premiere Pro or DaVinci Resolve in the sense of separating backend media processing from frontend editing.

---

### 1.2 System Requirements

**Minimum (browser / Tauri):**
- macOS (primary development and test platform; Apple Silicon recommended for MLX Whisper)
- Node.js 20+ (for building the frontend)
- Python 3.13 (backend)
- FFmpeg + FFprobe on system PATH (required — no bundled binary)
- 8 GB RAM

**Python backend dependencies (from `requirements.txt`):**
- `fastapi==0.120.0`, `uvicorn==0.38.0`
- `numpy==2.3.4`, `scikit-learn==1.8.0`, `Pillow==10.4.0`
- `mlx-whisper==0.4.3` (Apple Silicon), `openai-whisper==20250625`
- `torch==2.9.1` (for non-MLX paths)
- `qdrant-client==1.10.0`, `weaviate-client==3.26.7`
- `openai==2.6.1`, `anthropic==0.75.0`

**Frontend dependencies (from `client/package.json`):**
- `dockview-react==5.1.0` (panel docking)
- `zustand==4.5.2` (state)
- `three==0.170.0`, `@react-three/fiber==9.0.0`
- `@tauri-apps/api==2.9.1`, `@tauri-apps/plugin-dialog==2.6.0`

---

### 1.3 Launching CUT

CUT is launched via its dedicated entry point, separate from the main VETKA app. The frontend routing is handled in `CutStandalone.tsx` (not through the main `App.tsx` 3D canvas).

**Development server:**
```
cd client
npm run dev:cut:human    # port 3011, human user
npm run dev:cut:opus     # port 3111, Opus agent
```

**Tauri desktop build:**
```
npm run tauri:dev:cut:human
npm run tauri:build:cut:human
```

**What happens on launch:**

1. `CutStandalone.tsx` mounts and reads `sandboxRoot` + `projectId` from `useCutEditorStore`.
2. If no project is active, `DockviewLayout.tsx` detects `showWelcome = !sandboxRoot && !projectId` and renders `WelcomeScreen`.
3. On project open, the store loads project state from the backend (`GET /api/cut/project-state`), populates lanes, markers, thumbnails, waveforms.
4. `DockviewLayout` builds the panel layout using the saved or default preset builder.

---

### 1.4 Interface Overview

The CUT interface is a dockview-based layout — all panels are draggable, dockable, tab-groupable, and resizable. There is no fixed grid.

`[screenshot: CUT full interface — Editing workspace preset with all panels visible]`

**Complete panel registry** (verified from `DockviewLayout.tsx` `PANEL_COMPONENTS`):

| Panel ID | Title | Description |
|---|---|---|
| `project` | Project | Media bins: Video Clips, Audio, Music, Stills, Boards, Documents, Other |
| `script` | Script | Script text with scene sync |
| `graph` | Graph | Scene/DAG relationship graph (xyflow) |
| `inspector` | Inspector | Clip properties, effects, keyframes |
| `clip` | Clip | Clip inspector (per-clip metadata) |
| `storyspace` | StorySpace | 3D narrative positioning (PULSE) |
| `history` | History | Undo/redo history list |
| `montage` | Montage | AI auto-montage control panel |
| `effects` | Effects | Effects browser (transitions are a category inside Effects, not a separate panel) |
| `mixer` | Mixer | Audio mixer with per-lane faders and master bus |
| `scopes` | Scopes | Video scopes: histogram, waveform, vectorscope, parade |
| `colorcorrector` | Color | Color correction controls (log decode + LUT) |
| `lutbrowser` | LUTs | LUT file browser and preview |
| `tools` | Tools | Tool palette (Selection, Razor, Slip, Slide, Ripple, Roll, Hand, Zoom) |
| `markers` | Markers | Marker list (editorial + PULSE unified markers) |
| `timelines` | Timelines | Multi-timeline tab manager |
| `publish` | Publish | Export / publish panel |
| `source` | SOURCE | Source monitor (raw clip playback) |
| `program` | PROGRAM | Program monitor (timeline playback output) |
| `timeline` | Timeline | Main timeline (multi-instance capable) |
| `multicam` | MULTICAM | Multicam angle grid viewer |

**Not a panel (modal dialogs accessed via menu):**
- Speed/Duration dialog (Cmd+J)
- Sequence Settings dialog (via Sequence menu)
- Export dialog (Cmd+E)

---

### 1.5 Workspace Presets

**Status:** IMPLEMENTED

CUT has four built-in workspace presets, defined in `client/src/components/cut/presetBuilders.ts`:

| Preset | Panel arrangement |
|---|---|
| **Editing** | Left: Project/Script/Graph + Inspector/Clip/History/StorySpace. Center: Source + Program monitors. Right: Effects. Bottom: Timeline. |
| **Color** | Left top: Source monitor. Left bottom: Project/Inspector/Clip/History + Effects. Center: Program (large). Right: Color/LUTs + Scopes. Bottom: Timeline. |
| **Audio** | Left: Project/Script + Inspector/Clip/History. Center: Source/Program (stacked). Right: Mixer (wide). Right of analysis: Effects. Bottom: Timeline (tall, 380px). |
| **Multicam** | Left: Multicam angle grid + Mixer. Center: Program (large). Right: Project/Clip. Bottom: Timeline (tall). |

A `custom` preset also exists (maps to the Editing builder). Presets are switched via the Window menu. Custom layout modifications are saved per-preset to `localStorage` under `cut_dockview_{preset}`.

**Differs from FCP7:** FCP7 had three workspaces (Editing, Color Correction, Audio). CUT adds Multicam as a fourth built-in preset.

---

### 1.6 Panel Focus System

**Status:** IMPLEMENTED
**Hotkeys (both presets):** Cmd+1 through Cmd+5

Panel focus determines which panel receives keyboard input for panel-scoped actions.

| Hotkey | Panel focused |
|---|---|
| Cmd+1 | Source Monitor (`focusSource`) |
| Cmd+2 | Program Monitor (`focusProgram`) |
| Cmd+3 | Timeline (`focusTimeline`) |
| Cmd+4 | Project (`focusProject`) |
| Cmd+5 | Effects (`focusEffects`) |

Focus state is stored in `useCutEditorStore.focusedPanel`. The active focus scope is defined in `useCutHotkeys.ts` as `ACTION_SCOPE` — most actions are scoped to `'global'` (fire from any focused panel). Clicking into a panel activates its focus via dockview's `onDidActivePanelChange` event handler in `DockviewLayout.tsx`.

The `null` focus state is treated as `timeline` (the default focus on app load).

**Differs from FCP7:** FCP7 did not have an explicit Cmd+1–5 panel focus system. VETKA CUT adopts this pattern from Premiere Pro and extends it with a software focus scope per action, not just a visual highlight.

---

### 1.7 Backtick Panel Maximize

**Status:** IMPLEMENTED
**Hotkey:** Backtick (`` ` ``)

Pressing backtick maximizes the currently focused panel to fill the entire dockview area, hiding all other panels. Pressing again restores the layout. Implemented via `toggleMaximize` from `useDockviewStore`.

**Differs from FCP7:** FCP7 used a different mechanism for single-panel focus. The backtick convention is from Premiere Pro.

---

### 1.8 Keyboard Shortcut System

**Status:** IMPLEMENTED

CUT has a centralized hotkey registry in `client/src/hooks/useCutHotkeys.ts`. Two built-in presets are available; a third "custom" mode allows per-action overrides stored in localStorage.

**Preset selection:** Persisted in `localStorage` under `cut_hotkey_preset`. Default is `premiere`.

**Selected hotkey comparison (FCP7 vs Premiere preset):**

| Action | FCP7 Preset | Premiere Preset |
|---|---|---|
| Play / Pause | Space | Space |
| Stop | K | K |
| Shuttle Back | J | J |
| Shuttle Forward | L | L |
| Frame Step Back | ArrowLeft | ArrowLeft |
| Frame Step Forward | ArrowRight | ArrowRight |
| 5-Frame Step Back | Shift+ArrowLeft | Shift+ArrowLeft |
| 5-Frame Step Forward | Shift+ArrowRight | Shift+ArrowRight |
| Mark In | I | I |
| Mark Out | O | O |
| Clear In/Out | Alt+X | Cmd+Shift+X |
| Play In to Out | Ctrl+\ | Shift+\ |
| Undo | Cmd+Z | Cmd+Z |
| Redo | Cmd+Shift+Z | Cmd+Shift+Z |
| Split / Add Edit | Cmd+K | Cmd+K |
| Ripple Delete | Shift+Delete | Shift+Delete |
| Select tool | A | V |
| Razor tool | B | C |
| Ripple tool | R | B |
| Roll tool | Shift+R | N |
| Slip tool | Y | Y |
| Slide tool | U | U |
| Snap toggle | N | S |
| Linked selection | Shift+L | Cmd+L |
| Add Marker | M | M |
| Zoom In (timeline) | Cmd+= | = |
| Zoom Out (timeline) | Cmd+- | - |
| Zoom to Fit | Shift+Z | \ |
| Cycle Track Height | Shift+T | Shift+T |
| Save Project | Cmd+S | Cmd+S |
| Import Media | Cmd+I | Cmd+I |
| Export Timeline | Cmd+E | Cmd+E |
| Scene Detect | Cmd+D | Cmd+D |
| Speed / Duration | Cmd+J | Cmd+J |
| Match Frame | F | F |
| Extend Edit | E | E |
| L-Cut | Alt+E | Alt+E |
| J-Cut | Alt+Shift+E | Alt+Shift+E |
| Default Transition | Cmd+T | Cmd+T |
| Lift Clip | ; | ; |
| Extract Clip | ' | ' |
| Insert Edit | , | , |
| Overwrite Edit | . | . |
| Focus Source | Cmd+1 | Cmd+1 |
| Focus Program | Cmd+2 | Cmd+2 |
| Focus Timeline | Cmd+3 | Cmd+3 |
| Focus Project | Cmd+4 | Cmd+4 |
| Focus Effects | Cmd+5 | Cmd+5 |
| Make Subclip | Cmd+U | Cmd+U |
| Keyframe Record Mode | Cmd+Shift+K | Cmd+Shift+K |
| PULSE Analysis | Cmd+Shift+P | Cmd+Shift+P |
| Auto Montage | Cmd+Shift+M | Cmd+Shift+M |

**Differences between presets:**
- Select tool: `A` (FCP7) vs `V` (Premiere)
- Razor tool: `B` (FCP7) vs `C` (Premiere)
- Ripple tool: `R` (FCP7) vs `B` (Premiere) — note: `B` conflicts with FCP7's razor, which is why FCP7 uses `B` for razor and `R` for ripple
- Roll tool: `Shift+R` (FCP7) vs `N` (Premiere)
- Snap toggle: `N` (FCP7) vs `S` (Premiere)
- Clear In/Out: `Alt+X` (FCP7) vs `Cmd+Shift+X` (Premiere)
- Zoom commands: `Cmd+=`/`Cmd+-` (FCP7) vs `=`/`-` without modifier (Premiere)

Custom overrides are applied on top of the selected preset. The resolver merges preset + overrides at runtime and is recomputed on every keydown event.

---

## Section 2: Project and Media Management

### 2.1 Creating and Opening Projects

**Status:** IMPLEMENTED

Projects in VETKA CUT are created through the **bootstrap** flow. There is no "File > New Project" dialog in the traditional sense — instead, a project is initialized by pointing CUT at a media folder.

**Opening a project (WelcomeScreen flow):**
- On launch without an active project, the Welcome Screen is shown.
- Selecting a recent project or browsing for a folder triggers `POST /api/cut/bootstrap` (implemented in `cut_routes_bootstrap.py`).
- The backend creates a `CutProjectStore` in the selected `sandbox_root`, assigns a `project_id`, and begins background analysis jobs.
- Recent projects are tracked in localStorage by `WelcomeScreen.tsx` via `addRecentProject()`.

**Project state is loaded via:**
```
GET /api/cut/project-state?sandbox_root=...&project_id=...
```
This returns all project data: `timeline_state`, `scene_graph`, `thumbnail_bundle`, `waveform_bundle`, `sync_surface`, `time_marker_bundle`, etc.

**Differs from FCP7:** FCP7 used `.fcp` project files opened via standard macOS file dialog. CUT uses a sandbox directory structure on the filesystem — the project is a folder, not a single file.

---

### 2.2 Saving Projects

**Status:** IMPLEMENTED
**Hotkey:** Cmd+S (both presets)

Project saving is handled by `useCutAutosave.ts`.

**Manual save (Cmd+S):**
- Serializes the full timeline state in `cut_timeline_state_v1` schema (lanes, markers, playhead position, zoom, scroll, In/Out marks, framerate).
- POSTs to `POST /api/cut/save`.
- The status bar shows "saving" → "saved" feedback via `saveStatus` in the store.
- `lastSavedAt` (ISO timestamp) is returned from backend and displayed.

**Autosave:**
- Fires every 2 minutes when `hasUnsavedChanges === true` and `sandboxRoot` is set.
- `hasUnsavedChanges` is set to `true` whenever `lanes` or `markers` change in the store.

**Sequence settings** are saved separately via `POST /api/cut/sequence-settings` from `SequenceSettingsDialog.tsx`.

**Differs from FCP7:** FCP7 saved to a single `.fcp` binary/XML file. CUT saves to JSON files within the sandbox directory. Autosave interval (2 min) is similar to FCP7's autosave vault behavior.

---

### 2.3 Media Import Pipeline

**Status:** IMPLEMENTED
**Hotkey:** Cmd+I (both presets)

**Import methods (from `ProjectPanel.tsx`):**
1. **Cmd+I hotkey** — fires a `cut:import-media` custom DOM event, picked up by ProjectPanel to open the file picker.
2. **Double-click the dropzone** — opens native file picker via an `<input type="file">` element.
3. **Drag and drop** — files or folders dragged into the ProjectPanel dropzone.

**What happens on import:**
1. Files are sent to the backend via `POST /api/cut/media/import` (in the media sub-router).
2. The backend runs `probe_file()` from `cut_codec_probe.py` using `ffprobe` to extract full metadata.
3. Background jobs are triggered for: thumbnail generation, waveform extraction, optional proxy generation.
4. The frontend polls / receives Socket.IO events to update the Project panel as assets become available.

**Supported file types (from `ProjectPanel.tsx` `MEDIA_ACCEPT` string):**
```
video/*, audio/*, image/*,
.mov, .mp4, .avi, .mkv, .webm,
.m4a, .wav, .mp3, .flac, .aac, .ogg,
.jpg, .jpeg, .png, .tiff, .bmp, .webp
```

**Differs from FCP7:** FCP7's "Log and Transfer" flow was built around tape-based ingest. CUT imports from filesystem paths directly and has no tape/device capture workflow.

---

### 2.4 Project Panel (Media Bins)

**Status:** IMPLEMENTED

The Project panel (`client/src/components/cut/ProjectPanel.tsx`) organizes imported media into automatic bins based on file modality.

`[screenshot: Project Panel — bins with imported media in grid view]`

**Bin structure (fixed order):**

| Bin | Icon | Populated by |
|---|---|---|
| Video Clips | ▶ | Files with video stream |
| Audio | ♪ | Audio-only files (non-music-track) |
| Music | ♫ | Files in audio_sync lanes |
| Stills | ◻ | Image files (modality = image) |
| Boards | ▦ | Files under `/boards/` path |
| Documents | ≡ | Files with modality = document |
| Other | ● | Anything else |

**View modes (Cmd+\ cycles):**
- `list` — compact list with thumbnail, filename, duration
- `columns` — two-column list view
- `grid` — thumbnail grid (80px min cell width, 16:9 aspect)
- `dag` — DAG graph view (xyflow-based)

**Per-item actions (right-click context menu):**
- Open in Source Monitor (single-click also does this)
- Drag to timeline (drag and drop onto a lane)
- Rename, delete, reveal in Finder

**Differs from FCP7:** FCP7 bins were user-managed folders the editor created manually. CUT bins are auto-classified by modality — users cannot rename or create custom bins in the current implementation.

---

### 2.5 Proxy Workflow

**Status:** IMPLEMENTED

Proxy generation is handled by `src/services/cut_proxy_worker.py`.

**How it works:**
- When a clip is imported and `probe_file()` returns a `playback_class` of `proxy_recommended` or `transcode_required`, a proxy is automatically generated as a background job.
- Proxies are stored in `{sandbox_root}/cut_runtime/proxies/`.
- Three proxy tiers exist in code:

| Preset | Resolution | Codec | Bitrate | CRF |
|---|---|---|---|---|
| `PROXY_720P` | 1280x720 | libx264 ultrafast | 2 Mbps | 28 |
| `PROXY_480P` | 854x480 | libx264 ultrafast | 1 Mbps | 30 |
| `PROXY_360P` | 640x360 | libx264 ultrafast | 500 kbps | 32 |

**Auto-selection decision matrix (from `auto_select_proxy_spec()`):**

| Source class | Source resolution | Proxy selected |
|---|---|---|
| `transcode_required` | Any | 480p |
| `proxy_recommended` | 4K+ | 480p |
| `proxy_recommended` | 1080p | 720p |
| `proxy_recommended` | <1080p | No proxy (already small) |
| `native` | 4K+ | 720p |
| `native` | <4K | No proxy |
| `audio_only` | — | No proxy |

**Proxy mode control** is available in sequence settings via `proxyMode: 'full' | 'proxy' | 'auto'` in the store.

**Differs from FCP7:** FCP7 did not have built-in proxy generation — it relied on external tools or "offline" editing workflows. CUT generates proxies automatically via FFmpeg without user intervention.

---

### 2.6 Supported Codecs

**Status:** IMPLEMENTED (detection and classification)

The codec probe system (`cut_codec_probe.py`) classifies every imported file into a codec family and playback class.

**Codec families:**

| Family | Examples | Playback class |
|---|---|---|
| `camera_raw` | R3D, BRAW, CinemaDNG, ARRIRAW, DPX, EXR | `transcode_required` |
| `production` | ProRes, DNxHD/HR, CineForm, FFV1, HuffYUV, JPEG2000 | `proxy_recommended` |
| `delivery` | H.264, H.265/HEVC, MPEG-4, MPEG-2, Motion JPEG | `native` or `proxy_recommended` |
| `web` | VP8, VP9, AV1, WebP | `native` |
| `audio_only` | AAC, MP3, WAV, FLAC, ALAC, DTS, AC3, Opus | `native` |

**Playback classes:**
- `native` — browser/WebView can decode directly
- `proxy_recommended` — can play but generates proxy for smoother scrubbing
- `transcode_required` — cannot play natively; requires proxy transcode before editing
- `unsupported` — no known decode path

**Camera log detection** (`detect_log_profile()`) recognizes: Sony S-Log3, Panasonic V-Log, ARRI LogC3, Canon Log 3, RED Log3G10, DJI D-Log, Nikon N-Log, Fujifilm F-Log, Blackmagic Film, HLG, PQ/HDR10.

**Container support:**
- Native containers (direct playback): `mp4`, `m4v`, `webm`, `ogg`, `mov`
- Proxy containers (proxy recommended): `mxf`, `avi`, `mkv`, `mts`, `m2ts`, `ts`, `gxf`, `flv`, `wmv`
- Transcode containers: `r3d`, `braw`, `ari`, `dpx`, `exr`

**Differs from FCP7:** FCP7 was limited to QuickTime-compatible codecs. CUT's probe-based system handles any container/codec detectable by ffprobe, including camera-native formats.

---

### 2.7 Sequence Settings

**Status:** IMPLEMENTED

Sequence settings are configured via a modal dialog (`SequenceSettingsDialog.tsx`) and persisted through the store to `POST /api/cut/sequence-settings`.

**Available settings:**

**Resolution:**
- `4K` — 3840 x 2160
- `1080p` — 1920 x 1080
- `720p` — 1280 x 720
- `custom` — user-specified width and height

**Frame rate options:** 23.976, 24, 25, 29.97, 30, 48, 50, 59.94, 60 fps

**Color space:**
- `Rec.709` (standard HD)
- `Rec.2020` (HDR/wide gamut)
- `DCI-P3` (cinema)

**Audio settings:**
- Sample rate: 44100, 48000, or 96000 Hz
- Bit depth: 16, 24, or 32 bit

**Additional settings (in store, not yet in dialog UI):**
- `timecodeFormat`: `smpte` (HH:MM:SS:FF) or `milliseconds`
- `dropFrame`: boolean — only relevant for 29.97 and 59.94 fps
- `startTimecode`: initial sequence timecode (e.g. `01:00:00:00`)
- `proxyMode`: `full` | `proxy` | `auto`

**How to open:** Sequence menu > Sequence Settings (no default hotkey bound).

**Differs from FCP7:** FCP7 sequence settings were set at sequence creation time via a dialog that required choosing a preset. CUT allows changing settings at any time; the setting change is non-destructive and does not re-render existing clips.

---

### 2.8 Multi-Timeline (Tabs)

**Status:** IMPLEMENTED

CUT supports multiple named timelines within a single project. Each timeline is a separate `TimelineLane[]` array with its own markers, playhead, zoom, and scroll state.

**Timeline tabs** are displayed in the `timelines` panel (the multi-timeline manager). Each tab has:
- `id` — unique identifier
- `label` — display name (e.g. `project_cut-01`)
- `version` — auto-increment integer
- `mode` — `favorites` | `script` | `music` | `manual` (set by auto-montage)
- `parentId` — which timeline it was forked from

**Operations:**
- Create new timeline: `Timeline > New Timeline` (store action `createTimelineTab`)
- Switch: click tab in the Timelines panel
- Delete: store action `removeTimelineTab` (backend endpoint `DELETE /api/cut/timeline/{timeline_id}`)
- Each timeline snapshot (lanes, markers, playhead, zoom, scroll) is cached in `timelineSnapshots` Map in the store.

**Parallel timeline view:** Two timelines can be displayed side-by-side using `parallelTimelineTabIndex` — this enables A/B comparison of edit versions.

**Differs from FCP7:** FCP7 did not support multiple timelines in one project window. CUT's multi-timeline system supports up to N named timelines, each independently editable and dockable as separate `TimelinePanel` instances.

---

*Source files verified: `client/src/hooks/useCutHotkeys.ts`, `client/src/components/cut/presetBuilders.ts`, `client/src/components/cut/DockviewLayout.tsx`, `client/src/components/cut/ProjectPanel.tsx`, `client/src/store/useCutEditorStore.ts`, `client/src/hooks/useCutAutosave.ts`, `client/src/components/cut/SequenceSettingsDialog.tsx`, `src/api/routes/cut_routes.py`, `src/api/routes/cut_routes_media.py`, `src/services/cut_codec_probe.py`, `src/services/cut_proxy_worker.py`, `client/package.json`, `requirements.txt`*

---

## Section 3: Editing

_FCP7 Reference: Ch.13-15, 28_

---

`[screenshot: Source Monitor with IN/OUT marks + Timeline with sequence marks — three-point editing in action]`

### 3.1 Three-Point Editing System
**Status:** IMPLEMENTED
**Hotkey:** `,` Insert / `.` Overwrite (both presets)

The three-point editing system is the primary method for moving source content onto the timeline. The store maintains four independent mark points: `sourceMarkIn`, `sourceMarkOut` (marks on raw media in the Source Monitor) and `sequenceMarkIn`, `sequenceMarkOut` (marks on the timeline in the Program Monitor). The `resolveThreePointEdit` function in `useThreePointEdit.ts` calculates the fourth point automatically using FCP7 precedence rules:

- Sequence IN/OUT take priority for duration when both are set.
- Missing sequence IN falls back to playhead position.
- Missing source IN defaults to 0.
- If no marks at all are set, the entire source clip is used.

If the Source Monitor has no media loaded, the system falls back to the clip under the playhead as the source. All edits go through `applyTimelineOps` → `POST /cut/timeline/apply` → backend undo stack. After a successful edit, the playhead advances to the end of the inserted clip and sequence marks are cleared (matching FCP7 behaviour).

**Differs from FCP7:** Backtrack mode (only sequence OUT is set → calculate sequence IN from source duration) is implemented. Superimpose (F12) is also registered as a separate action that routes to track V2.

---

### 3.2 Insert Edit
**Status:** IMPLEMENTED
**Hotkey:** `,` (FCP7 and Premiere)

Performs a ripple insert at the sequence IN point (or playhead if no sequence IN is set). All clips at or after the insert point are shifted right by the clip duration. Uses a local-first strategy: the store's lane data is updated immediately for instant visual feedback, then `applyTimelineOps` posts the `insert_at` op to the backend with `{ skipRefresh: true }`.

---

### 3.3 Overwrite Edit
**Status:** IMPLEMENTED
**Hotkey:** `.` (FCP7 and Premiere)

Places source content at the sequence IN point (or playhead) without shifting existing clips. Existing content is replaced in-place. Same local-first strategy as Insert.

---

### 3.4 Replace Edit
**Status:** IMPLEMENTED
**Hotkey:** `F11` (both presets)

Replaces the clip under the playhead with source content from the Source Monitor, preserving the original clip's duration on the timeline. Uses `op: 'replace_media'` with `source_in` from `sourceMarkIn`. Routes through `applyTimelineOps` for undo support.

---

### 3.5 Fit to Fill
**Status:** IMPLEMENTED
**Hotkey:** `Shift+F11` (both presets)

Requires both source IN/OUT and sequence IN/OUT to be set. Calculates `speed = sourceDuration / sequenceDuration` and places the clip with that speed ratio so that a longer or shorter source segment fills exactly the marked sequence range.

**Differs from FCP7:** The speed ratio is stored on the clip as a numeric field (not rendered in real-time preview — the video element plays at native speed; speed is only applied at export).

---

### 3.6 Split / Razor at Playhead
**Status:** IMPLEMENTED
**Hotkey:** `Cmd+K` (both presets) / `B` key activates Razor tool

Two distinct mechanisms:
1. `Cmd+K` (splitClip action): Immediately splits clips at the current playhead position across all targeted lanes using a local-first approach — the store splits the clip into two records instantly, then posts `op: 'split_at'` to the backend with `{ skipRefresh: true }`.
2. `B` key: Activates the Razor tool. While Razor is active, clicking a clip performs the same split at the click position. The cursor changes to `crosshair`.

---

### 3.7 Ripple Delete
**Status:** IMPLEMENTED
**Hotkey:** `Shift+Delete` (both presets)

Removes selected clips and closes the resulting gap by shifting all subsequent clips left. Uses `op: 'ripple_delete'` via `applyTimelineOps`.

**Differs from FCP7:** In FCP7, ripple delete only applies to targeted tracks. In VETKA CUT, it operates on all selected clips regardless of track targeting.

---

### 3.8 Lift and Extract
**Status:** IMPLEMENTED
**Hotkey:** `;` Lift / `'` Extract (both presets)

**Lift** (`liftClip`): Removes selected clips, leaving a gap. If sequence IN/OUT marks are set, removes all clips within that range; partial overlaps are trimmed to the mark boundary.

**Extract** (`extractClip`): Removes selected clips and closes the gap (ripple). If IN/OUT marks are set, ripple-deletes all clips fully within the marked range.

---

### 3.9 Copy / Paste / Duplicate
**Status:** IMPLEMENTED
**Hotkey:** `Cmd+C` Copy / `Cmd+X` Cut / `Cmd+V` Paste / `Cmd+Shift+V` Paste Insert

The store maintains a `clipboard: TimelineClip[]` array. `pasteClips('overwrite')` places clips at the playhead; `pasteClips('insert')` uses `insert_at` ops. `pasteAttributes()` copies effects from the first clipboard clip to all selected clips via `op: 'set_effects'`.

**Differs from FCP7:** Duplicate (Cmd+D) is not a separate action — use Copy + Paste. Clipboard is in-memory only.

---

### 3.10 Undo / Redo System
**Status:** IMPLEMENTED
**Hotkey:** `Cmd+Z` Undo / `Cmd+Shift+Z` Redo (both presets)

All timeline mutations route through `applyTimelineOps` → `POST /cut/timeline/apply`. Undo calls `POST /cut/undo` and Redo calls `POST /cut/redo`, both followed by `refreshProjectState()`. The undo stack is per-project and per-timeline-id.

**Differs from FCP7:** Undo history is backend-managed rather than in-memory. History survives page reload but requires a network round-trip per undo step.

---

### 3.11 Selection
**Status:** IMPLEMENTED
**Hotkey:** `Cmd+A` Select All / `Escape` Deselect

Single click sets `selectedClipId`. `Cmd+Click` toggles multi-select via `toggleClipSelection(id)`. `Escape` clears selection, resets tool, and stops shuttle.

**Linked Selection** (`Shift+L` FCP7 / `Cmd+L` Premiere): When `linkedSelection` is true (default), clicking a video clip automatically selects the corresponding audio clip in synced lanes.

---

### 3.12 Match Frame
**Status:** IMPLEMENTED
**Hotkey:** `F` Match Frame / `Shift+F` Reverse Match Frame (both presets)

Match Frame (`F`): finds the clip under the playhead, calculates `sourceTime = (currentTime - clip.start_sec) + clip.source_in`, sets the Source Monitor to that frame and focuses the Source panel. Implemented in `useCutEditorStore.matchFrame()`.

Reverse Match Frame (`Shift+F`): from Source Monitor position + active source path, finds the matching clip on timeline and seeks the program monitor to `clip.start_sec + (sourceTime - clip.source_in)`. Implemented in `useCutEditorStore.reverseMatchFrame()`.

---

### 3.13 Subclip Creation
**Status:** IMPLEMENTED
**Hotkey:** `Cmd+U` (both presets)

Creates a virtual subclip from `sourceMarkIn`/`sourceMarkOut`. Dispatches a `pipeline-activity` event for ProjectPanel to display. The hotkey handler is fully functional and MenuBar item "Make Subclip" is enabled.

**Differs from FCP7:** Subclips are not persisted to disk — in-memory only for the current session.

---

### 3.14 Mark In / Out
**Status:** IMPLEMENTED
**Hotkey:** `I` Mark In / `O` Mark Out / `Alt+I` Clear In / `Alt+O` Clear Out

Separate mark sets: `sourceMarkIn`/`sourceMarkOut` (Source panel focused) and `sequenceMarkIn`/`sequenceMarkOut` (Program/Timeline focused). `goToIn` (`Shift+I`) and `goToOut` (`Shift+O`) seek to marks. `clearInOut` (`Alt+X` FCP7 / `Cmd+Shift+X` Premiere) clears both marks. `markClip` (`X`) sets IN/OUT to span the clip under the playhead.

---

## Section 4: Trimming Tools

_FCP7 Reference: Ch.44, 56-60_

---

`[screenshot: ToolsPalette — all 8 trim tools with active tool highlighted]`

### 4.1 Selection Tool (Arrow)
**Status:** IMPLEMENTED
**Hotkey:** `A` (FCP7) / `V` (Premiere)

Default tool. Click = select + move drag. Hovering the left/right 7px edge (`TRIM_HANDLE_WIDTH = 7`) activates trim mode with `ew-resize` cursor. Snappable to clip edges, playhead, marks, markers, and ruler ticks.

---

### 4.2 Razor Tool (Blade)
**Status:** IMPLEMENTED
**Hotkey:** `B` (FCP7) / `C` (Premiere)

Click on a clip = local-first split at click position. Cursor: `crosshair` on lane and clip.

---

### 4.3 Ripple Edit Tool
**Status:** IMPLEMENTED
**Hotkey:** `R` (FCP7) / `B` (Premiere)

Click position relative to clip centre determines left vs right ripple. Drag adjusts clip start/end while shifting subsequent clips. Minimum clip duration: `MIN_CLIP_DURATION_SEC = 0.15`. Cursor: `w-resize`.

---

### 4.4 Roll Edit Tool
**Status:** IMPLEMENTED
**Hotkey:** `Shift+R` (FCP7) / `N` (Premiere)

Moves edit point between two adjacent clips without changing total duration. Both clips resize simultaneously, clamped to min duration. Cursor: `col-resize`.

---

### 4.5 Slip Tool
**Status:** IMPLEMENTED
**Hotkey:** `Y` (both presets)

Moves source content inside clip boundaries without changing position or duration on timeline. Only `source_in` changes. Cursor: `ew-resize`.

**Differs from FCP7:** No two-up display in monitors during slip.

**Known issue:** ToolsPalette displays `S` as the badge for Slip, but actual hotkey is `Y` in both presets. Badge is cosmetically incorrect.

---

### 4.6 Slide Tool
**Status:** IMPLEMENTED
**Hotkey:** `U` (both presets)

Moves clip between neighbours, trimming neighbours symmetrically to keep total duration unchanged. Cursor: `col-resize` on body, `ew-resize` on edges.

---

### 4.7 Trim Cursors Per Tool
**Status:** IMPLEMENTED

| Tool | Lane bg | Clip body | Clip edge |
|---|---|---|---|
| selection | `default` | `grab` | `ew-resize` |
| razor | `crosshair` | `crosshair` | `crosshair` |
| ripple | `w-resize` | `w-resize` | `w-resize` |
| roll | `col-resize` | `col-resize` | `col-resize` |
| slip | `ew-resize` | `ew-resize` | `ew-resize` |
| slide | `col-resize` | `col-resize` | `ew-resize` |
| hand | `grab` | `grab` | `ew-resize` |
| zoom | `zoom-in` | `zoom-in` | `ew-resize` |

---

### 4.8 Snap During Trim
**Status:** IMPLEMENTED
**Hotkey:** `N` (FCP7) / `S` (Premiere)

`SNAP_THRESHOLD_PX = 5`. Snap candidates: clip edges, playhead, marks, markers (including BPM beat markers). Yellow indicator line at snap point. Hold `Alt` to temporarily bypass.

---

## Section 5: Timeline

_FCP7 Reference: Ch.32, 41_

---

`[screenshot: Timeline with multiple lanes — V1, A1, V2, AUX — clips, playhead, ruler, lane headers]`

### 5.1 Timeline Structure
**Status:** IMPLEMENTED

Flat array of `TimelineLane` objects. Lane types: `video_main`, `audio_sync`, `take_alt_y`, `take_alt_z`, `aux`. Each lane contains `TimelineClip` objects with `start_sec`, `duration_sec`, `source_path`, `source_in`, `speed`, `transition_out`, `effects`, `keyframes`. Gaps are implicit (unoccupied time ranges).

Lane headers (100px): label, lock, mute, solo, target, visibility icons.

**Differs from FCP7:** Lane types follow multicam-oriented scheme (`V1/A1/V2/V3/AUX`) rather than arbitrary `V1..Vn / A1..An`.

---

### 5.2 Multi-Timeline Support
**Status:** IMPLEMENTED

Two complementary systems:
1. **Timeline Tabs** — lightweight tab array with `id`, `label`, `version`, `mode` (`manual/favorites/script/music`).
2. **Timeline Instance Store** — richer `Map<string, TimelineInstance>` with per-instance `lanes`, `zoom`, `scrollX/Y`, `playheadPosition`, `markIn/Out`, `selectedClipIds`, `mutedLanes`, etc.

New timelines via `File > New Sequence` (Cmd+N). Each can be docked as its own panel. Side-by-side via `parallelTimelineTabIndex`.

**Differs from FCP7:** FCP7 opens sequences as separate tabs. CUT renders each as a dockable panel, enabling true side-by-side layout.

---

### 5.3 Track Targeting (Source Patching)
**Status:** IMPLEMENTED

`targetedLanes: Set<string>` — click Target button in lane header. `getInsertTargets()` resolves which lanes receive insert/overwrite edits.

**Differs from FCP7:** FCP7 uses drag-to-patch wiring. CUT uses click-to-toggle buttons.

---

### 5.4 Track Locking
**Status:** IMPLEMENTED

`lockedLanes: Set<string>` — click Lock icon. Locked lanes cannot be moved/trimmed.

---

### 5.5 Track Height Resize
**Status:** IMPLEMENTED
**Hotkey:** `Shift+T` (both presets)

Three preset sizes: Small (28px), Medium (56px), Large (112px) — cycled via `cycleTrackHeight()`. Per-lane drag resize via `TrackResizeHandle.tsx`.

---

### 5.6 Adding/Removing Tracks
**Status:** PARTIAL

`Insert Tracks...` and `Delete Tracks...` exist in Sequence menu but are `disabled: true`. Track structure determined by backend on project bootstrap.

---

### 5.7 Snapping
**Status:** IMPLEMENTED
**Hotkey:** `N` (FCP7) / `S` (Premiere)

`snapEnabled: boolean`. Yellow bar visual cue. Available in Sequence and View menus.

---

### 5.8 Playhead and Timecode
**Status:** IMPLEMENTED

Playhead: 1px vertical line, white when focused, grey when inactive. `TimecodeField.tsx`: SMPTE HH:MM:SS:FF, drop-frame (`;`) vs non-drop (`:`), relative entry (`+10`), partial entry (`1419` → `00:00:14:19`). Editable for direct seek.

---

### 5.9 Zoom Controls
**Status:** IMPLEMENTED
**Hotkey:** `Cmd+=`/`Cmd+-` (FCP7) / `=`/`-` (Premiere) / `Shift+Z` Zoom to Fit

`zoom: number` (px/sec). Range 10–300 px/s, default 80. Zoom-to-fit: `max(10, min(300, 800/duration))`. Each timeline instance maintains independent zoom.

---

### 5.10 Timeline Ruler
**Status:** IMPLEMENTED

`TimelineRuler.tsx` — zoom-adaptive ticks:

| Zoom (px/s) | Major | Secondary | Tertiary |
|---|---|---|---|
| < 10 | 30s | 10s | — |
| 10–20 | 10s | 5s | — |
| 20–40 | 10s | 5s | 1s |
| 40–80 | 10s | 5s | 1s (labeled) |
| 80–200 | 10s | 1s | 0.5s |
| > 200 | 1s | 0.5s | per-frame |

At zoom > 200, switches to full SMPTE `HH:MM:SS:FF`. Click = seek, drag = scrub.

---

### 5.11 Close Gap
**Status:** IMPLEMENTED
**Hotkey:** `Alt+Backspace` (both presets)

Finds gaps in targeted lanes and ripple-deletes them.

---

### 5.12 Sequence Menu
**Status:** IMPLEMENTED (partial items disabled)

| Item | Shortcut | Status |
|---|---|---|
| Render In to Out | Opt+R | DISABLED |
| Add Edit (split) | Cmd+K | IMPLEMENTED |
| Add Edit All Tracks | Cmd+Shift+K | IMPLEMENTED |
| Lift | ; | IMPLEMENTED |
| Extract | ' | IMPLEMENTED |
| Ripple Delete | Opt+Del | IMPLEMENTED |
| Close Gap | — | IMPLEMENTED |
| Extend Edit | E | IMPLEMENTED |
| Trim Edit | T | DISABLED |
| Add Video Transition | Cmd+T | IMPLEMENTED |
| Add Audio Transition | Cmd+Shift+T | IMPLEMENTED |
| Snap in Timeline | S | IMPLEMENTED |
| Insert Tracks... | — | DISABLED |
| Delete Tracks... | — | DISABLED |
| Nest Item(s) | — | DISABLED |
| Solo Selected | — | IMPLEMENTED |
| Scene Detection | Cmd+D | IMPLEMENTED |

---

### 5.13 Drop Frame / Non-Drop Frame
**Status:** IMPLEMENTED

`dropFrame: boolean` in store. Toggled via Project Settings dialog (`Cmd+;`). Only shown for 29.97 / 59.94 fps. Separator: `;` for drop-frame, `:` for non-drop.

---

### 5.14 Auto-Select Per Track
**Status:** [PLANNED — no wave assigned]

FCP7's per-track auto-select checkboxes for Lift/Extract are not implemented. `targetedLanes` partially fills this role for insert/overwrite only.

---

### 5.15 Nest Sequence
**Status:** [PLANNED — no wave assigned]

`Sequence > Nest Item(s)` is in MenuBar but `disabled: true`. No implementation.

---

### 5.16 BPM Markers on Timeline
**Status:** IMPLEMENTED

`MarkerKind` includes `bpm_audio`, `bpm_visual`, `bpm_script`. Generated by PULSE pipeline. Rendered as colored 2px vertical lines. Toggle per kind via `View > Overlays > Marker Overlay`.

**Differs from FCP7:** FCP7 has no BPM markers. This is a VETKA CUT exclusive.

---

## Section 6: Audio

_FCP7 Reference: Ch.61-65_

---

`[screenshot: Audio Mixer panel — channel strips with faders, pan knobs, VU meters, master bus]`

### 6.1 Audio Mixer Panel
**Status:** IMPLEMENTED

`AudioMixer.tsx` — per-lane channel strips: VU indicator, clipping detector, volume fader (0–150%), pan knob (-100L to +100R), mute/solo buttons. Master bus strip. VU fed from WebSocket `audio_scope_data` events.

**Differs from FCP7:** Simpler per-lane model with single master bus. No sends or sub-mixes.

---

### 6.2 Per-Track Volume, Pan, Mute, Solo
**Status:** IMPLEMENTED

- `laneVolumes: Record<string, number>` — 0.0 to 1.5 (0%–150%)
- `lanePans: Record<string, number>` — -1.0 (L) to +1.0 (R)
- `mutedLanes: Set<string>`, `soloLanes: Set<string>`

Solo logic follows FCP7 Ch.100: mute overrides solo. Enforced in frontend playback and `cut_audio_engine.py`.

---

### 6.3 Audio Rubber Band (Volume Automation)
**Status:** IMPLEMENTED

`AudioRubberBand.tsx` — SVG overlay on clips: volume line, keyframe dots, interpolated path. Option+click = add keyframe. Drag dot = move keyframe. Toggle via `showRubberBand`. Max volume 1.5.

**Differs from FCP7:** Monochrome (#999 grey) per UI policy. FCP7 uses pink/yellow.

---

### 6.4 Audio Playback
**Status:** IMPLEMENTED

`useAudioPlayback.ts` — Web Audio API. Per-clip: `AudioBufferSourceNode → GainNode → StereoPannerNode → destination`. Chunked fetch for clips > 30s. LRU buffer cache (50 entries / 50 MB). Multiple clips play simultaneously.

---

### 6.5 Audio Waveform Display
**Status:** IMPLEMENTED

Pre-computed by backend. Stereo: `StereoWaveformCanvas` (L above, R below). Mono: `WaveformCanvas`. Rendered on HTML Canvas, scaled to clip pixel dimensions.

---

### 6.6 Audio Scrubbing
**Status:** [PLANNED — no wave assigned]

No audio during manual playhead drag. Visual waveform hover tracks position but produces no sound.

**Differs from FCP7:** FCP7 plays audio at scrub speed during shuttle/drag. CUT is silent during scrub.

---

### 6.7 Audio Crossfade
**Status:** IMPLEMENTED
**Hotkey:** `Cmd+Shift+T` (both presets)

`addDefaultTransition()` store action — finds nearest edit point on audio lanes only (`lane_type.startsWith('audio')`), applies `cross_dissolve` transition. Render pipeline converts to FFmpeg `acrossfade` for audio streams. Menu item "Add Audio Transition" wired to `addDefaultTransition()`. `Cmd+T` remains "Add Video Transition" (`addDefaultTransition()` all lanes).

**Differs from FCP7:** Same Cmd+T / Cmd+Shift+T split as FCP7 (video vs audio transition).

---

### 6.8 VO Recording
**Status:** [PLANNED W9]

No voice-over recording, microphone input, or record-to-timeline feature.

---

### 6.9 Audio Scope / VU Meters
**Status:** IMPLEMENTED

`WaveformMinimap.tsx` — real-time stereo scope via WebSocket. `AudioMixer` subscribes to same socket for VU indicators. Data: `rms_left/right`, `peak_left/right`, `waveform_left/right[]`.

---

### 6.10 Audio Analysis (BPM, Key Detection)
**Status:** IMPLEMENTED

`cut_audio_analyzer.py`: BPM (spectral flux + autocorrelation), musical key (Krumhansl-Kessler profiles), Camelot key, energy contour (64 bins), onset times.

**API:** `POST /api/cut/pulse/analyze-clip` — `{source_path}` → `{bpm, key, camelot_key, energy_contour[], onset_times[], duration_sec}`. Backed by librosa if available, else FFmpeg + scipy/numpy fallback.

**UI:** "Audio Analysis" section in `ClipInspector.tsx` — on-demand per-clip (Analyze button). Displays BPM / Key / Camelot / onset count + SVG energy sparkline (64 bins). Resets when different clip is selected.

**Differs from FCP7:** FCP7 has no BPM/key detection. VETKA CUT exclusive via PULSE system.

---

### 6.11 Loop Playback
**Status:** [PLANNED — no wave assigned]

No `loopPlay` or `isLooping` state. No loop toggle in transport or playback hook.

**Differs from FCP7:** FCP7 has Loop Playback (Ctrl+L). CUT does not implement this yet.

---

## Section 7: Effects & Color Correction

_FCP7 Reference: Ch.67-72_

---

### 7.1 Effects Panel
**Status:** IMPLEMENTED

`EffectsPanel.tsx` — two modes:
- **No selection:** Searchable effects browser. 4 categories: Video Filters (10 effects), Audio Filters (8 effects), Transitions, Generators (5 types). Drag or double-click to apply.
- **Clip selected:** Effect Controls sliders — Color (brightness/contrast/saturation/gamma), Blur/Sharpen, Transform (vignette/crop/flip), Time (fade), Opacity.

All 17 ClipEffects fields persist to render pipeline via `set_effects` op → `clip_effects_dict_to_effect_params()` → `compile_video_filters()` → FFmpeg. Extended effects (gamma, sharpen, denoise, vignette, fade_in/out, hflip/vflip, crop) are fully rendered. Fractional crop (crop_top/bottom/left/right) compiles to `crop=iw*w:ih*h:iw*x:ih*y` FFmpeg expression.

**Differs from FCP7:** FCP7 has separate Effect Controls window. CUT merges browser + controls into one panel.

---

### 7.2 Transitions Panel
**Status:** IMPLEMENTED
**Hotkey:** `Cmd+T` (both presets)

10 transition types: Cross Dissolve, Dissolve, Dip to Black/White, Wipe L/R/U/D, Slide L/R. Duration presets: 0.25–5.0s. Render via FFmpeg `xfade` (video) + `acrossfade` (audio). Equal-power curve (`qsin`) for audio.

**Differs from FCP7:** FCP7 uses drag-to-edit-point. CUT uses Apply button per clip.

---

### 7.3 Motion Controls
**Status:** IMPLEMENTED

`MotionControls.tsx`: Position X/Y, Scale 1–400% (uniform/independent), Rotation -360°–360°, Anchor 9-point grid, Opacity 0–100% with keyframe button, Crop L/R/T/B. Render via FFmpeg: crop → scale → rotate → position → opacity.

**Differs from FCP7:** Sliders only. No on-canvas drag handles.

---

### 7.4 Speed Control / Time Remapping
**Status:** IMPLEMENTED
**Hotkey:** `Cmd+J` (FCP7)

`SpeedControl.tsx`: Presets 0.25x–4x, custom 10–400%, reverse checkbox, maintain pitch (FFmpeg `atempo`), Fit to Fill. Frame blending: `minterpolate` for smooth slow-motion.

**Differs from FCP7:** Constant-rate dialog, no variable-speed rubber-band curve editor.

---

`[screenshot: Color Correction panel — 3-way wheels (Shadows/Midtones/Highlights) + basic controls]`

### 7.5 Color Correction Panel
**Status:** IMPLEMENTED

`ColorCorrectionPanel.tsx`: Exposure (-4 to +4 stops), White Balance (2000–12000K), Contrast/Saturation (0–3), Hue (-180°–180°). Three-way corrector: `ColorWheel.tsx` (Shadows/Midtones/Highlights) with R/B correction, G derived. 9 curve presets + interactive spline editor (`CurveEditor.tsx`). Graded preview thumbnail via `POST /cut/preview/frame`.

Color correction persisted to backend via `set_prop(key='color_correction')` — reaches render pipeline.

#### 7.5.1 Secondary Color Correction (FCP7 Ch.28)
**Status:** IMPLEMENTED

HSL qualifier + masked secondary correction. Enable via "Secondary" section toggle in `ColorCorrectionPanel.tsx`.

**Qualifier controls:**
- Hue center (0°–360°) + Hue width (±degrees) — circular hue range
- Sat Min / Sat Max (0–1)
- Luma Min / Luma Max (0–1)
- Softness (0–1) — feathered edges around selection

**Correction controls:** Hue Shift (−180°–+180°), Saturation multiplier (0–3), Exposure (stops)

**Implementation:** Backend `cut_color_pipeline.py` — `rgb_to_hsl()` + `hsl_to_rgb()` + `build_hsl_mask()` + `apply_secondary_correction()`. Render path: `write_secondary_lut_cube()` generates a 17³ .cube LUT, applied via FFmpeg `lut3d=` filter. Preview path: `secondary_color` EffectParam sent to `POST /cut/preview/frame`. Timeline persistence: stored in `clip.color_correction.secondary` via `set_prop`.

**Differs from FCP7:** No eyedropper picker. No matte view (visualize mask overlay).

---

### 7.6 LUT Browser
**Status:** IMPLEMENTED

`LutBrowserPanel.tsx`: List `.cube` files, preview before/after, apply to clip, import from filesystem, delete. Render: `lut3d='path.cube'` after log decode. Log profiles: V-Log, S-Log3, LogC3, Canon Log 3, HLG, PQ HDR10.

---

`[screenshot: Video Scopes — waveform + vectorscope + histogram + parade tabs]`

### 7.7 Video Scopes
**Status:** IMPLEMENTED

`VideoScopes.tsx` — 4 modes:
- **Waveform:** Y=luma (0–100 IRE), green phosphor
- **Parade:** R/G/B side-by-side
- **Vectorscope:** CbCr plot with skin tone line at 123°
- **Histogram:** stacked R/G/B (0–255 bins)

SocketIO real-time (`scope_request` → `scope_data`). Fast mode during playback (histogram-only, 128px, ~2ms). Broadcast Safe indicator: SAFE/WARN/ILLEGAL. Pre/Post grade toggle.

---

### 7.8 Keyframe System
**Status:** IMPLEMENTED

`Keyframe` type: `{time_sec, value, easing}`. Easing: `linear`, `ease_in`, `ease_out`, `bezier`. Store: `addKeyframe()`, `recordPropertyChange()` (auto-keyframe in record mode), `getKeyframeTimes()`. Render: FFmpeg `sendcmd` file for per-frame parameter changes.

**Differs from FCP7:** No visual keyframe editor in timeline. Keyframes via "KF" button in MotionControls (opacity only in UI) or record mode.

---

### 7.9 Effects Node Graph
**Status:** [PLANNED W10]

No node-based compositor. Pipeline is flat ordered `list[EffectParam]` → linear FFmpeg filter chain.

---

## Section 8: Export & Delivery

_FCP7 Reference: Ch.73-78_

---

`[screenshot: Export Dialog — Master tab with codec/resolution/quality settings]`

### 8.1 Export Dialog
**Status:** IMPLEMENTED
**Hotkey:** `Cmd+E` (FCP7) / `Cmd+M` (Premiere)

`ExportDialog.tsx` — three tabs:

**Master** — Full render: codec (H.264/H.265/ProRes family/DNxHR), resolution (Source/4K/1080p/720p), rate control (CRF/CBR/VBR), audio codec (AAC/PCM 24-bit/MP3/FLAC), Selection Only, Audio Stems, Loudness normalization.

**Editorial** — Interchange: Premiere Pro XML (XMEML v5), FCPXML, EDL (CMX 3600), OpenTimelineIO.

**Publish** — Platform presets: YouTube, Instagram Reels, TikTok, Telegram.

---

### 8.2 Codec Support

| Key | Encoder | Container | Pixel Format |
|---|---|---|---|
| prores_proxy | prores_ks p=0 | .mov | yuv422p10le |
| prores_lt | prores_ks p=1 | .mov | yuv422p10le |
| prores_422 | prores_ks p=2 | .mov | yuv422p10le |
| prores_422hq | prores_ks p=3 | .mov | yuv422p10le |
| prores_4444 | prores_ks p=4 | .mov | yuva444p10le |
| prores_4444xq | prores_ks p=5 | .mov | yuva444p10le |
| dnxhr_lb/sq/hq/hqx/444 | dnxhd | .mxf | yuv422p–yuv444p10le |
| h264 / h264_10bit | libx264 | .mp4 | yuv420p(10le) |
| h265 / h265_10bit | libx265 | .mp4 | yuv420p(10le) |
| vp9 | libvpx-vp9 | .webm | yuv420p |
| av1 | libsvtav1 | .mp4 | yuv420p10le |
| ffv1 | ffv1 | .mkv | yuv422p10le |
| png/tiff/dpx/exr_seq | image sequences | — | — |

---

### 8.3 Publish Presets

| Preset | Codec | Resolution | FPS | Quality |
|---|---|---|---|---|
| youtube_1080 | h264 | 1080p | 30 | 85 |
| youtube_4k | h264 | 4K | 30 | 90 |
| instagram_reels | h264 | 1080p 9:16 | 30 | 80 |
| tiktok | h264 | 1080p 9:16 | 30 | 80 |
| telegram | h264 | 720p | 30 | 70 |
| vimeo | h264 | 1080p | 25 | 90 |

---

### 8.4 Render Progress
**Status:** IMPLEMENTED

SocketIO `render_progress` events: `job_id`, `progress` (0–1), `eta_sec`, `elapsed_sec`, `message`. FFmpeg `-progress pipe:1` parsing. HTTP polling fallback every 500ms/2s.

---

### 8.5 Render Cancel
**Status:** IMPLEMENTED

`POST /cut/job/{job_id}/cancel`. Backend raises `RenderCancelled` in FFmpeg subprocess.

---

### 8.6 Batch Export
**Status:** [PLANNED — no wave assigned]

No batch queue. Single-timeline render only.

---

### 8.7 Chapter Markers in Export
**Status:** [PLANNED — no wave assigned]

YouTube preset has `"extras": ["chapters_from_markers"]` metadata but no implementation reads chapter markers into output.

---

### 8.8 Render Pipeline Architecture
**Status:** IMPLEMENTED

Pipeline in `cut_render_engine.py`:
1. `build_render_plan()` — reads lanes → `RenderClip` list (effects, speed, motion, keyframes, color, transitions)
2. `build_ffmpeg_command()` — decides concat demuxer (simple) vs `filter_complex` (complex)
3. `FilterGraphBuilder.build()` — per-clip chains: trim → log decode → LUT → effects → motion → speed → reverse → frame blend → xfade/concat → scale/pad/fps
4. FFmpeg `-progress pipe:1` for real-time progress
5. SocketIO `render_progress` events
6. Audio stems: separate FFmpeg pass per lane → PCM 24-bit WAV 48kHz

---

## Section 9: Advanced — VETKA CUT Exclusive Features

---

`[screenshot: DAG Project Panel — scene graph with SceneChunkNodes spine and MediaAssetNodes]`

### 9.1 DAG Project Panel (Scene Graph)
**Status:** IMPLEMENTED

`DAGProjectPanel.tsx` renders the project as a directed acyclic graph using ReactFlow. Y-axis = film chronology (`Y = start_sec * 3 px/sec`).

**Node types** (`cut_scene_graph_taxonomy.py`): `scene`, `scene_chunk`, `take`, `asset`, `note`.
**Edge types:** `contains`, `follows`, `next_scene`, `semantic_match`, `alt_take`, `references`, `has_media`.

**SceneChunkNode** = script spine (vertical chain). **MediaAssetNode** = media linked to scenes (video/takes left, audio/music/sfx right).

**Y-axis flip toggle** — button in top-right: START at top (default) or START at bottom.

**Node interaction:** Click syncs `activeSceneId` across all panels. Right-click: Open in Source Monitor, Add to Timeline, Focus in Project Panel, Reveal in Finder.

**LoreNode** (characters/locations) — **[PLANNED W7]**

---

### 9.2 Multicam
**Status:** IMPLEMENTED

`MulticamViewer.tsx` — grid of camera angles (1 col for 1, 2x2 for 2-4, 3x3 for 5+). Active angle highlighted. Click-to-cut via `multicamSwitchAngle(i)`. Video preview in each cell via `/api/cut/thumbnail` endpoint (debounced 300ms fetch, cached thumbnails).

**Audio cross-correlation sync** — **[PLANNED — killer feature]** (PluralEyes replacement).

---

### 9.3 Screenplay / Logger
**Status:** IMPLEMENTED (plain text); [PLANNED W8] for .fountain and .fdx

`screenplay_timing.py`: Parses scene headings (`INT.`, `EXT.`, `СЦЕНА`, `#`-prefixed). Page timing: `max(lines/55, chars/1800) * 60 sec`. Output: `SceneChunk` objects with `chunk_id`, `scene_heading`, `start_sec`, `duration_sec`. These create the DAG spine via `POST /api/cut/project/apply-script`.

**.fountain parser** — **[PLANNED W8]** (task `tb_1774311929_1`)
**.fdx parser** — **[PLANNED W8]** (task `tb_1774436431_1`)

---

`[screenshot: PULSE markers on timeline — BPM audio/visual/script markers as colored vertical lines]`

### 9.4 PULSE System (Music-Driven Editing)
**Status:** IMPLEMENTED

Three-signal conductor fusing narrative, visual, and audio BPM into per-scene `PulseScore`.

**Audio Analyzer** (`cut_audio_analyzer.py`): BPM (spectral flux + autocorrelation, 60-200 range), musical key (Krumhansl-Kessler profiles), Camelot key, energy contour, onset times.

**Camelot Engine** (`pulse_camelot_engine.py`): 12 positions x 2 rings (A=minor, B=major). Harmonic distance calculation. Path planning for smoothest harmonic trajectory.

**PULSE Conductor** (`pulse_conductor.py`): Fuses NarrativeBPM (35%), VisualBPM (30%), AudioBPM (35%). Output per scene: `camelot_key`, `scale`, `pendulum_position`, `dramatic_function`, `energy_profile`, `alignment` (sync/counterpoint). "Nights of Cabiria pattern": minor scene + major music = counterpoint.

**Cinema Matrix** (`pulse_cinema_matrix.py`): Maps pendulum positions to genres, scales, Itten colors, music genres.

---

### 9.5 AI Integration
**Status:** [PLANNED W10]

- **Generation Control** (Runway, Kling) — not implemented
- **JEPA bridge** — interface designed (`vjepa2` source field) but not wired
- **Documentary mode** — not implemented
- **Multiverse UI** — not implemented

---

### 9.6 Scene Detection
**Status:** IMPLEMENTED
**Hotkey:** `Cmd+D` (both presets)

`cut_scene_detector.py`: Extracts frames at 1s intervals (64x48 RGB24). Chi-squared histogram distance, threshold 0.3 → `SceneBoundary` with `time_sec` and `diff_score`. Groups clips into `DetectedScene` objects. Store: `detectScenes` action.

---

### 9.7 Dockview Panel System
**Status:** IMPLEMENTED

22 registered panels. Full drag/drop/split/tab. Panel keyboard: Cmd+1-9 focus, Cmd+[/] cycle, backtick maximize, Tab toggle Source/Program. Layout persistence per preset in localStorage. Panel crash isolation via `PanelErrorBoundary`. Hotkey toast on every shortcut.

**Monochrome FCP7 theme** (`dockview-cut-theme.css`): Grey palette only. Tab bar 18px. Active tab: `border-bottom: 2px solid #888`. All dockview blue variables overridden. **Only exceptions:** playhead `#cc3333` (red, NLE standard) and colored markers.

---

### 9.8 Context Menus
**Status:** IMPLEMENTED

- **Clip context menu** (`ClipContextMenu.tsx`): Cut/Copy/Paste/Delete/Ripple Delete, Speed/Duration, Properties, Reveal in Project. Viewport-aware positioning.
- **Transition context menu**: Right-click cycles type; Shift+right-click cycles alignment.
- **Project panel**: Open in Source, Add to Timeline, Reveal in Finder.
- **DAG nodes**: Same as project panel + Focus in Project Panel.
- **Panel tabs**: Close/Close Others/Close All/Float/Maximize.

All menus: `#0b0b0b` bg, `#333` border, `#ccc` text, `#1a1a1a` hover.

---

### 9.9 Desktop App (Tauri)
**Status:** IMPLEMENTED

Tauri 2.x configuration:
- `productName: "VETKA"`, `identifier: "ai.vetka.app"`, `version: "0.1.0"`
- Bundle targets: `.app` + `.dmg` (macOS)
- Minimum macOS 10.15
- Two windows: main (VETKA, 1400x900) + mycelium (MYCELIUM, 960x680, initially hidden)
- CSP: `127.0.0.1:5001` + `localhost:5001`
- Deep-link scheme: `vetka://`
- Tauri-specific CSS: `pointer-events: auto !important` on sash elements for panel resize

---

## Appendix A: Feature Coverage Summary

### By Wave

| Wave | Scope | Coverage |
|---|---|---|
| W0-W6 | Core NLE (panels, editing, trim, docking, hotkeys, export, save) | ~90% |
| W7 | Data Model (LoreNode, taxonomy extension) | ~30% |
| W8 | Logger (.fountain/.fdx parsers, SourceAcquire) | ~40% |
| W9 | Audio (VO recording, crossfade UI, scrubbing) | ~50% |
| W10 | Future (documentary, multiverse, JEPA, effects graph) | 0% |

### FCP7 Feature Compliance (36 core features)

| Category | Implemented | Total | % |
|---|---|---|---|
| Editing | 9 | 9 | 100% |
| Playback | 3 | 4 | 75% |
| Timeline | 4 | 6 | 67% |
| Markers | 4 | 6 | 67% |
| Audio | 3 | 4 | 75% |
| Effects & Color | 4 | 4 | 100% |
| Export | 1 | 3 | 33% |
| **TOTAL** | **28** | **36** | **78%** |

### Missing Features (Priority)

| # | Feature | Wave | Complexity |
|---|---|---|---|
| 1 | Loop playback | — | Low |
| 2 | Marker edit dialog (name/color/duration) | — | Medium |
| 3 | Audio scrubbing | — | Medium |
| 4 | Auto-select per track | — | Medium |
| 5 | Nest sequence | — | High |
| 6 | Batch export | — | Medium |
| 7 | Chapter/scoring marker creation UI | — | Low |
| 8 | Chapter markers in export | — | Low |
| 9 | LoreNode implementation | W7 | High |
| 10 | .fdx parser | W8 | Medium |
| 11 | VO recording | W9 | High |
| 12 | Audio crossfade UI handles | W9 | Medium |
| 13 | useSelectionStore extraction (§4.1) | Arch | Medium |

---

*This manual was generated by 5 parallel Sonnet agents inspecting source code on 2026-03-25. Each section verified against actual TypeScript/Python files, not copied from prior docs. Task: `tb_1774437374_1`.*
