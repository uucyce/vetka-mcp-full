# ROADMAP B: MEDIA — Detailed Sub-Roadmap

**Parent:** `ROADMAP_CUT_MVP_PARALLEL.md` → Stream B
**Agent:** Opus (claude_code)
**Worktree:** `claude/cut-media`
**Created:** 2026-03-20

---

## Overview

Stream B owns the codec engine, effects pipeline, render system, and audio mixing.
Backend already has 54+ endpoints including POST /media/support (ffprobe probe) and
POST /render/master (FFmpeg concat pipeline). This stream extracts inline helpers into
dedicated service modules and adds missing capabilities.

## Existing Backend Assets

| What | Where | Status |
|------|-------|--------|
| `_probe_ffprobe_metadata()` | `cut_routes.py:2443` | Working, returns raw dict |
| `_probe_clip_duration()` | `cut_routes.py:2474` | Working, uses above |
| `_ffprobe_metadata()` | `video_scanner.py:44` | Working, returns `MediaMetadata` |
| `MediaMetadata` dataclass | `scan_types.py:17` | Active, used by scanners |
| POST /media/support | `cut_routes.py:5078` | Working, calls probe |
| POST /render/master | `cut_routes.py:8104` | Working, FFmpeg concat |
| `ProxyResult` dataclass | `cut_proxy_worker.py:67` | Active |
| `PRODUCTION_VIDEO_FORMATS` | `cut_routes.py:2419` | Classification constants |
| `_CODEC_MAP` | `cut_routes.py:7917` | ProRes/H.264/H.265 mapping |

## Task Breakdown — Wave 0.5 (Post-B1, priority 1, no deps)

### B1.5: Maximum Codec/Container Coverage — PyAV-Ready Registry
- **Files:** `cut_codec_probe.py`, `cut_render_engine.py`, `cut_routes.py`
- **Task ID:** `tb_1773989032_1`
- **Motivation:** Real production footage uses exotic codecs: GH5 HEVC 10-bit in MOV,
  Panasonic V-Log, Sony XAVC-S, Canon XF-AVC, RED R3D, BRAW, ARRIRAW, CinemaDNG.
  Current maps only cover 5 encode codecs and 5 native container extensions.
- **What:**
  1. `cut_codec_probe.py` — add `codec_family` classification (camera_raw, production,
     delivery, web, audio_only) + `playback_class` inference (native/proxy_recommended/
     transcode_required/unsupported). Expand pix_fmt and color primaries maps.
  2. `cut_render_engine.py` CODEC_MAP — add all ProRes profiles (LT/Proxy/422HQ/4444XQ),
     DNxHR tiers (LB/SQ/HQ/HQX/444), H.264 10-bit, H.265 10-bit, VP9, AV1.
  3. `cut_routes.py` — expand PRODUCTION_VIDEO_FORMATS, NATIVE_VIDEO_EXT,
     PROXY_RECOMMENDED_EXT to cover all camera/broadcast/web containers.
- **Future:** PyAV decoder path (B4) will use this registry for codec→decoder routing.
- **Acceptance:**
  - Codec family for all major camera codecs classified
  - Playback class auto-detected from codec+container
  - Render engine can target 15+ encode codecs
  - GH5 HEVC 10-bit MOV detected as proxy_recommended
  - Tests cover all codec families

## Task Breakdown — Wave 1 (Priority 1, no deps)

### B1: FFprobe Codec Detection + Metadata Extraction
- **File:** `src/services/cut_codec_probe.py` (NEW)
- **Task ID:** `tb_1773981821_8`
- **What:** Extract `_probe_ffprobe_metadata()` from cut_routes.py into structured service.
  Create `ProbeResult` dataclass with: video_codec, audio_codec, container, width, height,
  fps, duration_sec, audio_channels, sample_rate, pix_fmt, color_space, bit_depth, bitrate.
  Add color space detection from pix_fmt (Rec.709/Rec.2020/P3).
  Wire into POST /media/support to return structured ProbeResult.
- **Acceptance:**
  - `ProbeResult` has all fields above
  - `probe_file(path)` returns `ProbeResult` or raises
  - Color space inferred from pix_fmt + color_primaries
  - Unit tests pass with mock ffprobe output
  - POST /media/support returns ProbeResult-shaped JSON

### B3: Sequence Settings
- **File:** `client/src/components/cut/SequenceSettings.tsx` (enhance existing ProjectSettings)
- **Task ID:** `tb_1773981827_9`
- **What:** Add resolution (4K/1080/720/custom), color space (Rec.709/DCI-P3/Rec.2020),
  proxy mode toggle. Wire to backend POST /cut/project-state.
- **Acceptance:**
  - UI shows resolution/color space/proxy fields
  - Changes persist via backend
  - Framerate change reflects in export

## Task Breakdown — Wave 2 (Priority 1, deps on B1)

### B2: Proxy Generation Pipeline
- **Deps:** B1 (needs ProbeResult for auto-settings)
- **File:** `src/services/cut_proxy_worker.py` (enhance)
- **What:** Use ProbeResult to auto-select proxy spec. Add 480p tier.

### B5: Master Render Engine
- **Deps:** B1 (needs codec detection for source matching)
- **File:** `src/services/cut_render_engine.py` (NEW)
- **What:** Extract render logic from cut_routes.py. Add filter_complex for effects/transitions.

### B6: ExportDialog Rewrite
- **Deps:** B5
- **File:** `client/src/components/cut/ExportDialog.tsx` (rewrite)

## Task Breakdown — Wave 3 (Priority 2, parallel)

### B9: Effects System
- **File:** `src/services/cut_effects_engine.py` (NEW)
- **No deps.** Foundation for B10 (transitions) and B16 (color).

### B11: Clip Speed Control
- **File:** Backend + `client/src/components/cut/SpeedControl.tsx` (NEW)
- **No deps.**

### B13: Audio Mixer Panel
- **File:** `src/services/cut_audio_engine.py` (NEW) + `AudioMixer.tsx` (NEW)
- **No deps.** Foundation for B14 (audio transitions).

### B15: Audio Waveform Overlay
- **No deps.**

## Task Breakdown — Wave 4 (Priority 2-3, sequential)

- B2 → B4 (WebCodecs decoder)
- B5 → B6 → {B7, B8, B17} (render → export dialog → variants)
- B9 → {B10, B16} (effects → transitions + color)
- B13 → B14 (mixer → audio transitions)
- B12 (motion controls — independent)

## FFmpeg Build Strategy (Grok Recon 2026-03-20)

**Goal:** Maximum codec coverage via custom FFmpeg build (GPL + nonfree).

**Recommended:** `markus-perl/ffmpeg-build-script` → static binary, all libs.
```bash
git clone https://github.com/markus-perl/ffmpeg-build-script.git
cd ffmpeg-build-script
SKIPINSTALL=yes ./build-ffmpeg --build --enable-gpl-and-non-free
```

**Key --enable flags for full coverage:**
libx264, libx265, libvpx, libaom, libdav1d, libsvtav1, librav1e,
libfdk-aac, libopus, libmp3lame, libvorbis, libsoxr, libzimg,
libbluray, libwebp, libopenjpeg, openssl

**PyAV:** Must build from source against custom FFmpeg:
```bash
pip uninstall av -y
git clone https://github.com/PyAV-Org/PyAV.git
cd PyAV
export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig
pip install -e .
```

**Verify:** `ffmpeg -codecs | grep -E 'HEVC|ProRes|DNx|opus|fdk'`

## Parallel Execution Map

```
Wave 1 (NOW):     B1 ──┬── B3 ── B9 ── B11 ── B13 ── B15
                        │
Wave 2 (after B1): B2 ── B5
                        │
Wave 3 (after B5): B4    B6 ── {B7, B8, B17}
                        │
Wave 4 (after B9): B10 ── B16
                  B13 → B14
                  B12 (anytime)
```
