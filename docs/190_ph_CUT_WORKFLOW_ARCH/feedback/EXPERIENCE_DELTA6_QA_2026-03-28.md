# Delta-6 QA Experience Report — 2026-03-28
**Agent:** Delta-6 (Opus 4.6 1M) | **Role:** QA Engineer / FCP7 Compliance
**Branch:** worktree-cut-qa | **Session:** ~45 min, 4 verification rounds

---

## Session Results

| Metric | Value |
|--------|-------|
| Tasks verified (PASS) | 25 |
| Tasks verified (FAIL) | 6 |
| Already verified (parallel QA) | 4 |
| Bug tasks created | 5 |
| Contract tests written | 14 (TDD-RED) |
| Commits | 2 (36a91618, 6a3f06b18) |
| Sonnet agents used | 12 |

---

## Q1: What's broken that everyone walks past?

**cut-ux merge regression pattern.** Merge commits 1a632712c and e68a86736 silently reverted 4 correct Gamma fixes. Nobody noticed because the commits exist on the branch — they just got overwritten by stale merge-base. This will keep happening every time cut-ux merges with a stale base. Need: post-merge diff audit or a "verify HEAD matches last N commits" hook.

**Commander phantom closures.** Two PARALLAX tasks closed with a merge commit as "proof" — zero implementation. Manual close bypasses all QA gates. The task_board should reject `action=complete` with a merge commit hash (detect via `git cat-file -t` → "commit" with 2+ parents).

---

## Q2: What unexpectedly worked?

**Sonnet fleet at scale.** 12 parallel Sonnet agents verified 27 tasks in 4 rounds. Cost ~$1-2. Each agent got a focused scope (1-3 tasks), returned structured verdicts. Opus only coordinates and issues judgments. The pattern is now proven at 27-task scale.

**TDD-RED with xfail for cross-branch features.** 14 tests for APIs that don't exist in the worktree. Zero errors, clean `xfailed` signal. When harness merges, remove markers → instant green/red signal. This pattern should be standard for cross-branch feature validation.

---

## Q3: What tool or process would have saved the most time?

**`git merge-base --is-ancestor` pre-check before verification.** 4 tasks were already verified by Epsilon running in parallel — wasted agent runs. A quick "is this task already verified?" check before launching an audit agent would have saved those cycles.

**Auto-diff-audit post-merge.** After any `Merge branch 'claude/cut-ux'`, automatically verify that the merge didn't revert recent commits. Simple: for each commit in the merged branch, check if its changes survive in the merge result. Would have caught the 4-fix regression instantly.

---

## Q4: What anti-pattern did you see repeated?

**Field name mismatch between frontend and backend.** Three instances in this session alone:
- `clip_id_a` vs `clip_a_id` (swap_clips)
- `playhead_sec` vs `playhead` (rippleTrimToPlayhead)
- `transition` vs `transition_out` (MenuBar)

Root cause: no shared schema contract. Frontend TS types and backend Python op handlers evolve independently. Fix: shared op-type registry (already tracked as tb_1774424877_1) or at minimum a JSON schema for timeline ops that both sides validate against.

---

## Q5: What's the riskiest thing going to main next?

**claude/harness merge.** 10+ commits including TB_201.A-D (tool isolation), CLAUDE.md generator, feedback bridge, notification inbox, agent wake system. This is infra — if it breaks, every agent session is affected. Needs careful merge with full test run (including the 14 new xfail tests flipping to green).

**claude/cut-ux re-merge.** 7+ unmerged commits including the fixes that were already reverted once. Must verify merge doesn't re-introduce the stale patterns. Use `git diff HEAD...<merged>` to confirm all fixes survive.

---

## Q6: If you had 2 more hours, what would you build?

**Post-merge regression detector.** A script that, after any merge commit:
1. Lists all commits being merged
2. For each commit, checks if its diff is a subset of the merge diff
3. Flags any commit whose changes were dropped/reverted by the merge
4. Creates a DELTA-BUG task automatically for each regression

This would have caught the 4-fix cut-ux regression before anyone wasted time re-verifying. ~50 lines of Python, runs as a post-merge git hook. Would pay for itself in the first week.
