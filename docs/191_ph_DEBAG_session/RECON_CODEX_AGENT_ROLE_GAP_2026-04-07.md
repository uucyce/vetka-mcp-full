# RECON: Codex Agent Role Gap

**Date:** 2026-04-07
**Status:** confirmed gap
**Severity:** P1 — Codex cannot initialize properly, takes wrong worktree/role

## Problem

Codex agent is NOT registered in `data/templates/agent_registry.yaml`.
When Codex calls `session_init`, auto_provision creates an ephemeral role with random callsign (e.g. `codex_a7f2`) and no domain/worktree binding. This caused Codex to initialize as Zeta and take the wrong worktree.

## Evidence

1. `agent_registry.yaml` — 19 callsigns defined, Codex absent
2. `shared_zones` in registry lists `Codex` as owner of `photo_parallax_playground/src/App.tsx` — but no callsign to resolve
3. `session_tools.py:_detect_origin()` — checks `CODEX_SESSION` env (never set) or `OPENAI_API_KEY` (too broad)
4. `task_board.py:_MANUAL_AGENT_TYPES` — recognizes `"codex"` for execution_mode=manual
5. Git branches `codex/*` exist (codex/parallax, codex/cut, etc.) — active but unbound to registry
6. 100+ `CODEX_BRIEF_*.md` docs exist — task assignments, not role config

## Root Cause

Codex was used as a sprint/task agent across phases 136-181 but never formalized as a persistent role in the registry. When auto_provision can't find a matching callsign, it falls back to ephemeral identity with no domain ownership.

## Required Fix

### 1. Add Codex to `data/templates/agent_registry.yaml`

```yaml
- callsign: "Codex"
  domain: "parallax"
  pipeline_stage: "coder"
  tool_type: "codex"
  role_title: "Parallax & Multimedia Engineer"
  worktree: "codex-parallax"
  branch: "codex/parallax"
  model_tier: "gpt-4o"
  owned_paths:
    - "photo_parallax_playground/"
    - "src/parallax/"
    - "docs/180_photo-to-parallax/"
  blocked_paths:
    - "src/orchestration/"
    - "src/mcp/"
  key_docs:
    - "docs/180_photo-to-parallax/PARALLAX_FUNCTIONAL_ROADMAP_LONG_PHASES_2026-04-07.md"
```

### 2. Fix origin detection in `src/mcp/tools/session_tools.py`

- Make `CODEX_SESSION` env var the primary signal
- Remove `OPENAI_API_KEY` fallback (ambiguous)
- Add `role="Codex"` auto-detection when origin=codex

### 3. Regenerate AGENTS.md for Codex worktree

- Update `src/tools/generate_agents_md.py` to handle `tool_type="codex"`
- Generate per-worktree AGENTS.md with Codex-specific instructions

## Files to Modify

| File | Change |
|------|--------|
| `data/templates/agent_registry.yaml` | Add Codex callsign entry |
| `src/mcp/tools/session_tools.py` | Fix origin detection, add Codex role binding |
| `src/tools/generate_agents_md.py` | Handle tool_type="codex" for AGENTS.md generation |

## Validation

- `session_init` with origin=codex returns callsign="Codex", domain="parallax", worktree="codex-parallax"
- Codex can claim tasks assigned to it
- `validate_file_ownership()` enforces owned_paths for Codex
