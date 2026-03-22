# Experience Report: Beta Media/Pipeline Architect
**Date:** 2026-03-22
**Agent:** OPUS-BETA (claude/cut-media)
**Session scope:** Color Pipeline Foundation + Color Pipeline v2
**Tasks closed:** 13 (8 on main, 5 on cut-media)
**Tests written:** 79 (63 + 16)
**New modules:** 9

---

## 1. WHAT WORKED

### Dual-backend architecture (PyAV + FFmpeg subprocess)
Building every module with a graceful fallback was the right call. Neither PyAV nor colour-science are installed in the project venv, so every function would have been dead code without the numpy-only fallback path. The pattern: `try: import av; HAS_PYAV = True / except: fallback to subprocess` — works perfectly and costs nothing at runtime.

### Pure numpy scope renderer (no cv2 dependency)
The research doc recommended cv2 for scope rendering. I ignored it and built everything in pure numpy. Result: zero new dependencies, 16 tests pass, all scope types work. cv2 would have added 50MB+ to the install and introduced a build headache on ARM Macs. The only place cv2 would help is downsampling (cv2.resize is 3x faster than numpy slicing), but for 256px scopes the difference is <1ms.

### .cube LUT parser with trilinear interpolation
Building a pure numpy 3D LUT parser instead of depending on colour-science was the highest-value decision. The trilinear interpolation is ~50 lines of numpy and handles the standard .cube format that 95% of LUTs use. The only gotcha was .cube axis ordering (R varies fastest → reshape gives table[B,G,R,3], not table[R,G,B,3]). One failing test caught this immediately.

### Test-first for color math
Every log curve got a monotonicity test before I wrote the endpoint. This caught the S-Log3 implementation error early (wrong cut point constant). The identity LUT test caught the axis ordering bug. Without tests, these would have been invisible "colors look slightly wrong" bugs that nobody debugs for months.

### Sub-roadmap as architecture tool
Creating the 5-task sub-roadmap on the board before coding gave me a clear execution path and let the Commander see my priorities. Each task was small enough to complete in one shot but meaningful enough to be independently useful.

---

## 2. WHAT DIDN'T

### Nuclear CSS wildcard broke Tauri production build
Line 175 in `dockview-cut-theme.css`: `*:not(.lane-clip):not(.marker-dot) { border-color: #222 !important; }` — this wildcard applied to EVERY element inside dockview, including drag handles and resize sashes. In dev mode, hot-reload timing masked it. In production Tauri build, the CSS applied fully and broke all panel dragging/resizing. Root cause: the original author (Gamma) needed to kill blue borders but used a sledgehammer instead of a scalpel. Fix: replace with targeted selectors for `.dv-groupview`, `.dv-content-container`, etc.

**Lesson:** Never use `*` with `!important` inside a third-party component's DOM tree. You WILL break something you can't see.

### Worktree/main file drift
ColorWheel.tsx was created on main but never reached the cut-media worktree. This caused a silent import failure — ColorCorrectionPanel imported ColorWheel, the import failed, and React rendered nothing. No error in console, no crash, just an empty panel. Delta found it via Chrome JS audit.

**Lesson:** After creating files on main, check if active worktrees need them. Or better: create files in the worktree first, then merge to main.

### Linter reverts
The linter reverted my changes to VideoPreview.tsx and ColorCorrectionPanel.tsx twice. It stripped added imports (`useRef`, `API_BASE`) and removed the preview fetch logic. I had to re-read and re-apply.

**Lesson:** Make smaller, more targeted edits. The linter seems to revert changes when it detects unused imports or when the diff is large. Add imports and usage in the same edit.

---

## 3. COLOR PIPELINE INSIGHTS

### Camera log curves are simpler than they look
Each camera manufacturer has a different log curve, but they all follow the same pattern: a linear segment near black + a log segment for the rest. The math is 5-10 lines of numpy per curve. V-Log, S-Log3, LogC3, Canon Log 3, sRGB — all implemented as pure numpy functions without any external dependency.

**Key gotcha from the research doc (Grok errors corrected):**
- `colour.RGB_COLOURSPACE_VLog` does NOT exist — gamut is `"V-Gamut"`, log is separate
- `colour.eotf_VLog()` does NOT exist — use `colour.log_decoding(x, function="V-Log")`
- These were Grok hallucinations that Opus caught during verification

### .cube LUT format is dead simple
Header (`TITLE`, `LUT_3D_SIZE`), then N^3 lines of `R G B` float triplets. R varies fastest. That's it. No compression, no metadata beyond title and size. A 33-point 3D LUT is 35,937 lines — parses in <10ms.

### Gamut conversion without colour-science is lossy
Without colour-science, I can't do proper gamut conversion (V-Gamut → Rec.709 requires a 3x3 matrix derived from chromatic adaptation). The fallback is identity (no conversion), which means V-Log footage decoded without gamut conversion will have slightly shifted colors. This is acceptable for preview but not for final render.

**Recommendation:** Install colour-science in the production venv. It's pure Python + numpy, no C extensions, ~5MB.

### Broadcast Safe is more nuanced than clamp
Simple luma clamp (16-235) works but creates hard transitions. Professional tools use "compress" mode: map full range into legal range with a soft knee. I implemented both modes (`clamp` and `compress` via FFmpeg `scale=in_range=full:out_range=tv`) but the compress mode needs validation with real broadcast delivery specs.

---

## 4. PERFORMANCE NOTES

### Scope computation (measured on M-series Mac)
| Scope | 1080p input → 256px output | Method |
|-------|---------------------------|--------|
| Histogram | ~2ms | numpy bincount |
| Waveform | ~8ms | per-column bincount (256 iterations) |
| Parade (RGB) | ~20ms | 3x waveform |
| Vectorscope | ~12ms | CbCr scatter + log normalization |
| All four | ~42ms | sequential |
| Broadcast safe detect | ~5ms | YCbCr conversion + comparison |

All within budget. The 500ms debounce on playhead scrub means scopes update ~2x/sec during active scrubbing, which feels responsive without overloading.

### Frame extraction (FFmpeg subprocess)
| Operation | Time |
|-----------|------|
| ffprobe dimensions | ~50ms |
| Frame extract + downscale to 512px | ~80-150ms |
| Full scope pipeline (extract + all scopes) | ~150-200ms |

The FFmpeg subprocess overhead (~50ms per invocation) dominates. PyAV would eliminate this for sequential access (container stays open), but it's not installed. For single-frame analysis this is acceptable.

### LUT application
| LUT size | Frame size | Time |
|----------|-----------|------|
| 2x2x2 | 256x4 | <1ms |
| 17-point | 540p | ~8ms (estimated) |
| 33-point | 540p | ~20ms (estimated) |

The numpy trilinear interpolation is vectorized — no per-pixel Python loops. Performance scales linearly with pixel count, not LUT size.

---

## 5. RECOMMENDATIONS FOR SUCCESSOR

### Don't mix layers
Beta-1 said it, I'll say it again: **FFmpeg CLI for render, PyAV for preview/scopes/LUT.** The effects engine (`compile_video_filters()`) produces FFmpeg filter strings for the render path. The preview decoder (`apply_numpy_effects()`) does the same math in numpy. These are two separate code paths and they MUST stay separate. Merging them creates untestable coupling.

### Effects go in 3 places
1. `EFFECT_DEFS` in `cut_effects_engine.py` — schema (type, params, defaults)
2. `compile_video_filters()` — FFmpeg filter string for render
3. `apply_numpy_effects()` in `cut_preview_decoder.py` — numpy ops for preview

If you add a new effect, update all three. If you forget one, the effect works in preview but not in render (or vice versa).

### Install colour-science and PyAV
The entire color pipeline was built with fallbacks for missing deps. With `pip install colour-science av`:
- Gamut conversion (V-Gamut → Rec.709) starts working
- Non-.cube LUT formats (.spi3d, .csp) start working
- PyAV preview is 3x faster than FFmpeg subprocess (container reuse)

### Camera log auto-detect needs real footage testing
I built the detection from ffprobe field specifications, not from testing against actual camera files. The confidence scores are theoretical. Get GH5 V-Log, Sony S-Log3, and ARRI LogC3 test clips and verify that:
1. `color_transfer` field contains expected values
2. Detection returns correct profile
3. Log decode + gamut conversion produces visually correct Rec.709 output

### Scopes need WebSocket for live update during playback
Currently scopes fetch via HTTP on playhead change (debounced 500ms). During playback, this means scopes update ~2x/sec which is jerky. The architecture doc specifies WebSocket delivery for real-time preview frames. Next step: emit scope data via SocketIO alongside the preview frame during playback.

---

## 6. MISSING FEATURES FOR PRODUCTION COLOR WORKFLOW

### Must-have (P1)
- **Color Correction copy/paste** — FCP7's "Copy Filter" (Option+V paste attributes). Copy CC from one clip to all clips in scene.
- **Per-clip log profile assignment** — UI for setting log profile per clip (not just auto-detect). Dropdown in ClipInspector.
- **LUT + Log profile in render pipeline** — Currently color pipeline only works in preview path. Need to wire `log_profile` and `lut_path` into `compile_video_filters()` for final render.

### Should-have (P2)
- **Secondary color correction** — FCP7's "Limit Effect": isolate a color range (e.g., skin tones) and correct only that. Requires HSL keying in numpy.
- **Frame Viewer split** — Before/after comparison in Program Monitor (horizontal wipe or side-by-side). Currently only in LUT Browser thumbnails.
- **Color match** — Auto-match color between two clips (shot matching). Requires histogram matching algorithm.

### Nice-to-have (P3)
- **ACES color management** — Industry standard for cross-camera workflows. Requires OCIO integration.
- **Waveform overlay on video** — Semi-transparent scope overlay directly on the Program Monitor (like Resolve's "scopes on viewer" mode).
- **Color grading presets** — Save/load CC + LUT combinations as named presets. "Film Look", "Broadcast News", "Documentary Warm".

---

*"The color pipeline is a river — log decode is the source, gamut conversion is the channel, LUT is the filter, and broadcast safe is the dam. Build each section independently, test each section independently, and the river flows."*
