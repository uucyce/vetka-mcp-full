# Phase 172: CUT Backend Backbone
**Created:** 2026-03-13
**Status:** ready-for-execution
**Owner:** Opus
**Predecessor:** Phase 170 (sync pipeline, timeline state, contracts)
**Parallel:** Phase 171 (Codex — shell UX, sync badges, cue promotion)

## Vision
Phase 170 built the CUT state machine — timeline ops, sync pipeline, contracts, persistence. But the backend has critical gaps that block real editing: no media serving, stub-quality audio analysis, missing export routes, no scene detection. Phase 172 closes these gaps so CUT becomes a functional editing backend, not just a JSON engine.

## Priority: What blocks what

```
Media Proxy ──→ Player works ──→ Real editing possible
     │
Export Routes ──→ Work leaves CUT ──→ Premiere/FCP import
     │
FFmpeg Waveform ──→ Accurate timeline ──→ Visual editing
     │
Audio Sync Upgrade ──→ Professional sync ──→ PluralEyes replacement
     │
Scene Assembly ──→ Auto scene structure ──→ Smart storyboard
```

## Workstreams

### W1: Media Proxy (CRITICAL — unblocks player)
Serve media files from sandbox to the browser with range-request support.

| Task | ID | Complexity | Description |
|------|----|------------|-------------|
| W1.1 | 172.1 | medium | `GET /api/cut/media-proxy` — path validation, MIME detection, CORS headers |
| W1.2 | 172.2 | medium | Range-request support (HTTP 206) for large video files |
| W1.3 | 172.3 | small | Security: validate path is within sandbox_root, no path traversal |
| W1.4 | 172.4 | small | Tests: serve mp4/wav/m4a, range requests, path traversal rejection |

### W2: Export Endpoints
Wire existing artifact_routes export functions into CUT routes.

| Task | ID | Complexity | Description |
|------|----|------------|-------------|
| W2.1 | 172.5 | medium | `POST /api/cut/export/premiere-xml` — load timeline, generate Premiere XML |
| W2.2 | 172.6 | medium | `POST /api/cut/export/fcpxml` — load timeline, generate FCPXML |
| W2.3 | 172.7 | small | `POST /api/cut/export/otio` — OpenTimelineIO export |
| W2.4 | 172.8 | small | Export contract: `cut_export_result_v1` with format, path, clip count |
| W2.5 | 172.9 | small | Tests: export round-trip, verify XML structure, marker inclusion |

### W3: FFmpeg Waveform (replace byte-scanning stub)
Real audio analysis for accurate waveform display.

| Task | ID | Complexity | Description |
|------|----|------------|-------------|
| W3.1 | 172.10 | large | FFmpeg subprocess: extract PCM → compute RMS bins per N ms |
| W3.2 | 172.11 | small | Fallback: keep current byte-scanning when FFmpeg unavailable |
| W3.3 | 172.12 | small | Waveform resolution config: bins_per_second, channel selection |
| W3.4 | 172.13 | small | Tests: compare FFmpeg waveform vs stub on Berlin fixture |

### W4: Audio Sync Upgrade (full-file analysis)
Replace 8KB signal-proxy with proper audio fingerprinting.

| Task | ID | Complexity | Description |
|------|----|------------|-------------|
| W4.1 | 172.14 | large | FFmpeg PCM extraction → full waveform correlation |
| W4.2 | 172.15 | medium | Multi-pass sync: coarse (downsampled) → fine (full-rate) refinement |
| W4.3 | 172.16 | small | Confidence scoring based on correlation peak sharpness |
| W4.4 | 172.17 | medium | Batch sync: align N candidates against 1 reference in parallel |
| W4.5 | 172.18 | small | Tests: sync accuracy on Berlin multi-cam fixture |

### W5: Scene Assembly Worker
Real scene detection from media analysis.

| Task | ID | Complexity | Description |
|------|----|------------|-------------|
| W5.1 | 172.19 | medium | Thumbnail-based scene boundary detection (histogram diff) |
| W5.2 | 172.20 | medium | Group clips into scenes by temporal proximity + visual similarity |
| W5.3 | 172.21 | small | Scene graph auto-generation from detected boundaries |
| W5.4 | 172.22 | small | Tests: scene detection on Berlin footage fixture |

## Implementation Order

### Sprint 1: Player unblocked (W1 + W2)
- Media proxy with range-requests → player loads video
- Export routes → work can leave CUT
- **Outcome:** CUT becomes usable for basic clip organization + export

### Sprint 2: Audio quality (W3 + W4)
- Real waveforms → accurate timeline display
- Full-file sync → professional-grade alignment
- **Outcome:** CUT sync pipeline approaches PluralEyes quality

### Sprint 3: Scene intelligence (W5)
- Auto scene detection → smart storyboard
- Scene graph from real analysis, not just file listing
- **Outcome:** CUT understands content structure

## Technical Notes

### FFmpeg dependency
W3 and W4 require FFmpeg. Detection strategy:
```python
import shutil
FFMPEG = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
HAS_FFMPEG = FFMPEG is not None
```
When FFmpeg unavailable → graceful fallback to current byte-scanning.

### Range-request pattern (W1.2)
```python
from starlette.responses import FileResponse, Response
# Parse Range header → seek → return 206 with Content-Range
```

### Berlin fixture for testing
Source: `/Users/danilagulin/work/teletape_temp/berlin/`
- Multi-camera footage (cam_a, cam_b)
- Punch music track (m4a)
- Mixed media types (video, stills, generated)

## Success Criteria
1. Video plays in CUT shell from sandbox media
2. Timeline exports to Premiere XML with clips + markers
3. Waveform display matches actual audio (not byte approximation)
4. Audio sync detects offsets within ±1 frame accuracy on Berlin footage
5. Scene assembly creates meaningful scene boundaries automatically

## Dependencies
- Phase 171 (Codex) runs in parallel — shell UX on existing JSON data
- Phase 172 provides the backend foundation that makes 171's UI real
- No blocking dependency between 171 and 172 — both can start immediately
