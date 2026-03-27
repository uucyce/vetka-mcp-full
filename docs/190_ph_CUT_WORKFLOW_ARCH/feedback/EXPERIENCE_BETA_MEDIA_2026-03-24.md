# Experience Report: Beta (Media/Color Pipeline Architect)
**Date:** 2026-03-24
**Agent:** OPUS-BETA | Branch: claude/cut-media
**Session scope:** Bootstrap fix cascade + ROADMAP_B completion + real media verification
**Tasks closed:** 20+ (B40-B60)
**Commits:** 18+
**Tests written:** 78+ (across 6 test files)

---

## 1. DEBRIEF (6 Questions)

### Q1: Most harmful pattern — what slowed you down?
Bootstrap fix cascade: B54→B56→B58→B59→B60, five commits for one problem. Each fix caught an edge case of the previous instead of reading the entire flow once and fixing all failure points together. Root cause: never tested with a real CutBootstrapRequest against real files until B60.

### Q2: What worked well — what to keep?
Task board streaming: claim→build→complete in 5-10 min per task. Sub-router decomposition (B41) paid off immediately — all subsequent route additions were clean, zero merge conflicts across 18 commits. Also: EFFECT_APPLY_MAP export pattern (one map shared between EffectsPanel drag and TimelineTrackView drop).

### Q3: Repeated mistake — what did you do wrong more than once?
Not testing with real files early. Code passed unit tests but failed on production data. `body.timeline_id` AttributeError survived through 4 commits because tests mocked bootstrap rather than calling with an actual CutBootstrapRequest. Same pattern: `os.scandir` was flat (B56) — would have been caught instantly by testing with berlin/source_gh5/ subdirectory.

### Q4: Off-topic idea
`os.walk` in timeline builder scans ALL subdirectories including `video_gen/` (160 AI clips), `img_gen_sorted/`, etc. Need a `.cutignore` file (like .gitignore) to exclude directories from timeline scan. Otherwise bootstrap of berlin project creates 168 clips instead of 8 GH5 files. Implementation: read `.cutignore` from source_root, prune `_dirs` in os.walk.

### Q5: What would you do differently?
Start with `curl POST /cut/bootstrap` against real sandbox BEFORE writing any code. Real-request diagnosis would have found AttributeError in 30 seconds instead of 5 fix iterations. Rule: **always reproduce the bug with a real request before writing the fix.**

### Q6: Anti-pattern in communication/process
`cut_routes.py` is still 8000+ lines with inline helpers for timeline building, scene graph, music sync. B41 extracted media/export/render (28 routes), but core bootstrap/timeline/workers remain monolithic. Every bootstrap fix is surgery on an 8000-line file. Next decomposition needed: `cut_routes_bootstrap.py`, `cut_routes_timeline.py`, `cut_routes_workers.py`.

---

## 2. SESSION STATISTICS

| Metric | Value |
|--------|-------|
| Markers | B40-B60 (21 markers) |
| Commits | 18+ on claude/cut-media |
| New services | 4 (audio_scope_socket_handler, cut_conform, cut_multicam_sync, 3 sub-routers) |
| New endpoints | 20+ |
| New components | 3 (WaveformMinimap, SequenceSettingsDialog, ThumbnailStrip wiring) |
| Tests | 78+ across 6 test files |
| Lines removed | 1109 from cut_routes.py (B41 decomposition) |
| Merge conflicts | 0 |

## 3. KEY ACHIEVEMENTS

### ROADMAP_B Complete
All 16 roadmap items (B1-B16) verified done. No gaps remaining.

### Bootstrap Chain Fixed (B54-B60)
5-fix cascade that ensures clips appear on timeline regardless of project state:
- B54: Bootstrap creates timeline immediately
- B55: FPS auto-detected from first clip
- B56: Recursive os.walk for subdirs
- B58: Re-bootstrap rebuilds empty timelines
- B59: GET /project-state auto-creates if missing
- B60: AttributeError fix (timeline_id field)

### Real Media Verified
8 GH5 MOV files (1080p 50fps, PCM audio):
- Bootstrap: 8 clips, fps=50.0
- Thumbnail: 13KB JPEG <150ms
- Waveform: 64 bins, non-degraded
- Render: 5s clip → 31MB H.264 MP4 in 4.6s
- Audio: RMS L=0.087 R=0.086

### Multicam Sync Engine (B48)
PluralEyes replacement: audio cross-correlation (two-pass coarse→fine), timecode sync, marker sync. Core reason VETKA CUT exists.

### Sub-Router Architecture (B41)
media_router (28 routes), export_router (8), render_router (6) — total 42 routes extracted.

## 4. RECOMMENDATIONS FOR SUCCESSOR

1. **Test with real files FIRST** — `/Users/danilagulin/work/teletape_temp/berlin/source_gh5/` has 8 GH5 MOVs. Always reproduce bugs with real requests before coding fixes.

2. **Decompose cut_routes.py further** — still 8000+ lines. Extract: `cut_routes_bootstrap.py` (~500 lines), `cut_routes_timeline.py` (~800 lines), `cut_routes_workers.py` (~1500 lines).

3. **Add .cutignore** — timeline builder's os.walk scans everything including AI-generated video. Need ignore patterns.

4. **Video streaming endpoint** — `/cut/stream?source_path=...` for browser-native playback. Currently only thumbnail extraction, no streaming. Use FFmpeg pipe to WebM/MP4 fragment for browser `<video>` element.

5. **Waveform pre-generation at bootstrap** — currently waveforms are on-demand. Auto-trigger `/worker/scan-matrix-async` after bootstrap to pre-generate for all clips.

---

*"Five fixes for one bug taught me more than five features. Test with real data first."*
