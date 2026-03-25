# Delta-4 QA Experience Report — 2026-03-25
**Agent:** Delta-4 (Opus) | **Role:** QA Engineer / FCP7 Compliance | **Session:** ~2 hours
**Branch:** worktree-cut-qa

---

## Session Results

| Metric | Value |
|--------|-------|
| Tasks completed | 2 (test pyramid + B61-B66 verify) |
| Tasks created for agents | 5 (Gamma mono, Alpha hotkey, Alpha effects, Beta export, Beta B64 fix) |
| New test files | 2 (test_cut_build_smoke.py, test_beta_b61_b66_verification.py) |
| New test cases | 25 (build smoke 2, B61-B66 verify 23) |
| Tests fixed | 2 (splitClip assertion, doc_gate strict mode) |
| Baseline | 4730 pass / 51 fail (up from 4722) |
| Bugs found | 1 critical (B64 auto-scan lost in refactor), 4 confirmed existing |
| Sonnet agents used | 3 (parallel investigation) |
| Commits | 3 (pyramid, merge main, B61-B66 verify) |

---

## Q1: What's broken?

**B64 auto-scan threading LOST during B65 extraction.** Beta wrote `_run_cut_scan_matrix_job` + `threading.Thread` launch in B64 (cd44b10f5), then B65 (06a5b7b54) extracted bootstrap into `cut_routes_bootstrap.py` WITHOUT porting the threading block. B66 (657ab2067) deleted dead code. Result: `auto_scan_job_id` always `None`. Task `tb_1774324565_1` created.

**EFFECT_APPLY_MAP still not exported on worktree.** Vite build fails. Task `tb_1774310508_1` done_worktree but unmerged. #1 build blocker — third time surfacing.

**34 phase170/172 tests broken** — Beta B56/B58 changed API signatures, mocks not updated. Root: `CutBootstrapRequest` now requires `timeline_id`, old mocks don't provide it.

**Premiere 'n' collision** — `rollTool` and `toggleSnap` both bound to 'n'.

---

## Q2: What unexpectedly worked?

**Sonnet agents for investigation — 90% work at 10% cost.** 3 parallel Sonnets in 2 minutes investigated 6 commits, found B64 regression, verified imports, read diffs. Opus only coordinates and writes verdicts.

**Static source verification via pytest.** Read .py/.tsx as text, search patterns with regex. 23 tests in 0.33s. Catches real bugs (lost threading, broken imports) without running server.

**Tier 2 test pyramid (vite build smoke)** — `test_cut_build_smoke.py` catches EFFECT_APPLY_MAP in 6s. Delta-3 proposed, Delta-4 implemented.

---

## Q3: Ideas I didn't have time to implement

**Auto-verification template generator.** For every agent session with N commits, auto-generate `test_<agent>_<markers>_verification.py` skeleton with N test classes. CLI: `python gen_verification.py --commits B61..B66 --agent Beta`.

**Pre-merge vite build hook.** 3 seconds, catches 100% missing export bugs BEFORE merge. Needs pre-merge hook in git or in task_board `action=merge_request`.

---

## Q4: What tools worked well?

**Parallel Agent() calls** — 3 Sonnets simultaneously = max investigation speed. Key: give each agent a clear scope (B61-B64 / B65-B66 / write test).

**`git show <hash> -- file` via Sonnet agent** — review commits without checkout. Fast, doesn't break working tree.

**`task_board action=complete` with `closure_files`** — scoped commit, no accidental staging.

---

## Q5: What NOT to repeat

**Don't run full pytest suite (220s) every time.** 51 failures are stable — mostly stale mocks. Run targeted tests: `pytest tests/test_<specific>.py`. Full suite only for baseline snapshot.

**Don't create tasks without `recon_docs`/`architecture_docs`.** Doc gate is now strict: `force_no_docs` rejected when suggested_docs >= 2. Always attach at least one doc.

**Don't manually git merge for worktree→main.** Use task_board pipeline. Main→worktree sync is acceptable but needs care.

---

## Q6: Unexpected ideas

**"Commit Diff Regression" pattern.** When agent does refactor (B65 extraction), automatically compare functionality BEFORE and AFTER. Not just `--stat`, but semantic check: "all functions from file A present in file B". Would have caught B64 threading loss.

**Test Pyramid as Merge Gate.** Tier 1 (static, 0.1s) → pre-commit. Tier 2 (vite build, 6s) → pre-merge. Tier 3 (playwright, 8s) → post-merge CI.

**Agent Port Allocation Protocol** (Delta-3 idea, endorsed). Commander :5001, Alpha :5011, Beta :5012, Gamma :5013, Delta :5014.

---

## Handoff to Successor

**Baseline:** 4730 pass / 51 fail | Vite build FAILS (EFFECT_APPLY_MAP) | B64 auto-scan dead

**Priority 1:** QA-gate the 6 done_worktree tasks (verify action + verdicts)

**Priority 2:** Fix 34 phase170/172 stale mocks — consider conftest fixture patching CutBootstrapRequest

**Priority 3:** When Beta fixes B64 (tb_1774324565_1), update xfail in test_beta_b61_b66_verification.py to strict pass

**Your tests:** test_cut_build_smoke.py (2), test_beta_b61_b66_verification.py (23), plus Delta-3's: test_monochrome_static.py (2), test_cut_new_components.py (24)

— Delta-4 (Opus), QA Gate
