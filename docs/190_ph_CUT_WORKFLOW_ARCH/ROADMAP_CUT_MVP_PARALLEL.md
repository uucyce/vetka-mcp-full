# CUT MVP — Parallel Execution Roadmap
# 3 Opus 4.6 Agents × 1M Context

**Date:** 2026-03-20
**Architect-Commander:** Opus (this session)
**Basis:** ROADMAP_CUT_FULL.md v2 + RECON_192 + CUT_UNIFIED_VISION.md + CUT_TARGET_ARCHITECTURE.md
**Goal:** Working NLE application — real editing, real codecs, real export

---

## Root Documents (MANDATORY for every agent)

Every agent MUST read these before starting work:

| Document | Path | Purpose |
|----------|------|---------|
| **CUT Unified Vision** | `docs/190_ph_CUT_WORKFLOW_ARCH/CUT_UNIFIED_VISION.md` | SSOT: panels, functions, hotkeys, contracts |
| **CUT Target Architecture** | `docs/190_ph_CUT_WORKFLOW_ARCH/CUT_TARGET_ARCHITECTURE.md` | Deep architecture: DAG, routing, BPM, markers |
| **CUT Data Model** | `docs/190_ph_CUT_WORKFLOW_ARCH/CUT_DATA_MODEL.md` | Node/Edge type schemas |
| **CUT Full Roadmap** | `docs/190_ph_CUT_WORKFLOW_ARCH/ROADMAP_CUT_FULL.md` | Canonical task-level roadmap (Waves 0-10) |
| **RECON 192** | `docs/190_ph_CUT_WORKFLOW_ARCH/RECON_192_ARCH_VS_CODE_2026-03-18.md` | Code vs architecture gap audit |
| **This Roadmap** | `docs/190_ph_CUT_WORKFLOW_ARCH/ROADMAP_CUT_MVP_PARALLEL.md` | Parallel execution plan + protocol |
| **PULSE McKee** | `docs/besedii_google_drive_docs/PULSE-JEPA/PULSE_McKee_Triangle_Calibration_v0.2.md` | PULSE intelligence calibration |
| **Hotkey Reference** | `docs/185_ph_CUT_POLISH/hotcuts/premiere.md` | Premiere Pro keyboard shortcuts |
| **CUT Hotkey Architecture** | `docs/190_ph_CUT_WORKFLOW_ARCH/CUT_HOTKEY_ARCHITECTURE.md` | 115 actions, presets system |
| **Phase 198 Multi-Timeline** | `docs/198_ph_CUT_MULTI_TIMELINE/` | FCP7 reference + Moment Doctrine |

---

## Current State (as of 2026-03-20)

### Done
- PULSE pipeline: conductor, critics, camelot, auto-montage (Phase 179) — 100%
- Layout V2 + 22 components + 3 Zustand stores — working
- Backend: 70+ endpoints, undo/redo, proxy generation — working
- Export: Premiere XML, FCPXML, EDL, SRT — working
- Hotkeys: 40+ bindings implemented in useCutHotkeys.ts — NOT wired to layout
- Dockview migration: 5 commits on `claude/relaxed-rosalind` — NOT merged

### Done on worktree (awaiting merge)
- W0.1-W0.4: Legacy cleanup, transport split — done_worktree
- CUT-W3.7: Multi-select clips — done_worktree
- CUT-W3.4: JKL reverse playback — done_worktree
- Panel docking research — done_worktree

### Critical gaps (blocks "working APP")
1. **Stores disconnected** — PanelSyncStore island, no Source/Program split
2. **Track controls missing** — no lock/mute/solo/target
3. **Editing hotkeys dead** — useCutHotkeys not mounted in NLE layout
4. **No save/autosave** — work lost on reload
5. **No context menu** — right-click does nothing
6. **No effects/transitions** — zero visual effects, no crossfades
7. **No clip speed control** — can't change playback rate
8. **No audio mixer** — volume/pan/VU meters absent
9. **No sequence settings** — framerate/resolution/timecode hardcoded
10. **No real codec engine** — HTML5 video only (no ProRes, R3D, BRAW decode)
11. **No master render** — ExportDialog is stub, no FFmpeg pipeline
12. **No hotkey customization UI** — backend presets exist, no settings panel

---

## 3 Streams — File Ownership Map

### STREAM A: "ENGINE" — Core NLE Pipeline
**Focus:** Wiring, editing, save, transport — make it feel like an NLE
**Agent:** Opus-A (worktree: `claude/cut-engine`)

**Owned files:**
```
client/src/store/useCutEditorStore.ts        ← PRIMARY (store refactor)
client/src/store/usePanelSyncStore.ts        ← bridge
client/src/hooks/useCutHotkeys.ts            ← hotkey wiring
client/src/components/cut/CutStandalone.tsx   ← mount hotkeys here
client/src/components/cut/CutEditorLayoutV2.tsx  ← layout changes (shared — coordinate!)
client/src/components/cut/TimelineTrackView.tsx  ← track controls, editing ops
client/src/components/cut/MonitorTransport.tsx   ← transport controls
client/src/components/cut/ContextMenu.tsx        ← NEW
client/src/components/cut/ProjectSettings.tsx    ← NEW
client/src/components/cut/HistoryPanel.tsx       ← NEW
```

**Tasks (sequential order):**

| ID | Task | Wave | Deps | Complexity | Priority |
|----|------|------|------|------------|----------|
| A1 | PanelSyncStore → EditorStore bridge | W1.1 | — | medium | 1-CRITICAL |
| A2 | Panel focus system | W1.2 | — | medium | 1-CRITICAL |
| A3 | Source/Program feed split | W1.3 | A1 | medium | 1-CRITICAL |
| A4 | Separate Source/Sequence marks | W1.4 | A3 | medium | 1-CRITICAL |
| A5 | Mount useCutHotkeys in NLE layout | RECON-fix | — | low | 1-CRITICAL |
| A6 | Track header controls (lock/mute/solo/target) | W2.1 | — | high | 2-HIGH |
| A7 | Source patching / destination targeting | W2.2 | A6 | high | 2-HIGH |
| A8 | Split at playhead (⌘K) + Ripple Delete | W3.1 | A5 | medium | 1-CRITICAL |
| A9 | Insert/Overwrite (,/.) with targeting | W3.2 | A7 | high | 2-HIGH |
| A10 | Navigate edit points (↑/↓) | W3.3 | A5 | low | 2-HIGH |
| A11 | 5-frame step + Clear In/Out | W3.5 | A5 | low | 2-HIGH |
| A12 | Tool State Machine (V/C/B/Z) | W3.6 | — | medium | 2-HIGH |
| A13 | Context menu — Timeline clips | W4.1 | A8 | medium | 2-HIGH |
| A14 | Context menu — DAG/Project items | W4.2 | A13 | medium | 3-MEDIUM |
| A15 | Save / Save As / Autosave (⌘S) | W4.3 | — | high | 1-CRITICAL |
| A16 | Project settings dialog | W4.5 | — | medium | 2-HIGH |
| A17 | History Panel | W4.4 | — | medium | 3-MEDIUM |

**Parallel groups within Stream A:**
- `{A1, A2, A5}` — fully parallel (no deps)
- `{A6, A12, A15, A16}` — fully parallel (no deps between them)
- `A3 → A4` — sequential
- `A8, A10, A11` — parallel after A5
- `A13 → A14` — sequential

---

### STREAM B: "MEDIA" — Codec Engine + Effects + Export + Audio
**Focus:** Real codecs, effects pipeline, master render, audio mixing
**Agent:** Opus-B (worktree: `claude/cut-media`)

**Owned files:**
```
# Backend — codec & render
src/services/cut_proxy_worker.py             ← enhance proxy pipeline
src/services/cut_render_engine.py            ← NEW: master render
src/services/cut_codec_probe.py              ← NEW: FFprobe wrapper
src/services/cut_effects_engine.py           ← NEW: effects processing
src/services/cut_audio_engine.py             ← NEW: audio mix/render
src/api/routes/cut_routes.py                 ← new endpoints (coordinate!)

# Frontend — effects, audio, export
client/src/components/cut/ExportDialog.tsx   ← rewrite from stub
client/src/components/cut/AudioMixer.tsx     ← NEW
client/src/components/cut/EffectsPanel.tsx   ← NEW
client/src/components/cut/TransitionsPanel.tsx ← NEW
client/src/components/cut/SpeedControl.tsx   ← NEW
client/src/components/cut/ClipInspector.tsx  ← enhance (effects params)
client/src/components/cut/SequenceSettings.tsx ← NEW
```

**Tasks (sequential + parallel noted):**

| ID | Task | Wave | Deps | Complexity | Priority |
|----|------|------|------|------------|----------|
| B1 | FFprobe codec detection + metadata extraction | NEW | — | medium | 1-CRITICAL |
| B2 | Proxy generation pipeline (720p/480p H.264) | W6-ext | B1 | high | 1-CRITICAL |
| B3 | Sequence settings (framerate, resolution, timecode) | W4.5-ext | — | medium | 1-CRITICAL |
| B4 | WebCodecs decoder for ProRes/DNxHD (or FFmpeg fallback) | NEW | B1 | high | 2-HIGH |
| B5 | Master render engine (FFmpeg concat + filter_complex) | W6.1 | B1 | high | 1-CRITICAL |
| B6 | ExportDialog rewrite — real codec/quality/resolution | W6.1 | B5 | high | 1-CRITICAL |
| B7 | Crosspost presets (YouTube/IG/TikTok auto-reformat) | W6.3 | B6 | medium | 3-MEDIUM |
| B8 | OTIO / AAF export | W6.4 | B6 | medium | 3-MEDIUM |
| B9 | Effects system — video effects pipeline (brightness, contrast, saturation, blur) | W10.6 | — | high | 2-HIGH |
| B10 | Transitions — crossfade, dip-to-black, wipe, dissolve | W10.6 | B9 | high | 2-HIGH |
| B11 | Clip speed control (0.25x-4x + reverse + time remap) | NEW | — | medium | 2-HIGH |
| B12 | Motion controls (position, scale, rotation, anchor) | NEW | — | high | 2-HIGH |
| B13 | Audio mixer panel (per-track volume/pan/mute/solo/VU) | W9.1 | — | high | 2-HIGH |
| B14 | Audio transitions (crossfade curves) | W9.3 | B13 | medium | 3-MEDIUM |
| B15 | Audio waveform overlay on timeline clips | NEW | — | medium | 2-HIGH |
| B16 | Color correction basics (exposure, WB, saturation, curves) | NEW | B9 | high | 3-MEDIUM |
| B17 | Export selection + audio stems | W6.2 | B6 | medium | 3-MEDIUM |

**Parallel groups within Stream B:**
- `{B1, B3, B9, B11, B13, B15}` — fully parallel (no deps)
- `B2 → B4` — sequential (probe first, then decode)
- `B5 → B6 → {B7, B8, B17}` — render engine → dialog → variants
- `B9 → {B10, B16}` — effects base → transitions + color
- `B12` — independent (motion is pure transform math)

---

### STREAM C: "UX" — Dockview, Hotkey UI, Multi-Timeline, DAG+
**Focus:** Panel system, workspace presets, keyboard customization, multi-timeline
**Agent:** Opus-C (worktree: `claude/cut-ux`)

**Owned files:**
```
# Dockview integration
client/src/components/cut/CutDockviewLayout.tsx  ← NEW (replace CutEditorLayoutV2)
client/src/components/cut/panels/              ← NEW directory, per-panel wrappers
client/src/store/usePanelLayoutStore.ts        ← dockview state persistence

# Hotkey customization
client/src/components/cut/HotkeyEditor.tsx     ← NEW
client/src/components/cut/HotkeyPresetSelector.tsx ← NEW
client/src/store/useHotkeyStore.ts             ← NEW (or extend existing)

# Multi-timeline (Phase 198)
client/src/store/useTimelineInstanceStore.ts   ← NEW (Map<id, TimelineInstance>)
client/src/components/cut/TimelineTabBar.tsx   ← refactor for dockview tabs

# DAG enhancements
client/src/components/cut/DAGProjectPanel.tsx  ← Y-axis fix, timelineId prop
client/src/components/cut/StorySpace3D.tsx     ← mount in panel
client/src/components/cut/PulseInspector.tsx   ← mount in panel

# Workspace
client/src/components/cut/WorkspacePresets.tsx ← NEW
```

**Tasks:**

| ID | Task | Wave | Deps | Complexity | Priority |
|----|------|------|------|------------|----------|
| C1 | Merge dockview branch (claude/relaxed-rosalind) to main | MERGE | — | medium | 1-CRITICAL |
| C2 | Dockview dark theme + panel styling | DOCK-3 | C1 | medium | 1-CRITICAL |
| C3 | CutDockviewLayout — replace CutEditorLayoutV2 | DOCK | C2 | high | 1-CRITICAL |
| C4 | Panel wrappers (Source, Program, Timeline, Project, Script, DAG) | DOCK | C3 | medium | 2-HIGH |
| C5 | Workspace presets (Editing/Color/Audio layouts) | DOCK-4 | C4 | medium | 2-HIGH |
| C6 | Hotkey preset selector UI (Premiere/FCP7/Custom) | W10.7 | — | medium | 2-HIGH |
| C7 | Hotkey editor — full key rebinding UI | W10.7 | C6 | high | 2-HIGH |
| C8 | DAG Y-axis flip + timelineId prop | W2.3 | — | medium | 2-HIGH |
| C9 | Mount Inspector/StorySpace/PULSE panels in dockview | W0.5 | C3 | medium | 2-HIGH |
| C10 | Phase 198: Store refactor — TimelineInstance Map | P198 | — | high | 2-HIGH |
| C11 | Phase 198: TimelineTrackView → props-driven (timelineId) | P198 | C10 | high | 2-HIGH |
| C12 | Phase 198: Dockview multi-timeline wiring | P198 | C11, C3 | medium | 2-HIGH |
| C13 | Phase 198: Delete TimelineTabBar + parallel code | P198 | C12 | low | 3-MEDIUM |
| C14 | Auto-Montage UI (3 buttons + progress) | W5.1 | — | medium | 3-MEDIUM |
| C15 | Project Panel view modes (List/Grid/DAG) | W5.4 | — | medium | 3-MEDIUM |
| C16 | Favorite markers: N key + ⇧M comment | W5.3 | — | low | 3-MEDIUM |

**Parallel groups within Stream C:**
- `{C6, C8, C10, C14, C15, C16}` — fully parallel (no deps)
- `C1 → C2 → C3 → {C4, C9} → C5` — dockview pipeline (sequential)
- `C10 → C11 → C12 → C13` — multi-timeline pipeline
- `C3 + C11 → C12` — cross-dependency (dockview + timeline instance)

---

## Cross-Stream Dependencies

```
STREAM A                    STREAM B                    STREAM C
─────────                   ─────────                   ─────────
A1 (bridge)                 B1 (ffprobe)                C1 (merge dockview)
A2 (focus)                  B3 (seq settings)           C2 (dark theme)
A5 (hotkeys mount)          B9 (effects)                C3 (dockview layout)
     │                      B11 (speed)                      │
     │                      B13 (mixer)                      │
     ▼                      B15 (waveforms)                  ▼
A3 (src/prog split)              │                     C4 (panel wrappers)
A6 (track controls)              │                     C6 (hotkey presets)
     │                           │                     C8 (DAG fix)
     ▼                           ▼                     C10 (multi-tl store)
A8 (split/ripple) ◄──── B9 effects need clips ────►        │
A9 (insert/overwrite)   to apply to                         │
     │                       │                               ▼
     ▼                       ▼                         C11 (TTV props)
A13 (context menu)     B5 (render engine)             C12 (dockview+multi)
A15 (save)             B6 (export dialog)                   │
     │                       │                               ▼
     ▼                       ▼                         C5 (workspace presets)
A16 (project settings)  B7 (crosspost)                C7 (hotkey editor)
                        B10 (transitions)
                        B16 (color)
```

### Critical Merge Points (Architect-Commander coordinates)

1. **MERGE POINT 1** (after A1+A2+A3+A5 done): Stream A's store changes are foundation. B and C can start before, but MUST rebase after A1-A5 merge.

2. **MERGE POINT 2** (after C3 done): CutDockviewLayout replaces CutEditorLayoutV2. Stream A tasks that touch layout MUST use new dockview components after this merge.

3. **MERGE POINT 3** (after B9+A8 done): Effects pipeline needs clip editing to work. Transitions (B10) can only be tested when clips can be split/moved.

4. **MERGE POINT 4** (after A15+B5+B6 done): Save + Render + Export = app is usable. This is the MVP gate.

---

## Merge Order (Architect-Commander executes)

```
Phase 1: Foundation
  1. Merge done_worktree tasks (W0.1-W0.4, W3.4, W3.7) → main
  2. Merge dockview branch (claude/relaxed-rosalind) → main
  3. Stream A: A1-A5 (wiring) → main  [MERGE POINT 1]

Phase 2: Core editing
  4. Stream A: A6-A12 (tracks + editing) → main
  5. Stream C: C2-C4 (dockview layout) → main  [MERGE POINT 2]
  6. Stream B: B1-B3 (codec probe + proxy + seq settings) → main

Phase 3: Full NLE
  7. Stream A: A8-A11 (editing ops) → main
  8. Stream B: B5-B6 (render + export) → main
  9. Stream B: B9-B11 (effects + speed) → main  [MERGE POINT 3]
  10. Stream A: A13-A17 (context menu + save) → main  [MERGE POINT 4 = MVP GATE]

Phase 4: Polish
  11. Stream C: C5-C7 (workspace + hotkey UI) → main
  12. Stream B: B13-B16 (audio + color) → main
  13. Stream C: C10-C13 (multi-timeline) → main
  14. Stream B: B7-B8 (crosspost + OTIO) → main
```

---

## Agent Protocol (DNA)

### On Connect (MANDATORY for every Opus agent)

```
1. vetka_session_init → get project context
2. Read THIS roadmap (ROADMAP_CUT_MVP_PARALLEL.md)
3. Read your stream's root docs from the table above
4. vetka_task_board action=list project_id=CUT → find your stream's tasks
5. Claim a task → do work → complete via task_board
```

### Task Lifecycle

```
CLAIM:    vetka_task_board action=claim task_id=<id> assigned_to=<agent>
DO WORK:  Edit files, run tests
COMPLETE: vetka_task_board action=complete task_id=<id> branch=claude/<worktree-name>
```

**NEVER** raw `git commit`. **ALWAYS** close via `vetka_task_board action=complete`.
From worktree: **MUST** pass `branch=claude/<worktree-name>`.

### Test-Based Acceptance (MANDATORY)

Every task MUST have at least ONE verifiable test before completion:

**Frontend tasks:**
- Component renders without errors: `npx tsc --noEmit` passes
- Visual: screenshot via preview tools showing the feature works
- Interaction: click/key test showing the action triggers correctly

**Backend tasks:**
- `python -m pytest tests/test_<module>.py -v` passes
- If no test file exists — CREATE one before completing the task

**Integration tasks:**
- End-to-end: frontend action → backend response → UI update verified

### Self-Analysis Protocol

Before completing EACH task, the agent MUST answer:

```markdown
## Self-Analysis
1. **Do I understand the project?** [yes/partial/no] — brief explanation
2. **Does my code match the architecture docs?** [yes/partial/no] — cite specific doc section
3. **Did I introduce any regressions?** [yes/no] — how I verified
4. **File ownership respected?** [yes/no] — list any files I touched outside my stream
5. **What would I do differently?** — 1 sentence
```

### Feedback Protocol

**After each task:**
- If you noticed something unexpected or had an insight → add a 1-2 line note in your task completion message

**After completing the LAST task of your stream (or phase):**
- Write a `DOC_FEEDBACK_<stream>_<date>.md` in `docs/190_ph_CUT_WORKFLOW_ARCH/feedback/`
- Include:
  - Top 3 architectural insights
  - Bugs or inconsistencies found in docs
  - Ideas for improvement (features, UX, performance)
  - Suggestions for other streams
  - Self-assessment: what went well, what was hard

**Architect-Commander will:**
- Review all feedback docs
- Surface the most interesting ideas to the user
- Create follow-up tasks for the best suggestions

### Sub-Roadmap Protocol (DNA inheritance)

Each Opus agent MAY create detailed sub-roadmaps for their stream:
- File: `docs/190_ph_CUT_WORKFLOW_ARCH/ROADMAP_<STREAM>_DETAIL.md`
- MUST inherit this protocol verbatim (copy the "Agent Protocol" section)
- MUST reference all root documents from the table above
- CAN add stream-specific docs and implementation details
- CAN break tasks into sub-tasks (e.g., A8.1, A8.2)
- MUST NOT change task IDs from this parent roadmap

---

## Critical Architecture Notes

### Store Architecture (Stream A must know)
- `useCutEditorStore.ts` — main Zustand store (singleton → will become Map in Phase 198)
- `usePanelSyncStore.ts` — bridge between panels (Script/DAG/StorySpace → NLE)
- `usePanelLayoutStore.ts` — layout config (will be replaced by dockview state in Stream C)
- All stores are Zustand with `immer` middleware

### Component Hierarchy
```
CutStandalone (root — mounts hotkeys here)
  └─ CutEditorLayoutV2 (→ CutDockviewLayout after C3)
       ├─ VideoPreview feed="source"
       ├─ VideoPreview feed="program"
       ├─ TimelineTrackView (→ props-driven after C11)
       ├─ ProjectPanel
       ├─ ScriptPanel
       ├─ DAGProjectPanel
       ├─ PulseInspector
       ├─ ClipInspector
       └─ StorySpace3D
```

### Backend Structure
- `src/api/routes/cut_routes.py` — monolith (7818 lines), ALL CUT endpoints
- **DANGER:** Both Stream A and Stream B need to add endpoints here
- **Protocol:** Use `MARKER_<stream>_<task>` comments. E.g., `# MARKER_B5.1 — render engine endpoint`
- Stream B: prefer new files in `src/services/` over modifying cut_routes.py

### Design Rules
- **NO emoji/colored icons** in UI — ONLY white monochrome SVG/PNG (16x16, stroke 1.5px)
- Dark theme: `#1e1e1e` backgrounds, `#e0e0e0` text, `#3a3a3a` borders
- Active/selected: `#4A9EFF` accent (blue)

---

## MVP Definition (what "working APP" means)

The user has a **client coming tomorrow**. The MVP gate is MERGE POINT 4:

**MUST HAVE (Priority 1):**
- [ ] Source/Program monitors — separate feeds ✓
- [ ] Hotkeys working — play, pause, JKL, split, ripple delete ✓
- [ ] Track controls — lock, mute, solo ✓
- [ ] Insert/Overwrite editing ✓
- [ ] Save/Autosave — don't lose work ✓
- [ ] Master render — export video file with real codec ✓
- [ ] Sequence settings — choose framerate/resolution ✓

**SHOULD HAVE (Priority 2):**
- [ ] Effects — basic brightness/contrast/saturation
- [ ] Transitions — crossfade at minimum
- [ ] Clip speed control (0.25x-4x)
- [ ] Audio mixer (volume/pan per track)
- [ ] Hotkey preset selector (Premiere/FCP7)
- [ ] Dockview panel layout

**NICE TO HAVE (Priority 3):**
- [ ] Multi-timeline instances
- [ ] Color correction
- [ ] Workspace presets
- [ ] Full hotkey rebinding UI
- [ ] OTIO/AAF export

---

## Appendix: Gap Analysis Summary

| Feature | Architecture Doc | Code Status | Stream | Priority |
|---------|-----------------|-------------|--------|----------|
| Store bridge | CUT_TARGET_ARCH §5 | MISSING | A | 1 |
| Source/Program split | CUT_TARGET_ARCH §3.1 | MISSING | A | 1 |
| Track controls | CUT_UNIFIED_VISION W2 | MISSING | A | 2 |
| Editing ops (split/insert) | CUT_UNIFIED_VISION W3 | MISSING | A | 1 |
| Save/Autosave | CUT_UNIFIED_VISION W4 | MISSING | A | 1 |
| Context menu | CUT_UNIFIED_VISION W4 | MISSING | A | 2 |
| Codec detection | CUT_TARGET_ARCH §8 | PARTIAL (HTML5 only) | B | 1 |
| Proxy pipeline | CUT_TARGET_ARCH §8 | WORKING (basic) | B | 1 |
| Master render | CUT_UNIFIED_VISION W6 | STUB | B | 1 |
| Export dialog | CUT_UNIFIED_VISION W6 | STUB | B | 1 |
| Effects system | NOT IN DOCS (W10.6 only) | MISSING | B | 2 |
| Transitions | NOT IN DOCS | MISSING | B | 2 |
| Clip speed | NOT IN DOCS | MISSING | B | 2 |
| Motion controls | NOT IN DOCS | MISSING | B | 2 |
| Audio mixer | CUT_UNIFIED_VISION W9 | MISSING | B | 2 |
| Color correction | Itten grading exists | PARTIAL (backend only) | B | 3 |
| Dockview | RECON_PANEL_DOCKING | ON BRANCH (not merged) | C | 1 |
| Hotkey UI | CUT_HOTKEY_ARCH | MISSING | C | 2 |
| Multi-timeline | Phase 198 docs | PLANNED (store refactor) | C | 2 |
| Workspace presets | CUT_TARGET_ARCH §3 | MISSING | C | 2 |
| DAG Y-axis | RECON_192 §2.1 | INVERTED | C | 2 |

---

*Generated by Architect-Commander (Opus 4.6) on 2026-03-20*
*Protocol version: 1.0*
