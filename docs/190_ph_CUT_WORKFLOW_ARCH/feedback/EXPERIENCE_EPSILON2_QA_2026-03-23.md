# Experience Report: Epsilon-2 (QA-2) — 2026-03-23
**Agent:** Epsilon | **Branch:** claude/cut-qa-2 | **Session:** ~6 hours
**Role:** QA Engineer #2, Performance Guardian, Recon Hunter

---

## 1. What broke that shouldn't have?

**TimecodeField TC1-TC3 regression after multi-branch merge.** Tests were GREEN, then 3 branches merged to main simultaneously and `describe.serial` + TimecodeField input interaction broke. Root cause: Playwright `fill()` on controlled React input doesn't reliably trigger `handleConfirm` when store state changes between navigations. Delta later rewrote with `[title="Click to type timecode"]` selector which is more robust.

**Dockview tab backgrounds still navy blue after 5+ Gamma fixes.** `rgb(16,25,44)` and `rgb(0,12,24)` persisted through GAMMA-25 through GAMMA-35. Root cause was CSS variable `--dv-paneview-active-outline-color` defaulting to dodgerblue — a variable, not an inline style, so MutationObserver couldn't catch it. Finally fixed with explicit CSS var override.

**Debrief pipeline never worked on local fallback transport.** 4 attempts across session — `action=complete` never returned `debrief_requested` or `debrief_questions`. The entire debrief→CORTEX→ENGRAM learning loop is dead on local fallback. Only Mycelium transport has the injection (if implemented there at all).

## 2. What unexpectedly worked well?

**Performance exceeded all targets on first measurement.** Timeline scroll: 120fps avg (target was 60). Page load: 1.2s (target was 2s). Jank under 1.2%. Timeline virtualizes correctly — 14 visible clips out of 100 total. No optimization needed at current scale.

**Auto-commit scoping (Zeta Proof 1) worked perfectly.** `closure_files` filter correctly staged only listed files. Out-of-domain dirty file remained untracked. This is critical infrastructure that works.

**Tool hotkey coverage went from 0 to 36 GREEN in one spec file.** Key insight: `setFocusedPanel('timeline')` via store (not DOM click) before panel-scoped hotkeys. DOM click has side effects (seek, selection change). Store-direct is clean.

## 3. What idea came to mind that nobody else mentioned?

**Debrief-as-test: formalize the 6 provocative questions as a Playwright test suite.** Instead of asking agents, run automated "debrief" after every merge: check for console errors, color violations, dead imports, empty src attributes, seek boundary violations, panel visibility. The bug hunt script I wrote found 3 real bugs in 30 seconds — this should run in CI.

**Regression velocity metric:** Track not just GREEN count but GREEN-per-hour. This session: ~30 GREEN/hour. If velocity drops below 10/hour, it signals architectural debt blocking test progress.

**Test-first recon:** Reading feedback reports BEFORE writing tests is 10x more productive than exploring blind. The 14 missing items from debriefs generated 9 tasks and 3 direct bug fixes. Debrief reports are the most underutilized resource in the project.

## 4. What anti-pattern did you catch yourself doing?

**Writing tests with wrong selectors 3 times.** `button:text-is("Edit")` matched 2 elements (MenuBar + WorkspacePresets). `[data-testid="timecode-field"]` didn't match real testid `monitor-tc-source`. `soloedLanes` vs `soloLanes` (Set<string>). Lesson: always `grep` for actual testid/field name in source BEFORE writing test.

**Running tests from wrong directory.** The worktree root is NOT `client/` — Playwright needs to run from `client/` where `node_modules` lives. Lost 2 minutes each time. Should add `cwd: CLIENT_DIR` check at top of every session.

**Not checking if task already done before claiming.** TransportBar.tsx delete, focusPerPreset localStorage, FFmpeg progress pipe — all already done by other agents. Wasted 5 minutes checking each. Lesson: `task_board action=get` FIRST, then claim only if status=pending.

## 5. Session Stats

| Metric | Value |
|--------|-------|
| Tasks completed | 12 (E1-E9 + doc fix + 3 bug fixes) |
| Test specs written | 97 new specs |
| GREEN specs (Epsilon suites) | 91/97 (94%) |
| Global GREEN (all suites) | 183/226 (81%) |
| Bugs found (bug hunt) | 3 (seek clamp, empty src, dblclick) |
| Bugs fixed | 3 (seek clamp, empty src, containerWidth) |
| Recon tasks created | 9 from debriefs + 3 from hunt = 12 |
| Reviews completed | 4 (Gamma-29/30/31, Beta-B31, Beta-B4.1, Gamma cut-ux full diff) |
| Visual audits | 1 (45 color violations found) |
| Zeta proofs | 3 (auto-commit PASS, digest PARTIAL, debrief FAIL) |
| Performance baseline | 120fps scroll, 1.2s load, <1.2% jank |

## 6. Files Touched

### Test files (my domain):
- `client/e2e/cut_fcp7_hotkey_coverage_tdd.spec.cjs` — 44 specs
- `client/e2e/cut_undo_redo_tdd.spec.cjs` — 8 specs
- `client/e2e/cut_performance_scroll.spec.cjs` — 4 specs
- `client/e2e/cut_panel_interactions_tdd.spec.cjs` — 18 specs
- `client/e2e/cut_context_effects_tdd.spec.cjs` — 14 specs
- `client/e2e/cut_edge_cases_tdd.spec.cjs` — 9 specs
- `client/e2e/cut_layout_compliance_tdd.spec.cjs` — selector fixes
- `client/e2e/cut_timecode_trim_tdd.spec.cjs` — navigateToCut + selector fixes

### Bug fixes (Commander-authorized):
- `client/src/store/useCutEditorStore.ts` — seek() clamp to duration
- `client/src/components/cut/VideoPreview.tsx` — empty src="" → undefined
- `client/src/components/cut/TimelineTrackView.tsx` — containerWidth stale ref

### Docs:
- `docs/190_ph_CUT_WORKFLOW_ARCH/ROADMAP_E_PERFORMANCE.md` — strategic plan
- `docs/190_ph_CUT_WORKFLOW_ARCH/CUT_TARGET_ARCHITECTURE.md` — CUT acronym

## 7. Recommendations for Next Epsilon

1. **Run regression FIRST** — before any work, sync main and run all 17 suites. Baseline shifts constantly.
2. **Use `setFocusedPanel` via store** for panel-scoped hotkey tests — never click timeline to focus.
3. **Read ALL feedback reports** — gold mine of untracked bugs and ideas.
4. **Bug hunt script** — the Playwright edge-case scanner found 3 bugs in 30s. Run it after every merge wave.
5. **E8 CTX-R9 is now GREEN** — GAMMA-R9 merged. 14/14.
6. **Debrief pipeline is broken** — don't waste time retesting until Zeta confirms fix on local fallback.
7. **Alpha's P1 fixes** (Mark I/O, 3PT edit, ripple trim, JKL shuttle) — verify when they land. These will flip many RED tests GREEN.
