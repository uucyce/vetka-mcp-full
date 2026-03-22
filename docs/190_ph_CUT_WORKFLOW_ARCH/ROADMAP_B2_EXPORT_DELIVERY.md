# ROADMAP B2: EXPORT & DELIVERY — Sub-Roadmap

**Parent:** `ROADMAP_B_MEDIA_DETAIL.md` → Wave 5
**Agent:** Beta (Media/Color Pipeline Architect)
**Created:** 2026-03-22
**Deps:** B5 (render engine), B6 (ExportDialog), B9 (effects) — all done

---

## Overview

Export fundamentals work: ExportDialog → POST /render/master → FFmpeg → file.
But the export experience is raw — no cancel, no ETA, no batch, no thumbnails.
This roadmap adds delivery-grade polish that makes CUT usable for production.

## Current State

| What | Status |
|------|--------|
| ExportDialog UI (3 tabs) | done (671 lines) |
| Render engine (filter_complex) | done (800+ lines) |
| Progress polling (500ms HTTP) | done (ExportDialog.tsx) |
| Cancel endpoint | exists (`POST /job/{id}/cancel`) — sets flag only |
| Cancel in UI | MISSING — no button, flag not checked by FFmpeg |
| ETA calculation | MISSING |
| Batch export | MISSING |
| Thumbnail at export | MISSING |
| SocketIO progress (replace polling) | MISSING |

## Task Breakdown

### B2.1: Render Cancel — kill FFmpeg subprocess on cancel (P0)
- **Files:** `cut_render_engine.py`, `cut_routes.py`
- **What:** `_run_master_render_job` currently ignores `cancel_requested` flag.
  Use `subprocess.Popen` instead of `subprocess.run` so we can `.kill()`.
  Check `cancel_requested` in progress callback loop.
  Add Cancel button to ExportDialog UI (calls POST /job/{id}/cancel).
- **Acceptance:**
  - Cancel button visible during render
  - Clicking cancel kills FFmpeg within 1s
  - Partial output file cleaned up
  - UI shows "Cancelled" state

### B2.2: ETA Calculation — elapsed + estimated remaining (P1)
- **Files:** `cut_render_engine.py`, `cut_routes.py`
- **What:** Track render start time. Compute ETA from progress:
  `eta_sec = elapsed * (1.0 - progress) / progress`.
  Include in job status response. Display in ExportDialog.
- **Acceptance:**
  - Job response includes `elapsed_sec` and `eta_sec`
  - ExportDialog shows "~2:30 remaining"

### B2.3: Export Presets — named render configurations (P1)
- **Files:** `cut_render_engine.py` (SOCIAL_PRESETS already exists)
- **What:** Extend SOCIAL_PRESETS with production presets:
  - `prores_master` → ProRes 422HQ, source resolution, 48kHz audio
  - `archive_4444` → ProRes 4444, 4K, 96kHz
  - `review_h264` → H.264 720p, low bitrate, fast encode
  - `instagram_story` → H.264, 1080x1920 (9:16), 15s max
  - `tiktok_vertical` → H.264, 1080x1920, 60s max
  Frontend: preset selector dropdown in ExportDialog.
- **Acceptance:**
  - 5+ new presets beyond current 4
  - Preset auto-fills codec/resolution/fps/quality
  - ExportDialog shows preset dropdown with labels

### B2.4: Batch Export — multiple formats in one job (P2)
- **Files:** `cut_routes.py`, `cut_render_engine.py`
- **What:** POST /render/batch endpoint that takes list of render configs.
  Creates parallel or sequential FFmpeg jobs.
  Returns batch job_id with per-format progress.
- **Acceptance:**
  - Can export ProRes master + YouTube H.264 + Instagram in one action
  - Progress tracked per sub-job
  - UI shows batch progress grid

### B2.5: Thumbnail Generation — poster frame at export (P2)
- **Files:** `cut_render_engine.py`
- **What:** After render, extract thumbnail (JPEG) at first frame or middle frame.
  Store alongside output file: `{output}_thumb.jpg`.
  Return thumbnail_path in render result.
- **Acceptance:**
  - Thumbnail generated automatically on render complete
  - 720p JPEG, <200KB
  - Path returned in render result

### B2.6: SocketIO Render Progress — replace HTTP polling (P3)
- **Files:** `cut_routes.py`, ExportDialog.tsx
- **What:** Emit progress via SocketIO (`sio.emit("render_progress", {job_id, progress, eta})`)
  instead of 500ms HTTP polling. Reduces latency and server load.
  Frontend: connect to SocketIO room for job_id.
- **Acceptance:**
  - Progress updates via SocketIO at 200ms interval
  - ExportDialog subscribes to room
  - Fallback to HTTP polling if SocketIO unavailable

## Execution Order

```
B2.1 (Cancel) ← P0, immediate value
  ↓
B2.2 (ETA) ← builds on cancel infrastructure (Popen)
  ↓
B2.3 (Presets) ← independent, quick win
  ↓
B2.4 (Batch) ← depends on presets + cancel
  ↓
B2.5 (Thumbnail) ← independent, post-render hook
  ↓
B2.6 (SocketIO) ← architectural, lowest priority
```

## Key Insight

B2.1 (Cancel) requires switching from `subprocess.run()` to `subprocess.Popen()`
in `render_timeline()`. This is the hardest change — everything else builds on it.
Once we have Popen, cancel + ETA + progress streaming all become trivial.
