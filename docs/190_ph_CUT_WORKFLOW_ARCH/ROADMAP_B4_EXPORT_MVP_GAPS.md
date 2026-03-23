# ROADMAP B4: Export MVP Gap Closure
**Agent:** Beta (Media Pipeline)
**Branch:** claude/cut-media
**Date:** 2026-03-23

## Status: 90% done — closing 4 gaps for usable export

### Already Working (predecessor Beta-Forge)
- POST /cut/render/master — full FFmpeg pipeline
- RenderPlan → FilterGraphBuilder → filter_complex
- 14 EXPORT_PRESETS (YouTube/Instagram/TikTok/ProRes/DNxHR/AV1)
- Transitions (crossfade, dip-to-black) via filter_complex
- Speed/reverse, color grading (log+LUT), audio stems
- Job progress polling + cancel backend + ETA + thumbnail
- ExportDialog.tsx — 3 tabs (Master/Editorial/Publish)
- Editorial export (Premiere XML, FCPXML, EDL, OTIO)

### Gaps to Close

| # | Task | Priority | Complexity | What |
|---|------|----------|------------|------|
| B4.1 | Cancel button in ExportDialog | P0 | Low | Add cancel button during render, call POST /job/{id}/cancel |
| B4.2 | SocketIO render progress | P1 | Low | Wire ExportDialog to listen for render_progress events (backend already emits) |
| B4.3 | Preset-driven export | P2 | Low | Dropdown of EXPORT_PRESETS in Master tab, auto-fills codec/res/quality |
| B4.4 | Open in Finder on complete | P2 | Low | Tauri shell.open or window.open for output path |

### Execution Order
1. B4.1 Cancel button (P0, blocks usability)
2. B4.3 Preset dropdown (P2, replaces manual codec/res selection)
3. B4.2 SocketIO progress (P1, smoother UX)
4. B4.4 Open in Finder (P2, nice-to-have)
