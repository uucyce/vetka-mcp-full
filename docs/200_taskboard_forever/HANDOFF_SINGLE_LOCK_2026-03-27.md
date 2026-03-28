# HANDOFF: MARKER_200.SINGLE_LOCK — Dirty Working Copy Exorcism

**Date:** 2026-03-27 07:00 UTC
**Author:** Zeta (Harness Engineer)
**Commit:** `81745e6a0` on main
**Phase:** 200 — TaskBoard Forever, Part 2

---

## Root Cause (the real one)

**The FOREVER fix was correct. The disk file was wrong.**

`src/orchestration/task_board.py` on main had **uncommitted local changes** that overwrote the FOREVER fix (`a662c64ff`). The working copy on disk contained old LOCK_FIX code:

| What git had (correct) | What disk had (broken) |
|---|---|
| `busy_timeout=5000` | `busy_timeout=30000` |
| No `timeout=` in connect() | `sqlite3.connect(timeout=30)` |
| No `_execute_with_retry()` | `_execute_with_retry()` with sleep |
| No `_backfill_modules()` in init | Various bulk writes |

All MCP servers load from disk, not from git. Every agent restart loaded the broken code. **Every session since the FOREVER fix was running the OLD code.**

### How it happened

Likely scenario: a merge operation (`git merge claude/cut-engine` or similar) created a merge conflict in `task_board.py`. The conflict resolution picked the wrong side — taking the pre-FOREVER version. The merge was committed but `task_board.py` ended up modified in the working tree (unstaged changes leftover from conflict resolution or an interrupted merge).

Evidence: `git diff a662c64ff..HEAD -- src/orchestration/task_board.py` = 0 lines (git history clean), but `git status` showed `modified: src/orchestration/task_board.py` (disk dirty).

---

## What SINGLE_LOCK Adds (on top of restored FOREVER)

6 changes to reduce lock contention 4x:

| # | Change | Before | After | Effect |
|---|---|---|---|---|
| 1 | `_save_task()` bundles FTS | task INSERT (lock) → FTS DELETE (lock) → FTS INSERT (lock) | All in one `with self.db:` | **4 lock cycles → 1** |
| 2 | `_delete_task()` bundles FTS | task DELETE (lock) → FTS cleanup (lock) | One transaction | **2 → 1** |
| 3 | `_backfill_modules()` merged txns | Two `with self.db:` blocks | One block | **2 → 1** |
| 4 | `busy_timeout` raised | 5000ms (5s) | 15000ms (15s) | Margin for 10+ processes |
| 5 | `synchronous=NORMAL` added | Default (FULL) | NORMAL | **2-5x faster** WAL commits |
| 6 | `_index_task_fts_inner()` | Only `_index_task_fts` (always own lock) | Inner (no lock) + Outer (own lock) | Callers choose |

### Stress Test Results (3 Sonnet agents, parallel)

- **7/7** unit tests PASS (concurrent writes, read/write mix, latency <100ms)
- **5/5** lifecycle tasks: add → claim → complete — zero lock errors
- **FTS5**: 1680 rows indexed, 4 queries — zero timeout
- All 3 tasks closed via `action=complete` successfully

---

## What Hooks Exist (as of 2026-03-27)

| Hook | Purpose | Status |
|---|---|---|
| `pre-commit` | Update project digest, phase sync in CLAUDE.md | Working |
| `post-commit` | Auto-push main to origin | Working |
| `post-merge` | Promote tasks done_worktree→done_main, regen CLAUDE.md, stale scan | Working |
| `pre-merge-commit` | Unknown/empty | Needs check |

### What's MISSING: Dirty Working Copy Guard

**No hook prevents the scenario that caused this outage.** A `pre-merge-commit` or `post-merge` guard should:

1. After every merge on main, check if critical files have unstaged changes
2. If `src/orchestration/task_board.py` is modified but not staged → **auto-restore from HEAD**
3. Alert the user

Recommended implementation (add to `post-merge` hook):
```bash
# MARKER_200.DIRTY_GUARD: Protect critical files from dirty working copy
CRITICAL_FILES="src/orchestration/task_board.py src/mcp/tools/task_board_tools.py"
for f in $CRITICAL_FILES; do
    if git diff --name-only -- "$f" | grep -q .; then
        echo "⚠️  DIRTY GUARD: $f has unstaged changes after merge!"
        echo "    Restoring from HEAD to prevent broken MCP..."
        git checkout -- "$f"
        echo "    ✅ Restored $f"
    fi
done
```

**Task needed:** Implement DIRTY_GUARD in post-merge hook.

---

## Eta Agent

New agent **Eta** (Harness Engineer 2, Zeta's partner) created:
- Worktree: `.claude/worktrees/harness-eta` (branch `claude/harness-eta`)
- Registry: `data/templates/agent_registry.yaml` — 8 roles now
- CLAUDE.md: auto-generated
- USER_GUIDE: updated to v2.1 with Eta launch codes

Launch: `cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/harness-eta && claude`

---

## Files Changed

| File | Change |
|---|---|
| `src/orchestration/task_board.py` | SINGLE_LOCK fix (6 changes) |
| `data/templates/agent_registry.yaml` | Added Eta role |
| `docs/USER_GUIDE_MULTI_AGENT.md` | v2.1 — Eta launch codes |
| `tests/test_phase200_single_lock.py` | 7 stress tests (harness worktree) |
| `tests/test_phase200_taskboard_forever.py` | Updated for busy_timeout=15000 (harness worktree) |

---

## Open Tasks for Next Session

1. **DIRTY_GUARD hook** — add to post-merge, protect critical files from dirty working copy
2. **RECON: Git post-commit → TaskBoard sync** — reconcile tasks on server restart (task created but DB was locked)
3. **RECON: Git mirror broken** — vetka-core not syncing (task created but DB was locked)
4. **Merge harness → main** — tests + updated test assertions
5. **Single-writer architecture** — long-term: route all writes through one REST endpoint

---

## Lesson

> The fix was committed. The disk was wrong. Git is the source of truth — but only if you read from git. MCP servers read from disk.

**Protection:** Always verify `git status -- <critical_file>` after merges. Automate with DIRTY_GUARD hook.

---

*"Мы не видели очевидного: git и диск — не одно и то же."*
