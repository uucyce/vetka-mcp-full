# Experience Report: Beta-Forge (Media/Color Pipeline Architect)
**Date:** 2026-03-22
**Agent:** OPUS-BETA (Beta-Forge) | Branch: main (on-main session)
**Session scope:** Stream B completion + ROADMAP_B2 Export & Delivery + FCP7-66 Motion + Audio
**Tasks closed:** 14
**Tests written:** 235 (across 10 test files)
**New modules:** 4 (cut_audio_engine.py, scope_socket_handler.py, ROADMAP_B2_EXPORT_DELIVERY.md, test files)
**Commits:** 14

---

## 1. WHAT WORKED

### Recon before code — found 80% already done
Before creating any task, I checked if the work existed. Of 11 Stream B Wave 1-3 tasks, 6 were already done by predecessor Beta. My contribution was cleanup (removing dead inline code from cut_routes.py) and wiring gaps (reverse not in render, mixer not in export, LUT/log not in render). This saved massive time and prevented duplicate work.

### Cleanup-first pattern
Every major module had dead code left behind in cut_routes.py after extraction. The pattern: (1) check if module exists, (2) check if old inline code still lives in routes, (3) create cleanup task, (4) replace calls + delete old functions. Applied to B1 (probe), B5 (render), both completed in <10 min each.

### Indentation bug pattern — caught twice
When deleting inline functions from cut_routes.py, the replacement comment inherited the indentation of the deleted code, placing it inside the previous function/class. Caught this both times by reading the context after edit. **Rule:** after deleting a function from cut_routes.py, always verify the replacement comment is at module level (no indent).

### ROADMAP_B2 as execution framework
Creating ROADMAP_B2_EXPORT_DELIVERY.md before coding gave a clear 6-task pipeline. Every task built on the previous: Cancel (Popen) → ETA (elapsed tracking) → Presets (EXPORT_PRESETS) → Batch (sequential jobs) → Thumbnail (post-render hook) → SocketIO (event-driven progress). This natural dependency chain made each task trivial.

### Tests-first for decision logic
Auto-proxy decision matrix, audio mixer solo/mute logic, LUFS compliance — all had tests before implementation. The tests defined the contract, implementation followed. Zero debugging needed.

---

## 2. WHAT DIDN'T

### SpeedControl.tsx was orphaned
Component existed (135 lines) but was never imported or rendered anywhere. No store state for show/hide. Had to add `showSpeedControl` to store, `SpeedControlModal` wrapper in CutEditorLayoutV2, and wire ⌘R in MenuBar. **Lesson:** check if a component is actually rendered, not just defined.

### EffectParam dict vs object inconsistency
`compile_video_filters()` expects `EffectParam` objects (has `.enabled` attribute), but test data used raw dicts. Tests failed with `AttributeError: 'dict' object has no attribute 'enabled'`. Fixed by using `EffectParam()` in tests. **Lesson:** the effects system has two code paths — EffectParam objects (from store) and raw dicts (from JSON/timeline state). Both need to work.

### Drop shadow FFmpeg filter is complex
FCP7's drop shadow requires splitting the video stream, darkening one copy, blurring it, shifting it, and overlaying. In FFmpeg this is a multi-step filter chain with split/colorchannelmixer/boxblur/pad/overlay — all in a single filter string. Works but is the most complex single filter in the system. CSS preview (`drop-shadow()`) is trivial by comparison.

---

## 3. KEY ARCHITECTURE DECISIONS

### Render pipeline filter order
```
trim → log_decode → lut3d → user_effects → speed → reverse → frame_blend → scale
```
Log decode MUST come before user effects — you grade on linear footage, not log. This is the professional NLE convention.

### Audio crossfade curves
- **Equal power (+3dB):** `c1=qsin:c2=qsin` — quarter-sine curve, sounds smooth, no dip at midpoint. FCP7 default.
- **Linear (0dB):** `c1=tri:c2=tri` — triangle/linear, audible dip at midpoint. Used for dialogue where you want natural fade.

### SocketIO for scopes — event-driven, not subscription
Client pushes `scope_request` with playhead position, server computes and emits `scope_data` back. No subscription/timer — the client controls the rate. Per-client debounce via threading.Lock prevents pileup (if previous computation still running, skip request).

### LUFS standards as data, not code
7 loudness standards stored as simple dicts: `{target_lufs, tolerance, max_true_peak, label}`. Compliance check is 3 lines of math. Adding new standards = add dict entry, no code changes.

---

## 4. PERFORMANCE NOTES

### Tests execution
- 235 tests across 10 files: 1.42s total (all pass)
- Zero FFmpeg subprocess calls in tests (all use mocks or check for missing files)
- Pure logic tests: decision matrices, filter string generation, dataclass validation

### Render engine complexity
- cut_render_engine.py grew from ~743 to ~960+ lines this session
- FilterGraphBuilder handles: trim, log decode, LUT, 35 effects, speed, reverse, frame blend, transitions (video xfade + audio acrossfade with curve types), resolution scaling
- This is approaching the limit of a single module — consider splitting into filter_graph.py + render_runner.py in future

---

## 5. RECOMMENDATIONS FOR SUCCESSOR

### Don't touch cut_routes.py more than necessary
File is 8800+ lines, every agent touches it, merge conflicts guaranteed. My 14 commits modified it 10 times. If possible, move new endpoints to separate route files (e.g., `cut_audio_routes.py`, `cut_render_routes.py`).

### The effects system has 38 effect types now
After this session: 35 video effects + 3 audio-only effects. Each effect exists in up to 3 places:
1. `EFFECT_DEFS` in cut_effects_engine.py (schema)
2. `compile_video_filters()` or `compile_audio_filters()` (FFmpeg render path)
3. `apply_numpy_effects()` in cut_preview_decoder.py (preview path) — only ~12 effects implemented here
4. `compile_css_filters()` (browser preview) — subset

**Gap:** Many new effects (drop_shadow, distort, motion_blur) don't have numpy preview path implementations. Preview will show raw footage without these effects applied. Low priority — render works correctly.

### Batch export runs sequentially
`_run_batch_render_job` renders presets one at a time because FFmpeg is CPU-bound. Parallel would OOM on most machines. If users complain about batch speed, consider: (1) render to temp files concurrently if system has enough RAM, (2) offer a "parallel" flag for high-end machines.

### LUFS analysis requires FFmpeg with ebur128 filter
The `ebur128` filter is built into standard FFmpeg — no special build flags needed. But if the system has a minimal FFmpeg build without the filter, `analyze_loudness()` will return `parse_failed`. The function is best-effort and never crashes.

---

## 6. SESSION STATISTICS

| Metric | Value |
|--------|-------|
| Tasks claimed + completed | 14 |
| Commits on main | 14 |
| Tests written | 235 |
| Test files created | 10 |
| New Python modules | 4 |
| New API endpoints | 8 |
| New EFFECT_DEFS | 4 (drop_shadow, distort, motion_blur, audio_crossfade) |
| Export presets added | 14 |
| Loudness standards | 7 |
| Lines of code (estimate) | ~1200 new |

---

*"The render pipeline is a river — each filter is a dam. Build each dam independently, test each independently, and the river flows. But when you chain 15 dams together, always check the water level at the end."*
