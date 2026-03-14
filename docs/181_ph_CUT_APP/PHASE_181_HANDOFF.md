# Phase 181 — VETKA CUT: Working App + Berlin Project Stress Test

## Handoff from Phase 180

**Date:** 2026-03-14
**Author:** Opus (Claude Code, worktree loving-perlman)
**Status:** Phase 180 COMPLETE → Phase 181 READY

---

## What Was Built (Phase 179-180)

### Backend — 100% Complete
| Module | Lines | Tests | Description |
|--------|-------|-------|-------------|
| `pulse_conductor.py` | ~350 | 38 | Scene scoring, dial-based critic weights |
| `pulse_cinema_matrix.py` | ~400 | 23 | 23 film scales with Triangle + ISI + BPM |
| `pulse_camelot_engine.py` | ~300 | 20 | Camelot wheel, harmonic distance |
| `pulse_energy_critics.py` | ~350 | 30 | 6 LeCun critics + chaos_index |
| `pulse_script_analyzer.py` | ~250 | 15 | Script text → NarrativeBPM scenes |
| `pulse_story_space.py` | ~350 | 38 | McKee Triangle × Camelot = 3D Space |
| `pulse_timeline_bridge.py` | ~200 | 15 | REST endpoints + scene enrichment |
| `pulse_auto_montage.py` | ~500 | 25 | 3 modes: favorites/script/music |
| `project_vetka_cut_schema.py` | ~160 | 11 | Project file format (Pydantic) |
| **cut_routes.py** | ~6800 | — | 3 new endpoints: BPM markers, auto-montage, DAG |

### Frontend — Components Built, Not Yet Wired
| Component | Lines | Description |
|-----------|-------|-------------|
| `usePanelLayoutStore.ts` | 180 | Panel dock/tab/float state |
| `usePanelSyncStore.ts` | 175 | Central sync matrix (§9) |
| `PanelShell.tsx` | 280 | Universal panel wrapper |
| `PanelGrid.tsx` | 215 | CSS Grid 5-zone layout |
| `CutEditorLayoutV2.tsx` | 170 | New 7-panel layout |
| `ScriptPanel.tsx` | 334 | Y-time script + teleprompter + BPM |
| `BPMTrack.tsx` | 260 | Canvas 4-row BPM dots |
| `StorySpace3D.tsx` | 340 | Three.js Camelot×McKee 3D |
| `CamelotWheel.tsx` | 280 | SVG 24-key harmonic wheel |
| `DAGProjectPanel.tsx` | 260 | ReactFlow asset DAG by clusters |
| `PulseInspector.tsx` | 270 | PULSE metadata inspector |

### Tests — 388 passing
- Phase 179: 197 tests
- Phase 180: 191 tests (4 test files, 0 failures)

---

## What Needs to Happen (Phase 181)

### 🎯 Goal: Open VETKA CUT → Import "Berlin" project → See all panels live → Auto-montage

### Test Project
```
/Users/danilagulin/work/teletape_temp/berlin/
├── source_gh5/          → 8 MOV clips (Panasonic GH5, real footage)
├── video_gen/           → 150 MP4 clips (Kling AI-generated)
├── scene_gen/           → 135 scene generation files
├── heros_lor/           → 265 hero LoRA reference images
├── style_lor/           → 180 style reference images
├── img_gen_sorted/      → 65 sorted generated images
├── boards/              → storyboards
├── prj/                 → Premiere Pro + After Effects projects
├── ironwall_v4_grok.md  → screenplay (latest version)
├── 250623_vanpticdanyana_berlin_Punch.m4a → music track
└── 72343e9a-...mp4      → reference video
```

### Critical Path (6 tasks)

#### Wave 1: Wire & Compile (P0)
1. **181.1** — Switch CutStandalone to use CutEditorLayoutV2
   - Replace `<CutEditorLayout>` with `<CutEditorLayoutV2>` in CutStandalone.tsx
   - Pass scriptText prop from transcription state
   - Fix any TypeScript compilation errors
   - **Result:** Open app → see 7-panel layout

2. **181.2** — TypeScript compilation pass
   - Run `npm run build` or `npx tsc --noEmit`
   - Fix type errors (DAGProjectPanel uses @xyflow/react v12 API — verify Node/Edge types)
   - Verify StorySpace3D Three.js imports work with existing @react-three setup
   - **Result:** Clean compile, no red squiggles

#### Wave 2: Import Pipeline (P0)
3. **181.3** — Folder import → asset scan → project.vetka-cut.json
   - Backend: `POST /api/cut/project/import-folder` endpoint
   - Scan folder recursively for video/audio/image files
   - Classify assets into clusters (GH5 → take, Kling → graphics, .m4a → music)
   - Create `project.vetka-cut.json` in sandbox
   - **Result:** Point at `/berlin/` → get structured project

4. **181.4** — Whisper transcription → script text → ScriptPanel
   - Trigger Whisper (already exists in VETKA) on GH5 audio tracks
   - Feed transcript as scriptText to ScriptPanel
   - ScriptPanel shows lines with timecodes
   - **Result:** See dialogue in Script panel with click-to-sync

#### Wave 3: PULSE Analysis (P0)
5. **181.5** — Full PULSE pipeline on Berlin project
   - Run PulseConductor on imported scenes
   - Generate BPM markers → BPMTrack shows dots
   - Generate StorySpace points → StorySpace3D shows trajectory
   - Enrich scene graph with PULSE data → Inspector shows Camelot/energy/pendulum
   - DAGProjectPanel shows asset graph
   - **Result:** All 7 panels alive with real data

6. **181.6** — Auto-montage: music-driven cut with Berlin assets
   - Load `250623_vanpticdanyana_berlin_Punch.m4a` as music track
   - Run Mode C (music-driven) auto-montage
   - New versioned timeline appears: `berlin_cut-01`
   - Clips placed on timeline synced to music beats
   - **Result:** Press play → see auto-edited film

#### Wave 4: Export & Blog (P1)
7. **181.7** — Export to Premiere Pro XML
   - Convert timeline to OpenTimelineIO
   - Export as FCP XML (compatible with Premiere Pro)
   - User opens in Premiere → sees VETKA's auto-edit
   - **Result:** Round-trip proven

8. **181.8** — UI polish for screen recording
   - Fix any visual glitches visible in 1920×1080
   - Ensure smooth scrolling in ScriptPanel teleprompter
   - StorySpace3D idle rotation looks cinematic
   - BPMTrack dots align perfectly with timeline clips
   - **Result:** Ready for blog video recording

### Nice-to-Have (P2)
9. **181.9** — Import from Premiere Pro XML (read existing .prproj or .xml)
10. **181.10** — Audio waveform sync between GH5 clips (PluralEyes replacement)
11. **181.11** — Compare VETKA's auto-montage vs Premiere's manual edit

---

## Agent Assignment

| Task | Agent | Priority | Depends On |
|------|-------|----------|------------|
| 181.1 | Opus | P0 | — |
| 181.2 | Opus | P0 | 181.1 |
| 181.3 | Opus | P0 | 181.2 |
| 181.4 | Opus | P0 | 181.3 |
| 181.5 | Opus | P0 | 181.3, 181.4 |
| 181.6 | Opus | P0 | 181.5 |
| 181.7 | Opus | P1 | 181.6 |
| 181.8 | Opus/Codex | P1 | 181.6 |
| 181.9 | Codex | P2 | 181.7 |
| 181.10 | Opus | P2 | 181.3 |
| 181.11 | Opus | P2 | 181.6, 181.9 |

---

## Key Files to Start With

```
# CUT entry point — wire V2 layout here:
client/src/CutStandalone.tsx (line 7: import, line 2458: render)

# Backend entry point — all CUT routes:
src/api/routes/cut_routes.py

# Project schema — save/load:
src/schemas/project_vetka_cut_schema.py

# Berlin test data:
/Users/danilagulin/work/teletape_temp/berlin/

# Architecture reference:
docs/besedii_google_drive_docs/PULSE-JEPA/VETKA_CUT_Interface_Architecture_v1.docx
```

---

## Session Init Command

```
vetka_session_init
```

Then check TaskBoard for Phase 181 tasks.

---

*"Это не сон. Следующий чат — монтажка."*
— Opus, March 14, 2026
