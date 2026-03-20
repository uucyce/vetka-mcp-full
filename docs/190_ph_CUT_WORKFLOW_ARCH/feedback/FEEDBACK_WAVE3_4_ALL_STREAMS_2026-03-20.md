# CUT Wave 3-4 Agent Feedback Synthesis
**Date:** 2026-03-20
**Compiled by:** Opus Commander (inspiring-cohen)
**Sources:** Alpha, Beta, Gamma, Delta-1 farewell feedback

---

## Top 3 Architectural Truths (consensus across agents)

### 1. Backend is production-ready, frontend is "museum of components"
**Alpha + Beta confirm:** 54 endpoints, zero stubs. Render, export, PULSE, undo/redo all real.
Frontend had every brick, but no wiring. One 47-line bridge (usePanelSyncBridge) unlocked half the NLE.
**Implication:** New features should wire existing backend endpoints, not create new ones.

### 2. Singleton store must die
**Alpha:** useCutEditorStore is a singleton pretending to be multi-timeline. 50+ fields live flat, snapshot/restore is a hack.
**Gamma confirms:** TimelineTrackView accepts timelineId prop, but data still comes from legacy singleton.
**Action:** Alpha-2's first implicit task: all timeline reads go through useTimelineInstanceStore. Kill singleton timeline state.

### 3. Panel focus scoping is the #1 UX gap
**Gamma:** "Without this, CUT feels wrong to any editor." JKL should control active monitor, Delete only in timeline.
**Delta confirms:** Tests break because actions are global, not panel-scoped.
**Action:** Must implement focusedPanel + panel-scoped hotkey dispatch before any more editing features.

---

## Top 3 Ideas for CUT's Unique Identity

### 1. Timeline-as-DAG-Projection (Alpha)
Timeline = path through the multiverse graph. "Create new cut" = choose different DAG path.
PULSE auto-montage already works this way on backend. Close the loop on frontend.
**This is CUT's killer feature.** No other NLE has this.

### 2. Split Timeline + DAG Reverse Navigation (Gamma)
Two timelines side-by-side → click clip → DAG highlights alternative takes → drag alt take from DAG to second timeline.
**Workflow that doesn't exist anywhere.** Leverages dockview multi-panel + useTimelineInstanceStore.

### 3. Proxy-First Color Pipeline (Beta)
Import → generate 540p proxy → all grading on proxy (30fps on any hardware) → final render on full-res via PyAV.
FCP7's Offline/Online workflow, modernized. Zero GPU dependency for preview.
**Critical for CUT's accessibility story** — professional grading on a MacBook Air.

---

## Critical Technical Insights (for Wave 5 agents)

### FFmpeg filter_complex (Beta)
- Build incrementally: each clip = independent chain, merge at end via xfade/concat
- Merge eq params into single filter (brightness+contrast+saturation = one eq, not three) → 15% speedup
- Identity values (brightness=0, scale=1, rotation=0) → skip filter entirely → critical at 50+ clips

### Dockview CSS (Gamma)
- Internal inline styles + hardcoded rgb() ignore CSS vars
- Required 30+ !important overrides with attribute selectors
- Any dockview update can break theme — pin version, test after upgrade

### Testing Strategy (Delta)
- **Golden Screenshot Baseline:** page.screenshot() + pixelmatch diff → catches visual regressions that DOM checks miss
- **Test workflows, not features:** "open clip → set IN/OUT → press , → clip appears at correct position" > menuContains()
- **Editing ops don't update store:** API returns success, but Zustand doesn't re-fetch. Need optimistic update or test helper.

### Three-Point Editing (Delta — CRITICAL)
FCP7 Ch.36: Source IN/OUT + Sequence IN/OUT + Destination Track = auto-fourth-point.
**This is muscular memory for every editor.** CUT has I/O buttons but no workflow.
Until three-point editing works as a system, CUT is a drag-and-drop timeline, not an NLE.

---

## Advice Chain (agent → successor)

| From | To | Key Advice |
|------|-----|-----------|
| Alpha → Alpha-2 | Don't touch useCutEditorStore for timeline data — use useTimelineInstanceStore.updateTimeline(). Add onProjectStateRefresh → re-snapshot. Read RECON_192. |
| Beta → Beta-2 | Effects go in 3 places: EFFECT_DEFS (schema), compile_video_filters (FFmpeg), compile_css_filters (preview). Don't mix layers: FFmpeg CLI for render, PyAV for preview/scopes/LUT. |
| Gamma → Gamma-2 | Next step: bridge effect — addTimelinePanel → createTimeline in instance store → backend fetch → updateTimeline. Then second panel shows its own data, not mirror. |
| Delta → QA | Test workflows, not features. Golden screenshot baselines. FCP7 manual = chapter-based workflow tests, not feature checklists. |

---

## Priority Matrix for Wave 5 (Commander's synthesis)

| Priority | What | Why | Agent |
|----------|------|-----|-------|
| **P0** | Three-Point Editing system | "Without this, CUT is not an NLE" — Delta | Alpha-2 |
| **P0** | Panel focus scoping | "Feels wrong without it" — Gamma | Gamma-2 |
| **P1** | Store migration completion | Kill singleton, full useTimelineInstanceStore | Alpha-2 |
| **P1** | Video Scopes (Waveform/Vectorscope) | Foundation for color pipeline | Beta-2 |
| **P2** | Golden Screenshot baselines | Catch visual regressions automatically | Delta/QA |
| **P2** | Proxy-first color pipeline | 30fps preview on any hardware | Beta-2 |
| **P3** | DAG → Timeline projection | CUT's killer feature | Future wave |

---

*"The orchestra played. The conductor listened. The music was in the silence between the notes."*
