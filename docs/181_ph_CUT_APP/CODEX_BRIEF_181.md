# Codex Brief: VETKA CUT Phase 181 — Parallel Tasks

**Date:** 2026-03-14
**Assigned to:** Codex
**Architecture doc:** `docs/181_ph_CUT_APP/PREMIERE_LAYOUT_ARCHITECTURE.md`
**Constitution:** `docs/besedii_google_drive_docs/PULSE-JEPA/VETKA_CUT_Interface_Architecture_v1 (1).docx`

---

## Context

VETKA CUT is an NLE (video editor) built with React + TypeScript frontend and Python FastAPI backend. The interface follows Premiere Pro conventions — free windows, not fixed zones. Import on the left, output on the right.

Key files:
- Layout: `client/src/components/cut/CutEditorLayoutV2.tsx`
- Panel shell: `client/src/components/cut/PanelShell.tsx`
- Panel grid: `client/src/components/cut/PanelGrid.tsx`
- Layout store: `client/src/store/usePanelLayoutStore.ts`
- Editor store: `client/src/store/useCutEditorStore.ts`
- Video preview: `client/src/components/cut/VideoPreview.tsx`
- Backend routes: `src/api/routes/cut_routes.py`
- Project store: `src/services/cut_project_store.py`

---

## Task C-181.4: Codec & Resolution Support
**ID:** `tb_1773521348_5`
**Priority:** P2

Ensure all production codecs work in VETKA CUT:
- H.264, H.265, ProRes, DNxHD, RED R3D, BRAW
- MOV, MP4, MXF, AVI, MKV containers
- Audio: WAV, AIFF, MP3, AAC, FLAC, M4A
- SD through 8K, all standard frame rates

**Where to work:**
- `src/services/cut_project_store.py` — file classification, ffprobe metadata extraction
- `client/src/components/cut/VideoPreview.tsx` — HTML5 video playback + proxy fallback
- `src/api/routes/cut_routes.py` — bootstrap pipeline asset scanning

**Test with:** Berlin footage at `/Users/danilagulin/work/teletape_temp/berlin` (GH5 MOV files)

---

## Task C-181.5: Window Control Polish
**ID:** `tb_1773521356_6`
**Priority:** P3

Detailed per-panel window management:
- PanelShell header: 20px compact, monochrome SVG icons (§11)
- Buttons: tab, detach, fullscreen, minimize, close
- Resize handles on all edges
- Track height: pinch-to-zoom or Shift+drag (NOT toggle sliders)
- Mute/Solo: single button click (NOT ratchet toggle)
- Minimum padding — squeeze all air out
- Timeline default ~35% screen height
- Dynamic window titles ("Source: GH5_0001.MOV")

**Where to work:**
- `client/src/components/cut/PanelShell.tsx`
- `client/src/components/cut/PanelGrid.tsx`
- `client/src/components/cut/TimelineTrackView.tsx`
- `client/src/components/cut/TransportBar.tsx`

---

## Task C-181.6: Export Mode
**ID:** `tb_1773521363_7`
**Priority:** P3

Export pipeline:
- Premiere Pro XML (FCP XML / xmeml v4) — use existing `adobe-xml-converter` skill
- OpenTimelineIO (.otio)
- EDL
- Direct render: H.264/H.265/ProRes presets
- Social cross-posting: YouTube (chapters), Instagram (9:16), TikTok, Telegram, VK, Twitter

**Where to work:**
- New: `src/services/cut_export.py`
- New: `client/src/components/cut/ExportDialog.tsx`
- Backend route: add to `src/api/routes/cut_routes.py`

---

## Task C-181.7: VETKA Lab Player Integration
**ID:** `tb_1773521369_8`
**Priority:** P3

Player + markers + comments:
- Export markers as SRT (with metadata in curly braces)
- Import SRT markers back into timeline
- Timecoded comment system
- Shareable review links
- Viewer favorites → PULSE feedback (§0.3 principle #6)

**Where to work:**
- New: `src/services/cut_srt_bridge.py` (may already exist from phase 179)
- `client/src/components/cut/TimelineTrackView.tsx` — marker display
- `src/api/routes/cut_routes.py` — SRT export/import endpoints

---

## Rules
1. Follow Premiere Pro terminology (Project, Bin, Clip, Source Monitor, Program Monitor)
2. NO standard UI library buttons — monochrome SVG only (§11)
3. No fixed layout zones — free windows everywhere
4. Test with `python -m pytest tests/ -v`
5. Complete task → auto git commit → auto digest update
6. Architecture doc is the source of truth
