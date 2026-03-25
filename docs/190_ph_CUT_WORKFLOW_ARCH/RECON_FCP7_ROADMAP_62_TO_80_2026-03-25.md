# RECON: FCP7 Compliance Roadmap — 62%(stated) → 70%(actual) → 80%(target)

**Author:** Epsilon QA Agent
**Date:** 2026-03-25
**Branch:** `claude/cut-qa-2`
**Status:** Final Synthesis

---

## Key Discovery

The compliance matrix was STALE. Real coverage is ~68-70% after code audit found 10 features marked missing/partial that are actually implemented:

1. **Slip/Slide drag** — fully functional via `applyTimelineOps`
2. **Snap indicator** — visual indicator rendered at line 1931
3. **Cross-lane drag** — `originalLaneId` tracked, `move_clip` sends `lane_id`
4. **pasteAttributes/splitEditL/J undo** — now route through `applyTimelineOps`
5. **deleteMarker** — exists in store at line 1230
6. **makeSubclip** — handler in `CutEditorLayoutV2` line 838
7. **Match Frame (F)** — fully implemented handler
8. **Drop frame timecode** — full algorithm in `TimecodeField.tsx`
9. **Type-to-seek timecode** — implemented (click → edit → Enter)
10. **3-way color corrector + video scopes** — ColorWheel + waveform/vectorscope/histogram/parade all working

The stated 62% figure should be revised upward to ~70% as the baseline for all future planning and dispatch.

---

## Roadmap: 3 Tiers to 80%

### Tier 1: XS Wins (~4 dev-days, +4.5% → reaches ~73%)

Low-hanging fruit — code exists, just needs wiring.

#### Alpha tasks
- Wire 7 missing mark handlers: `goToIn`, `goToOut`, `clearIn`, `clearOut`, `clearInOut`, `markClip`, `playInToOut` — all LOW effort (seek/set store values)
- Fix Add Edit (Cmd+K) undo bypass in MenuBar — route through `split_at` op
- Fix Ripple Delete undo bypass in MenuBar — call `extractClip()` instead of inline mutation
- Wire Scene Detection to store action (endpoint already works)
- 5-frame step handlers (`fiveFrameStepBack`/`Forward`)

#### Beta tasks
- Wire AudioMixer pan to store (`setLanePan` already exists, currently `useState`)
- Wire master volume to store (currently `useState`, not exported to render)

#### Gamma tasks
- Wire File menu items (New/Open/Save As) to WelcomeScreen flow
- Wire Export sub-menu to ExportDialog with format pre-selection
- Add Drop Frame toggle to SequenceSettingsDialog (store has `setDropFrame`, `TimecodeField` already reads it)

---

### Tier 2: S Wins (~8 dev-days, +5.5% → reaches ~78.5%)

#### Alpha tasks
- Slip/Slide/Roll tool drag handler verification + E2E tests (drag behavior exists but untested)
- Replace Edit (F11) / Fit to Fill (Shift+F11) / Superimpose (F12) — verify handlers + write E2E tests
- Nudge left/right handlers + 5-frame nudge variants
- Extend Edit verification
- Progressive JKL shuttle (rAF speed accumulation loop)

#### Beta tasks
- Keyframe hotkey handlers: `addKeyframe` (Ctrl+K), `nextKeyframe` (Shift+K), `prevKeyframe` (Alt+K)
- Add Default Transition (Cmd+T) verification + visual feedback
- MulticamViewer angle video previews (replace placeholder divs with `VideoPreview`)
- Speed Control Cmd+J hotkey wiring

#### Gamma tasks
- Panel focus Cmd+1-5 physical activation via Dockview API
- Cursor change per active tool (CSS cursor on `TimelineTrackView`)
- Marker delete UI button in timeline context menu
- Subclip button in ProjectPanel (handler already exists)
- Chapter/duration marker types in marker system

---

### Tier 3: M Wins (if needed, ~4 dev-days, +1.5% → reaches ~80%)

#### Beta tasks
- Audio scrubbing during timeline drag (Web Audio API)
- Transition real-time preview during playback

#### Gamma tasks
- Two-up trim preview for Slip/Slide/Roll operations
- Maximize panel (backtick key)

---

## Low-Hanging Fruit from Code Audit (16 items)

| # | Finding | Agent | Effort |
|---|---------|-------|--------|
| 1 | Add Edit (Cmd+K) bypasses undo — route through `split_at` op | Alpha | trivial |
| 2 | Ripple Delete bypasses undo — call `extractClip()` | Alpha | trivial |
| 3 | AudioMixer pan: `useState` → `store.setLanePan` (already exists) | Beta | trivial |
| 4 | MulticamViewer placeholders → `VideoPreview` per angle | Beta | small |
| 5 | Clip Enable/Disable stub — needs type + store + backend op | Alpha+Beta | medium |
| 6 | Scene Detection: direct fetch → `store.runSceneDetection()` | Alpha | trivial |
| 7 | File menu New/Open/Save As/Export disabled — wire to existing flows | Gamma | small |
| 8 | Find (Cmd+F) disabled — new feature needed | Gamma | medium |
| 9 | Composite Mode (blend modes) — no backend | Alpha+Beta | medium |
| 10 | Freeze Frame — no implementation | Alpha+Beta | medium |
| 11 | Scale to Sequence — transform infra exists, just compute ratio | Alpha | trivial |
| 12 | Color Curves — preset only, no interactive editor | Beta | large |
| 13 | Master volume: `useState` → store (not exported to render) | Beta | trivial |
| 14 | Insert/Delete Tracks — no backend ops | Alpha | medium |
| 15 | Zero MulticamViewer UI tests | Epsilon | small |
| 16 | Zero tests for Freeze Frame, Clip Enable, Composite Mode | Epsilon | small |

---

## Architecture Blockers (affect multiple items)

1. **Source/Program Monitor split** — same video feed. Blocks: Match Frame reverse, 3PT editing, panel-scoped I/O marks
2. **JKL Progressive Shuttle** — fixed ±5s, not speed accumulation. Blocks professional playback feel
3. **Tool state machine visual feedback** — tools activate but lack cursor change + preview
4. **Two-up trim display** — no dual preview during trim operations

These blockers are architectural scope decisions for Commander. None of the Tier 1 or Tier 2 XS/S wins are blocked by them.

---

## Timeline Estimate

| Tier | Scope | Dev-days | Cumulative % |
|------|-------|----------|--------------|
| Baseline (post-audit) | — | — | ~70% |
| Tier 1 (XS wins) | ~4 dev-days | 4 | ~73% |
| Tier 2 (S wins) | ~8 dev-days | 12 | ~78.5% |
| Tier 3 (M wins) | ~4 dev-days | 16 | ~80% |
| **Total** | | **~16 dev-days** | **80%** |

---

## Agent Workload Distribution

| Agent | Task Count | Focus Area |
|-------|------------|------------|
| Alpha | 15 tasks | Editing ops, handlers, store wiring, undo fixes |
| Beta | 10 tasks | Keyframes, audio, multicam, effects |
| Gamma | 9 tasks | Panels, menus, UI, visual indicators |
| Epsilon | 3 tasks | Test coverage for new features |

---

## Dispatch Notes for Commander

- **Start with Tier 1 trivial items** — most are single-file wiring tasks, ideal for parallel Alpha/Beta/Gamma dispatch
- **Undo bypass fixes (items 1, 2)** are highest priority: they are regressions in existing features, not new work
- **Architecture blockers** should be scoped as separate tasks only if Commander decides to pursue 3PT editing or dual-monitor mode — they do not gate the 80% target
- **Epsilon owns test coverage** for all new Tier 1/2 features as they land, not after the fact
- **Do not re-run the compliance matrix** until at least Tier 1 is merged — the current stated 62% is misleading and will cause duplicate work
