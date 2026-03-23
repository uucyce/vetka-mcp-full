# RECON: FFmpeg Codec Compatibility Matrix
**Agent:** Beta | **Date:** 2026-03-23
**System:** FFmpeg 7.1.1, Homebrew, Apple Silicon (M-series)

## System FFmpeg Build

```
ffmpeg version 7.1.1 (2025)
built with Apple clang 17.0.0
--enable-libx264 --enable-libx265 --enable-libaom --enable-libdav1d
--enable-libsvtav1 --enable-librav1e --enable-libvpx --enable-libmp3lame
--enable-videotoolbox --enable-audiotoolbox
```

## Codec Matrix (this build)

### VIDEO — DECODE + ENCODE

| Codec | Decode | Encode | FFmpeg lib | CUT CODEC_MAP | Notes |
|-------|--------|--------|-----------|---------------|-------|
| H.264/AVC | YES | YES | libx264, videotoolbox | `h264` | Universal. GH4, iPhone, Canon all work |
| H.265/HEVC | YES | YES | libx265, videotoolbox | `h265` | iPhone 7+, GoPro HERO6+. HW accel on Mac |
| ProRes | YES | YES | prores_ks, videotoolbox | `prores_proxy` thru `prores_4444xq` | 6 profiles. Builtin decoder |
| DNxHD/DNxHR | YES | YES | dnxhd (builtin) | `dnxhd`, `dnxhr_*` | 5 profiles. Avid workflows |
| DV (PAL/NTSC) | YES | YES | dvvideo (builtin) | Not in CODEC_MAP | AVI DV PAL works. Add if needed |
| AV1 | YES | YES | libdav1d (dec), libsvtav1/libaom/librav1e (enc) | `av1` | Slow encode, fast decode |
| VP9 | YES | YES | libvpx-vp9 | `vp9` | WebM delivery |
| MPEG-2 | YES | YES | mpeg2video (builtin) | Not in CODEC_MAP | Legacy DVD/broadcast |

### VIDEO — DECODE ONLY (no encode in our map)

| Format | Decode | Source | Notes |
|--------|--------|--------|-------|
| AVCHD (.mts) | YES | H.264 in MPEG-2 TS | Consumer cameras (Sony, Panasonic) |
| MXF wrapped | YES | Container, not codec | Broadcast container. Wraps DNxHD/ProRes/XDCAM |
| XDCAM | YES | MPEG-2/H.264 variant | Sony broadcast |
| Canon XF | YES | MPEG-2 in MXF | Canon cinema |

### VIDEO — NOT SUPPORTED (need external decoders)

| Format | Status | What's needed |
|--------|--------|---------------|
| RED R3D | NOT SUPPORTED | REDline SDK (proprietary). Transcode to ProRes first |
| BRAW | NOT SUPPORTED | Blackmagic RAW SDK (proprietary). Use DaVinci Resolve to transcode |
| ARRIRAW | NOT SUPPORTED | ARRI SDK. Transcode to ProRes/DNxHR |
| CinemaDNG | PARTIAL | Individual DNG frames decode OK, sequence needs wrapper |

### AUDIO

| Codec | Decode | Encode | CUT Support |
|-------|--------|--------|-------------|
| AAC | YES | YES | Default for MP4/MOV |
| MP3 | YES | YES (libmp3lame) | Legacy delivery |
| FLAC | YES | YES | Lossless archive |
| PCM 16/24/32 | YES | YES | Masters, stems |
| Opus | YES | YES (libopus) | Not in UI yet |
| Vorbis | YES | YES | Not in UI yet |
| AC3/E-AC3 | YES | YES | 5.1 surround (future) |

## Recommendations

1. **H.265 works** — our build has libx265 + videotoolbox HW encoder. Safe to offer
2. **DV PAL** — FFmpeg decodes natively. Consider adding `dvvideo` to CODEC_MAP for import support
3. **RED/BRAW/ARRIRAW** — these need proprietary SDKs. Document as "transcode first" in UI
4. **VideoToolbox** — Mac has HW H.264/H.265/ProRes encode. Could add HW-accelerated presets (future)
5. **Opus audio** — better than AAC for web delivery. Add to AUDIO_CODECS in ExportDialog

## Runtime Detection

Added `GET /cut/codecs/available` endpoint that runs `ffmpeg -codecs` and returns
per-codec decode/encode capability. ExportDialog can disable unavailable codecs.
