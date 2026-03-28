# Delta-5 QA Experience Report — 2026-03-25
**Agent:** Delta-5 (Opus) | **Role:** QA Engineer / FCP7 Compliance | **Session:** ~1.5 hours
**Branch:** worktree-cut-qa

---

## Session Results

| Metric | Value |
|--------|-------|
| Tasks verified (PASS) | 11 |
| Tasks verified (FAIL) | 1 (FCP7 hotkey audit — no deliverable) |
| Test fixes committed | 3 (timeline_apply, SocketIO import, effects contract) |
| Fix tasks created | 3 (Gamma monochrome, Alpha mark-in/out, Delta multicam test) |
| Baseline before | 4785 pass / 16 fail |
| Baseline after | 4790 pass / 12 fail (projected post-commit) |
| Sonnet agents used | 12 (parallel investigation fleet) |
| Commits | 3 (e5b696d05, 2f699aff2, da3d9d4cf) |

---

## Q1: What's broken?

**FCP7 hotkey audit (tb_1774312429_64) was empty.** Task marked done_worktree with zero deliverable — no commit, no doc, no mapping table. Sent to needs_fix. Agent either abandoned mid-task or status was set incorrectly.

**Playwright Tier 3 needs live server.** 0/26 smoke specs pass — all fail on `toBeVisible()` because no Vite dev server + FastAPI running. This is infrastructure, not code. Commander needs to coordinate server startup for Tier 3 runs.

**Pre-existing monochrome violations (2 new findings):**
- `DAGProjectPanel.tsx:117` — `#5DCAA5` teal (task tb_1774410493_1 for Gamma)
- `TimelineTrackView.tsx:1753` — mark-in/out uses green/red rgba (task tb_1774418815_1 for Alpha)

**Multicam test gap.** `test_no_multicam_ui` is vacuous PASS — was a skip-placeholder, now falls through with no assertion. Task tb_1774419069_1 created.

---

## Q2: What unexpectedly worked?

**12 parallel Sonnet agents = complete branch audit in 20 minutes.** Each agent got a clear scope (1 branch or 1-2 tasks), returned structured PASS/FAIL verdict. Opus only coordinates, reads verdicts, records to task board. Delta-4 pattern confirmed at scale.

**Delta-4's "34 stale mocks" was actually 1.** Wrong pytest venv (missing fastapi) caused 19 collection errors. Only `test_cut_timeline_apply_returns_recoverable_error_when_timeline_missing` was a real failure. 4-line fix (delete timeline_state file after B65 bootstrap).

**Effects contract fix via regex expansion.** Alpha refactored to ops-based `applyTimelineOps` — test checked for inline `effects: undefined`. Added `op: 'reset_effects'` to regex pattern. Test now accepts both implementations.

---

## Q3: Ideas I didn't have time to implement

**Branch merge-status pre-check.** 4 of 13 tasks were already `done_main` — wasted audit cycles on retroactive reviews. Add `git merge-base --is-ancestor` check before launching Sonnet audit agents.

**Automated vacuous-test detector.** Scan all test files for `pytest.skip` → verify the skip condition still holds. If MulticamViewer now exists, the skip-pass is a lie. Could be a Tier 1 static check.

**Tier 3 server orchestration.** Delta should be able to spin up `vite dev` + FastAPI in background, run Playwright, then kill. Needs port allocation per Delta-3's protocol (Delta: 5014).

---

## Q4: What tools worked well?

**`task_board action=verify verdict=pass/fail`** — direct verdict recording, atomic status change. Clean workflow.

**Parallel Agent() with model=sonnet** — 12 agents, ~$0.50 total, replaced 2 hours of sequential review.

**`git diff main...origin/<branch>`** — three-dot diff shows exactly what a merge would bring. Combined with `--name-only` for scope check, grep for monochrome.

---

## Q5: What NOT to repeat

**Don't verify tasks that are already done_main.** Check status before launching audit agent. Wasted 4 agent runs on retroactive reviews where `action=verify` couldn't even execute.

**Don't run full pytest with -x.** Delta-4's advice confirmed — use `-q --tb=no` for baseline snapshot, targeted `-v --tb=short` for specific fixes.

**Auto-commit logger bug in MCP.** `action=complete` fails with "name 'logger' is not defined" but actually commits the file first. Confusing — the commit lands but the task status doesn't update. Workaround: `action=update status=done_worktree` after failed complete.

---

## Q6: Unexpected ideas

**"Verdict-as-Code" pattern.** Each verify verdict could auto-generate a test assertion: `assert task_tb_xxx.verdict == 'PASS'` with the notes as docstring. Creates audit trail that's also runnable.

**QA agent should own vite build check.** Tier 2 (vite build) is the most valuable gate — catches 100% of missing export bugs. Should run automatically on every `action=verify` call, not manually.

**Monochrome scanner as pre-commit hook.** The static grep test catches violations in 0.1s. Wire into git pre-commit for all agents — prevents monochrome bugs from ever reaching QA.

---

## Handoff to Successor

**Baseline:** 4790 pass / 12 fail (projected) | Tier 3 needs live server | 1 FAIL task (hotkey audit)

**Priority 1:** Run Tier 3 Playwright with live server (vite dev + FastAPI) — 26 smoke specs need validation

**Priority 2:** Fix vacuous multicam test (tb_1774419069_1) — replace skip-pass with positive assertions

**Priority 3:** When Gamma fixes DAGProjectPanel monochrome — re-run test_monochrome_static.py, expect 0 violations

**Your tests:** test_cut_build_smoke.py (2), test_beta_b61_b66_verification.py (23), test_monochrome_static.py (2), test_cut_new_components.py (24), plus Delta-4's fixes

**Auto-commit bug:** MCP `action=complete` throws logger error but DOES commit. Use `action=update status=done_worktree` after failure.

— Delta-5 (Opus), QA Gate
