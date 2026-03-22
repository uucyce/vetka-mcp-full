# Delta QA Debrief — 2026-03-22
**Agent:** Delta (Opus) | **Role:** QA & FCP7 Compliance | **Session:** ~3 hours

## Results
- Smoke: 17 fail → **0 fail, 16 pass**
- TDD: 24 fail → **16 fail, 73 pass**
- Total: **89 pass / 16 fail / 135 total**

---

## Q1: What's broken? (including other agents' zones)

**DockviewLayout default tab order.** Graph tab activates last because `addPanel({ direction: 'within' })` makes the last-added tab active. Every test that needs ProjectPanel must click the PROJECT tab first. This isn't a test issue — real users see Graph on launch too. **Fix: Alpha should swap the addPanel order or call `api.getPanel('project')?.api.setActive()` after layout init.**

**`focusedPanel` defaults to `null`.** The hotkey system treats `null` as `'timeline'` (line 695 fallback), but this only works if nothing else captures the keypress first. In practice, after page load focus is on `<body>` and tool hotkeys silently fail. Every TDD spec needed an explicit timeline click. **Fix: Alpha should auto-set `focusedPanel: 'timeline'` in the DockviewLayout onReady callback.**

**JKL shuttle is still ±5s jumps, not progressive.** This is the single most impactful FCP7 gap. Every professional editor uses JKL for variable-speed scrubbing. The `shuttleSpeed` field exists but the rAF render loop doesn't read it.

**DebugShellPanel (MARKER_QA.W5.1) broke 10 smoke tests.** The rewrite changed every section label and removed marker create/toggle buttons without updating tests. This is expected during rapid iteration but the gap wasn't caught for ~2 days.

**`time_markers_ready` vs `time_markers: N`** — the word "markers" appears in both `time_markers: 2` and `markers: 2`, causing Playwright strict mode violations. Any text that's a substring of another testable text needs `{ exact: true }`.

---

## Q2: What unexpectedly worked?

**Direct API call as hotkey substitute.** When `m` hotkey failed (store wiring issue), calling `/api/cut/time-markers/apply` directly + `refreshProjectState()` was a clean workaround. Pattern: if hotkey → handler → API, just call the API and refresh. Saved hours vs debugging the full hotkey chain.

**`[title="Click to type timecode"]` as universal TimecodeField selector.** Three different testid patterns failed (`timecode-field`, `cut-timeline-timecode`, `monitor-timecode`). The `title` attribute was the only stable anchor. Lesson: when data-testid naming is unstable, HTML `title` attributes are surprisingly reliable selectors.

**`addInitScript` for preset switching.** Setting `localStorage` before page load via Playwright's `addInitScript` cleanly switches the hotkey preset without touching component code. This pattern works for any localStorage-driven feature flag.

**JSON reporter + Python one-liner for real counts.** The `--reporter=list` output hides flaky/retry details. `--reporter=json | python3 -c "..."` gives exact pass/fail/flaky/skip counts without ambiguity. Should be the standard for CI.

---

## Q3: Ideas I didn't have time to implement

**Shared dev server pool.** Every spec spawns its own Vite dev server (30s startup each). With 7 specs, that's 3.5 minutes of pure server boot time. A `globalSetup` that starts ONE server and routes all specs to it would cut the TDD suite from 7min to ~2min.

**ProjectPanel testids for berlin acceptance tests.** I added `cut-source-bucket-{binKey}` and `cut-source-item-{item_id}` to ProjectPanel but the berlin montage/music tests also need `cut-status-text` (NLE status bar) and `cut-source-item-badge-*` (primary music badge). These require new components, not just testids.

**DebugShellPanel test generator.** The 10 debug smoke tests follow an identical pattern: navigate → toggle to debug → assert section content → refresh → assert updated content. A shared helper `assertDebugSection(page, sectionTitle, assertions)` would make these tests 20 lines instead of 80.

---

## Q4: What tools worked well?

**`page.evaluate(() => window.__CUT_STORE__)`** — Direct Zustand store access from tests is incredibly powerful. Read any field, set any state, call any action. This is the single most valuable test hook in the codebase.

**Playwright `page.route()` for API mocking** — Clean, per-test API interception without any backend. The pattern of mutating a `state` object inside the route handler to simulate server-side changes is elegant.

**`test.fixme()` as triage tool** — Marks tests as "known broken, needs work" without hiding them. Better than `.skip()` for tests that SHOULD pass but need component changes.

**Error context markdown files** — Playwright's ARIA snapshots in `error-context.md` are gold for understanding what the page actually rendered vs what the test expected. Saved multiple rounds of screenshot analysis.

---

## Q5: What NOT to repeat

**Don't rewrite DebugShellPanel without updating tests in the same PR.** The QA.W5.1 rewrite created 10 broken smoke tests that went undetected. Rule: any component that has E2E tests MUST have those tests updated in the same commit.

**Don't use `text=X` without `.first()` or `{ exact: true }`.** Playwright strict mode catches ambiguous selectors. Timecode fields, marker counts, and section titles frequently create substring collisions. Always be explicit.

**Don't run full TDD suite with default workers.** Port conflicts between dev servers cause phantom failures. Use `--workers=1` or implement a shared server pool. The parallel execution saves ~2min but creates ~20 false failures.

**Don't test hotkeys without setting panel focus first.** The `focusedPanel` scope system means pressing a key without the right panel focused = silent no-op. Every hotkey test needs an explicit click on the target panel element before the keyboard press.

**Don't assume `networkidle` means "app is ready".** DockView panels render asynchronously after the page is "idle". A `waitForSelector` on a specific panel element is always needed after `goto`.

---

## Q6: Unexpected ideas (off-topic)

**Test-driven component discovery.** Writing TDD specs BEFORE reading component code is an effective way to discover the API surface. The test failures tell you exactly what exists vs what's missing. This could be formalized: new agents start by running tests, not reading code.

**Coverage matrix as project management tool.** The `CUT_FCP7_COVERAGE_MATRIX.md` maps every FCP7 chapter to implementation status + test status. This is more useful than a roadmap because it shows WHAT'S VERIFIED, not just what's planned. Consider generating it automatically from test results.

**Hotkey preset as test dimension.** Every TDD test should run twice: once with Premiere preset, once with FCP7. Same feature, different key bindings. Currently we only test FCP7. A Playwright `project` config could parameterize this cheaply.

**The "splash screen" is actually a feature.** CutStandalone showing "Open CUT Project" when no sandbox_root is set isn't a bug — it's the correct empty state. But NO test validates this flow. A smoke test for the empty-state → bootstrap → project-loaded transition would catch regressions in the onboarding path.
