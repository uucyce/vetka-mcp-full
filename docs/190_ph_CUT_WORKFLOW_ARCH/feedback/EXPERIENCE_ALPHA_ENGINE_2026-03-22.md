# Experience Report: Alpha Engine Session 2026-03-22
**Agent:** OPUS-ALPHA-2 (Claude Code)
**Branch:** claude/cut-engine
**Duration:** Single session, 12 tasks, 141 tests
**Scope:** Precision editing, store migration, desktop build, bug fixes

---

## 1. WHAT WORKED

### Test-first velocity
Writing Python reference tests for every feature (formatTimecode, 3PT resolution, slip/slide/ripple/roll) before wiring the TypeScript caught real bugs early. The drop-frame timecode test at 60.0 seconds exposed a subtle frame boundary issue — 60s at 29.97fps = 1798 frames, NOT at the minute mark (which is frame 1800 ≈ 60.06s). Would have been a broadcast compliance bug.

### Incremental store migration
The `effective*` variable pattern worked perfectly for Phase 1. Instead of rewriting the entire data flow, I introduced `effectiveLanes`, `effectiveZoom`, etc. that resolve from instance store when multi-instance is active, else fall back to singleton. Zero breakage — the component works identically when no instance store data exists.

### Task board discipline
Every line of code traced to a task. The `vetka_task_board action=complete branch=claude/cut-engine` flow kept everything clean. 12 commits, 12 tasks, no orphaned code.

### FCP7 manual as spec
Reading actual FCP7 chapters before coding (Ch.36 Three-Point, Ch.44 Trim Tools, Ch.50 Match Frame) produced architecturally correct implementations. The "sequence marks take precedence over source marks" rule from Ch.36 is non-obvious but critical — without it, filling gaps in the timeline would be impossible.

### Parallel pure-function approach
Keeping core logic as pure functions (`resolveThreePointEdit`, `formatTimecode`, `parseTimecodeInput`) exported for testing, then wrapping in React hooks, made both testing and reasoning straightforward.

---

## 2. WHAT DIDN'T

### Worktree node_modules
The `claude/cut-engine` worktree doesn't have `node_modules` — every `npx` command fails until you symlink from main. Had to create the symlink manually. This should be automated in worktree setup.

### TypeScript strictness vs velocity
The codebase has ~50 pre-existing TS errors (unused vars, missing types in useSocket.ts, useArtifactMutations.ts). These block `tsc && vite build` — had to use `TAURI_PLATFORM=1 npx vite build` (skip tsc) for the Tauri build. Not ideal for production.

### Dockview layout corruption
The duplicate transport bar bug was caused by corrupt localStorage, not code duplication. My first fix (panel ID dedup guard) was correct but the REAL cause was deeper — the user had to hard-reload to trigger the cleanup. Diagnostic would have been faster with a browser DevTools screenshot showing the DOM tree.

### containerWidth non-reactive
The ruler label cutoff at 12s was a pre-existing bug exposed by my flex restructuring. `containerRef.current?.clientWidth || 800` is a common React anti-pattern — reading DOM measurements in render without state/effect. Should have caught this during the Timecode integration in Фаза 1.

---

## 3. ARCHITECTURAL INSIGHTS

### Three-Point Edit is the NLE litmus test
If your NLE can't do `I → O → , (comma)` to insert a clip at playhead from source marks, it's a drag-and-drop timeline, not an NLE. This single feature (resolveThreePointEdit + backend insert_at) transforms the workflow from "visual arrangement" to "precision editing." Every other NLE feature builds on this.

### JKL shuttle needs its own render loop
HTML5 `<video>` only supports forward playback at browser-determined rates. For reverse playback and speed > 2x, you MUST manually seek via requestAnimationFrame. The video element becomes a frame source, not a playback controller. This is why Premiere/Resolve have custom playback engines.

### Store migration should be lane-level, not field-level
The current `effective*` pattern works but creates 10+ shadow variables. A cleaner Phase 2 approach: create a `useTimelineData(timelineId?)` hook that returns `{ lanes, waveforms, zoom, scrollLeft, ... }` — resolving from instance store or singleton internally. Components call one hook instead of 10 selectors.

### Dockview is layout, not component model
Dockview manages panel positions, tabs, and drag. It should NOT drive component lifecycle. The duplicate transport bug happened because dockview's serialization preserved panel instances that shouldn't exist. Rule: components should be idempotent — rendering them twice should be harmless (or prevented at the component level, not the layout level).

---

## 4. BUGS FOUND (not fixed — outside scope)

1. **Source = Program video feed**: Both monitors still read from the same video element. `sourceMediaPath` and `programMediaPath` exist in store but VideoPreview doesn't use `feed` prop to switch. Gamma's domain.

2. **TransportBar.tsx still exists**: File is 800+ lines, marked `@deprecated`, never imported. Should be deleted to prevent confusion. Gamma domain (MenuBar.tsx ownership).

3. **Pre-existing TS errors**: ~50 errors in useSocket.ts, useArtifactMutations.ts, App.tsx, ChatPanel.tsx. Blocks `tsc` build. Not CUT-specific but blocks clean Tauri builds.

4. **BPMTrack labels overlap**: "AUD", "VIS", "SCR" labels at bottom left are tiny and clip against the timeline bottom edge. Minor visual issue.

5. **Autosave not wired to backend**: `useCutAutosave` calls `saveProject()` but it's a stub in the CutEditorLayoutV2 handler. No actual project persistence except through timeline ops.

---

## 5. RECOMMENDATIONS FOR SUCCESSOR

### Do
- **Read FCP7 PDF chapters before coding.** `docs/185_ph_CUT_POLISH/hotcuts/APPLE_FINALCUT7PRO_ENG.pdf` — the answers are in there.
- **Write Python reference tests first.** They're fast (0.03s for 40 tests) and catch logic bugs before you touch React.
- **Use `effective*` pattern** for any new reads that should eventually come from instance store. It's backwards-compatible.
- **Check dockview localStorage** when debugging visual duplicates. `localStorage.getItem('cut_dockview_editing')` — inspect the JSON for duplicate panel IDs.

### Don't
- **Don't touch MenuBar.tsx** — Gamma's territory. Same for VideoScopes, e2e specs (Delta).
- **Don't refactor singleton writes yet** — Phase 2 needs a `useTimelineData` hook designed first.
- **Don't add new store fields to useCutEditorStore** for timeline-specific data — put them in useTimelineInstanceStore.
- **Don't run `npm run build`** (includes tsc) — use `TAURI_PLATFORM=1 npx vite build` until TS errors are fixed.

### Priority for next session
1. Source/Program video split (VideoPreview feed prop)
2. Store migration Phase 2 (useTimelineData hook)
3. Delete TransportBar.tsx (dead code)
4. E2E tests for 3PT / JKL workflows

---

## 6. STORE MIGRATION STATUS

### Phase 1: COMPLETE ✅

| Area | Status | Notes |
|------|--------|-------|
| **Read lanes** | ✅ effectiveLanes | Falls back to singleton |
| **Read waveforms** | ✅ effectiveWaveforms | Falls back to singleton |
| **Read zoom** | ✅ effectiveZoom | Falls back to singleton |
| **Read scrollLeft** | ✅ effectiveScrollLeft | Falls back to singleton |
| **Read trackHeight** | ✅ effectiveTrackHeight | Falls back to singleton |
| **Read currentTime** | ✅ effectiveCurrentTime | Falls back to singleton |
| **Read duration** | ✅ effectiveDuration | Falls back to singleton |
| **Read markIn/Out** | ✅ effectiveMarkIn/Out | Falls back to singleton |
| **onProjectStateRefresh** | ✅ | Syncs backend data → active instance |
| **CutStandalone bridge** | ✅ | instanceRefresh called alongside editorSetLanes |

### Phase 2: NOT STARTED

| Area | Status | Recommendation |
|------|--------|----------------|
| **Write lanes** | ❌ | Needs useTimelineData hook |
| **Write zoom/scroll** | ❌ | updateTimeline() exists but not wired |
| **Write marks** | ❌ | Instance-scoped marks vs global |
| **Write selection** | ❌ | selectedClipIds: string[] in instance |
| **Snapshot on tab switch** | Partial | snapshotTimeline/restoreTimeline exist |
| **Delete singleton timeline fields** | ❌ | Phase 3 — after all reads+writes migrated |

### Key insight
The singleton store has ~50 timeline-related fields. Instance store has ~20. The gap is view state (trackHeights, hiddenLanes, etc.) that needs to be per-instance but currently lives flat in the singleton. Phase 2 should add these to TimelineInstance incrementally, not all at once.

---

*"12 задач. 141 тест. CUT теперь NLE. Следующий Alpha: Source/Program split + Store Phase 2."*
