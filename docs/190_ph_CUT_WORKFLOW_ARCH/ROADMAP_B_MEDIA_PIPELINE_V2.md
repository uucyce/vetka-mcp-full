# ROADMAP B: MEDIA PIPELINE V2 — Deep Architecture

**Agent:** Beta (Media/Color Pipeline Architect)
**Branch:** `claude/cut-media`
**Task:** `tb_1775145271_85802_1`
**Created:** 2026-04-02

---

## Executive Summary

This document is a complete architectural map of the VETKA CUT media pipeline as of 2026-04-02.
Based on direct code inspection of: `cut_codec_probe.py`, `cut_audio_engine.py`,
`cut_render_pipeline.py`, `cut_codecs.py`, `cut_render_engine.py`, `cut_effects_engine.py`,
`cut_routes_render.py`, `useCutEditorStore.ts`, `ExportDialog.tsx`.

**Priority tiers:**
- **MVP** — required for production-ready NLE deployment (week 1)
- **v1.0** — full professional feature parity (month 1)
- **v2.0** — camera RAW / ACES / advanced color science (quarter 1)

---

## 1. AUDIO PIPELINE — Current State + Gaps

### 1.1 What Exists (IMPLEMENTED)

| Component | File | Status |
|-----------|------|--------|
| `MixerState` dataclass | `cut_audio_engine.py:46` | IMPLEMENTED |
| `LaneMixerState` (volume, mute, solo, pan) | `cut_audio_engine.py:36` | IMPLEMENTED |
| `apply_mixer_to_plan(plan, mixer_state)` | `cut_audio_engine.py:176` | IMPLEMENTED |
| `build_lane_audio_filters()` | `cut_audio_engine.py:103` | IMPLEMENTED |
| `compile_pan_filter()` | `cut_audio_engine.py:158` | IMPLEMENTED |
| `_volume_to_db()`, `linear_to_db()` | `cut_audio_engine.py` | IMPLEMENTED |
| `render_timeline(mixer=...)` parameter | `cut_render_pipeline.py:915` | IMPLEMENTED |
| Audio crossfade via `acrossfade` | `cut_render_pipeline.py:572` | IMPLEMENTED (MARKER_B14) |
| Per-clip `audio_effects` injection | `cut_render_pipeline.py:506` | IMPLEMENTED |
| `export_audio_stems()` | `cut_render_pipeline.py:781` | IMPLEMENTED |
| Frontend mixer state in store | `useCutEditorStore.ts:280` | IMPLEMENTED |
| Frontend `renderSelection` passes mixer | `useCutEditorStore.ts:1483` | IMPLEMENTED |
| Frontend `renderAll` passes mixer | `useCutEditorStore.ts:1526` | IMPLEMENTED |

### 1.2 P0 BLOCKER — ExportDialog does NOT pass mixer

**Bug location:** `client/src/components/cut/ExportDialog.tsx`

The main export path (`ExportDialog` → POST `/cut/render/master`) calls the render endpoint
**without** including `mixer` in the request body. The `renderSelection` and `renderAll`
store actions both correctly build and pass the mixer dict, but the primary export UI does not.

**Root cause:** `ExportDialog` does not read `laneVolumes`/`masterVolume`/`soloLanes`/`mutedLanes`
from `useCutEditorStore` before constructing the API request body.

**Fix plan (task `tb_1775145287_85802_1`):**
```typescript
// In ExportDialog.tsx — before fetch call:
const { laneVolumes, masterVolume, soloLanes, mutedLanes } = useCutEditorStore.getState();
const mixerLanes: Record<string, ...> = {};
for (const [laneId, vol] of Object.entries(laneVolumes)) {
  mixerLanes[laneId] = { volume: vol, mute: mutedLanes.has(laneId), solo: soloLanes.has(laneId), pan: 0 };
}
// Add to request body:
mixer: { lanes: mixerLanes, master_volume: masterVolume }
```

**FFmpeg filter chain (how mixer works end-to-end):**
```
useCutEditorStore (laneVolumes)
  → ExportDialog/renderAll/renderSelection
  → POST /cut/render/master { mixer: { lanes, master_volume } }
  → render_timeline(mixer=...)
  → MixerState.from_dict(mixer)
  → apply_mixer_to_plan(plan, mixer_state)
  → build_lane_audio_filters()
  → clip.audio_effects.extend([{type:"volume", db:X}, {type:"pan", ...}])
  → FilterGraphBuilder._clip_audio_filter()
  → compile_audio_filters() → ["volume=X.XdB", "pan=stereo|c0=..."]
  → FFmpeg -filter_complex "[0:a]volume=-3.5dB,pan=stereo|c0=0.5*c0[a0]"
```

### 1.3 Audio Transitions

| Feature | FFmpeg Filter | Status |
|---------|--------------|--------|
| Crossfade between clips | `acrossfade=d={dur}:curve={type}` | IMPLEMENTED (MARKER_B14) |
| Dip-to-black audio | `afade` | IMPLEMENTED (via transition type) |
| Wipe/dissolve audio | `acrossfade` | IMPLEMENTED |
| EQ per track | `equalizer`, `anequalizer` | NOT IMPLEMENTED |
| Compression/limiter | `acompressor`, `alimiter` | NOT IMPLEMENTED |
| Reverb/delay | `aecho`, `reverb` | NOT IMPLEMENTED |

### 1.4 Stem Export

`export_audio_stems()` exists at `cut_render_pipeline.py:781`.
Extracts per-lane WAV stems by running FFmpeg per audio lane.
**Gap:** No UI to trigger stem export from ExportDialog.

### 1.5 Audio v1.0 / v2.0 Roadmap

**v1.0:**
- [ ] Wire EQ effect type in `cut_effects_engine.compile_audio_filters` (FFmpeg `anequalizer`)
- [ ] Add acompressor support for dynamic range control
- [ ] Expose stem export toggle in ExportDialog
- [ ] Fix `pan` value: currently always 0 in store build — should read per-lane pan from store

**v2.0:**
- [ ] Web Audio API real-time monitoring (replace simulated VU meters)
- [ ] AAC/MP3/Opus target bitrate per-track in stems
- [ ] Dolby Atmos metadata passthrough (spatial audio)

---

## 2. CODEC UNIVERSE — Full Map

### 2.1 FFmpeg Native Codec Support (this machine)

Verified via `ffmpeg -codecs` and `ffmpeg -formats`:

**Video Encode/Decode (DE):**

| Codec | FFmpeg Name | Encode | Decode | Notes |
|-------|-------------|--------|--------|-------|
| H.264 | `h264` | libx264, h264_videotoolbox | ✓ | VideoToolbox HW accel on macOS |
| H.265/HEVC | `hevc` | libx265, hevc_videotoolbox | ✓ | VideoToolbox HW accel on macOS |
| Apple ProRes | `prores` | prores, prores_aw, prores_ks, prores_videotoolbox | ✓ | All profiles |
| DNxHD/HR | `dnxhd` | ✓ | ✓ | All DNxHR tiers |
| AV1 | `av1` | libaom-av1, librav1e, libsvtav1 | libdav1d, libaom-av1 | Modern web |
| VP9 | `vp9` | libvpx-vp9 | ✓ | Google web format |
| MPEG-2 | `mpeg2video` | ✓ | ✓ | Broadcast, DVD |
| Motion JPEG | `mjpeg` | ✓ | ✓ | ENG cameras |
| GoPro CineForm | `cfhd` | ✓ | ✓ | Production |
| DPX | `dpx` | ✓ | ✓ | Film scanning |
| OpenEXR | `exr` | ✓ | ✓ | VFX pipelines |
| FFV1 | `ffv1` | ✓ | ✓ | Archive lossless |
| HuffYUV | `huffyuv` | ✓ | ✓ | Lossless |
| Uncompressed 10-bit | `v210`, `v410` | ✓ | ✓ | Broadcast |
| RED R3D | via `r3d` format | ✗ | ✓ (demux only) | Needs SDK for full decode |

**Container Support:**

| Container | FFmpeg Format | R/W | Notes |
|-----------|--------------|-----|-------|
| MOV/MP4 | `mov,mp4,...` | RW | Primary |
| MXF | `mxf` | RW | Broadcast |
| AVI | `avi` | RW | Legacy |
| MKV/WebM | `matroska`, `webm` | RW | Open source |
| RED R3D | `r3d` | R only | Demux supported |
| DPX sequence | `dpx_pipe` | R only | Piped sequence |
| EXR sequence | `exr_pipe` | R only | Piped sequence |
| TIFF sequence | `tiff_pipe` | R only | Piped sequence |

### 2.2 Camera RAW — SDK Availability Matrix

| Camera System | Format | FFmpeg Native? | SDK Available? | Integration Path |
|--------------|--------|----------------|----------------|-----------------|
| RED DSMC2/V-RAPTOR | `.r3d` | Demux only (no color) | REDline SDK — **free download** (REDCOM) | Python subprocess REDline → DPX/EXR → FFmpeg |
| Blackmagic RAW | `.braw` | ✗ | BMD RAW SDK — **free** (Blackmagic Design) | Python ctypes/subprocess → DPX/MOV proxy |
| ARRIRAW | `.ari`, `.mxf` | Via ARRI MXF wrapper | ARRI SDK — closed, NDA required | Use OpenEXR proxy via ARRIscope or DaVinci |
| CinemaDNG | `.dng` | Via rawvideo | None needed | dcraw/libraw → TIFF → FFmpeg |
| Sony RAW | `.mxf` (XAVC RAW) | Partial (XAVC-S via HEVC) | None needed for XAVC-S | Direct FFmpeg for XAVC-S; F55/F65 RAW needs SDK |
| Canon RAW | `.crm` | ✗ | Canon Cinema RAW Light SDK | Canon provides macOS dylib |

**Practical recommendation for v2.0:**
- BMD SDK: highest ROI (BMPCC 4K/6K ubiquitous, free SDK, Python-friendly)
- REDline: second priority (RED cameras common in film production)
- CinemaDNG via libraw: low effort, supports many older cameras

### 2.3 Current CODEC_MAP (Render Engine)

Already implemented in `cut_codecs.py` (`src/services/cut_codecs.py:19`):

```
ProRes: proxy/lt/422/422hq/4444/4444xq
DNxHR: lb/sq/hq/hqx/444 + dnxhd
H.264: h264 + h264_10bit
H.265: h265 + h265_10bit
Web: vp9, av1, av1_8
Lossless: ffv1, huffyuv, ut_video
Legacy: mpeg2, mjpeg
Image sequences: png_seq, tiff_seq, dpx_seq, exr_seq
```

**Total encode targets: 24 presets** — comprehensive for delivery.

### 2.4 HDR Support

| HDR Format | FFmpeg | Status |
|-----------|--------|--------|
| Rec.2020 + PQ (HDR10) | `zscale=transfer=bt709:transferin=smpte2084:tonemap=hable` | Decode filter exists (`cut_codecs.py:_LOG_DECODE_FILTERS`) |
| HLG (Hybrid Log-Gamma) | `zscale=transfer=bt709:transferin=arib-std-b67` | Decode filter exists |
| Dolby Vision | via `dvhe` demux | NOT IMPLEMENTED |
| HDR10+ | metadata passthrough | NOT IMPLEMENTED |

---

## 3. COLOR SCIENCE — Current State + Roadmap

### 3.1 What Exists (IMPLEMENTED)

| Component | File | Status |
|-----------|------|--------|
| Log profile detection (10 cameras) | `cut_codec_probe.py:detect_log_profile()` | IMPLEMENTED (MARKER_B24) |
| Log decode filters (V-Log, S-Log3, LogC3, CLog3, HLG, PQ) | `cut_codecs.py:_LOG_DECODE_FILTERS` | IMPLEMENTED (MARKER_B16) |
| Color primaries map (bt709→Rec.2020→DCI-P3) | `cut_codec_probe.py:_COLOR_PRIMARIES_MAP` | IMPLEMENTED |
| 3-way color wheels (lift/gamma/gain) | `ColorCorrectionPanel.tsx` | IMPLEMENTED |
| LUT browser + .cube apply | `LUTBrowserPanel.tsx`, `cut_lut_manager.py` | IMPLEMENTED |
| Color scopes (waveform, vectorscope, histogram) | `cut_scope_renderer.py`, WebSocket | IMPLEMENTED |
| pix_fmt → bit depth + chroma map | `cut_codec_probe.py:_PIX_FMT_INFO` | IMPLEMENTED (44 formats) |
| Camera tag heuristic detection (GH5/FX6/A7S/Alexa/RED/DJI etc.) | `cut_codec_probe.py:_TAG_CAMERA_HINTS` | IMPLEMENTED |

### 3.2 Camera Log Profiles Supported (MARKER_B16 + B24)

| Camera | Log Profile | Gamut | Detection Method |
|--------|------------|-------|-----------------|
| Panasonic GH5/GH6/Lumix | V-Log | V-Gamut | color_transfer + tag |
| Sony FX6/FX3/A7S | S-Log3 | S-Gamut3.Cine | color_transfer + tag |
| ARRI Alexa | LogC3 | ARRI Wide Gamut 3 | color_transfer + tag |
| Canon EOS R5/C300 | Canon Log 3 | — | color_transfer + tag |
| RED | Log3G10 | REDWideGamutRGB | color_transfer + tag |
| DJI Mavic/drone | D-Log | — | color_transfer + tag |
| Nikon Z-series | N-Log | — | color_transfer |
| Fujifilm | F-Log | — | color_transfer |
| Blackmagic | BMDFilm | — | color_transfer + tag |
| Broadcast HDR | HLG | Rec.2020 | color_transfer (arib-std-b67) |
| HDR10 | PQ | Rec.2020 | color_transfer (smpte2084) |

### 3.3 LUT Support

| Format | Status |
|--------|--------|
| `.cube` (1D/3D) | IMPLEMENTED |
| `.3dl` (Lustre/Nuke) | NOT IMPLEMENTED |
| `.csp` (Rising Sun) | NOT IMPLEMENTED |
| `.lut` (generic) | NOT IMPLEMENTED |
| OCIO `.clf` | NOT IMPLEMENTED |

### 3.4 Color Science v1.0 / v2.0 Roadmap

**v1.0:**
- [ ] .3dl and .csp LUT parser (extend `cut_lut_manager.py`)
- [ ] Auto-apply log decode filter on import when log profile detected
- [ ] Color space sequence setting (Rec.709 / DCI-P3 / Rec.2020) wired to render

**v2.0 — OpenColorIO (OCIO):**
OpenColorIO (ASWF, open source) provides the industry-standard ACES workflow:
- `pip install opencolorio` — Python bindings available
- ACES config: https://github.com/colour-science/OpenColorIO-Configs
- Integration path: `cut_color_pipeline.py` → `ocio.ColorSpaceTransform` → apply to export
- Key benefit: camera log → ACES AP0 → output transforms (Rec.709/P3/Rec.2020)
- Enables: proper color management, ICC profiles, output LUT baking

**v2.0 — colour-science Python:**
- `pip install colour-science` — broad color math library
- Use for: delta-E calculations, color checker detection, gamut mapping
- Integration: `cut_color_pipeline.py` additions

---

## 4. IMPORT PIPELINE — Current State + Roadmap

### 4.1 What Exists (IMPLEMENTED)

| Component | File | Status |
|-----------|------|--------|
| `probe_file()` → `ProbeResult` | `cut_codec_probe.py:473` | IMPLEMENTED |
| `detect_log_profile()` | `cut_codec_probe.py:660` | IMPLEMENTED |
| `codec_family` classification | `cut_codec_probe.py:_CODEC_FAMILY_MAP` | IMPLEMENTED |
| `playback_class` inference | `cut_codec_probe.py:_infer_playback_class()` | IMPLEMENTED |
| POST `/media/support` probe endpoint | `cut_routes_media.py` | IMPLEMENTED |
| Proxy generation (libx264 ultrafast) | `cut_proxy_worker.py` | IMPLEMENTED |
| Bootstrap pipeline | `cut_routes_bootstrap.py` | IMPLEMENTED |
| Degraded mode error struct | `cut_routes_bootstrap.py:55` | IMPLEMENTED |

### 4.2 P1 — Bootstrap Degraded Mode Notification

**Gap:** When bootstrap returns `degraded_mode: true`, the frontend shows no visible
user notification. Users don't know media import failed.

**Fix location:** Frontend bootstrap response handler.
**Fix:** `pipeline-activity` CustomEvent dispatch when `data.degraded_mode === true`,
showing the `degraded_reason` in the activity bar with `status: 'error'`.
Task: `tb_1775145299_85802_1`.

### 4.3 Playback Class Routing

```
import file
  → probe_file() → ProbeResult { codec_family, playback_class }
  → playback_class == "native"       → direct WebCodecs/HTML5 video
  → playback_class == "proxy_recommended" → generate_proxy(libx264 ultrafast 720p)
  → playback_class == "transcode_required" → proxy mandatory before edit
  → playback_class == "unsupported"  → error + message
```

### 4.4 Missing: Proxy Strategy for Heavy Formats

**Current:** Single proxy profile — libx264 ultrafast, no resolution target specified.

**v1.0 needed:**
```python
# Proxy strategy by codec_family:
PROXY_PROFILES = {
    "camera_raw":  {"codec": "prores_proxy", "height": 1080},  # DPX/EXR/R3D
    "production":  {"codec": "h264", "height": 720, "crf": 18},  # ProRes/DNxHR
    "delivery":    {"codec": "h264", "height": 720, "crf": 23},  # HEVC 10-bit
}
```

### 4.5 Missing: Media Reconnect

When sandbox moves or files relocate, no reconnect workflow exists.
**v1.0:** `POST /cut/media/reconnect` endpoint with path remapping.
**v2.0:** Watch folder + auto-reconnect via `watchdog` library.

### 4.6 Import Pipeline v1.0 / v2.0

**v1.0:**
- [ ] Resolution-targeted proxy generation (see PROXY_PROFILES above)
- [ ] Bootstrap degraded mode notification in frontend (task `tb_1775145299_85802_1`)
- [ ] POST `/cut/media/reconnect` endpoint
- [ ] Import progress via SocketIO events

**v2.0:**
- [ ] BMD RAW SDK integration for `.braw` files
- [ ] CinemaDNG via libraw for `.dng` sequences
- [ ] Watch folder import with inotify/FSEvents
- [ ] Automatic scene detection on import

---

## 5. PRIORITY TIERS SUMMARY

### MVP (Week 1 — production deploy gate)

| # | Task | File | Effort |
|---|------|------|--------|
| P0 | Wire mixer → ExportDialog render call | `ExportDialog.tsx` | 30 min |
| P1 | Bootstrap degraded mode notification | Frontend bootstrap handler | 1 hour |

These are the only items blocking a production-ready NLE experience.

### v1.0 (Month 1 — full professional feature parity)

| # | Task | Files | Effort |
|---|------|-------|--------|
| A | Per-lane pan value from store (currently always 0) | `useCutEditorStore.ts`, `AudioMixer.tsx` | 2 hours |
| B | Stem export UI toggle in ExportDialog | `ExportDialog.tsx` | 2 hours |
| C | EQ effect in compile_audio_filters | `cut_effects_engine.py` | 3 hours |
| D | .3dl / .csp LUT parser | `cut_lut_manager.py` | 4 hours |
| E | Auto log-detect + apply decode filter on import | `cut_routes_import.py`, `cut_color_pipeline.py` | 4 hours |
| F | Resolution-targeted proxy profiles | `cut_proxy_worker.py` | 3 hours |
| G | Media reconnect endpoint | `cut_routes_media.py` | 4 hours |
| H | Color space sequence setting wired to render | `cut_render_pipeline.py`, `SequenceSettings.tsx` | 3 hours |

### v2.0 (Quarter 1 — camera RAW + ACES)

| # | Task | Dependency | Effort |
|---|------|-----------|--------|
| I | BMD RAW SDK integration | BMD SDK download | 2 weeks |
| J | REDline SDK integration | REDline download | 1 week |
| K | OpenColorIO ACES pipeline | `pip install opencolorio` | 2 weeks |
| L | colour-science color math | `pip install colour-science` | 1 week |
| M | HDR10+ / Dolby Vision passthrough | FFmpeg DVhe support | 1 week |
| N | CinemaDNG via libraw | `brew install libraw` | 1 week |
| O | Watch folder import | `pip install watchdog` | 1 week |

---

## 6. FFmpeg Filter Graph Reference

### Audio Filters Available (FFmpeg built-in)

```
Volume:        volume=3.5dB  or  volume=0.707
Pan:           pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1
Fade in/out:   afade=t=in:d=0.5
Crossfade:     acrossfade=d=0.5:c1=tri:c2=tri
EQ (parametric): anequalizer=c0 f=1000 w=200 g=-3 t=0
Compression:   acompressor=threshold=0.5:ratio=4:attack=5:release=50
Limiter:       alimiter=level_in=1:level_out=0.9:limit=0.9
Normalize:     dynaudnorm
Mix tracks:    amix=inputs=3:duration=longest:normalize=0
Delay:         adelay=500|1000  (ms per channel)
Echo/Reverb:   aecho=0.8:0.88:60:0.4
```

### Video Color Filters Available

```
Curves:        curves=master='0/0 0.5/0.6 1/1'
Color matrix:  colormatrix=bt601:bt709
Zscale:        zscale=transfer=bt709:transferin=smpte2084:tonemap=hable
LUT3D:         lut3d=file.cube
Color channels: colorchannelmixer=rr=1:gg=1:bb=1
Hue/Saturation: hue=s=1.2
Brightness:    eq=brightness=0.1:contrast=1.2:saturation=1.1
```

---

## 7. Key Files Map

```
src/services/
├── cut_codec_probe.py       # ProbeResult, detect_log_profile, codec_family
├── cut_audio_engine.py      # MixerState, apply_mixer_to_plan, compile_pan_filter
├── cut_render_pipeline.py   # FilterGraphBuilder, render_timeline, export_audio_stems
├── cut_render_engine.py     # Re-export facade (B5 split)
├── cut_codecs.py            # CODEC_MAP (24 presets), _LOG_DECODE_FILTERS
├── cut_formats.py           # EXPORT_PRESETS, RESOLUTION_MAP
├── cut_effects_engine.py    # compile_audio_filters, compile_video_filters
├── cut_color_pipeline.py    # Color pipeline (LUT apply, OCIO future)
├── cut_lut_manager.py       # .cube LUT loading
├── cut_scope_renderer.py    # Waveform/vectorscope WebSocket
└── cut_proxy_worker.py      # Proxy generation

src/api/routes/
├── cut_routes_render.py     # POST /render/master, /render/selection, /render/all
├── cut_routes_bootstrap.py  # POST /bootstrap, degraded_mode handling
├── cut_routes_media.py      # POST /media/support (probe)
└── cut_routes_audio.py      # Audio mixer endpoints

client/src/components/cut/
├── ExportDialog.tsx         # ⚠️ P0: missing mixer in /render/master call
├── AudioMixer.tsx           # UI — volume/mute/solo/VU
└── panels/
    ├── ColorCorrectionPanel.tsx
    ├── VideoScopesPanel.tsx
    └── LUTBrowserPanel.tsx

client/src/store/
└── useCutEditorStore.ts     # laneVolumes, masterVolume, soloLanes, mutedLanes
```

---

*Beta — Media/Color Pipeline Architect | 2026-04-02*
