# Gamma-4 UX/Panel Architect — Experience Report
**Date:** 2026-03-22
**Agent:** OPUS-GAMMA-4 (claude/cut-ux)
**Session:** Wave 8, 12 tasks (10 code + 2 research), 12 commits
**Scope:** Workspace presets, CSS architecture, DnD, panel verification, focus persistence, tab context menus

---

## 1. WHAT I DID

| Task | Commit | Impact |
|------|--------|--------|
| GAMMA-5: Preset-specific layouts (C5) | `434c783c` | Editing/Color/Audio workspace configurations |
| GAMMA-6: C9 panel audit | — | All 12 panels verified rendering content |
| GAMMA-7: CSS token sync | `23e0a489` | 47 hardcoded hex → var() |
| GAMMA-8: Mount WorkspacePresets | `3f4ed901` | Orphaned component now live in UI |
| GAMMA-9: !important cleanup | `dfc62a7a` | 63 → 10 !important (84% reduction) |
| GAMMA-10: Project→Timeline DnD | `2da1aee0` | Clips draggable from Project to Timeline |
| GAMMA-11: HotkeyPresetSelector | — | Already integrated in MenuBar submenu |
| GAMMA-12: Focus persistence | `27316e41` | focusedPanel saved/restored per workspace |
| GAMMA-13: focusPerPreset localStorage | `f7449889` | Focus survives page reload |
| GAMMA-14: Custom drag preview | `cb49df0c` | Thumbnail + filename badge on drag |
| GAMMA-15: Panel tab context menu | `3f6c147f` | Close, Close Others, Maximize on right-click |
| — | `715fd731` | Experience report + ROADMAP_C2 sub-roadmap |

---

## 2. WHAT WORKED

### Double-class specificity eliminates !important systematically
`.dockview-theme-dark.dockview-theme-dark .dv-tab` has higher specificity than dockview's `.dockview-theme-dark .dv-tab` without needing `!important`. This pattern reduced 63 `!important` to 10 — the remaining 10 are all justified (pointer-events for Tauri, inline style overrides, focus outline kills).

### CSS custom property chain: tokens.css → dockview-cut-theme.css
Replacing hardcoded hex (`#000`, `#0a0a0a`, etc.) with `var(--bg-primary)`, `var(--bg-secondary)` etc. means any future theme change in tokens.css automatically propagates to dockview panels. Zero visual change, maximum maintainability.

### Recon scouts (3 parallel) before coding
Launching 3 Explore agents simultaneously (panel audit, CSS audit, workspace audit) gave complete domain picture in ~2 minutes. This prevented wasted work — C9 turned out to need zero code (all panels render), WorkspacePresets turned out to be functional but unmounted, HotkeyPresetSelector was already in MenuBar.

### Timeline DnD was half-built — just needed the drag source
Timeline's `handleLaneDrop` already reads `text/cut-media-path` from dataTransfer. ProjectPanel clips just needed `draggable=true` + `onDragStart`. 16 lines to complete the pipeline.

---

## 3. WHAT DIDN'T WORK / OBSTACLES

### First-time workspace switch requires page reload
When user switches to Color workspace for the first time (no saved layout), we can't rebuild dockview in-place — the API doesn't have a "clear all panels" method. Current solution: `window.location.reload()`. Works but loses state. After first switch, the layout is saved to localStorage and subsequent switches are instant via `fromJSON()`.

**Potential fix:** Pre-build all 4 preset layouts on first mount, serialize them, and save to localStorage. But this requires creating/destroying panels in rapid succession which is risky with dockview.

### 6 keyboard dispatches still blocked on Alpha
Undo, Redo, Add Marker, Comment Marker, Insert, Overwrite in MenuBar still use synthetic KeyboardEvent dispatch. Their handlers live in CutEditorLayoutV2 (Alpha territory). Need Alpha to extract to store actions.

### Focus persistence is in-memory only
`focusPerPreset` lives in Zustand store — not persisted to localStorage. On page reload, defaults kick in (editing→timeline, color→program). This is acceptable for now since workspace switches within a session preserve focus correctly.

---

## 4. ARCHITECTURAL DECISIONS

### Preset builders as standalone functions
Each workspace layout is a plain function `(api: DockviewApi, scriptText: string) => void`. This makes layouts:
- Testable (call with mock API)
- Composable (custom preset could extend editing)
- Readable (each builder is self-contained, ~20 lines)

### WorkspacePresets mounted ABOVE dockview, not inside
The preset bar is a thin strip above `<DockviewReact>`, not a dockview panel. This means:
- It's always visible regardless of layout
- It doesn't participate in dockview's save/restore
- It doesn't interfere with panel drag operations

### Color workspace: right column for grading tools
Color preset puts Color Corrector + LUT Browser as tabs in a right column, with Scopes below them. This mirrors DaVinci Resolve's color page layout where grading controls are always to the right of the preview.

### Audio workspace: tabbed monitors
Audio preset tabs Source and Program monitors together (same group) since audio mixing rarely needs dual preview. This frees horizontal space for the Mixer panel.

---

## 5. DOMAIN STATUS (all Gamma-owned)

| Area | Status | Notes |
|------|--------|-------|
| DockviewLayout.tsx | ACTIVE | Preset builders, maximize, focus wiring |
| dockview-cut-theme.css | CLEAN | 10 !important (all justified), var() synced |
| useDockviewStore.ts | COMPLETE | toggleMaximize, togglePanel, focusPerPreset |
| MenuBar.tsx | 80% | 5 dispatches → store, 6 remain (blocked on Alpha) |
| WorkspacePresets.tsx | COMPLETE | Mounted, switching works |
| panels/*.tsx | VERIFIED | All 12 render content |
| ProjectPanel.tsx | COMPLETE | DnD draggable added |
| DAGProjectPanel.tsx | COMPLETE | Y-axis fixed |
| HotkeyEditor.tsx | COMPLETE | Mounted via MenuBar lazy |
| HotkeyPresetSelector.tsx | ORPHANED OK | Functionality in MenuBar submenu |

---

## 6. RECOMMENDATIONS FOR SUCCESSOR (Gamma-5)

### Priority 1: Wire 6 remaining MenuBar dispatches (after Alpha)
- `undo()`, `redo()` → store actions (currently fetch calls in CutEditorLayoutV2)
- `addMarker(kind)` → store action
- `insertEdit()`, `overwriteEdit()` → store actions
**Prerequisite:** Alpha extracts these to useCutEditorStore

### Priority 2: Pre-seed workspace layouts
Build all 4 preset layouts on first mount, serialize, save to localStorage. This eliminates the reload on first switch.

### Priority 3: Persist focusPerPreset to localStorage
Add `localStorage.setItem('cut_focus_per_preset', JSON.stringify(map))` in saveFocusForPreset. Load in store initializer.

### Priority 4: DnD improvements
- Drag preview image (clip thumbnail) instead of default browser ghost
- Multi-clip drag (drag selection, not single clip)
- Drop position indicator in timeline (vertical line at drop point)

### Don't touch (blocked/future):
- C10-C13 Multi-timeline (blocked on Alpha store refactor)
- CSS @layer migration (needs testing infrastructure)
- HotkeyPresetSelector component — keep orphaned, functionality lives in MenuBar

---

## 7. FILES TOUCHED THIS SESSION

```
MODIFIED:
  client/src/components/cut/DockviewLayout.tsx      — preset builders, WorkspacePresets mount, seed-save
  client/src/components/cut/dockview-cut-theme.css   — 47 hex→var(), 53 !important removed
  client/src/store/useDockviewStore.ts               — focusPerPreset, toggleMaximize
  client/src/components/cut/MenuBar.tsx              — switchWorkspace focus save/restore
  client/src/components/cut/WorkspacePresets.tsx     — focus save/restore, reload fallback
  client/src/components/cut/ProjectPanel.tsx         — draggable clips + custom drag preview
```

---

## 8. LATE-SESSION ADDITIONS (GAMMA-13 through GAMMA-15)

### Custom drag preview (GAMMA-14)
`setDragImage()` with an offscreen div: 80px card, dark background, thumbnail (or modality icon for audio), filename with ellipsis. Created on dragstart, removed on next animation frame. Applied to both grid and list views. The browser's default ghost was a full DOM clone — ugly and uninformative. The custom preview shows exactly what you're dragging.

### Panel tab context menu (GAMMA-15)
Document-level contextmenu listener checks if target is inside `.dv-tab`. If yes, finds the panel ID by matching tab text to `api.panels`, renders a dark menu at click position. Three items: Close Panel (`api.removePanel`), Close Others in Group (iterate group panels, remove all except clicked), Maximize/Restore (same as backtick key). Dismisses on any click. Styled to match TimelineTrackView's clip context menu.

### focusPerPreset localStorage (GAMMA-13)
10-line addition: read `cut_focus_per_preset` from localStorage on store init, write on every `saveFocusForPreset()`. Defaults: editing→timeline, color→program, audio→timeline.

---

## 9. DOMAIN EXHAUSTION REPORT

All Gamma-owned features are now implemented or blocked on Alpha:

| Status | Items |
|--------|-------|
| **DONE** | Workspace presets (C5), Panel wrappers (C4), DAG Y-axis (C8), Panel audit (C9), CSS architecture, DnD, Focus persistence, Tab context menu, Maximize, WorkspacePresets mount, 5 menu dispatches |
| **BLOCKED on Alpha** | 6 remaining MenuBar dispatches (need store actions from CutEditorLayoutV2) |
| **LOW PRIORITY** | Pre-seed workspace layouts (R2), CSS @layer (R7), Hotkey Editor improvements (R6) |
| **FUTURE** | Multi-timeline dockview wiring (C12/C13 — blocked on Alpha C10/C11) |

**Gamma domain is exhausted.** No more unblocked high-priority work.

---

*"The workspace is the editor's desktop. Each preset is a different desk arrangement for a different task. When you switch desks, your coffee cup should be where you left it."*
