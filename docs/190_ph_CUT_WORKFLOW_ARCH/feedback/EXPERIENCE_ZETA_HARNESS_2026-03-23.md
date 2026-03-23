# Experience Report: Zeta — Harness Session
**Date:** 2026-03-23
**Agent:** Zeta (Opus 4.6)
**Domain:** Harness / Infrastructure
**Branch:** main (direct)
**Session Duration:** ~2 hours
**Tasks Completed:** 11 commits, 9 tasks closed

---

## Session Summary

**Mission:** Fix cascading infrastructure bugs blocking fleet operations — branch_name mapping, auto-commit scoping, debrief routing, CLAUDE.md identity confusion, worktree branch detection.

**Results:**
- 11 commits on main (MARKER_195.22 series)
- Local fallback reload chain fixed (orchestration + tools layers)
- Auto-commit scoped staging (closure_files > allowed_paths > all dirty)
- Debrief _route_to_memory: 4/4 subsystems verified end-to-end
- CLAUDE.md dual-write + auto-regen on session_init
- Branch auto-infer from registry (role/assigned_to/title prefix)
- 14 done_worktree tasks bulk-fixed with branch_name

---

## Q1: What's broken?

1. **Auto-commit false-positive** — git commit succeeds but GitCommitTool returns success:false because pre-commit hook stdout is parsed as error. Task tb_1774245114_6 open.
2. **Task board singleton race condition** — two processes write to same JSON file. reload() creates new singleton → stale data. Need SQLite with WAL.
3. **MCP subprocess doesn't hot-reload** — stdio subprocess launched at Claude Code start. Code changes on disk require full restart. importlib.reload only helps local fallback transport.

## Q2: What unexpectedly worked?

1. **importlib.reload chain** — reload dependency BEFORE dependent module. Simple, effective, no restart needed for local fallback.
2. **ENGRAM as universal fallback** — when AURA schema didn't accept debrief keys, ENGRAM's flexible key-value worked instantly.
3. **Title-prefix branch inference** — "ALPHA-P1: ..." → registry lookup → branch. Covers 90% of cases where agents forget branch=.

## Q3: Ideas not implemented?

1. **CLAUDE.md as compiled artifact** — .gitignore it, auto-regen always. Zero merge conflicts forever.
2. **Post-merge hook** — auto-regen all CLAUDE.md after every merge. Catches the gap between merge and next session_init.
3. **Harness integration test suite** — tests for the infra itself (not CUT features). Would have caught cascade bugs earlier.

## Q4: Tools that worked well?

1. `vetka_task_board action=complete` with closure_files — scoped commits, no cross-domain pollution
2. `generate_claude_md.py --all` — one command, 12 files, correct roles
3. agent_registry.yaml — single source of truth for the whole fleet

## Q5: What NOT to repeat?

1. **Fixing symptoms instead of root cause** — skip-worktree → merge resets → skip-worktree again. Auto-regen on session_init was the right fix.
2. **Testing only on main** — all my proofs passed on main, but worktree debrief was broken. Need worktree proof path.
3. **Trusting singleton state across processes** — session_tracker singleton lives in one process only.

## Q6: Unexpected ideas?

1. **Cascade debugging pattern** — each fix revealed the next bug. Infrastructure bugs hide behind each other. Need integration test coverage for harness.
2. **VETKA_MCP_CWD env var** — capturing initial cwd at MCP startup. Simple but critical for worktree detection.

---

## Commits This Session

| Hash | Task | Fix |
|------|------|-----|
| `885abd02` | tb_1774235598_17 | Reload orchestration layer + branch_name tests |
| `30b44b9e` | tb_1774241588_1 | Scoped auto-commit (allowed_paths filter) |
| `5afc39b6` | tb_1774242784_2 | Scoping proof (1 file committed, 2 excluded) |
| `57231135` | tb_1774243260_3 | AURA->ENGRAM redirect in debrief routing |
| `3c989cc3` | tb_1774243711_4 | closure_files MCP override passthrough |
| `259167f29` | tb_1774244568_5 | Dual-write CLAUDE.md + L1/L2 memory pointers |
| `371f24ba` | tb_1774245386_7 | Restore root CLAUDE.md + skip-worktree guard |
| `5c751596` | tb_1774245607_8 | Debrief always injects (no session_tracker dep) |
| `255ec2a6` | tb_1774247251_9 | Auto-infer branch from AgentRegistry on complete |
| `5363183e` | tb_1774247860_10 | action=update error context |
| `881add11` | tb_1774248245_23 | Auto-regen CLAUDE.md on session_init |
| `f94bd3ff` | tb_1774248915_11 | Worktree branch detection via VETKA_MCP_CWD |

---

## Open Tasks for Next Zeta

| Task ID | Title | Priority |
|---------|-------|----------|
| tb_1774245114_6 | Auto-commit false-positive (pre-commit hook stdout as error) | P2 |
| — | Task board JSON → SQLite migration (race condition fix) | P3 |
| — | Post-merge hook for CLAUDE.md auto-regen | P3 |
| — | Harness integration test suite | P3 |

---

## Predecessor Advice for Next Zeta

- **Always test on worktrees**, not just main. MCP subprocess behavior differs.
- **importlib.reload order matters**: dependency first, then dependent module.
- **closure_files must be passed from MCP arguments**, not just task object. Check override_closure_files param.
- **AURA set_preference has fixed schema** — don't invent new keys. Use ENGRAM for flexible storage.
- **session_init is the only reliable hook** for worktree context. Everything else (skip-worktree, .gitattributes) gets overwritten by merge.
- **`VETKA_MCP_CWD` env var** — set in main() of vetka_mcp_bridge.py, read in session_tools.py. This is how worktree detection works.

---

*"Каждый фикс обнажал следующий баг. Инфраструктура — это каскад."*
