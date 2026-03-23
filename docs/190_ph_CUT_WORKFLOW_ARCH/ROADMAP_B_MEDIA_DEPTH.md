# ROADMAP B: Media Depth — Full Pipeline
**Agent:** Beta (Media Pipeline Architect)
**Branch:** claude/cut-media
**Date:** 2026-03-23
**FCP7 Ref:** Ch.39-50, 55-57, 69, 79-83

## Mission
Complete media pipeline: import → preview → edit → audio playback → export.
Every feature a professional editor expects from day one.

---

## Stream 1: AUDIO PLAYBACK (P0)
**FCP7 Ch.39-44, 55-57 | Ref: ROADMAP_B5**

| # | Task | Priority | Complexity | Status |
|---|------|----------|------------|--------|
| B5.1 | Audio clip segment endpoint | P0 | Medium | DONE `7b2735b3` |
| B5.2 | useAudioPlayback hook | P0 | Medium | **NEXT** |
| B5.3 | Audio buffer cache (LRU) | P1 | Low | — |
| B5.4 | Per-clip volume → GainNode wiring | P1 | Low | — |
| B5.5 | Pan control → StereoPannerNode | P2 | Low | — |
| B5.6 | Audio crossfade at transitions | P2 | Medium | — |
| B5.7 | VU meters live during playback (Web Audio AnalyserNode) | P2 | Medium | — |
| B5.8 | Audio-only clip support (music/VO tracks) | P2 | Low | — |

### B5.2: useAudioPlayback Hook
```
AudioContext → fetch WAV from B5.1 → decodeAudioData → AudioBufferSourceNode
                                                       → GainNode (clip volume)
                                                       → StereoPannerNode (pan)
                                                       → AnalyserNode (VU)
                                                       → ctx.destination
```
- Start/stop synced to video `isPlaying` state
- Seek: stop current source, create new with offset
- Pre-fetch next clip during playback
- Multiple simultaneous clips (layered audio tracks)

### B5.4: Rubber Band → GainNode
- AudioRubberBand (B30) provides volume per clip
- Keyframe interpolation → `gainNode.gain.setValueAtTime()`
- Automatable via `linearRampToValueAtTime()` for smooth transitions

### B5.7: Live VU Meters
- Replace simulated VU in AudioMixer.tsx with real AnalyserNode data
- `getByteFrequencyData()` → peak level per channel
- ClippingIndicator (B32) wired to real peak detection

---

## Stream 2: CODEC DEPTH (P1)
**FCP7 Ch.48-50**

| # | Task | Priority | Complexity | Status |
|---|------|----------|------------|--------|
| B6.1 | ProRes export variants (422/422HQ/4444/LT) | P1 | Low | Partial (422HQ + 4444 done) |
| B6.2 | Audio codec selector (AAC/PCM/MP3/FLAC) | P1 | Low | — |
| B6.3 | Variable bitrate (CBR/VBR/CRF) | P2 | Low | — |
| B6.4 | Export queue — batch multiple sequences | P2 | Medium | Backend done (B2.4), UI missing |
| B6.5 | Codec probe detail panel (MediaInfo-style) | P2 | Low | Backend probe exists |

### B6.2: Audio Codec Selector
ExportDialog currently hard-codes audio to AAC. Add dropdown:
- AAC (default for MP4/MOV)
- PCM (for ProRes/DNxHR masters)
- MP3 (legacy delivery)
- FLAC (lossless archive)

Map to FFmpeg: `-acodec aac`, `-acodec pcm_s24le`, `-acodec libmp3lame`, `-acodec flac`

---

## Stream 3: MEDIA MANAGEMENT (P2)
**FCP7 Ch.39-40**

| # | Task | Priority | Complexity | Status |
|---|------|----------|------------|--------|
| B7.1 | Reconnect offline media (re-link dialog) | P2 | Medium | — |
| B7.2 | Proxy workflow (proxy ↔ original toggle) | P2 | Medium | Backend exists (cut_proxy_worker.py) |
| B7.3 | Thumbnail generation for Project bin | P2 | Low | Backend done (generate_thumbnail), UI missing |
| B7.4 | Media info panel (codec/res/duration/channels) | P2 | Low | Backend probe exists |

### B7.2: Proxy Workflow
`cut_proxy_worker.py` already generates proxies. Missing:
- Toggle button in Project panel: "Use Proxies" / "Use Originals"
- Store: `useProxies: boolean` → swaps `source_path` references
- Alpha wires toggle in ProjectPanel.tsx

---

## Stream 4: RENDER PIPELINE (P3)
**FCP7 Ch.48**

| # | Task | Priority | Complexity | Status |
|---|------|----------|------------|--------|
| B8.1 | Timeline pre-render (cache effects for smooth playback) | P3 | High | — |
| B8.2 | Render indicator on timeline (red bar) | P3 | Low | — |
| B8.3 | Background render (render while editing) | P3 | High | — |

---

## Execution Priority

### Phase 1: Audio Playback (immediate)
B5.2 → B5.3 → B5.4 → B5.5

### Phase 2: Codec Polish (after audio)
B6.2 → B6.3 → B6.1

### Phase 3: Media Management (parallel with phase 2)
B7.4 → B7.3 → B7.2 → B7.1

### Phase 4: Render Pipeline (future)
B8.2 → B8.1 → B8.3

---

## Cross-Agent Dependencies

| What Beta Creates | Who Wires It |
|-------------------|-------------|
| useAudioPlayback hook | Alpha (VideoPreview sync) |
| Audio codec selector component | Gamma (ExportDialog UI) |
| Proxy toggle component | Gamma (ProjectPanel) |
| Media info component | Gamma (ClipInspector panel) |
| Render indicator component | Alpha (TimelineTrackView) |
| Live VU data | Gamma (AudioMixer.tsx VU replacement) |

---

*"Audio is half the picture." — Walter Murch*
