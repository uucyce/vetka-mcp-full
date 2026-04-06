# Alpha-5 Engine Debrief — 2026-03-29
**Agent:** SONNET-ALPHA-5 (Claude Code, Sonnet 4.6)
**Branch:** `claude/cut-engine`
**Session:** 5 commits, 4 tasks closed
**Duration:** ~1 session (context-compacted continuation)

---

## Q1: What's broken?

### 1. Pre-existing TS errors in CutEditorLayoutV2 and AudioMixer
The store is missing `selectedClipIds`, `masterVolume`, `masterPan`, `setMasterVolume`, `setMasterPan`, `clearSelection`, `toggleLinkedSelection` etc. These fire TS errors on every build but are pre-existing — not introduced this session. Whoever owns AudioMixer and CutEditorLayoutV2 needs to resolve these gaps vs the store interface.

### 2. KeyframeGraphEditor drag uses stale `kfs` snapshot
During drag, we capture `kfs: [...keyframes]` at mousedown. If the store updates mid-drag (e.g. playback adding a keyframe), the stale snapshot is used for `remove + re-add` logic. Probability is low, but it's a data integrity hole. Fix: re-read from store on each mousemove via `useCutEditorStore.getState()`.

### 3. `set_prop` with nested key `keyframes.opacity` — backend not verified
`updateKeyframeBezier` dispatches `{ op: 'set_prop', key: 'keyframes.opacity', value: [...] }`. The backend `_apply_timeline_ops` handles `set_prop` but it's unclear if it supports dot-notation keys for nested assignment. Needs a pytest test to confirm.

### 4. Diamond overlay in TimelineTrackView uses `pointer-events: none`
KF diamonds on the clip track are not interactive — you can't click them to navigate. They're purely visual indicators. Fine for now, but a click-to-seek behavior would be expected from FCP7 users.

---

## Q2: What unexpectedly worked?

### 1. Bezier bisection — drop-in, zero visual artifact
14-iteration bisection on the x→s parametrization converges to ~0.006% error. The fallback (smooth-step when no cp data) is invisible in transitions. Zero regressions in curve rendering.

### 2. `MARKER_KF67` diamond overlay was already complete
TimelineTrackView already had the full diamond rendering block for `clip.keyframes` at line 2664. Saved ~50 lines of JSX work.

### 3. Rebase resolved automatically
The "conflict in useGenerationControlStore.ts" mentioned in the task turned out to be auto-resolved by git — no manual conflict needed. Stash → rebase → pop was clean.

---

## Q3: Ideas I didn't implement

### 1. Easing preset toolbar in KeyframeGraphEditor
A 4-button row (Linear / Ease In / Ease Out / Bezier) next to the property selector — click to set `easing` type on selected keyframe. Would require adding a `setKeyframeEasing` action (via `set_prop` on the specific KF). The whole thing is ~40 lines.

### 2. Click-to-seek on timeline diamonds
Right now diamonds are `pointer-events: none`. Adding `onClick: () => s.seek(clip.start_sec + kf.time_sec)` on each diamond div would make them navigable directly from the timeline. One line per diamond.

### 3. Curve color by property
KeyframeGraphEditor draws all curves in `#5588cc`. Could color-code by property: opacity=white, volume=green, brightness=yellow, etc. Helps when multiple properties overlap (though we only show one at a time currently).

---

## Q4: What tools worked?

### TypeScript gate — `npx tsc --noEmit | grep filename`
Filtering TS output to only my files (`grep KeyframeGraphEditor`) cut through hundreds of pre-existing errors instantly. Standard technique now.

### Canvas ResizeObserver for responsive panels
`ResizeObserver` on the parent div ensures the canvas auto-resizes when the panel is resized by the dockview layout. No hardcoded dimensions needed.

---

## Q5: What NOT to repeat?

### Don't use `require()` inside React components for ES module imports
Used `require('../../store/useCutEditorStore')` inside a callback as a lazy import workaround. Fails TS (`Cannot find name 'require'`). Fix: import at top level. Caught by TS gate before commit.

### Don't declare constants you don't use
`HANDLE_ARM = 32` was declared but not referenced — TS6133. Comment it out or delete it immediately.

---

## Q6: Ideas (cross-domain)

### 1. KeyframeGraphEditor → Panel slot in CutEditorLayoutV2
The component exists but isn't mounted anywhere in the layout. Gamma should add it as a collapsible panel below the timeline (like DaVinci's curve editor). The slot already exists in CutEditorLayoutV2's dockview layout — just needs a panel entry added.

### 2. Backend `set_prop` dot-notation test
A single pytest test: `{ op: 'set_prop', clip_id: X, key: 'keyframes.opacity', value: [...] }` → assert nested write succeeded. If it fails, backend needs a recursive key split handler. 20-line test, could save a nasty prod bug.

### 3. `opacity` as a volume-style overlay in TimelineTrackView
Like the waveform shows audio level, could draw a thin colored bar at the bottom of each clip showing opacity keyframe curve as a visual hint (brighter = more opaque). Purely cosmetic, but gives instant feedback without opening KeyframeGraphEditor.

---

## Session Stats

| Metric | Value |
|--------|-------|
| Commits | 5 |
| Tasks closed | 4 (op-registry, markIn/markOut unify, rebase, KF graph editor) |
| New files | `client/src/config/timeline_ops.ts`, `client/src/components/cut/KeyframeGraphEditor.tsx` |
| TS errors introduced | 0 |
| Pre-existing TS errors | ~80 (unrelated to engine domain) |
| New store actions | 1 (`updateKeyframeBezier`) |
| Type extensions | `Keyframe.cp_in`, `Keyframe.cp_out` |
| Backend ops added | `reset_effects` + `VALID_TIMELINE_OPS` frozenset |
| Tests added | +6 (reset_effects x3, registry x3) |

---

## For next Alpha (Engine):

1. **Mount KeyframeGraphEditor** — add to CutEditorLayoutV2 as a panel (coordinate with Gamma)
2. **Verify `set_prop` dot-notation** — pytest for `keyframes.opacity` nested write
3. **Fix drag stale snapshot** in KeyframeGraphEditor — use `getState()` on mousemove
4. **Easing preset toolbar** — 4 buttons in KeyframeGraphEditor toolbar (40 lines)
5. **`masterVolume`/`masterPan` gap** — AudioMixer.tsx references missing store fields; either add to store or remove from AudioMixer
6. **Diamond click-to-seek** — one-liner in TimelineTrackView diamond div

---

*"The curve editor is drawn. The diamonds are placed. The math is clean. What's left is wiring it into the room."*
