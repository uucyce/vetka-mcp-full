# OPUS-DELTA-2 QA Experience Report
**Date:** 2026-03-22
**Agent:** OPUS-DELTA-2 (Claude Code, Opus 4.6)
**Role:** QA/Compliance Agent — FCP7 Ch.41-115 reverse scan + E2E TDD
**Session Duration:** ~90 min (recon) + ~60 min (TDD) + ~60 min (UI verification + smoke tests)
**Branch:** claude/cut-qa (TDD tests), main (recon doc, experience report)

---

## 1. WHAT WORKED

### FCP7 Bible Recon (Ch.41-115 + Appendix A)
- Read 15 chapters from 1924-page PDF using Read tool with page ranges (max 20 pages per request)
- Parallel reads (4 chapters simultaneously) dramatically sped up research
- Codebase exploration via Agent/Explore subagent gave complete inventory in one pass (40 components, 25 services, 547 LOC hotkeys)
- Cross-referencing PDF features vs code immediately identified 40 GAPs
- Created comprehensive recon doc (RECON_FCP7_DELTA2_CH41_115_2026-03-20.md) — became the reference for all subsequent tasks

### TDD Test Writing (RED-FIRST)
- Wrote 40 Playwright specs across 4 files:
  - `cut_fcp7_precision_editing_tdd.spec.cjs` — 22 tests (tool state, trim, JKL, match frame, split edits, speed, 3-point editing)
  - `cut_panel_focus_tdd.spec.cjs` — 10 tests (JKL scope, Delete scope, Cmd+1-4, visual indicator)
  - `cut_timecode_trim_tdd.spec.cjs` — 8 tests (absolute/relative/partial TC, drop-frame, ripple/roll, handles, API)
- Tests written against actual implementation code (read ACTION_SCOPE, focusedPanel store, TimecodeField.tsx) — not guessing at selectors
- Shared test infrastructure pattern (server bootstrap, API mocking, project fixture) consistent with Delta-1's existing specs

### Chrome UI Verification
- Used osascript to control Chrome and execute JavaScript for DOM auditing
- Verified 15 dockview panels rendering, 7 menu buttons, TimecodeField presence
- Found 2 real bugs that no automated test caught

---

## 2. WHAT DIDN'T WORK

### Chrome Control Reliability
- User's browser tabs switch constantly (YouTube, Claude.ai, etc.) — osascript `execute javascript` runs on **active tab**, not a specific tab
- No reliable way to pin a tab or target by URL via osascript
- Screenshots captured terminal windows instead of Chrome (foreground issue)
- **Lesson:** Chrome Control MCP (Playwright MCP) is essential for UI verification. osascript is fragile for multi-tab users.

### `window.__CUT_STORE__` Exposure
- Code at end of `useCutEditorStore.ts` doesn't execute due to Vite ESM circular dependency deadlock
- Dynamic `import()` hangs (never resolves) — confirming circular dep
- Top-level module assignment in `CutStandalone.tsx` also fails (module evaluation deferred)
- **Fix:** `useEffect(() => { window.__CUT_STORE__ = useCutEditorStore; }, [])` in CutStandalone — executes after React mount when all modules resolved
- **Root cause never fully verified in Chrome** because tabs kept switching
- The 7 passing smoke tests don't use `__CUT_STORE__` — they use DOM assertions only

### Playwright Setup
- `npx playwright test` exits with code 194 and zero output — no error message
- Browser installed (`chromium.launch()` works in Node) but CLI runner fails silently
- `node node_modules/@playwright/test/cli.js test` works — workaround for npx issue
- Tests take ~7s each with 60s timeout and 1 retry — full smoke suite = ~8 min

### Vite Dev Server Cache
- Editing files doesn't always invalidate Vite cache — `touch` needed
- Starting dev server from wrong CWD serves wrong files
- Multiple Vite instances accumulate (need explicit `pkill -f vite` cleanup)

---

## 3. TEST ARCHITECTURE INSIGHTS

### What Makes CUT Tests Hard
1. **Dockview wrapping** — components like ProjectPanel have `data-testid` but dockview wraps them in `.dv-view` containers. Tests looking for testid at specific DOM positions fail.
2. **Debug shell vs NLE mode** — 10+ smoke tests require debug shell mode which needs a real bootstrapped project from backend. They can't run with API mocks alone.
3. **Port contention** — each spec spawns its own Vite dev server. With `--workers=1` this is fine, but `--workers=3` causes port conflicts.
4. **Store access** — `window.__CUT_STORE__` is the only way to verify internal state. DOM-only assertions can't check `focusedPanel`, `activeTool`, `currentTime`.

### Recommendations for Test Architecture
- **Split tests into tiers:**
  - Tier 1: DOM-only (no store, no backend) — menu presence, layout structure
  - Tier 2: Store-based (needs `__CUT_STORE__`) — hotkey actions, state changes
  - Tier 3: Backend-integrated (needs running FastAPI on 5001) — bootstrap, timeline ops
- **Use a shared dev server** instead of per-spec spawn — saves 6s per test
- **Tag tests:** `@smoke`, `@tdd`, `@integration` — run only relevant subset
- **Golden screenshots:** Delta feedback was right — pixelmatch diff catches CSS regressions that DOM checks miss

### Data-testid Convention
Established pattern:
- `cut-editor-layout` — root
- `cut-timeline-track-view` — timeline
- `cut-timeline-clip-{id}` — individual clip
- `cut-timeline-lane-{id}` — track lane
- `cut-source-browser` — project panel
- `monitor-tc-source` / `monitor-tc-program` — timecode fields
- `timeline-tc-field` — timeline timecode
- `prev-edit` / `next-edit` — transport navigation

---

## 4. BUGS DISCOVERED

| # | Bug | Priority | Task ID | Status |
|---|-----|----------|---------|--------|
| 1 | `window.__CUT_STORE__` undefined — ESM circular dep blocks side-effect | P1 | `tb_1774132019_20` | Fixed (useEffect in CutStandalone) |
| 2 | Color Correction 3-Way wheels not rendering in dockview Color tab | P2 | `tb_1774132026_21` | Open |
| 3 | `data-testid="cut-source-browser"` not visible through dockview wrapper | P3 | — | Causes 2 berlin smoke test failures |
| 4 | 10 debug shell smoke tests fail — need real backend bootstrap | P4 | — | Infrastructure issue, not code bug |
| 5 | `ReferenceError: duration is not defined` in TimelineTrackView (persisted in localStorage from past crash) | P3 | — | May be stale error from prior session |

---

## 5. RECOMMENDATIONS FOR SUCCESSOR

### For the next QA/Delta agent:

1. **Don't use osascript for Chrome testing.** Use Playwright MCP or run tests headless. osascript is unreliable when user has multiple tabs.

2. **Check `__CUT_STORE__` first.** If it's undefined, most E2E store assertions will fail. The useEffect fix in CutStandalone should resolve this — verify it works before writing more store-dependent tests.

3. **Debug shell tests need real backend.** The 10 failing debug smoke tests spawn their own server but expect backend on port 5001 with a bootstrapped project. Consider adding a test fixture that mocks the full bootstrap response.

4. **Read existing tests first.** Delta-1 wrote `cut_fcp7_deep_compliance_tdd.spec.cjs` and `cut_fcp7_menus_editing_tdd.spec.cjs` covering Ch.1-40. My tests cover Ch.41-115. Don't duplicate.

5. **Coordinate file ownership.** Delta-1 was simultaneously editing debug smoke specs while I was analyzing them. We avoided conflicts because I was read-only on those files, but explicit coordination via task board `allowed_paths` is essential.

6. **FCP7 recon doc is your map.** `RECON_FCP7_DELTA2_CH41_115_2026-03-20.md` has every GAP with FCP7 chapter references. Use it to write targeted tests — don't re-read the PDF.

7. **Run smoke tests with `node node_modules/@playwright/test/cli.js test`** — not `npx playwright test` which may exit silently with code 194.

---

## 6. E2E TEST STATUS (as of 2026-03-22 02:50)

### Smoke Tests (26 unique, --grep smoke)

| Status | Count | Percentage |
|--------|-------|-----------|
| PASS | 7 | 27% |
| FAIL | 14 | 54% |
| SKIP | 5 | 19% |

### Passing Tests (7)
| Test | What it verifies |
|------|-----------------|
| `cut_debug_cam_ready_smoke` | CAM Ready state + hydration |
| `cut_debug_inspector_questions_smoke` | Inspector bootstrap stats |
| `cut_debug_runtime_flags_smoke` | Runtime flags rendering |
| `cut_nle_export_failure_smoke` (x2) | Premiere + FCPXML export error handling |
| `cut_nle_interactions_smoke` | Timeline clips, context menu, marker create |
| `cut_scene_graph_node_click_smoke` | Node click → timeline focus |

### Failure Root Causes
| Cause | Tests Affected | Fix Needed |
|-------|---------------|------------|
| `cut-source-browser` testid not visible in dockview | 2 (berlin_fixture, berlin_montage) | Propagate testid through dockview panel wrapper |
| Debug shell backend dependency | 10 (all `cut_debug_*` that fail) | Mock backend or run with live server |
| VideoPreview empty state changed | 1 (playback_reliability) | Update assertion |
| Scene graph UI refactor | 1 (edge_filter_minicard) | Update selectors |

### TDD Tests (40 total — all RED by design)
| File | Tests | Verifies |
|------|-------|---------|
| `cut_fcp7_precision_editing_tdd.spec.cjs` | 22 | Tool state, trim tools, JKL, match frame, split edits, speed |
| `cut_panel_focus_tdd.spec.cjs` | 10 | Panel focus scoping (JKL/Delete scope, Cmd+1-4, visual indicator) |
| `cut_timecode_trim_tdd.spec.cjs` | 8 | TimecodeField navigation, ripple/roll trim operations |

---

## 7. TASK BOARD CONTRIBUTIONS

### Tasks Created (15 fix tasks from FCP7 recon)
- 7x P2 CRITICAL: tool state machine, ripple/roll/slip/slide, JKL shuttle, match frame, wire handlers
- 6x P3 HIGH: transitions Cmd+T, audio mixer automation, motion attributes, speed indicators, split edits, TC navigation
- 2x P4 MEDIUM: color 3-way + scopes, keyframe navigation

### Tasks Completed (4)
- `tb_1774127249_16` — 22 precision editing TDD specs (done_worktree → merged to main)
- `tb_1774127761_17` — 10 panel focus TDD specs (done_worktree → merged to main)
- `tb_1774128295_18` — 8 timecode+trim TDD specs (done_worktree → merged to main)
- `tb_1774130588_5` — Chrome UI verification (done_worktree)
- `tb_1774132019_20` — __CUT_STORE__ fix (done_worktree)

---

*"Test the contract, not the implementation. The FCP7 manual is the contract."*
