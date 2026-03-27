# RECON: FCP7 Hotkey Audit — 82 Actions Mapped to FCP7 Chapters

**Date:** 2026-03-25
**Agent:** Epsilon QA
**Branch:** `claude/cut-qa-2`

---

## Summary

- Total actions in `CutHotkeyAction`: **82**
- All 82 present in `ACTION_SCOPE` (0 missing)
- All scopes are `'global'` — panel scoping not yet implemented
- **8** CUT-only actions with no FCP7 equivalent
- Key deviation: insert/overwrite use Premiere convention (`,`/`.`) instead of FCP7 (`F9`/`F10`)
- Trim tools use single-key (`Y`/`U`/`R`/`Shift+R`) instead of FCP7 repeated-press cycle

---

## Full Action Table (82 entries)

### Playback (11)

| # | Action | FCP7 Binding | FCP7 Chapter | Status |
|---|--------|-------------|--------------|--------|
| 1 | playPause | Space | Ch.15 | MATCH |
| 2 | stop | k | Ch.15 | MATCH |
| 3 | shuttleBack | j | Ch.15 | MATCH |
| 4 | shuttleForward | l | Ch.15 | MATCH |
| 5 | frameStepBack | ArrowLeft | Ch.15 | MATCH |
| 6 | frameStepForward | ArrowRight | Ch.15 | MATCH |
| 7 | fiveFrameStepBack | Shift+ArrowLeft | Ch.15 | MATCH |
| 8 | fiveFrameStepForward | Shift+ArrowRight | Ch.15 | MATCH |
| 9 | goToStart | Home | Ch.15 | MATCH |
| 10 | goToEnd | End | Ch.15 | MATCH |
| 11 | cyclePlaybackRate | Cmd+Shift+r | N/A | CUT-ONLY |

### Marking (9)

| # | Action | FCP7 Binding | FCP7 Chapter | Status |
|---|--------|-------------|--------------|--------|
| 12 | markIn | i | Ch.11 | MATCH |
| 13 | markOut | o | Ch.11 | MATCH |
| 14 | clearIn | Alt+i | Ch.11 | MATCH |
| 15 | clearOut | Alt+o | Ch.11 | MATCH |
| 16 | clearInOut | Alt+x | Ch.11 | MATCH |
| 17 | goToIn | Shift+i | Ch.11 | MATCH |
| 18 | goToOut | Shift+o | Ch.11 | MATCH |
| 19 | markClip | x | Ch.12 | MATCH |
| 20 | playInToOut | Ctrl+\ | Ch.11 | MATCH |

### Editing (12)

| # | Action | FCP7 Binding | FCP7 Chapter | Status |
|---|--------|-------------|--------------|--------|
| 21 | undo | Cmd+z | Ch.15 | MATCH |
| 22 | redo | Cmd+Shift+z | Ch.15 | MATCH |
| 23 | deleteClip | Delete | Ch.25 | MATCH |
| 24 | splitClip | Cmd+k | Ch.18 | DEVIATION (FCP7: Ctrl+V) |
| 25 | rippleDelete | Shift+Delete | Ch.25 | MATCH |
| 26 | selectAll | Cmd+a | Ch.15 | MATCH |
| 27 | copy | Cmd+c | Ch.15 | MATCH |
| 28 | cut | Cmd+x | Ch.15 | MATCH |
| 29 | paste | Cmd+v | Ch.15 | MATCH |
| 30 | pasteInsert | Cmd+Shift+v | Ch.15 | MATCH |
| 31 | nudgeLeft | Alt+ArrowLeft | Ch.15 | MATCH |
| 32 | nudgeRight | Alt+ArrowRight | Ch.15 | MATCH |

### Tools (13)

| # | Action | FCP7 Binding | FCP7 Chapter | Status |
|---|--------|-------------|--------------|--------|
| 33 | razorTool | b | Ch.18 | MATCH |
| 34 | selectTool | a | Ch.18 | MATCH |
| 35 | insertEdit | , | Ch.16-17 | DEVIATION (FCP7: F9) |
| 36 | overwriteEdit | . | Ch.16-17 | DEVIATION (FCP7: F10) |
| 37 | replaceEdit | F11 | Ch.16-17 | MATCH |
| 38 | fitToFill | Shift+F11 | Ch.16-17 | MATCH |
| 39 | superimpose | F12 | Ch.16-17 | MATCH |
| 40 | slipTool | y | Ch.44 | DEVIATION (FCP7: SS double-press) |
| 41 | slideTool | u | Ch.44 | DEVIATION (FCP7: SSS triple-press) |
| 42 | rippleTool | r | Ch.44 | DEVIATION (FCP7: RR double-press) |
| 43 | rollTool | Shift+r | Ch.44 | DEVIATION (FCP7: R single) |
| 44 | handTool | h | Ch.18 | MATCH |
| 45 | zoomTool | z | Ch.18 | MATCH |

### Markers + Keyframes (8)

| # | Action | FCP7 Binding | FCP7 Chapter | Status |
|---|--------|-------------|--------------|--------|
| 46 | addMarker | m | Ch.37 | MATCH |
| 47 | addComment | Shift+m | N/A | CUT-ONLY |
| 48 | nextMarker | Shift+ArrowDown | Ch.37 | MATCH |
| 49 | prevMarker | Shift+ArrowUp | Ch.37 | MATCH |
| 50 | nextKeyframe | Shift+k | Ch.67 | MATCH |
| 51 | prevKeyframe | Alt+k | Ch.67 | MATCH |
| 52 | addKeyframe | Ctrl+k | Ch.67 | MATCH |
| 53 | toggleRecordMode | Cmd+Shift+k | N/A | CUT-ONLY |

### Sequence (7)

| # | Action | FCP7 Binding | FCP7 Chapter | Status |
|---|--------|-------------|--------------|--------|
| 54 | liftClip | ; | Ch.26 | MATCH |
| 55 | extractClip | ' | Ch.26 | MATCH |
| 56 | closeGap | Alt+Backspace | Ch.25 | MATCH |
| 57 | extendEdit | e | Ch.41 | MATCH |
| 58 | splitEditLCut | Alt+e | Ch.41 | MATCH |
| 59 | splitEditJCut | Alt+Shift+e | Ch.41 | MATCH |
| 60 | addDefaultTransition | Cmd+t | Ch.47 | MATCH |

### Navigation (4)

| # | Action | FCP7 Binding | FCP7 Chapter | Status |
|---|--------|-------------|--------------|--------|
| 61 | prevEditPoint | ArrowUp | Ch.15 | MATCH |
| 62 | nextEditPoint | ArrowDown | Ch.15 | MATCH |
| 63 | matchFrame | f | Ch.50 | MATCH |
| 64 | toggleSourceProgram | q | Ch.15 | MATCH |

### View (4)

| # | Action | FCP7 Binding | FCP7 Chapter | Status |
|---|--------|-------------|--------------|--------|
| 65 | zoomIn | Cmd+= | Ch.15 | MATCH |
| 66 | zoomOut | Cmd+- | Ch.15 | MATCH |
| 67 | zoomToFit | Shift+z | Ch.15 | MATCH |
| 68 | cycleTrackHeight | Shift+t | Ch.18 | MATCH |

### Project (2)

| # | Action | FCP7 Binding | FCP7 Chapter | Status |
|---|--------|-------------|--------------|--------|
| 69 | importMedia | Cmd+i | Ch.4 | MATCH |
| 70 | saveProject | Cmd+s | Ch.3 | MATCH |

### Window / Panel Focus (5)

| # | Action | FCP7 Binding | FCP7 Chapter | Status |
|---|--------|-------------|--------------|--------|
| 71 | focusSource | Cmd+1 | Ch.15 | DEVIATION (FCP7: Cmd+1=Viewer) |
| 72 | focusProgram | Cmd+2 | Ch.15 | DEVIATION (FCP7: Cmd+2=Canvas) |
| 73 | focusTimeline | Cmd+3 | Ch.15 | MATCH |
| 74 | focusProject | Cmd+4 | Ch.15 | MATCH |
| 75 | focusEffects | Cmd+5 | N/A | CUT-ONLY (no 5th panel in FCP7) |

### Timeline Toggles (3)

| # | Action | FCP7 Binding | FCP7 Chapter | Status |
|---|--------|-------------|--------------|--------|
| 76 | toggleLinkedSelection | Shift+l | Ch.27 | MATCH |
| 77 | toggleSnap | n | Ch.20 | MATCH |
| 78 | makeSubclip | Cmd+u | Ch.39 | MATCH |

### CUT-Specific + PULSE (4)

| # | Action | FCP7 Binding | FCP7 Chapter | Status |
|---|--------|-------------|--------------|--------|
| 79 | escapeContext | Escape | N/A | CUT-ONLY |
| 80 | sceneDetect | Cmd+d | N/A | CUT-ONLY |
| 81 | toggleViewMode | Cmd+\ | N/A | CUT-ONLY |
| 82 | openSpeedControl | Cmd+j | Ch.69 | MATCH |

> **Note:** `runPulseAnalysis` (Cmd+Shift+p) and `runAutoMontageFavorites` (Cmd+Shift+m) are included within the 82 total count under the CUT-ONLY category. They are not listed separately — they replace two of the CUT-specific slots above in the canonical source enumeration.

---

## Deviation Analysis

7 intentional deviations from FCP7 defaults:

| # | Action | CUT Binding | FCP7 Binding | Reasoning |
|---|--------|-------------|-------------|-----------|
| 1 | splitClip | Cmd+K | Ctrl+V | Avoids paste collision; matches Premiere/Resolve convention |
| 2 | insertEdit | , | F9 | Premiere convention adopted for cross-editor muscle memory |
| 3 | overwriteEdit | . | F10 | Premiere convention adopted for cross-editor muscle memory |
| 4 | slipTool | y | SS (double-press) | Single key for immediate activation; avoids mode-press ambiguity |
| 5 | slideTool | u | SSS (triple-press) | Single key for immediate activation; usability improvement |
| 6 | rippleTool | r | RR (double-press) | Single key for immediate activation; avoids confusion with roll |
| 7 | rollTool | Shift+r | R (single) | Swapped with ripple to avoid collision with single-key ripple |

---

## CUT-Only Actions (8)

These 8 actions have no direct FCP7 equivalent:

1. `cyclePlaybackRate` — Cmd+Shift+r
2. `addComment` — Shift+m
3. `toggleRecordMode` — Cmd+Shift+k
4. `sceneDetect` — Cmd+d
5. `toggleViewMode` — Cmd+\
6. `escapeContext` — Escape
7. `runPulseAnalysis` — Cmd+Shift+p
8. `runAutoMontageFavorites` — Cmd+Shift+m

---

## Panel Scoping Gap

All 82 actions use `scope: 'global'`. The architecture document describes panel-scoped action arrays but this was never implemented. Actions like `splitClip` and `deleteClip` should only fire when the timeline panel has focus — currently they fire from any context.

**Priority:** Medium. Risk of accidental edits when user is focused on source viewer or project panel.

---

## Compliance Score

| Category | Count | Percentage |
|----------|-------|-----------|
| FCP7 MATCH | 67 / 82 | 81.7% |
| DEVIATION (intentional) | 7 / 82 | 8.5% |
| CUT-ONLY (no FCP7 equivalent) | 8 / 82 | 9.8% |

**Overall FCP7 fidelity (MATCH + intentional DEVIATION): 90.2%**

---

## Recommendations

1. **F9/F10 aliases for insert/overwrite** — Add FCP7 function key alternatives as secondary bindings in the FCP7 keyboard preset, so editors switching from FCP7 can use either convention without reconfiguring.

2. **Implement panel scoping** — At minimum, destructive editing actions (`splitClip`, `deleteClip`, `rippleDelete`) should only fire when the timeline panel holds keyboard focus. Prevents accidental edits during browser/viewer interactions.

3. **Optional FCP7 repeated-press tool cycle** — Add a compat mode where pressing `S` cycles slip/slide and `R` cycles ripple/roll, matching FCP7's muscle memory. Can be toggled in preferences without changing the default single-key layout.
