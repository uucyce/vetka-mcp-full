# STREAM A: ENGINE — Detailed Sub-Roadmap

**Date:** 2026-03-20
**Agent:** Opus (Claude Code)
**Parent:** ROADMAP_CUT_MVP_PARALLEL.md → STREAM A
**Focus:** Wiring, editing, save, transport — make it feel like an NLE

---

## Status Summary

| ID | Task | Wave | Status | Evidence |
|----|------|------|--------|----------|
| A1 | PanelSyncStore → EditorStore bridge | W1.1 | **DONE** | `usePanelSyncBridge.ts` + `CutStandalone.tsx:518` |
| A2 | Panel focus system | W1.2 | **DONE** | `DockviewLayout.tsx:254-261` + `useCutEditorStore.ts:122,455` |
| A3 | Source/Program feed split | W1.3 | **DONE** | `VideoPreview.tsx:122-140` — feed prop + sourceMediaPath/programMediaPath |
| A4 | Separate Source/Sequence marks | W1.4 | **DONE** | `useCutEditorStore.ts:97-101,380-384` — sourceMarkIn/Out + sequenceMarkIn/Out |
| A5 | Mount useCutHotkeys in NLE layout | RECON-fix | **DONE** | `CutEditorLayoutV2.tsx:22,184` — hook called with full handlers |
| A6 | Track header controls (lock/mute/solo/target) | W2.1 | PENDING | Store has state (`lockedLanes`, `targetedLanes`), UI needs SVG icons |
| A7 | Source patching / destination targeting | W2.2 | PENDING | Depends on A6 |
| A8 | Split at playhead + Ripple Delete | W3.1 | **DONE** | `CutEditorLayoutV2.tsx:136-154` — splitClip handler |
| A9 | Insert/Overwrite with targeting | W3.2 | PENDING | Depends on A7 |
| A10 | Navigate edit points (Up/Down) | W3.3 | PENDING | |
| A11 | 5-frame step + Clear In/Out | W3.5 | **DONE** | `CutEditorLayoutV2.tsx:73-81,107-111` |
| A12 | Tool State Machine (V/C/B/Z) | W3.6 | **DONE** | `useCutEditorStore.ts:124-125,457` + `CutEditorLayoutV2.tsx:157-158` |
| A13 | Context menu — Timeline clips | W4.1 | PENDING | |
| A14 | Context menu — DAG/Project items | W4.2 | PENDING | |
| A15 | Save / Save As / Autosave | W4.3 | PENDING | HIGH PRIORITY |
| A16 | Project settings dialog | W4.5 | **DONE** | `ProjectSettings.tsx` + `CutEditorLayoutV2.tsx:189` |
| A17 | History Panel | W4.4 | **DONE** | `HistoryPanel.tsx` + `DockviewLayout.tsx:58,216-221` |

---

## Remaining Work (7 tasks)

### Priority 1: CRITICAL

**A15: Save / Save As / Autosave (Cmd+S)**
- Complexity: HIGH
- Deps: none
- What: Serialize project state → backend POST endpoint → file on disk
- Store fields: `projectId`, `sandboxRoot`, `timelineId`
- Backend: Need `POST /api/cut/project/save` endpoint
- Frontend: Cmd+S hotkey + "Saved" status indicator + autosave timer

### Priority 2: HIGH

**A6: Track header controls (lock/mute/solo/target)**
- Complexity: HIGH
- Deps: none
- What: SVG icons in track headers, wired to store toggleMute/toggleSolo/toggleLock/toggleTarget
- Store: DONE — `mutedLanes`, `soloLanes`, `lockedLanes`, `targetedLanes` (all with togglers)
- Gap: No visual UI rendered — `TimelineTrackView.tsx` needs header column with icon buttons

**A10: Navigate edit points (Up/Down)**
- Complexity: LOW
- Deps: none
- What: Up/Down arrows jump playhead to nearest clip boundary
- Implementation: Scan all clips for start/end points, find nearest to currentTime

**A13: Context menu — Timeline clips**
- Complexity: MEDIUM
- Deps: A8 (done)
- What: Right-click on timeline clip → context menu with Cut/Copy/Delete/Split/Unlink/Properties
- Implementation: New ContextMenu component, positioned at click coordinates

### Priority 3: MEDIUM

**A7: Source patching / destination targeting**
- Complexity: HIGH
- Deps: A6
- What: Click V1/A1 headers to target lanes for insert/overwrite
- Store: DONE — `targetedLanes`, `getInsertTargets()`
- Gap: Visual indication of targeted lanes + click handlers

**A9: Insert/Overwrite with targeting**
- Complexity: HIGH
- Deps: A7
- What: , (comma) = insert, . (period) = overwrite — use marked region from source → targeted lanes
- Requires: getInsertTargets() + source marks + timeline manipulation

**A14: Context menu — DAG/Project items**
- Complexity: MEDIUM
- Deps: A13
- What: Right-click on DAG/Project items → context menu (Open in Source, Add to Timeline, etc.)

---

## Execution Order

```
Phase 1 (parallel, no deps):
  A15 — Save/Autosave (CRITICAL)
  A6  — Track headers (HIGH)
  A10 — Navigate edit points (HIGH)

Phase 2 (after A6):
  A7  — Source patching
  A13 — Context menu (clips)

Phase 3 (after A7, A13):
  A9  — Insert/Overwrite
  A14 — Context menu (DAG)
```

---

## STREAM A Owned Files

```
client/src/store/useCutEditorStore.ts        ← PRIMARY (store)
client/src/store/usePanelSyncStore.ts        ← bridge (DONE)
client/src/hooks/useCutHotkeys.ts            ← hotkey wiring (DONE)
client/src/hooks/usePanelSyncBridge.ts       ← bridge hook (DONE)
client/src/CutStandalone.tsx                 ← entry point
client/src/components/cut/CutEditorLayoutV2.tsx  ← layout + hotkey handlers
client/src/components/cut/DockviewLayout.tsx     ← dockview panel system
client/src/components/cut/TimelineTrackView.tsx  ← track controls, editing ops
client/src/components/cut/MonitorTransport.tsx   ← transport controls
client/src/components/cut/VideoPreview.tsx       ← source/program feed (DONE)
client/src/components/cut/ProjectSettings.tsx    ← settings dialog (DONE)
client/src/components/cut/HistoryPanel.tsx       ← undo/redo (DONE)
```
