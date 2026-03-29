# Commander Debrief — pedantic-bell session #2
**Date:** 2026-03-29 | **Duration:** ~4 hours | **Phase:** 200

---

## Q1: What bugs did you find?

1. **Doc version rollback on merge** — CRITICAL. Agents rebase from old main, take their version of docs (v2.0), merge brings v2.0 back to main overwriting v3.0. DOC_GUARD catches deletions but NOT rollbacks. User lost USER_GUIDE v3.0 three times. VERSION_GUARD task created (tb_1774759589_97753_1).
2. **merge_request empty error** — tool fails silently when submodules (pulse, back_to_ussr_app) show as dirty. Workaround: `git stash push` before merge. Root cause: merge_request checks git status and misinterprets submodule markers.
3. **merge_request ignores branch_name parameter** — uses task's stored branch_name instead. Caused wrong branch merges (harness-eta instead of harness).
4. **origin/main not pushed after merges** — agents can't rebase onto latest main because Commander only merges locally. Had to add explicit `git push origin main` after merge waves.
5. **Stale task IDs dispatched** — gave Alpha/Beta old done_main task IDs (tb_1773996076_15, tb_1773996025_9). Sonnet agents self-corrected by searching task board. Commander must verify task status before dispatching.

## Q2: What unexpectedly worked?

1. **DOC_GUARD** — Eta's triple-layer protection (STASH_SCOPE + STASH_SAFE + DOC_GUARD) caught doc deletions 4 times this session. Without it, 15+ docs would have been lost silently.
2. **QA_WARN on merge_request** — first real activation. Logged warning when tasks merged without QA verification. Non-blocking, exactly as requested.
3. **Sonnet fleet full autonomy** — Alpha found its own keyframe task, Beta found audio mixer task, Gamma churned 10+ ESC-guard tasks autonomously. Zero hand-holding needed.
4. **Delta 24-task verification marathon** — single QA session verified 24 tasks across 5 branches. Comprehensive, caught the stale merge_result.success=false field.
5. **Agents restoring docs themselves** — Beta/Gamma/Epsilon all did `git checkout main -- docs/...` when DOC_GUARD blocked. Pattern is teachable.

## Q3: What idea came to mind?

1. **post-rewrite hook for auto doc restore** — already tasked (tb_1774758174_97753_1). After every rebase, hook runs `git checkout main -- docs/` for any missing/older docs. Zero manual intervention.
2. **VERSION_GUARD** — compare doc versions (by header date/version string) not just existence. Block merge if branch has older doc than main.
3. **Stop IDEA task inflation** — agents created 30+ P4 IDEA tasks per session from debrief Q3. Rule saved to memory: ideas go to engram/memory, NOT task board. Only P1-P2 bugs get tasks.
4. **Auto-push after merge** — merge_request should `git push origin main` automatically so agents can always rebase onto latest.

## Q4: What anti-pattern did you see?

1. **Stash ping-pong** — I did 10+ stash push/pop cycles because dirty working tree blocked merges. Each pop risked conflicts. Need merge_request to handle dirty submodules internally.
2. **User as message relay** — Captain bounced between Commander and agents for doc restores, rebases, conflict resolution. 7 round-trips for one Beta merge. Notifications help but don't eliminate relay.
3. **Dispatching without checking task status** — gave agents stale task IDs without verifying they were still pending. Must `action=get` before dispatching.
4. **Rebasing after merge creates new conflicts** — merged cut-engine (keyframes), then Beta couldn't merge because cut_routes.py now had keyframe ops that conflicted with mixer ops. Need to merge in dependency order.

## Q5: What should the next Commander know?

1. **Main is at `a6ea761c5`** — USER_GUIDE v3.0 committed + pushed. 60+ commits this session.
2. **DOC_GUARD is live** — merge_request blocks doc deletions. But VERSION rollbacks not caught yet (Eta task pending).
3. **post-rewrite hook pending** — tb_1774758174_97753_1 (Eta). Once deployed, agents auto-restore docs after rebase. No more manual relay.
4. **Always push after merge** — `git push origin main` after every merge wave. Agents fetch from origin.
5. **FCP7 progress:**
   - Keyframes: 0% → ~60% (Alpha, bezier solver + graph editor + diamond overlay)
   - Audio Mixer: 0% → ~50% (Beta, per-track state + WebSocket levels)
   - Trim: ~30% (unchanged)
   - Match Frame: 0% (next priority)
6. **Task inflation rule** — feedback_no_idea_tasks.md saved. Agents must NOT create P4+ tasks from debrief.
7. **Merge order matters** — merge engine before media (shared cut_routes.py). Merge harness-eta before harness (shared task_board.py).
8. **Stash before merge** — `git stash push -- scripts/ data/reflex/` before merge_request if submodules are dirty.

## Q6: Session stats

| Metric | Value |
|--------|-------|
| Merge commits | ~12 (multiple waves) |
| Total commits merged | ~60+ |
| Conflict resolutions | 5 (delegated to agents) |
| DOC_GUARD blocks | 4 (all resolved) |
| Tasks verified by Delta | 24 |
| Tasks created | 6 (keyframes, mixer, VERSION_GUARD, post-rewrite hook, doc guard, no-idea rule) |
| Agents directed | 8 (Alpha, Beta, Gamma, Delta, Epsilon, Zeta, Eta + Codex parallax) |
| FCP7 features landed | 2 (keyframes, audio mixer) |
| Docs recovered | USER_GUIDE v3.0 (3rd recovery) |
| Memory entries | 1 (feedback_no_idea_tasks.md) |
| Critical bugs found | 2 (doc version rollback, merge_request empty error) |
| Origin pushes | 3 |
