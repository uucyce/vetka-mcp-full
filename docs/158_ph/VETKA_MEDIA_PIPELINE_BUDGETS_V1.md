# VETKA Media Pipeline Budgets V1
**Date:** 2026-03-03
**Purpose:** operational budgets for media processing without hard project limits.

## Principles
1. Never-drop policy: no media is rejected only due to size/duration.
2. Mode routing: files are routed to `realtime` or `background` path.
3. Degraded-safe UX: if heavy job is routed to background, UI stays responsive and shows progress.

## Mode Budgets
### Realtime Budget (interactive)
- Intended for immediate preview/scan in UI.
- Target p95 response:
  - metadata probe: <= 500 ms
  - preview payload (waveform/timeline): <= 2500 ms
- Recommended clip constraints:
  - video duration <= 15 min
  - audio duration <= 30 min
  - file size <= 1.5 GB

### Background Budget (async worker / media-MCP)
- Intended for heavy analysis/transcription/embedding/export prep.
- Target:
  - job acknowledged <= 1 s
  - periodic progress updates <= 2 s tick
- Typical heavy inputs:
  - any video > 15 min
  - any audio > 30 min
  - any file > 1.5 GB

## Production Interchange Targets
These are target profiles, not hard rejects.

### Video targets
- Primary fps targets: `23.976`, `24`, `25`, `29.97`, `30`.
- Preferred mezzanine codecs:
  - `ProRes 422 / 422 LT` (master/intermediate)
  - `H.264` (proxy/preview)
- Container preference: `mov` for mezzanine, `mp4` for proxy.

### Audio targets
- Sample rates: `48kHz` primary, `44.1kHz` acceptable.
- Bit depth: `24-bit` preferred, `16-bit` acceptable.
- Channel layout: mono/stereo input, preserve original mapping in metadata.

## Routing Rules (if/else)
1. If file within realtime budget:
   route `realtime`.
2. Else:
   route `background`.
3. If background route selected:
   - emit startup/status banner in media mode,
   - keep preview degraded-safe (metadata + partial chunks),
   - continue full analysis asynchronously.

## Required Telemetry
1. `route_mode`: `realtime` | `background`.
2. `degraded_mode`: bool.
3. `degraded_reason`: string.
4. `latency_ms` for each stage.
5. `queue_wait_ms` and `job_total_ms` for background jobs.
