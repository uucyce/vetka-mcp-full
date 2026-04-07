# RECON: Codex Agent Role Gap

**Date:** 2026-04-07
**Status:** FIXED (all issues resolved)
**Severity:** P1 — Codex cannot initialize properly, takes wrong worktree/role

## Problem

Codex agent was NOT registered in `data/templates/agent_registry.yaml`.
When Codex called `session_init`, it initialized as Zeta and took the wrong worktree.

## Root Causes (5 layers)

### Layer 1: No registry entry
Codex was used as a sprint agent (phases 136-181) but never formalized in `agent_registry.yaml`. Auto_provision created ephemeral roles with random callsigns.

### Layer 2: AGENTS.md on main hardcoded to Zeta
Snapshot merge from harness branch committed Zeta's `AGENTS.md` to repository root. Any agent opened from main or its subdirectories (including `photo_parallax_playground/`) inherited `role=Zeta` from this file.

### Layer 3: Codex worktree AGENTS.md also stale
`photo_parallax_playground_codex/AGENTS.md` was also hardcoded to Zeta (generated before Codex role existed).

### Layer 4: No worktree name detection in session_init
`session_tools.py` had `get_by_worktree()` method in `AgentRegistry` but **never called it**. Even with a correct registry entry, session_init couldn't match worktree directory name to callsign.

### Layer 5: Codex opened in wrong directory
Codex was opened in `photo_parallax_playground/` (subdirectory of main) instead of `photo_parallax_playground_codex` (the actual worktree). Attempting to switch to `codex/parallax` branch failed with git error: branch already used by another worktree.

### Layer 6: VETKA server caching
After fixing code on disk, VETKA FastAPI server kept old Python modules in memory. Worktree detection only worked after server restart. Meanwhile, explicit `role=Codex` parameter in session_init was the reliable workaround.

## Fixes Applied

| Fix | Commit | What |
|-----|--------|------|
| Registry entry | `8d68e8cb7` | Added Codex callsign to `agent_registry.yaml` with correct worktree `photo_parallax_playground_codex` |
| Origin detection | `8d68e8cb7` | Removed `OPENAI_API_KEY` fallback, added `_ORIGIN_CALLSIGN_MAP` codex->Codex |
| generate_agents_md | `8d68e8cb7` | Added `TEMPLATE_CODEX` for tool_type="codex" |
| Worktree detection | `38e2d1f41` | session_init now calls `get_by_worktree(Path(cwd).name)` before origin detection |
| Role generator hint | `38e2d1f41` | Unregistered agents see `add_role.sh` command in next_steps |
| Root AGENTS.md | `85e5b73dc` | Replaced Zeta-hardcoded AGENTS.md with generic template |
| Codex AGENTS.md | manual copy | Regenerated via `generate_agents_md.py --role Codex` |
| get_subtask_progress | `857bb8d71` | Added missing `@staticmethod` to TaskBoard (unrelated but blocking task_board action=get) |
| Circular import | `8d68e8cb7` | Fixed cut_routes.py ↔ cut_routes_workers.py circular import that crashed server on restart |

## Quick Fix for Users

If an agent initializes with wrong role after all fixes:

```bash
# Explicit role= always works, bypasses all detection logic
vetka session init role=Codex
```

## Lessons

1. **Snapshot merges are dangerous** — Zeta's AGENTS.md leaked to main root, affecting all agents
2. **AGENTS.md and CLAUDE.md on main must be generic** — role-specific versions belong in worktrees only
3. **Worktree detection should be first** — most reliable signal (directory name matches registry)
4. **MCP server restart required** after code changes — Python modules cached in memory
5. **`role=` parameter is the ultimate override** — when auto-detection fails, explicit role always works
6. **Role generator script exists** — `scripts/release/add_role.sh` creates everything (registry, branch, worktree, CLAUDE.md, AGENTS.md) in one command
