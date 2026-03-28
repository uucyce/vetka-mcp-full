# RECON: CLAUDE.md Git-Tracking Root Cause Analysis
**Date:** 2026-03-28 | **Agent:** Epsilon-6 (QA-FIX) | **Task:** tb_1774643900_64500_1
**Parent task:** tb_1774592883_1 | **Status:** Root cause confirmed, 4 fixes identified

---

## Q1: What is the root cause?

**CLAUDE.md re-enters the git index on every cherry-pick from worktree branches.**

The sequence of failure:
1. CLAUDE.md was tracked in git since project inception (as Commander config / role config)
2. Task `tb_1774312037_33` (commit `ff2333fe4`, Mar 24) added `/CLAUDE.md` to `.gitignore` and ran `git rm --cached CLAUDE.md` — **but only on the main branch**
3. All 6 worktree branches (`cut-engine`, `cut-media`, `cut-ux`, `cut-qa`, `cut-qa-2`, `harness`) still have CLAUDE.md tracked in their commit histories, because `git rm --cached` was never run on those branches
4. Every cherry-pick of a worktree commit to main that touches CLAUDE.md re-adds CLAUDE.md to main's index
5. `.gitignore` **cannot stop this**: `.gitignore` only prevents untracked files from being staged via `git add`. Cherry-pick and merge explicitly apply tracked-file changes, bypassing `.gitignore` entirely

Evidence: After `ff2333fe4`, main still received CLAUDE.md changes via cherry-picks:
- `d0419481f` — Gamma testid batch commit included CLAUDE.md
- `4d67416f0` — Alpha insertEdit fix included CLAUDE.md
- `c40ccccb7` — phantom Epsilon recon included CLAUDE.md
- `fcd6b3044` — Beta media pipeline included CLAUDE.md

---

## Q2: What triggered it specifically in this instance (rebase conflict)?

When a worktree agent **rebases** their branch on updated main after `ff2333fe4`:

```
main (after ff2333fe4):   CLAUDE.md = NOT TRACKED (deleted from index)
worktree branch:          CLAUDE.md = TRACKED (timestamps, role config)
```

Git rebase replays each commit on top of main. When it replays a commit that **modifies** CLAUDE.md, git sees:
- Base tree: file existed and was tracked
- Destination (main): file deleted
- Rebase commit: file modified

→ **Conflict: "deleted by them, modified by us"**

The agent sees `deleted by them` in `git status` and resolves by keeping their version (logical — it's their role config). This resolution re-adds CLAUDE.md to the branch index with a merge commit. Next cherry-pick to main: conflict reappears.

Additionally, `generate_claude_md.py` runs on post-merge hook and writes a fresh CLAUDE.md. If the hook fires after a merge but before the cherry-pick pipeline runs, the generated file is dirty-tracked and gets swept into the next commit.

---

## Q3: Why did the `skip-worktree` guard not solve it?

Commit `371f24baf` (Mar 23) added `skip-worktree` as a mitigation:

```bash
git update-index --skip-worktree CLAUDE.md
```

**`skip-worktree` only prevents git from updating the working copy** when git pulls/merges updates to a tracked file. It does NOT:
- Remove the file from the index
- Prevent cherry-pick from re-adding the file to the index
- Apply across worktrees (skip-worktree is stored in `.git/index`, each worktree has its own index)

So skip-worktree is per-worktree, per-session state. On fresh checkout or in a different worktree, the bit is gone.

---

## Q4: Why does `/CLAUDE.md` in `.gitignore` not help?

The `.gitignore` entry added in `ff2333fe4`:
```
/CLAUDE.md
```

**Works for:** Preventing a freshly created, never-tracked CLAUDE.md from being staged by `git add` or `git add -A`.

**Does NOT work for:**
- Files already in the index (tracked files ignore `.gitignore` entirely)
- Files re-introduced by `git cherry-pick`, `git merge`, or `git rebase` (these are explicit index operations, not `git add`)
- Worktrees where a previous agent already tracked the file

Result: CLAUDE.md was removed from main's index on Mar 24, but worktree branches continued committing it, and every cherry-pick re-adds it.

---

## Q5: What is the current state (as of 2026-03-28)?

- **Main branch:** `git ls-files --cached CLAUDE.md` → empty (not tracked) ✓
- **Worktree branches:** All still have CLAUDE.md tracked in commit history
- **Pending:** Task `tb_1774641693_84216_1` — "ETA-FIX: git rm --cached CLAUDE.md on main + all worktree branches" — still pending, not yet executed
- **Ongoing conflicts:** Every cherry-pick wave from worktree branches to main will produce `deleted by us / modified by them` conflicts on CLAUDE.md until the Eta fix runs on all branches

---

## Fix Recommendations

### Fix 1 (CRITICAL — unblocks all merges): Run `git rm --cached CLAUDE.md` on every worktree branch
```bash
for worktree in cut-engine cut-media cut-ux cut-qa cut-qa-2 harness; do
  git -C .claude/worktrees/$worktree rm --cached CLAUDE.md 2>/dev/null || true
done
```
This removes CLAUDE.md from the index on all live branches. Future cherry-picks will no longer see it as a tracked file.
**Owner:** Eta (task `tb_1774641693_84216_1` already created)

### Fix 2 (STRUCTURAL — closes the reintroduction vector): Add pre-commit guard in pipeline
In `generate_claude_md.py` or the task completion hook, before committing:
```bash
git rm --cached CLAUDE.md 2>/dev/null || true
```
This ensures even if CLAUDE.md is re-added to the index by a cherry-pick, it gets removed before the next agent commit. A one-line addition to the pipeline closure step.
**Owner:** Zeta (harness domain)

### Fix 3 (PREVENTIVE — stops .gitignore bypass): Add `.gitattributes` merge=ours rule
```
CLAUDE.md merge=ours
```
This instructs git to always keep the current branch's version of CLAUDE.md during merges/cherry-picks, preventing the file from being pulled in from source branches. Combined with Fix 1, eliminates the conflict entirely.
**Owner:** Eta or Zeta

### Fix 4 (AUDIT — verify the full fleet): Confirm no CLAUDE.md in index after fixes
```bash
for worktree in . .claude/worktrees/*/; do
  result=$(git -C "$worktree" ls-files --cached CLAUDE.md 2>/dev/null)
  echo "$worktree: ${result:-CLEAN}"
done
```
Run this after Fix 1 lands. Any branch showing `CLAUDE.md` needs an additional `git rm --cached`.
**Owner:** Delta QA (verification step after Eta fix)

---

## Summary

| Question | Answer |
|----------|--------|
| Root cause | `git rm --cached` ran only on main, not worktree branches |
| Trigger mechanism | Cherry-pick re-adds tracked files, bypassing `.gitignore` |
| Why skip-worktree failed | Per-worktree, per-session; doesn't prevent index re-add |
| Why .gitignore failed | Only blocks `git add`; cherry-pick/merge bypass it |
| Current state | Main clean; worktrees still track CLAUDE.md |
| Critical fix | Eta: `git rm --cached CLAUDE.md` on all 6 worktrees |
| Structural fix | Zeta: Add `git rm --cached` to pipeline closure hook |
