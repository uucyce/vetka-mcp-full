# Experience Report: Beta (Media/Color Pipeline Architect)
**Date:** 2026-03-23
**Agent:** OPUS-BETA | Branch: claude/cut-media
**Session scope:** Full media pipeline — audio, export, codecs, color grading, scopes, media management
**Tasks closed:** 26
**Commits:** 26
**Tests written:** ~100+ (across 5 test files)
**New components:** 12 frontend, 4 backend endpoints, 3 roadmaps

---

## 1. WHAT WORKED

### Recon-first saved massive time
Before writing code, I always checked what existed. Found export pipeline 90% done, waveform pipeline 100% done, CODEC_MAP already had all ProRes variants. Saved hours of duplicate work.

### Streaming task execution
Small focused tasks (1 component each) with auto-commit via task_board action=complete. No manual git add/commit — pipeline handles everything. Average task: 5-10 minutes.

### Numpy effects via cumsum trick
All blur/sharpen/denoise effects use the cumsum box blur trick: O(1) per pixel regardless of kernel size. 3-pass approximates gaussian. Separable (horizontal then vertical) keeps memory flat.

### Ownership boundaries worked
Never touched TimelineTrackView (Alpha), MenuBar (Gamma), or useCutHotkeys (Alpha). Created components with clear APIs for other agents to wire. Zero merge conflicts in 26 commits.

### Roadmaps before execution
ROADMAP_B3 (Audio Mixer), ROADMAP_B4 (Export Gaps), ROADMAP_B5 (Audio Playback), ROADMAP_B6 (Color Grading), ROADMAP_B_MEDIA_DEPTH (master) — each defined scope before code. Made task sequencing trivial.

---

## 2. WHAT DIDN'T

### White balance tests initially failed
Numpy in-place mutation (`frame[:,:,0] += shift`) modified the fixture. Tests compared mutated input to mutated output — both changed. Fix: use `.copy()` in tests. **Rule:** always copy fixtures before apply_numpy_effects.

### Denoise/sharpen cumsum shape mismatch
Vertical cumsum pass after horizontal pass produced array 1 row larger. Fix: trim `smoothed[:h, :w, :]` after cumsum. **Rule:** always trim to original shape after separable filter.

### CLAUDE.md worktree conflict on first pull
Main had Gamma's CLAUDE.md, our worktree had Beta's. Fixed manually. Filed ZETA-BUG for systematic fix.

---

## 3. KEY ARCHITECTURE DECISIONS

### Color grading: luma-weighted regions
- Lift: weight = clip(1 - luma*2, 0, 1) — strongest in blacks
- Midtone: weight = clip(1 - |luma-0.5|*4, 0, 1) — bell curve at 0.5
- Gain: weight = clip(luma*2 - 1, 0, 1) — strongest in whites
- These match FFmpeg's colorbalance behavior

### Audio playback: AudioContext per hook
Shared AudioContext would leak between components. One per useAudioPlayback hook, cleaned up on unmount. LRU cache of 32 AudioBuffers avoids re-fetching.

### Export dialog: socket + HTTP dual path
SocketIO for real-time progress, HTTP polling as fallback (2s interval when socket active, 500ms without). Cancel via job store flag → FFmpeg subprocess kill.

### Scope throttle: fast mode during playback
10 requests/sec max during playback (histogram only, 128px, ~2ms). Full scopes (all types, 256px, ~42ms) on pause. Prevents socket flooding.

---

## 4. PERFORMANCE NOTES

### Numpy effect timings (100x100 frame)
| Effect | Time |
|--------|------|
| brightness/contrast/saturation | <0.1ms |
| lift/midtone/gain | ~0.3ms |
| curves (preset) | ~0.2ms |
| blur (sigma=5, 3-pass) | ~2ms |
| sharpen (unsharp mask) | ~1ms |
| vignette (mgrid + sqrt) | ~1ms |
| drop_shadow (shift + blur + composite) | ~5ms |
| distort (perspective remap) | ~3ms |
| All 16 effects chained | ~15ms |

On 1920x1080: multiply by ~200x ≈ 3 seconds. For preview, use proxy (540p) → ~200ms.

### Tests: 52 preview decoder tests in 0.58s

---

## 5. RECOMMENDATIONS FOR SUCCESSOR

### Export is feature-complete, polish it
Cancel, presets, audio codec, bitrate modes, editorial formats — all working. Next: real user testing with actual media files. Found edge cases will be in codec compatibility matrix.

### Audio playback hook is ready, needs Alpha wiring
useAudioPlayback provides playAt/stopAll/setClipVolume/setClipPan. Alpha needs to call these from VideoPreview play/pause/seek handlers.

### Color grading preview works but needs UI feedback
Numpy preview for 16 effects is done. But ColorCorrectionPanel fetches preview frame from HTTP — should use the same numpy pipeline via WebSocket for instant response when dragging wheels.

### Don't touch cut_routes.py more than necessary
File is now 9000+ lines. Consider splitting: cut_audio_routes.py, cut_render_routes.py, cut_probe_routes.py. Predecessor warned about this too.

### Proxy workflow needs store integration
ProxyToggle component created but needs `useProxies` boolean in useCutEditorStore + source_path swap logic. Alpha/Gamma task.

---

## 6. SESSION STATISTICS

| Metric | Value |
|--------|-------|
| Tasks closed | 26 |
| Commits on claude/cut-media | 26 |
| New frontend components | 12 |
| New backend endpoints | 4 |
| New hooks | 1 (useAudioPlayback) |
| Numpy effects implemented | 16 (100% coverage) |
| Roadmaps written | 5 |
| Recon documents | 2 |
| Tests written | ~100+ |
| Lines of code (estimate) | ~3000 new |
| Merge conflicts | 0 |

---

## 7. COMPONENTS CREATED (for wiring by Alpha/Gamma)

| Component | Wires Into | Agent |
|-----------|-----------|-------|
| AudioRubberBand.tsx | TimelineTrackView clip blocks | Alpha |
| StereoWaveformCanvas.tsx | TimelineTrackView (when stereo peaks available) | Alpha |
| ClippingIndicator.tsx | AudioMixer.tsx VU section | Gamma |
| MixerViewPresets.tsx | AudioMixer.tsx top bar | Gamma |
| FaderDbInput.tsx | AudioMixer.tsx volume label | Gamma |
| MediaInfoPanel.tsx | ClipInspector panel | Gamma |
| CodecProbeDetail.tsx | ClipInspector (expandable section) | Gamma |
| ThumbnailStrip.tsx | ProjectPanel clip list | Gamma |
| ProxyToggle.tsx | ProjectPanel toolbar | Gamma |
| RenderIndicator.tsx | TimelineTrackView above ruler | Alpha |
| useAudioPlayback.ts | VideoPreview/playback control | Alpha |

---

*"The render pipeline is a river — each filter is a dam. I built 16 dams, tested each independently, and the river flows."*
