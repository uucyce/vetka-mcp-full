# Recon: Video Filmstrip on Timeline Clips
**Date:** 2026-03-23
**Agent:** Beta (Media)
**Ref:** FCP7 Ch.15, Ch.18, Premiere Pro "Show Video Thumbnails"

---

## Current State

| Feature | Status | Details |
|---------|--------|---------|
| Audio waveforms on clips | WORKING | WaveformCanvas / StereoWaveformCanvas in TimelineTrackView |
| Video thumbnails on clips | NOT IMPLEMENTED | Only filename + colored block |
| ThumbnailStrip.tsx | EXISTS (184 lines) | Fetches N frames from GET /cut/thumbnail, blob cache, lazy load |
| GET /cut/thumbnail | WORKING | Single-frame JPEG via FFmpeg, disk cache |
| Store showWaveforms | EXISTS | Toggle for audio waveform display |
| Store showThumbnails | MISSING | Need new store field |
| Track height presets | EXISTS | S(28px), M(56px), L(112px) — Shift-T cycles |

## Architecture Decision: Sprite Sheet vs Individual Frames

### Option A: Individual Frames (current ThumbnailStrip.tsx approach)
- N separate `GET /cut/thumbnail` requests per clip
- Each frame cached independently on disk + in-memory blob URL
- **Pro:** Simple, works now, cache-friendly, incremental loading
- **Con:** N requests per clip × M visible clips = N*M HTTP requests on scroll

### Option B: Horizontal Sprite Sheet (Premiere Pro approach)
- One `GET /cut/thumbnail-strip?source_path=...&count=N` → single wide JPEG
- Backend: FFmpeg extract N frames → stitch horizontally → cache as one file
- Frontend: CSS `background-image` + `background-position` per frame slot
- **Pro:** 1 request per clip, efficient rendering, easy CSS scroll
- **Con:** Regenerate on zoom change, larger single transfer

### DECISION: **Hybrid** — Option A for initial load, upgrade to B for heavy timelines
- Phase 1: Wire existing ThumbnailStrip.tsx (individual frames) — works today
- Phase 2: Add sprite sheet endpoint for 20+ clip timelines — performance optimization

## FCP7 Display Modes (Ch.15, Ch.18)

FCP7 offers per-track display options via track header popup:

| Mode | Description | CUT Equivalent |
|------|-------------|----------------|
| Name | Text only, minimal height | S preset (28px) — current default look |
| Name + Thumbnail | Poster frame on left, name on right | Poster mode (frameCount=1) |
| Filmstrip | Full filmstrip across clip width | Strip mode (frameCount=auto) |
| Filmstrip + Name | Filmstrip with name overlay | Strip + text overlay |
| Audio Waveform | Waveform display | Already implemented |
| Audio + Name | Waveform with name | Already implemented |

**Settings location:** Track header right-click menu or View > Timeline Display Options.
**Scaling:** Taller track = more vertical space = taller filmstrip frames. FCP7 calculates
frame count from `clip_width_px / frame_aspect_width`.

## Frame Count Calculation

```
frameCount = floor(clipWidthPx / (frameHeightPx * aspectRatio))
```

For a 56px track height, 16:9 aspect:
- frameWidth = 56 * (16/9) ≈ 100px per frame
- 500px wide clip → 5 frames
- 200px wide clip → 2 frames
- 100px wide clip → 1 frame (poster)

For L preset (112px): frameWidth ≈ 200px → fewer but larger frames.

## Performance Budget

| Operation | Target | Method |
|-----------|--------|--------|
| Visible clip filmstrip render | <50ms | CSS background-image, no JS per frame |
| Thumbnail fetch (cached) | <5ms | Disk cache → HTTP 304 / blob URL |
| Thumbnail fetch (uncached) | <150ms | FFmpeg seek + extract + JPEG encode |
| Scroll/zoom filmstrip update | <16ms | Only re-render visible clips (intersection observer) |
| Memory per clip | <200KB | 5 frames × 40KB JPEG ≈ 200KB blob |

## Store Changes Needed

```typescript
// New fields in useCutEditorStore:
showThumbnails: boolean;           // default: true for video lanes
clipDisplayMode: 'name' | 'filmstrip' | 'waveform' | 'both';  // per-lane or global

// New actions:
toggleShowThumbnails: () => void;
setClipDisplayMode: (mode) => void;
```

## Roadmap

### Phase 1: Wire ThumbnailStrip to Timeline (Beta + Alpha coordination)
- Add `showThumbnails` to store (default true)
- Import ThumbnailStrip in TimelineTrackView
- Render inside video clip blocks when `showThumbnails && lane_type.startsWith('video')`
- Calculate frameCount from `clipWidthPx / (trackHeight * 16/9)`
- Lazy: only render for clips in viewport (use scroll position)

### Phase 2: Track Display Options (Gamma — track header UI)
- Right-click on track header → display mode menu
- Options: Name Only, Filmstrip, Waveform, Both
- Per-track override stored in `trackDisplayModes: Record<string, ClipDisplayMode>`
- Track height presets affect filmstrip frame size

### Phase 3: Sprite Sheet Optimization (Beta — backend)
- `GET /cut/thumbnail-strip?source_path=...&count=N&height=H` → single sprite JPEG
- FFmpeg: extract N frames → ffmpeg -i concat → horizontal tile
- Disk cache by content hash (source+count+height)
- Frontend: single `<img>` with CSS `object-position` per visible frame slot

### Phase 4: Smart Prefetch (Beta — performance)
- Predict visible clip range from scroll position + zoom
- Prefetch thumbnails for clips about to enter viewport
- LRU eviction when memory exceeds 50MB blob URL budget
