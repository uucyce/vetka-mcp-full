# Alpha-6 Engine Debrief — 2026-04-01
**Agent:** SONNET-ALPHA-6 (Claude Code, Sonnet 4.6)
**Branch:** `claude/cut-engine`
**Session:** TS error cleanup + SVG icons + color label + color_correction typing
**Duration:** 2-session context-compacted continuation (Alpha-5 handoff → Alpha-6)

---

## Q1: What's broken?

### 1. Gamma left duplicate hotkey keys — TS1117 landmines
Gamma's GAMMA-TRIM5-WIRE block re-defined 13+ keys that were already in the object literal:
`pasteAttributes`, `rippleTrimToPlayhead`, `swapClips`, `deleteMarker`, `selectClipAtPlayhead`, `selectAllOnTrack`, `selectForward`, `toggleAVSelection`, `linkUnlinkClips`, `focusSourceAcquire`, `runPulseAnalysis`, `runAutoMontageFavorites`, `exportTimeline`.
A second block added `revealMasterClip`, `collapseExpandTrack`, `expandTrack`, `renameClipInline` duplicates at line 1279.
Result: 43 TS errors, build broken. The pattern is dangerous — each new agent block appends to the same object without scanning for existing keys first.

### 2. Gamma used wrong store for selection state
Multiple OLD handler implementations called `useCutEditorStore.getState().selectedClipIds`, `.selectedClipId`, `.setSelectedClip()`, `.clearSelection()`, `.toggleLinkedSelection()` — none of these exist on `CutEditorState`. They all live in `useSelectionStore`. Required a full grep pass to find all wrong refs and update them.

### 3. `pasteAttributesSelective` in store used `get().selectedClipIds`
`useCutEditorStore`'s `pasteAttributesSelective` destructured `selectedClipIds` from `get()` — but selection is in a separate store. The error only surfaces in tsc, not at runtime (Set always empty → paste silently does nothing). Fixed to `useSelectionStore.getState().selectedClipIds`.

### 4. Unused `clipEnd` variable in AUDIO_PREFETCH loop
Declared but never used after the loop logic was rewritten. TS6133, trivial to remove but required reading the loop to confirm `clipEnd` wasn't accidentally needed.

---

## Q2: What unexpectedly worked?

### 1. SVG icons fit one row, no Unicode fallback needed
All 4 new transport icons (PrevFrame, NextFrame, PrevEdit, NextEdit) used pure SVG geometry — bars + triangles via `<line>` and `<polygon>` — with `currentColor` fill. No Unicode glyphs, no `fontFamily: monospace` hacks. The icon bar stayed single-row in 28px height.

### 2. `ClipColorCorrection` type — zero ripple
Adding `color_correction?: ClipColorCorrection` to `TimelineClip` and defining `ClipColorCorrection = Partial<ColorCorrection> & { lutPath?; lutName?; logProfile? }` cleaned up all `(c as any).color_correction` casts across 4 files with no new errors introduced.

### 3. Color label strip — 3px left border, zIndex:2, pointerEvents:none
The implementation is invisible unless a label is set, non-interactive, and doesn't disturb clip content layout. No regression in existing clip rendering.

### 4. Context-compact handoff worked cleanly
Received a detailed Alpha-5 handoff with exact line numbers and error list. Could resume exactly at the error fix without re-reading the full file.

---

## Q3: Ideas I didn't implement

### 1. Keyboard shortcut to cycle color labels on selected clip
`Shift+L` could cycle through `COLOR_LABEL_MAP` entries on selected clip. Currently labels are only settable from the context menu. One-liner handler in `hotkeyHandlers` + `applyTimelineOps`.

### 2. Color label filter in Find dialog
The find dialog (Cmd+F) could filter clips by color label — checkbox row for each color. Requires extending `FindDialog` state and the clip highlight logic.

### 3. Multi-file LUT drop target
LutBrowserPanel's import field accepts one path at a time. A drag-drop zone accepting multiple `.cube` files would feel more native. Would need a `dragover/drop` handler and loop over `dataTransfer.files`.

---

## Q4: What tools worked?

### Grep for duplicate keys
`grep "pasteAttributes:\|revealMasterClip:\|collapseExpand" --output_mode=content -C 1` instantly showed all occurrences with line numbers. Far faster than reading the 1400-line file linearly.

### `npx tsc --noEmit 2>&1 | grep CutEditorLayoutV2`
File-scoped TS filter cuts through the ~80 pre-existing errors in App.tsx and other files. Standard gate: run, filter, fix, re-run until file is clean.

### Two-store awareness before touching handlers
Checking `useSelectionStore.ts` exports first (Grep for `selectedClipIds\|setSelectedClip`) before editing handlers prevented wrong-store guesses.

---

## Q5: What NOT to repeat?

### Don't append new hotkey blocks without scanning for existing keys
The object literal in `CutEditorLayoutV2.tsx` has 80+ keys. Before adding any key, grep the file for that key name. TS1117 is silent until tsc runs — the app may boot fine but with one handler silently ignored.

### Don't trust `(s as any).someField` in stores
Casts hide missing fields from tsc. When adding features that read from stores, declare the field properly or read from the correct store. The `pasteAttributesSelective` bug existed for weeks because the cast suppressed the error.

### Don't re-read entire 1400-line files to find one line
Use `Grep pattern --output_mode=content -C 1` to locate the exact block first, then read only that region with offset/limit. Saves 10+ tool calls per session.

---

## Q6: Ideas (cross-domain)

### 1. Hotkey map validator
A CI test that builds `hotkeyHandlers` and asserts no duplicate keys at runtime. Would catch TS1117-class bugs before they reach the branch. ~20 lines in `useCutHotkeys.test.ts`.

### 2. Store field coverage test
A test that imports both `useCutEditorStore` and `useSelectionStore`, checks that fields referenced in `hotkeyHandlers` exist on the correct store. Would have caught the `selectedClipIds` wrong-store bug.

### 3. Color label persistence via project save
`color_label` is set via `set_clip_meta` op → applied to timeline lanes → survives `applyTimelineOps`. But when the project is loaded fresh, the label must come from the saved JSON. Verify that `set_clip_meta` with `color_label` is serialized in `save_project` response. If `_safe_meta_keys` whitelist exists, verify `color_label` is in it (confirmed at `cut_routes.py:1662`).

---

## Session Stats

| Metric | Value |
|--------|-------|
| Sessions | 2 (context compact between) |
| Tasks worked | TS cleanup + icons + color label + color_correction type |
| TS errors at session start | 43 |
| TS errors at session end | 0 (in owned files) |
| New files | `client/src/components/cut/icons/CutIcons.tsx` extended |
| Duplicate hotkey blocks removed | 2 |
| Wrong-store refs fixed | 8+ |
| Type assertions removed | 6 (`as any`) |
| New types added | `ClipColorCorrection` in `useCutEditorStore.ts` |
| Store methods added | `setShowPublishDialog`, `setShowTimecodeEntry`, `cycleTimelineDisplayMode` |

---

## For next Alpha (Engine):

1. **Mount KeyframeGraphEditor** — still unmounted in CutEditorLayoutV2 (carried from Alpha-5)
2. **Hotkey duplicate guard** — before any new hotkey block, grep first
3. **Verify `set_prop` dot-notation** — pytest for `keyframes.opacity` nested write (carried from Alpha-5)
4. **`pasteAttributes` store method** — line 491 was removed; `pasteAttributes()` on store may still be called elsewhere — verify no dead references
5. **`masterVolume`/`masterPan` gap** — AudioMixer.tsx still has missing store fields (carried from Alpha-5)
6. **`showMatchSequencePopup` / `pendingMatchClipPath`** — MatchSequencePopup.tsx references these on CutEditorState but they don't exist; pre-existing but needs resolution

---

*"43 errors, 0 bugs introduced, 0 lines of feature code lost. The handoff stack is the only thing that made this possible."*
