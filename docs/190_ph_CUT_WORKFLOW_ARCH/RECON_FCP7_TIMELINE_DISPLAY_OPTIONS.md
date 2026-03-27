# RECON: FCP7 Timeline Display Options
**Author:** Epsilon (QA-2) | **Date:** 2026-03-24
**Source:** FCP7 User Manual Ch.15 (Viewing & Navigating), Ch.18 (Timeline Display)
**Audience:** Beta (filmstrip implementation), Alpha (track header controls)

---

## 1. FCP7 Clip Display Modes

FCP7 provides 4 clip display modes in the timeline, controlled per-track or globally:

| Mode | Video Track Shows | Audio Track Shows |
|------|-------------------|-------------------|
| **Name** | Clip name as text label (default) | Clip name |
| **Name + Filmstrip** | Name + filmstrip thumbnail strip | Name + waveform |
| **Filmstrip Only** | Filmstrip thumbnails, no name | Waveform only |
| **Name + Waveform** | N/A (video tracks) | Name + audio waveform overlay |

### How to access (FCP7):
- **Per-track**: Right-click track header → "Track Display" submenu
- **Global**: Sequence menu → Settings → Timeline Options tab
- **Toggle**: Keyboard shortcut `Cmd+Option+W` cycles through modes

### Track height interaction:
- **Minimal height**: Name only (filmstrip collapses to 0px)
- **Small height** (28-40px): Name + 1 filmstrip row (one frame every ~2 seconds)
- **Medium height** (41-80px): Name + filmstrip fills available space
- **Tall height** (80px+): Multi-row filmstrip OR larger frames
- **Rule**: Track height directly controls filmstrip density — taller = more frames visible

---

## 2. Filmstrip Specification (FCP7)

### Thumbnail density:
- **Not fixed per-second** — density is **per-pixel-width**
- Each thumbnail = clip height × clip height (square, cropped to frame aspect)
- Count = `floor(clip_pixel_width / frame_width)`
- At typical zoom: ~1 frame every 1-3 seconds of timeline time
- At high zoom: up to 1 frame per timeline frame (24-60 thumbnails per second)

### Rendering behavior:
- Thumbnails render **on idle** — not during drag/resize/scroll
- During scroll: grey placeholder rectangles
- Progressive: first frame renders immediately, remaining fill in L-R
- Cache: decoded frames cached in memory, evicted on sequence close

### Frame selection:
- First frame of each "slot" — not nearest keyframe
- Source timecode determines frame position
- Retimed clips: thumbnails reflect speed-adjusted time

---

## 3. Premiere Pro Comparison

| Feature | FCP7 | Premiere Pro |
|---------|------|-------------|
| Display modes | 4 modes (Name/Filmstrip/Both/Waveform) | 2 toggles: "Show Video Thumbnails" + "Show Audio Waveforms" |
| Control location | Track header context menu | Sequence → Settings (global) OR wrench icon in track header |
| Per-track control | YES | YES (wrench icon per track) |
| Keyboard shortcut | Cmd+Option+W | None (menu only) |
| Filmstrip density | Proportional to track height | Fixed: first/last frame OR all frames |
| Filmstrip during scroll | Grey placeholders | Renders continuously (GPU-accelerated) |
| Waveform style | Filled waveform (green) | Filled waveform (varies by track color) |
| Audio waveform in video clips | Not shown | Can be shown below filmstrip |

### Premiere "Show Video Thumbnails" sub-options:
1. **Head Only** — only first frame of clip
2. **Head and Tail** — first + last frame
3. **Continuous** — filmstrip (matches FCP7's "Filmstrip Only")

---

## 4. CUT Current Implementation

Based on source analysis of TimelineTrackView.tsx and ThumbnailStrip.tsx:

| Feature | CUT Status | Notes |
|---------|-----------|-------|
| Clip name label | YES | Rendered in clip body |
| ThumbnailStrip component | YES | `ThumbnailStrip.tsx` exists |
| Waveform overlay | YES | `WaveformOverlay.tsx` + `WaveformCanvas.tsx` |
| Per-track display mode | NO | No track-level display toggle |
| Global display mode toggle | NO | No View menu option |
| Keyboard shortcut for display | NO | Not in useCutHotkeys.ts |
| Track height → filmstrip density | PARTIAL | Track resize exists but filmstrip density may not adapt |
| Filmstrip during scroll | UNKNOWN | Need browser test |
| Audio waveform in video tracks | NO | Waveform only on audio tracks |

### Backend support:
- `GET /cut/thumbnail` — single frame extraction (verified PASS this session)
- `GET /cut/waveform-peaks` — audio waveform bins (verified PASS this session)
- No batch thumbnail endpoint for filmstrip range

---

## 5. Recommendations for Beta/Alpha

### Minimum Viable (P1):
1. **ThumbnailStrip already renders** — verify it shows in default editing workspace
2. **WaveformOverlay already renders** — verify it shows on audio tracks
3. **Track height → density** — filmstrip frame count should scale with track height

### Professional (P2):
4. **Display mode toggle** — add to track header right-click menu (3 modes: Name / Name+Film / Film Only)
5. **Keyboard shortcut** — `Cmd+Option+W` to cycle display modes (add to FCP7_PRESET)
6. **Batch thumbnail endpoint** — `GET /cut/thumbnail-strip?source_path=...&start=0&end=10&count=20` for efficient filmstrip

### Polish (P3):
7. **Progressive rendering** — grey placeholders during scroll, fill on idle
8. **Premiere-style head/tail option** — simpler than full filmstrip, good for low-res previews
9. **Waveform color** — monochrome filled waveform (current: white/grey — correct per monochrome rule)

---

## 6. Contract Test Gaps

These features should have tests once implemented:
- `test_track_display_mode_state` — store tracks display mode per lane
- `test_filmstrip_density_scales_with_height` — more frames at taller height
- `test_display_mode_keyboard_shortcut` — Cmd+Option+W cycles modes
- `test_batch_thumbnail_endpoint` — returns array of JPEG frames
