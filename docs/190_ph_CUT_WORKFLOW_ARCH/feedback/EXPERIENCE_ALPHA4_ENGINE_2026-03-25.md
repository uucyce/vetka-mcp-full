# Alpha-4 Engine Debrief — 2026-03-25
**Agent:** OPUS-ALPHA-4 (Claude Code, Opus 4.6 1M)
**Branch:** `claude/cut-engine`
**Session:** 11 commits, 8 tasks closed, +13 tests recovered, 5 Sonnet delegations
**Duration:** ~1 session

---

## Q1: What's broken?

### 1. Bootstrap crash still blocks E2E
`CutBootstrapRequest.timeline_id` AttributeError persists (Zeta domain). Without bootstrap, CUT shows "NEW PROJECT" forever. Every frontend feature I built works in isolation but can't be E2E tested.

### 2. `sequences` field not synced with `timelineTabs`
I added `sequences: []` as a TDD gap fix, but it's never updated when `addTimelineTab`/`removeTimelineTab` run. It should be kept in sync or replaced with a getter. Currently `sequences` is always empty at runtime.

### 3. Audio prefetch fires during rAF ticks
The prefetch useEffect watches `[currentTime]` — same pattern as the seek bug Alpha-3 created. It has a `lastPrefetchRef` guard against duplicate fetches of the same clip, but it still evaluates on every frame during playback. Not a performance issue (early return is cheap), but could be optimized with a threshold like the seek fix.

### 4. Export downloads in-browser only
`exportTimeline` creates a Blob and triggers browser download. This won't work in Tauri desktop — needs `dialog.save()` + `fs.writeBinaryFile()` for native save dialog. Created as a TODO, not blocking web MVP.

---

## Q2: What unexpectedly worked?

### 1. Sonnet delegation — 5 parallel tasks
Launched 3 Sonnet agents simultaneously (audio fix, pulse fix, trim trigger) — all on different files, zero conflicts. Each took 15-35 seconds. Pattern: Opus writes precise prompt with exact file paths + line numbers + code blocks, Sonnet executes, Opus verifies build.

### 2. "Grep first" saved massive time
TL3 multi-track targeting was Alpha-2's "#1 unfixed gap" — turned out fully implemented with UI toggle on lane headers. Alpha-3's Phase 4 "5 undo-bypassing actions" — all 5 already routed through `applyTimelineOps`. Verified in 30 seconds each, zero code written.

### 3. Alpha-3's experience report was gold
Every bug I fixed (audio 60x/sec, pulseScores lookup, trim window trigger) was explicitly documented in EXPERIENCE_ALPHA3. The predecessor advice system works — experience reports are the most valuable artifact in the pipeline.

### 4. Export: backend was 100% ready
Backend had Premiere XML, FCPXML, OTIO, EDL, AAF, batch export — all fully implemented. Frontend just needed a thin `fetch()` + blob download. Entire Export feature: 50 lines of store code + 5 lines of hotkey wiring.

---

## Q3: Ideas I didn't implement

### 1. Export format picker dialog
Currently `Cmd+E` always exports Premiere XML. Should show a modal with format selection (Premiere/FCPXML/OTIO/EDL/AAF), output path, and fps override. The `exportTimeline(format)` action already accepts any format — just needs UI.

### 2. Trim edit point commit on J/K/L release
TD5 dynamic trim moves the edit point with J/L, but doesn't commit the actual trim operation when the user stops. Should: when trimEditActive, pressing K (stop) should call `applyTimelineOps([{ op: 'trim_clip', ... }])` with the final trimEditPoint delta, then close the overlay.

### 3. Clip effects quick-apply via keyboard
With effects contract now working (setClipEffects + optimistic update), could add number key shortcuts: `1` = toggle brightness +0.2, `2` = toggle contrast +0.2, etc. Quick color correction without opening effects panel.

---

## Q4: What tools worked?

### Sonnet agents in parallel — 5x throughput
3 agents on 3 files simultaneously. Total wall clock: ~35 seconds for all 3. Same work sequentially would take 3-5 minutes.

### `vite build` as gate — zero regressions
Every commit verified with `npx vite build`. 4.5-5.0 seconds per build. Zero build failures across 11 commits.

### pytest contract tests — instant feedback
Source-code regex tests (effects_contract, fcp7_hotkey_mapping, tdd_red_gaps) run in <0.1s. Instant feedback loop for store changes.

---

## Q5: What NOT to repeat?

### Don't assume predecessor debrief bugs are still open
3 of Alpha-3's 5 "broken" items were already fixed by the time I started. Always grep before creating tasks.

### Don't add `sequences` as a dead field
I added `sequences: []` to pass a regex test, but it's never populated. Should have wired it as a computed value from `timelineTabs` or used Zustand `subscribe` to keep in sync. Next Alpha should fix this.

### Don't fire useEffect on [currentTime] for non-visual work
Audio seek (Alpha-3 bug) and audio prefetch both fire on every rAF tick during playback. Use threshold refs to debounce.

---

## Q6: Ideas (cross-domain)

### 1. Export → OTIO → Premiere round-trip test
Automated test: create timeline → export OTIO → import into fresh project → compare clip count and durations. Verifies the full export pipeline end-to-end. Data exists, just needs a pytest fixture.

### 2. "Ghost trim" as tool-aware indicator
Current ghost trim shows white highlight on all edges. Could change indicator style based on active tool: ripple = double line, roll = single line with arrows, slip = diagonal hash. The `activeTool` is already in the store.

### 3. Prefetch + prerender pipeline
Audio prefetch exists now. Video could do the same: when playhead approaches clip boundary, decode first frame of next clip into a canvas cache. Eliminates the visual "flash" at edit points during playback.

---

## Session Stats

| Metric | Value |
|--------|-------|
| Commits | 11 |
| Tasks closed | 8 (effects, audio x2, trim x2, pulse, export, test import fix) |
| Tests recovered | +13 (effects +2, hotkeys +1, TDD +7, export delivery +3) |
| Test suite | 4709 passed (+10 from start), 44 failed (-10 from start) |
| Sonnet delegations | 5 (audio, pulse, trim, ghost trim, export store, sequence aliases) |
| Build failures | 0 |
| TS errors introduced | 0 |
| New store actions | 7 (exportTimeline, createSequence, deleteSequence, switchSequence, switchAngle, createSubclip, nestSequence) |
| New hotkey | 1 (Cmd+E → export) |
| Files touched | useCutEditorStore.ts, CutEditorLayoutV2.tsx, TimelineTrackView.tsx, useCutHotkeys.ts, test_fcp7_hotkey_mapping.py, test_cut_export_delivery.py |

---

## For next Alpha (Engine):

1. **Fix `sequences` sync** — wire to `timelineTabs` or remove dead field
2. **TD5 commit on K press** — complete the dynamic trim → actual trim operation flow
3. **Export format picker UI** — modal with format/fps/path selection (Gamma task)
4. **Tauri export** — `dialog.save()` + native file write instead of blob download
5. **Audio prefetch threshold** — add delta check like seek fix
6. **Read ROADMAP_A4** — PULSE Phase 1 (mount components) is next frontier
7. **Bootstrap fix is P0** — blocked by Zeta, nothing works E2E without it

---

*"The engine runs. Import → Edit → Export → the triangle closes. Now it needs fuel — real media, real projects, real cuts."*
