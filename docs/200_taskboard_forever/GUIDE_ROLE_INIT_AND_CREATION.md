# Role Initialization & Quick Creation Guide

**Date:** 2026-04-07 | **Phase:** 210

---

## Role Resolution Priority (session_init)

When `vetka_session_init` is called, role is resolved in this order:

1. **Explicit `role=` parameter** — always wins, bypasses everything
2. **Worktree name detection** — `Path(cwd).name` matched against `agent_registry.yaml` worktree field
3. **Origin detection** — env vars (`CODEX_SESSION`, `OPENCODE_SESSION`, etc.) mapped to callsigns via `_ORIGIN_CALLSIGN_MAP`
4. **Auto-provision** — creates ephemeral role `{origin}_{hash}` (fallback, no persistence)

**If role is wrong:** use explicit `role=` as immediate fix, then investigate why detection failed.

---

## Creating a New Role (One Command)

```bash
scripts/release/add_role.sh \
  --callsign Codex \
  --domain parallax \
  --worktree photo_parallax_playground_codex \
  --tool-type codex \
  --model-tier gpt-4o \
  --role-title "Parallax & Multimedia Engineer"
```

**What it does automatically:**
1. Validates callsign uniqueness in `agent_registry.yaml`
2. Inserts role entry into registry (before `shared_zones:` section)
3. Creates git branch + worktree
4. Creates registry symlink (worktree reads from main)
5. Generates `CLAUDE.md` + `AGENTS.md` for the worktree
6. Updates `USER_GUIDE_MULTI_AGENT.md`
7. Prints launch command

**Options:**
- `--tool-type` — opencode | claude_code | vibe | codex | free_code
- `--model-tier` — opus | sonnet | haiku | gpt-4o
- `--pipeline-stage` — coder | verifier | architect
- `--owned-paths` — JSON array (auto-detected from domain if omitted)
- `--blocked-paths` — JSON array (auto-detected from domain if omitted)
- `--dry-run` — preview without writing

---

## Troubleshooting: Agent Gets Wrong Role

| Symptom | Cause | Fix |
|---------|-------|-----|
| Agent initializes as Zeta/other | Root AGENTS.md hardcoded to that role | Regenerate: `git checkout HEAD -- AGENTS.md` |
| Agent gets `terminal_XXXX` callsign | No registry match for worktree/origin | Add role to registry or use explicit `role=` |
| Agent can't switch to branch | Branch already used by another worktree | Open agent from the correct worktree directory |
| Changes not taking effect | VETKA MCP server caches Python modules | Restart VETKA server (`./run.sh`) |
| Worktree detection doesn't work | Server running old code without `get_by_worktree()` | Restart server to load new session_tools.py |

---

## Role Init Flow Diagram

```
session_init(role=?)
    │
    ├─ role= provided? ──yes──> registry.get_by_callsign(role) ──> DONE
    │
    ├─ worktree name match? ──yes──> registry.get_by_worktree(cwd.name) ──> DONE
    │
    ├─ origin in ORIGIN_MAP? ──yes──> registry.get_by_callsign(map[origin]) ──> DONE
    │
    └─ auto_provision() ──> ephemeral role {origin}_{hash}
         │
         └─ next_steps includes: "run scripts/release/add_role.sh"
```

---

## Registered Roles (current)

See `data/templates/agent_registry.yaml` for the full list.
Run `vetka_session_init` without `role=` to see `available_roles` in response.

**Key fields per role:**
- `callsign` — unique name (Alpha, Codex, Commander)
- `domain` — functional area (engine, parallax, harness, qa)
- `worktree` — directory name (must match actual git worktree)
- `branch` — git branch (one branch per worktree, enforced by git)
- `tool_type` — claude_code | opencode | vibe | codex | free_code
- `owned_paths` / `blocked_paths` — file access boundaries
