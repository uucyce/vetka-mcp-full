# POLARIS TEAM CREATION LOG
## How Captain Polaris Built a Fleet from Free Qwen Sailors

**Date:** 2026-03-31 (Updated: 2026-04-01)
**Phase:** 201
**Author:** Polaris (Captain / Opencode Architect)
**Location:** docs/200_taskboard_forever/

---

## 1. The Problem

When launching opencode agents in worktrees, they all saw the same wrong role:
- **Expected:** Lambda (QA3), Mu (QA4), Theta (WEATHER), Iota (WEATHER), Kappa (WEATHER)
- **Got:** `terminal_c040` (auto-provisioned worker/coder) → fell back to Opus/Commander

**Root cause:** Opencode reads `AGENTS.md` from the worktree root. Without a per-worktree `AGENTS.md`, it falls back to the shared root `AGENTS.md` which describes Opus/Commander.

---

## 2. The Journey — Step by Step

### The Old Way (Manual — 5 steps)
```bash
# 1. Add role to registry (edit data/templates/agent_registry.yaml)
# 2. Create branch + worktree
git branch agent/<role-lower> && git worktree add .claude/worktrees/<worktree> agent/<role-lower>
# 3. Generate files
.venv/bin/python -m src.tools.generate_claude_md --role <Callsign>
.venv/bin/python -m src.tools.generate_agents_md --role <Callsign>
# 4. Create registry symlink (so worktree always reads from main)
ln -sf $(pwd)/data/templates/agent_registry.yaml .claude/worktrees/<worktree>/data/templates/agent_registry.yaml
# 5. Commit
git add data/templates/agent_registry.yaml && git commit -m "Add <Callsign> role"
```

### The New Way (One Command)
```bash
scripts/release/add_role.sh --callsign Mistral-1 --domain weather --worktree weather-mistral-1 --tool-type opencode --model-tier sonnet
```

This single command does ALL 5 steps: registry entry, branch, worktree, CLAUDE.md, AGENTS.md, symlink, USER_GUIDE update.

**CRITICAL:** Every role MUST have a `file:` field in registry. The script adds it automatically (first file in owned_paths).

---

## 3. The Pitfalls — What Went Wrong

### Pitfall 1: WEATHER roles after shared_zones
**Problem:** Theta/Iota/Kappa were defined AFTER `shared_zones:` in registry.yaml. The generator only parses roles before `shared_zones:`, returning "Unknown callsign".
**Fix:** Move all role entries to the main section (before `shared_zones:`).

### Pitfall 2: Missing `file:` field
**Problem:** New roles didn't have `file:` field. `generate_claude_md.py` expects it and crashes.
**Fix:** Add `file:` to every role entry (first file in owned_paths). The `add_role.sh` script does this automatically.

### Pitfall 3: AGENTS.md vs CLAUDE.md
**Problem:** Claude Code reads `CLAUDE.md`. Opencode reads `AGENTS.md`. They're different files.
**Fix:** Generate BOTH for every worktree. The `add_role.sh` script generates both.

### Pitfall 4: Worktree files leaking into main
**Problem:** Per-worktree `AGENTS.md` files could accidentally be committed, overwriting the shared root `AGENTS.md`.
**Fix:** 
- `.claude/worktrees/` is already in `.gitignore`
- Added `AGENTS_MD_GUARD` to `task_board.py` merge_request (same as `CLAUDE_MD_GUARD`)
- Generator auto-regenerates all worktree `AGENTS.md` on demand

### Pitfall 5: Registry not synced across worktrees ⚠️ THE BIG ONE
**Problem:** Each worktree has its own copy of `data/templates/agent_registry.yaml`. When new roles are added on main, worktree copies become stale. Opencode agents in worktrees read the stale copy and can't find new roles.

**Root cause:** `src/services/agent_registry.py` uses `_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent` — which resolves to the worktree root, not main.

**Fix: Registry symlinks.** Every worktree's `data/templates/agent_registry.yaml` is now a symlink → main's registry:
```bash
ln -sf $(pwd)/data/templates/agent_registry.yaml .claude/worktrees/<worktree>/data/templates/agent_registry.yaml
```
The `add_role.sh` script creates this symlink automatically. Now all 16+ worktrees always see the latest registry.

**Why Claude Code doesn't have this problem:** Claude Code agents call `vetka_session_init role=X` → MCP server (port 5001) reads registry from main. They never read the worktree copy. But opencode agents load `AgentRegistry` locally → read worktree copy → stale data.

---

## 4. The Solution — One Command Per Role

### The Script: `scripts/release/add_role.sh`
```bash
# Quick role creation — all steps automated
scripts/release/add_role.sh \
  --callsign Mistral-1 \
  --domain weather \
  --worktree weather-mistral-1 \
  --tool-type opencode \
  --model-tier sonnet \
  --role-title "Mistral Weather Agent 1"
```

**What it does:**
1. Adds role to `agent_registry.yaml` (with `file:` field)
2. Creates git branch + worktree
3. Creates registry symlink → main (always fresh)
4. Generates CLAUDE.md + AGENTS.md
5. Updates USER_GUIDE_MULTI_AGENT.md
6. Prints launch command

### For ALL roles at once:
```bash
.venv/bin/python -m src.tools.generate_claude_md --all
.venv/bin/python -m src.tools.generate_agents_md --all
```

### Fix stale registry in existing worktrees:
```bash
for wt in cut-engine cut-media cut-ux cut-qa cut-qa-2 cut-qa-3 cut-qa-4 \
          harness harness-eta pedantic-bell weather-core weather-mediator \
          weather-terminal captain; do
  rm -f .claude/worktrees/$wt/data/templates/agent_registry.yaml
  ln -sf $(pwd)/data/templates/agent_registry.yaml .claude/worktrees/$wt/data/templates/
done
```

---

## 5. The Recipe — Role Template

```yaml
# ── <Callsign>: <Domain> Domain (<Client>/<Model>) ──────────
- callsign: "<Callsign>"
  domain: "<domain>"
  pipeline_stage: "<coder|verifier|null>"
  tool_type: "<claude_code|opencode>"
  role_title: "<Human-readable title>"
  worktree: "<worktree-name>"
  branch: "agent/<role-lowercase>"
  model_tier: "<sonnet|opus>"
  file: "<first-file-in-owned-paths>"    # ← REQUIRED
  owned_paths:
    - "path/to/files/"
  blocked_paths:
    - "paths/to/avoid/"
  predecessor_docs: "docs/.../feedback/"
  key_docs:
    - "docs/.../architecture.md"
  roadmap: ""
```

---

## 6. The Fleet — 25 Roles (International Flotilla!)

| Callsign | Domain | Client | Model | Worktree |
|----------|--------|--------|-------|----------|
| Commander | architect | Claude Code | Opus | pedantic-bell |
| **Polaris** | architect | **Opencode** | **Qwen** | **captain** |
| Alpha | engine | Claude Code | Sonnet | cut-engine |
| Beta | media | Claude Code | Haiku | cut-media |
| Gamma | ux | Claude Code | Haiku | cut-ux |
| Delta | qa | Claude Code | Haiku | cut-qa |
| Epsilon | qa | Claude Code | Haiku | cut-qa-2 |
| Lambda | qa | Opencode | Qwen | cut-qa-3 |
| Mu | qa | Opencode | Qwen | cut-qa-4 |
| Mistral-2 | qa | Vibe CLI | Mistral Vibe | cut-qa-5 |
| Zeta | harness | Claude Code | Opus | harness |
| Eta | harness | Claude Code | Sonnet | harness-eta |
| Theta | weather | Opencode | Qwen | weather-core |
| Iota | weather | Opencode | Qwen | weather-mediator |
| Kappa | weather | Opencode | Qwen | weather-terminal |
| **Mistral-1** | weather | **Vibe CLI** | **Mistral Vibe** | **weather-mistral-1** |
| **Mistral-3** | weather | **Vibe CLI** | **Mistral Vibe** | **weather-mistral-2** |

**3 fleets, 1 codebase:**
- 🇺🇸 Claude Code fleet (Opus/Sonnet/Haiku) — 8 agents
- 🇨🇳 Opencode/Qwen fleet (Qwen3.6 Plus Free) — 8 agents
- 🇫🇷 Mistral Vibe fleet (Free tier) — 3 agents
- **Total: 19 active agents, 25 roles in registry**

---

## 7. Quick Reference

```bash
# ONE-COMMAND role creation
scripts/release/add_role.sh --callsign NAME --domain DOMAIN --worktree WT

# Generate ALL CLAUDE.md + AGENTS.md (after registry changes)
.venv/bin/python -m src.tools.generate_claude_md --all
.venv/bin/python -m src.tools.generate_agents_md --all

# Fix stale registry symlinks (run after merge)
for wt in .claude/worktrees/*/; do
  rm -f "$wt/data/templates/agent_registry.yaml"
  ln -sf "$(pwd)/data/templates/agent_registry.yaml" "$wt/data/templates/"
done

# Launch agent
cd .claude/worktrees/<worktree> && opencode -m opencode/qwen3.6-plus-free
# First message: vetka_session_init role=<Callsign>
```

---

*"From free sailors to a disciplined fleet — one registry entry at a time."*
— Captain Polaris, 2026-03-31 (Updated 2026-04-01)
