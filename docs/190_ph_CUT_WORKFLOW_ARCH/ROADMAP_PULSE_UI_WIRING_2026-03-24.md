# ROADMAP: PULSE/Logger/Cinema UI Wiring
**Author:** Gamma-9 (UX Architect) | **Date:** 2026-03-24
**Scope:** Wire existing PULSE backend services to existing UI panels
**Premise:** Backend 100% ready, UI panels 90% built, wiring 30% done

---

## Status: What's READY

### Backend Services (ALL WORKING)
| Service | Endpoint | Returns |
|---------|----------|---------|
| Auto-Montage | `POST /pulse/auto-montage` | timeline_label, clips[], mode |
| Camelot Engine | `POST /pulse/camelot/path` | harmonic progression suggestion |
| Camelot Distance | `GET /pulse/camelot/distance` | key distance metric |
| Camelot Neighbors | `GET /pulse/camelot/neighbors` | harmonic neighbors |
| Energy Critics | `POST /pulse/energy-critics` | genre-aware energy scores |
| Story Space | `POST /pulse/story-space/{id}` | 3D Camelot + McKee coords |
| Cinema Matrix | `POST /pulse/matrix` | scale-genre-function mapping |
| Script Enrich | `POST /pulse/enrich-from-script/{id}` | apply PULSE metadata to clips |
| Timeline Enrich | `POST /pulse/enrich-from-timeline/{id}` | scan + compute + update graph |
| Scene Detect | `POST /cut/scene-detect-and-apply` | auto-split by scene changes |

### UI Panels (ALL MOUNTED in dockview)
| Panel | Component | What it shows |
|-------|-----------|---------------|
| PulseInspector | `PulseInspector.tsx` | Camelot key, energy, pendulum, McKee |
| StorySpace3D | `StorySpace3D.tsx` | Three.js Camelot wheel + McKee triangle |
| AutoMontagePanel | `AutoMontagePanel.tsx` | 3 buttons: Favorites/Script/Music cut |
| ScriptPanel | `ScriptPanel.tsx` | Clickable scene chunks + teleprompter |
| DAGProjectPanel | `DAGProjectPanel.tsx` | Multiverse graph with clustered nodes |
| ClipInspector | `ClipInspector.tsx` | File, timing, waveform, effects |

---

## Gap Analysis: What's BROKEN

### G1: Auto-Montage result doesn't populate timeline
- Panel calls POST, gets clips[], creates empty tab
- Missing: convert clips[] → timeline_ops[] → applyTimelineOps()
- **Owner: Alpha (engine) + Beta (backend ops format)**

### G2: Panel sync broken — Script/DAG clicks don't update Inspector
- ScriptPanel onClick calls syncFromScript() but selectedScene not propagated
- DAGProjectPanel uses hardcoded timeline_id='main'
- PulseInspector reads selectedScene but never receives it from DAG/Script
- **Owner: Alpha (store bridge) + Gamma (panel wiring)**

### G3: StorySpace3D not reactive
- useEffect doesn't re-fetch on timeline change
- Hardcoded timeline_id in fetch call
- No camera animation synced to playhead
- **Owner: Gamma (component fix)**

### G4: DAG Y-axis is abstract, not chronological
- Nodes positioned by cluster column, not by scene time
- Script Spine should be center vertical axis
- Video LEFT, Audio RIGHT of spine
- **Owner: Gamma (DAGProjectPanel layout logic)**

### G5: No enrichment progress feedback
- Logger runs async but no UI indicator
- No toast on "enrichment complete"
- **Owner: Gamma (toast) + Alpha (event listener)**

---

## Roadmap: Priority Tasks

### Phase 1: PULSE Wiring (P0 — makes Auto-Montage actually work)

| ID | Task | Owner | Domain | Files |
|----|------|-------|--------|-------|
| PW-1 | Auto-Montage → Timeline: extend MontageResult with timeline_ops, apply on UI | Alpha + Beta | engine + media | pulse_auto_montage.py, AutoMontagePanel.tsx |
| PW-2 | Panel Sync Bridge: Script/DAG click → selectedScene → PulseInspector | Alpha | engine (store) | usePanelSyncStore.ts, useCutEditorStore.ts |
| PW-3 | PulseInspector: show active scene title + Camelot suggested flow | Gamma | ux | PulseInspector.tsx |
| PW-4 | AutoMontagePanel: progress bar during analysis, result → open timeline tab | Gamma | ux | AutoMontagePanel.tsx |

### Phase 2: DAG + StorySpace Fix (P1 — data integrity)

| ID | Task | Owner | Domain | Files |
|----|------|-------|--------|-------|
| PW-5 | DAG Y-axis chronological: Script Spine center, Video LEFT, Audio RIGHT | Gamma | ux | DAGProjectPanel.tsx |
| PW-6 | StorySpace3D reactive: timeline_id from store, re-fetch on change | Gamma | ux | StorySpace3D.tsx |
| PW-7 | Fix hardcoded timeline_id='main' across DAG/StorySpace/Inspector | Alpha + Gamma | engine + ux | multiple |
| PW-8 | Expose activeTimelineId from CutEditorStore (not just TimelineInstanceStore) | Alpha | engine | useCutEditorStore.ts |

### Phase 3: Logger + Cinema Polish (P2)

| ID | Task | Owner | Domain | Files |
|----|------|-------|--------|-------|
| PW-9 | Logger enrichment progress toast + status badge in Project Panel | Gamma | ux | ProjectPanel.tsx, useCutEditorStore.ts |
| PW-10 | Script Panel: lore token hyperlinks (click name → DAG character node) | Gamma | ux | ScriptPanel.tsx |
| PW-11 | Project Panel DAG mode: [List] [Grid] [DAG] view switcher | Gamma | ux | ProjectPanel.tsx |
| PW-12 | Script Import Dialog: .fountain/.fdx/.pdf format picker | Gamma | ux | new ScriptImportDialog.tsx |

### Phase 4: Cinema Pipeline Extras (P3)

| ID | Task | Owner | Domain | Files |
|----|------|-------|--------|-------|
| PW-13 | Camelot Path visualization in PulseInspector (previous→current→next) | Gamma | ux | PulseInspector.tsx |
| PW-14 | Energy Critics radar/bar chart in PulseInspector | Gamma | ux | PulseInspector.tsx |
| PW-15 | DAG Flip Y toggle (START bottom vs top) | Gamma | ux | DAGProjectPanel.tsx |
| PW-16 | Montage comparison: side-by-side timeline diff (DAG-native) | Gamma | ux | new MontageComparePanel.tsx |

---

## Dependencies

```
PW-1 (Auto-Montage → Timeline) → needs Alpha + Beta
PW-2 (Panel Sync Bridge) → needs Alpha (store architecture)
PW-3, PW-4 → Gamma solo (can start now)
PW-5, PW-6 → Gamma solo (can start now)
PW-7, PW-8 → needs Alpha
PW-9 through PW-16 → Gamma solo (after PW-3..PW-6)
```

**Gamma can start immediately on:** PW-3, PW-4, PW-5, PW-6
**Gamma needs Alpha for:** PW-1, PW-2, PW-7, PW-8

---

*"The pipeline is built. The panels are mounted. Now we wire them together."*
