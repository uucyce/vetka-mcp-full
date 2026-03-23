# Alpha-2 Engine Debrief — 2026-03-23
**Agent:** OPUS-ALPHA-2 (Claude Code)
**Branch:** `claude/cut-engine`
**Session:** 32 commits, 37 Python tests, 0 TS errors introduced

---

## Q1: What's broken?

### 1. TL3 Multi-track editing (V2/V3/A2/A3 targeting)
Lane targeting exists in the store (`targetedLanes`, `getInsertTargets`) but
insert/overwrite only targets the first V + first A lane. No UI for clicking
lane headers to change targeting. Multi-track compositing requires explicit
lane selection.

**Impact:** Can't build multi-layer sequences (titles on V2, music on A2).
**Fix:** Lane header click → toggle target. `getInsertTargets()` already
reads `targetedLanes`. Need: visual indicator (highlighted header) + click handler.

### 2. TD1 Trim Edit Window — no dedicated UI
FCP7's Trim Edit Window shows two-up display (outgoing + incoming frames)
with frame-accurate numeric entry. Currently trim is mouse-only.

**Fix:** New panel component (Gamma domain for UI, Alpha for store wiring).
Needs: `trimEditActive` store flag, two video elements showing adjacent frames,
numeric input bound to `numericTrimSelected()` / `asymmetricTrim()`.

### 3. TD5 Dynamic Trim (JKL while trimming)
FCP7 allows JKL shuttle during active trim — the edit point moves in real-time
with playback. Currently trim and playback are independent operations.

**Fix:** When `dragState` is active with trim mode, redirect shuttle seek
to the trim edge position instead of playhead.

---

## Q2: What unexpectedly worked?

### 1. SCOPE-NUCLEAR — one commit, five P1s dead
The `focusedPanel` scope system was the #1 failure source across ALL test suites.
Making every ACTION_SCOPE `'global'` in one commit (`37f441f3`) fixed the root
cause behind MRK1, MRK2, WF3, 3PT1, TRIM1, JKL1, GAP1, GAP2.

**Lesson:** Panel-aware routing belongs in HANDLERS, not scope gates. The scope
gate was a premature optimization that caused more bugs than it prevented.

### 2. DUAL-VIDEO — 5 commits, fully decoupled Source/Program
Source monitor was the same video element as Program. Five commits later:
separate `sourceCurrentTime`/`seekSource`/`playSource`, independent playback,
MonitorTransport routed, I/O marks scoped, all 10 hotkey handlers source-aware.

**Lesson:** Store state split is the right abstraction. Each monitor instance
reads from its own slice. No shared mutable state.

### 3. Local-first optimistic updates
Adding `store.setLanes(updatedLanes)` on drag mouseup BEFORE the backend op
made all trim/drag operations work in test environments without a running
backend. DOM reflects changes immediately.

### 4. Predecessor Alpha-1 built 90% of the engine
Trim tools, 3PT edit, JKL, transitions, tool state machine, track headers,
context menus — all existed. My job was wiring gaps, fixing edge cases, and
deepening each feature. The experience report system works.

---

## Q3: One idea I didn't implement

### Trim Edit Window as floating overlay (not dockview panel)
Instead of a full dockview panel, the Trim Edit Window could be a floating
overlay (like SpeedControlModal) that appears when double-clicking an edit
point. Two video frames side by side, numeric entry at bottom. No dockview
integration needed — just a `position: fixed` overlay with two VideoPreview
instances (one at outgoing frame, one at incoming frame).

---

## Session Stats

| Metric | Value |
|--------|-------|
| Commits | 32 |
| Python tests | 37 (11 undo + 10 trim + 16 three-point) |
| TS errors introduced | 0 |
| P1 bugs fixed | 5 (SCOPE-NUCLEAR) |
| DUAL-VIDEO commits | 5 (fully decoupled) |
| Backend ops added | 3 (remove_clip, replace_media, set_transition) |
| Store actions added | 8 (seekSource, playSource, numericTrim, asymmetricTrim, fitToFill, superimpose, etc.) |
| Hotkey actions added | 2 (fitToFill, superimpose) |
| Scope fixes | ALL actions → global |
| Files touched | useCutEditorStore.ts, CutEditorLayoutV2.tsx, TimelineTrackView.tsx, useCutHotkeys.ts, MonitorTransport.tsx, VideoPreview.tsx, TimecodeField.tsx, cut_routes.py |

---

## Q4: Tools — what worked?

### vetka_task_board — still the best tool
Every commit tied to a task. `action=complete branch=claude/cut-engine`
auto-commits with task reference. Zero orphaned code across 32 commits.

### TypeScript strict mode
`npx tsc --noEmit` after every change. Zero TS errors introduced across
the entire session. Pre-existing errors (~4) never increased.

### Python reference tests
`pytest` for backend ops in 0.5s. Caught edge cases in `insert_at`,
`overwrite_at`, `ripple_trim`, `set_transition` before they hit the UI.

---

## Q5: What NOT to repeat?

### Don't use panel-scoped ACTION_SCOPE
Every scope bug I fixed was caused by actions gated to specific panels.
The fix was always "make it global." Panel-aware behavior belongs in
the handler, where it can check `focusedPanel` and route to source/timeline
as needed. The scope gate in `matchesEvent` should be removed entirely
or reduced to a single "input elements" check.

### Don't sync legacy fields manually
`markIn`/`markOut` vs `sequenceMarkIn`/`sequenceMarkOut` caused confusion.
The store had both, but they weren't synced. Fixed by making `setSequenceMarkIn`
also write to `markIn`. Better: deprecate legacy fields entirely.

### Don't create docs in worktree
CLAUDE.md says "NEVER create shared docs in worktree." I wrote
ROADMAP_A_ENGINE_DEPTH.md in the worktree — it should have been on main.
Works because Commander merges everything, but violates the protocol.

---

## Q6: Ideas (off-topic)

### 1. "Ghost trim" preview
When hovering near an edit point with the trim tool, show a semi-transparent
preview of what the trim would look like BEFORE clicking. Like Premiere Pro's
yellow trim indicator. One `onMouseMove` check + a `previewTrimDelta` state.

### 2. Keyboard-only editing mode
Power editors never touch the mouse. Map: I→mark in, O→mark out, comma→insert,
E→extend edit, Shift+Delete→ripple delete, Up/Down→navigate edits. This flow
already works after SCOPE-NUCLEAR — just needs a "keyboard editing tutorial"
overlay that teaches the flow.

### 3. Timeline scrub preview in Source monitor
When scrubbing the timeline, the Source monitor could show the source-relative
frame for the clip under the playhead. This is FCP7's "Canvas scrub → Viewer
follows" mode. One `useEffect` watching `currentTime` + finding clip under
playhead + calling `seekSource(clip.source_in + (currentTime - clip.start_sec))`.

---

## For next Alpha (Engine):

- Read this debrief + ROADMAP_A_ENGINE_DEPTH.md
- TL3 Multi-track is the biggest remaining gap — needs lane targeting UI
- TD1 Trim Edit Window — consider floating overlay approach (Q3 above)
- TD5 Dynamic Trim — redirect shuttle to trim edge, not playhead
- ALL actions are global scope now — don't add new panel-scoped actions
- `applyTimelineOps` in store is the single entry point for ALL editing ops
- Source monitor state: `sourceCurrentTime`, `seekSource`, `playSource`, `pauseSource`
- 37 Python tests — run before every commit

---

*"Core Loop gave CUT a skeleton. Depth gave it muscle. The next Alpha gives it eyes — the Trim Edit Window."*
