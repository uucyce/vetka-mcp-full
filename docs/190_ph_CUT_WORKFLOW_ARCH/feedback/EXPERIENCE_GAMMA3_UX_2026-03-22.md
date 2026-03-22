# Gamma-3 UX/Panel Architect — Experience Report
**Date:** 2026-03-22
**Agent:** OPUS-GAMMA-3 (claude/cut-ux)
**Session:** Wave 7, 3 tasks completed (4 commits incl. merge)
**Scope:** Menu dispatch cleanup, panel maximize, DAG Y-axis fix, TransportBar deletion

---

## 1. WHAT I DID

| Task | Commit | Files | Lines |
|------|--------|-------|-------|
| GAMMA-2: Menu keyboard dispatch → store actions | `a2cc15a8` | MenuBar.tsx | +50/-5 |
| GAMMA-3: Panel maximize (backtick key) | `dfc724d2` | DockviewLayout, MenuBar, useDockviewStore | +36 |
| GAMMA-4: DAG Y-axis flip + TransportBar cleanup | `8be6314f` | DAGProjectPanel, ProjectPanel, -TransportBar | +10/-909 |

**Net: -900 lines removed** (TransportBar.tsx finally killed after 3 waves of "someone should delete this").

---

## 2. WHAT WORKED

### Direct store calls eliminate invisible dependencies
Replacing `document.dispatchEvent(new KeyboardEvent(...))` with `store.getState().action()` in MenuBar was the right pattern. The keyboard dispatch chain was: MenuBar → synthetic KeyboardEvent → document keydown → useCutHotkeys handler → CutEditorLayoutV2 handler → store mutation. The direct call is: MenuBar → store mutation. Same result, zero intermediaries, trivially debuggable.

For actions where no store method existed (splitClip, rippleDelete, sceneDetect), I inlined the logic from CutEditorLayoutV2. This creates temporary duplication, but it's better than synthetic keyboard events. TODO markers point to the refactor path when Alpha adds store actions.

### Dockview maximize API is clean
`api.maximizeGroup(panel)` / `api.exitMaximizedGroup()` / `api.hasMaximizedGroup()` — three calls, zero surprises. The store wrapper (`toggleMaximize`) is 8 lines. Keydown listener in DockviewLayout correctly skips input/textarea/contentEditable. Menu item in Window provides discoverability.

### TransportBar deletion was blocked for 3 waves — ownership boundaries were the bottleneck
Every predecessor said "kill TransportBar.tsx." None could because CutEditorLayoutV2 (Alpha territory) imported it. The actual fix required Alpha to remove the import first (P0 fix), then Gamma to delete the file. **Lesson:** cross-domain dead code needs Commander coordination, not just agent initiative.

---

## 3. WHAT DIDN'T WORK / OBSTACLES

### 6 remaining keyboard dispatches in MenuBar — blocked on Alpha
Undo, Redo, Add Marker, Comment Marker, Insert, Overwrite still use `document.dispatchEvent(new KeyboardEvent(...))`. Their handlers live in CutEditorLayoutV2 and there are no equivalent store actions. I can't touch CutEditorLayoutV2 (Alpha) or add actions to useCutEditorStore (Alpha).

**Recommendation for Commander:** Ask Alpha to extract these 6 handlers into store actions:
- `undo()` / `redo()` — currently fetch calls in CutEditorLayoutV2
- `addMarker(kind)` — currently inline in CutEditorLayoutV2
- `insertEdit()` / `overwriteEdit()` — currently calls `performSourceEdit` in CutEditorLayoutV2

Once in store, Gamma can wire MenuBar in 5 minutes.

### Predecessor experience report said "TransportBar: 0 imports" — was wrong
When I grepped, TransportBar was imported and mounted in CutEditorLayoutV2:574. The predecessor checked on their branch where it may have been different, or the code changed after their session. **Lesson:** always verify predecessor claims before acting. `grep` is truth, experience reports are opinions.

### CLAUDE.md ownership lists don't cover edge cases
My CLAUDE.md says "useCutEditorStore.ts — UI state: focusedPanel, viewMode only." But `toggleMaximize` lives in useDockviewStore (my file), not useCutEditorStore. The boundary was fine this time, but the split of "UI state" across two stores creates ambiguity. Consider consolidating ownership lists by functional domain, not file.

---

## 4. DAG Y-AXIS FIX DETAILS

The previous default was `flipY = true` which made Y = -(sec * PX_PER_SEC), placing START at bottom and END at top. This felt wrong — scripts read top-to-bottom, film flows top-to-bottom, every flowchart reads top-to-bottom.

Changed default to `flipY = false` → Y = sec * PX_PER_SEC → START at top, END at bottom. Toggle button preserved for anyone who prefers inverted view.

The fix was 4 lines of state change + comment updates. Architecture doc §2.2 specifies top-to-bottom as the canonical direction.

---

## 5. RECOMMENDATIONS FOR SUCCESSOR (Gamma-4)

### Priority 1: Wire remaining 6 menu dispatches (after Alpha adds store actions)
See section 3. This is the single biggest UX debt in MenuBar.

### Priority 2: C9 — Verify panel content rendering
Inspector, Clip, StorySpace, History panels may return null or placeholder. Need to verify each renders actual content when data exists. Quick verification task.

### Priority 3: C5 — Workspace Presets UI
WorkspacePresets.tsx exists but may be a stub. The store (`useDockviewStore`) has save/load/switch — the UI just needs a preset bar or dropdown.

### Priority 4: Focus persistence across workspace switches
When user switches from Editing to Color workspace, `focusedPanel` resets to null. Should restore the last focused panel for each preset. Requires a `Map<PresetName, FocusPanelId>` in store.

### Don't touch (blocked/future):
- C10-C13 Multi-timeline (blocked on Alpha store refactor)
- C6-C7 Hotkey Editor (needs coordination with Alpha on useCutHotkeys.ts)
- CSS isolation (research task, no clear solution yet)

---

## 6. FILES TOUCHED THIS SESSION

```
MODIFIED:
  client/src/components/cut/MenuBar.tsx           — 5 keyboard dispatches → direct calls
  client/src/components/cut/DockviewLayout.tsx     — backtick keydown → toggleMaximize
  client/src/store/useDockviewStore.ts             — toggleMaximize() method
  client/src/components/cut/DAGProjectPanel.tsx    — flipY default false (START at top)
  client/src/components/cut/ProjectPanel.tsx       — comment: TransportBar → MenuBar

DELETED:
  client/src/components/cut/TransportBar.tsx       — 900 lines dead code, 0 imports
```

---

*"Three tasks, four commits, minus nine hundred lines. The best code is the code you delete."*
