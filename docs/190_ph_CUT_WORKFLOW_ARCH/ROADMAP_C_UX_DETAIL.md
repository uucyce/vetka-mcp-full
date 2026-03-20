# ROADMAP C: UX Stream — Detailed Sub-Roadmap
# OPUS-C (Dockview, Hotkey UI, Multi-Timeline, DAG)

**Date:** 2026-03-20
**Owner:** Opus-C
**Parent:** ROADMAP_CUT_MVP_PARALLEL.md
**Stream:** C — UX

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| DONE | Merged to main |
| ACTIVE | In progress |
| NEXT | Ready to start |
| BLOCKED | Waiting on dependency |
| FUTURE | Phase 4 / Polish |

---

## C1-C3: Foundation (DONE)

These were completed in `claude/relaxed-rosalind` and merged to main.

| ID | Task | Status | Commits |
|----|------|--------|---------|
| C1 | Merge dockview branch | DONE | merge commit on main |
| C2 | Dark theme + panel styling | DONE | DOCK-3 (196.4) + DOCK-FIX (196.5) |
| C3 | CutDockviewLayout replaces V2 | DONE | DOCK-2 (196.3) |
| A5 | Mount useCutHotkeys in NLE layout | DONE | 196.1 |

---

## C4: Panel Wrappers (Priority 2-HIGH)

**Goal:** Extract inline panel wrappers from DockviewLayout.tsx into `client/src/components/cut/panels/` directory. Each wrapper = proper component with focus handling.

| Sub-ID | Task | Deps | Files |
|--------|------|------|-------|
| C4.1 | Create panels/ directory + index.ts | — | `panels/index.ts` |
| C4.2 | SourceMonitorPanel + ProgramMonitorPanel | — | `panels/SourceMonitorPanel.tsx`, `panels/ProgramMonitorPanel.tsx` |
| C4.3 | TimelinePanel (toolbar + tabs + track + BPM) | — | `panels/TimelinePanel.tsx` |
| C4.4 | Navigation panels: ProjectPanel, ScriptPanel, GraphPanel | — | `panels/ProjectPanelDock.tsx`, `panels/ScriptPanelDock.tsx`, `panels/GraphPanelDock.tsx` |
| C4.5 | Analysis panels: Inspector, Clip, StorySpace, History | — | `panels/InspectorPanelDock.tsx`, `panels/ClipPanelDock.tsx`, `panels/StorySpacePanelDock.tsx`, `panels/HistoryPanelDock.tsx` |
| C4.6 | Update DockviewLayout.tsx — import from panels/ | C4.1-C4.5 | `DockviewLayout.tsx` |

**Contract:**
- Each panel wraps existing component (no logic rewrite)
- `onMouseDown` → `setFocusedPanel(type)` for panels in PANEL_FOCUS_MAP
- Dark bg `#0d0d0d`, full height, overflow hidden
- Export all from `panels/index.ts`

---

## C5: Workspace Presets (Priority 3-MEDIUM)

**Goal:** UI for switching between Editing/Color/Audio/Custom layouts.

| Sub-ID | Task | Deps | Files |
|--------|------|------|-------|
| C5.1 | WorkspacePresetBar component (dropdown or tab strip) | C4 | `WorkspacePresets.tsx` |
| C5.2 | Preset definitions (4 layouts) | C5.1 | `useDockviewStore.ts` |
| C5.3 | Save custom layout (Cmd+Shift+L) | C5.2 | `useDockviewStore.ts` |

---

## C6: Hotkey Preset Selector (Priority 2-HIGH)

**Goal:** UI to switch between Premiere/FCP7/Custom presets.

| Sub-ID | Task | Deps | Files |
|--------|------|------|-------|
| C6.1 | HotkeyPresetSelector dropdown component | — | `HotkeyPresetSelector.tsx` |
| C6.2 | Wire to useCutHotkeys preset switching | C6.1 | `useCutHotkeys.ts` (read-only, coordinate with A) |
| C6.3 | Mount in Settings or Toolbar | C6.1 | `DockviewLayout.tsx` or toolbar |

---

## C7: Hotkey Editor (Priority 2-HIGH)

**Goal:** Full rebinding UI — list all 115 actions, show current key, click-to-rebind.

| Sub-ID | Task | Deps | Files |
|--------|------|------|-------|
| C7.1 | useHotkeyStore — action registry + custom overrides | — | `useHotkeyStore.ts` |
| C7.2 | HotkeyEditor component — table with search/filter | C7.1 | `HotkeyEditor.tsx` |
| C7.3 | Key capture modal (press key → assign) | C7.2 | `HotkeyEditor.tsx` |
| C7.4 | Conflict detection + reset to default | C7.3 | `useHotkeyStore.ts` |

---

## C8: DAG Y-axis Flip + timelineId (Priority 2-HIGH)

**Goal:** Fix inverted Y-axis in DAGProjectPanel, add timelineId prop for multi-timeline.

| Sub-ID | Task | Deps | Files |
|--------|------|------|-------|
| C8.1 | Y-axis fix in DAGProjectPanel layout direction | — | `DAGProjectPanel.tsx` |
| C8.2 | Add timelineId prop, wire to active timeline | C10 (optional) | `DAGProjectPanel.tsx` |

---

## C9: Mount Inspector/StorySpace/PULSE (Priority 2-HIGH)

**Goal:** Ensure Inspector, Clip, StorySpace, History panels actually render content (not null).

| Sub-ID | Task | Deps | Files |
|--------|------|------|-------|
| C9.1 | Verify each panel renders (not returning null) | C4 | panels/ wrappers |
| C9.2 | Wire PulseInspector to selected scene data | — | `PulseInspector.tsx` |
| C9.3 | Wire ClipInspector to selected clip data | — | `ClipInspector.tsx` |

---

## C10-C13: Multi-Timeline (Phase 198) — FUTURE

Sequential pipeline. Blocked until core editing works.

| ID | Task | Deps | Complexity |
|----|------|------|------------|
| C10 | Store refactor — `Map<string, TimelineInstance>` | — | high |
| C11 | TimelineTrackView → props-driven (timelineId) | C10 | high |
| C12 | Dockview multi-timeline wiring | C11, C3 | medium |
| C13 | Delete TimelineTabBar + parallel code | C12 | low |

**Contract (Phase 198):**
- No `Set<>` in serializable state — use `string[]` and `Record<string, boolean>`
- Active timeline gets keyboard, inactive gets mouse only
- Close fallback: most-recently-focused remaining timeline
- Each instance = separate dockview panel with `params: { timelineId }`

---

## C14-C16: Polish — FUTURE

| ID | Task | Deps | Priority |
|----|------|------|----------|
| C14 | Auto-Montage UI (3 buttons + progress) | — | 3 |
| C15 | Project Panel view modes (List/Grid/DAG) | — | 3 |
| C16 | Favorite markers: N key + Shift+M comment | — | 3 |

---

## Execution Order

```
Phase 2 (NOW):
  C4 → C9 → C5      (dockview panels pipeline)
  C6 → C7            (hotkey UI pipeline, parallel with above)
  C8                  (DAG fix, independent)

Phase 4 (FUTURE):
  C10 → C11 → C12 → C13   (multi-timeline)
  C14, C15, C16            (polish, parallel)
```

---

## File Ownership (Stream C)

```
client/src/components/cut/DockviewLayout.tsx       ← PRIMARY
client/src/components/cut/panels/                  ← NEW directory
client/src/components/cut/dockview-cut-theme.css    ← theme
client/src/store/useDockviewStore.ts               ← layout state
client/src/components/cut/HotkeyEditor.tsx         ← NEW
client/src/components/cut/HotkeyPresetSelector.tsx ← NEW
client/src/store/useHotkeyStore.ts                 ← NEW
client/src/components/cut/WorkspacePresets.tsx      ← NEW
client/src/components/cut/DAGProjectPanel.tsx       ← Y-axis fix only
client/src/store/useTimelineInstanceStore.ts       ← NEW (Phase 198)
client/src/components/cut/TimelineTabBar.tsx       ← refactor (Phase 198)
```

DO NOT TOUCH: useCutEditorStore.ts, useCutHotkeys.ts, TimelineTrackView.tsx (Stream A), cut_routes.py (Stream B).

---

*Generated by Opus-C on 2026-03-20*
*Protocol: ROADMAP_CUT_MVP_PARALLEL.md v1.0*
