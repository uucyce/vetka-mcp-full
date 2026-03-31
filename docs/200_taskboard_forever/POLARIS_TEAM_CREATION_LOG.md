# POLARIS TEAM CREATION LOG
## How Captain Polaris Built a Fleet from Free Qwen Sailors

**Date:** 2026-03-31
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

### Step 1: Define Roles in Registry
Add entries to `data/templates/agent_registry.yaml`:
```yaml
- callsign: "Lambda"
  domain: "qa"
  pipeline_stage: "verifier"
  tool_type: "opencode"
  role_title: "QA Engineer 3 / Opencode Qwen"
  worktree: "cut-qa-3"
  branch: "agent/lambda-qa"
  model_tier: "sonnet"
  file: "e2e/*.spec.cjs"          # ← REQUIRED for generate_claude_md.py
  owned_paths: [...]
  blocked_paths: [...]
```

**CRITICAL:** Every role MUST have a `file:` field. Without it, `generate_claude_md.py` crashes with `KeyError: 'file'`.

### Step 2: Create Branch + Worktree
```bash
git branch agent/lambda-qa
git worktree add .claude/worktrees/cut-qa-3 agent/lambda-qa
```

### Step 3: Generate CLAUDE.md
```bash
.venv/bin/python -m src.tools.generate_claude_md --role Lambda
```
This creates `.claude/worktrees/cut-qa-3/CLAUDE.md` — used by Claude Code agents.

### Step 4: Generate AGENTS.md
```bash
.venv/bin/python -m src.tools.generate_agents_md --role Lambda
```
This creates `.claude/worktrees/cut-qa-3/AGENTS.md` — used by opencode agents.

**CRITICAL:** Opencode reads `AGENTS.md`, NOT `CLAUDE.md`. Without per-worktree `AGENTS.md`, opencode agents see the wrong role.

### Step 5: Verify
Launch the agent and ask "какая твоя роль?" — should see the correct callsign, domain, and pipeline_stage.

---

## 3. The Pitfalls — What Went Wrong

### Pitfall 1: WEATHER roles after shared_zones
**Problem:** Theta/Iota/Kappa were defined AFTER `shared_zones:` in registry.yaml. The generator only parses roles before `shared_zones:`, returning "Unknown callsign".
**Fix:** Move all role entries to the main section (before `shared_zones:`).

### Pitfall 2: Missing `file:` field
**Problem:** New roles didn't have `file:` field. `generate_claude_md.py` expects it and crashes.
**Fix:** Add `file:` to every role entry (first file in owned_paths).

### Pitfall 3: AGENTS.md vs CLAUDE.md
**Problem:** Claude Code reads `CLAUDE.md`. Opencode reads `AGENTS.md`. They're different files.
**Fix:** Generate BOTH for every worktree.

### Pitfall 4: Worktree files leaking into main
**Problem:** Per-worktree `AGENTS.md` files could accidentally be committed, overwriting the shared root `AGENTS.md`.
**Fix:** 
- `.claude/worktrees/` is already in `.gitignore`
- Added `AGENTS_MD_GUARD` to `task_board.py` merge_request (same as `CLAUDE_MD_GUARD`)
- Generator auto-regenerates all worktree `AGENTS.md` on demand

### Pitfall 5: Registry not synced across worktrees
**Problem:** Changes to `agent_registry.yaml` in one worktree don't appear in another until merged.
**Fix:** Always merge registry changes to main before generating CLAUDE.md/AGENTS.md.

---

## 4. The Solution — One Command Per Role

### For a SINGLE role:
```bash
# 1. Add role to registry (edit data/templates/agent_registry.yaml)
# 2. Create branch + worktree
git branch agent/<role-lower> && git worktree add .claude/worktrees/<worktree> agent/<role-lower>
# 3. Generate files
.venv/bin/python -m src.tools.generate_claude_md --role <Callsign>
.venv/bin/python -m src.tools.generate_agents_md --role <Callsign>
# 4. Commit
git add data/templates/agent_registry.yaml && git commit -m "Add <Callsign> role"
```

### For ALL roles at once:
```bash
.venv/bin/python -m src.tools.generate_claude_md --all
.venv/bin/python -m src.tools.generate_agents_md --all
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

## 6. The Fleet — 14 Roles

| Callsign | Domain | Client | Model | Worktree |
|----------|--------|--------|-------|----------|
| Commander | architect | Claude Code | Opus | pedantic-bell |
| **Polaris** | architect | **Opencode** | **Qwen** | **captain** |
| Alpha | engine | Claude Code | Sonnet | cut-engine |
| Beta | media | Claude Code | Sonnet | cut-media |
| Gamma | ux | Claude Code | Sonnet | cut-ux |
| Delta | qa | Claude Code | Sonnet | cut-qa |
| Epsilon | qa | Claude Code | Sonnet | cut-qa-2 |
| Lambda | qa | Opencode | Qwen | cut-qa-3 |
| Mu | qa | Opencode | Qwen | cut-qa-4 |
| Zeta | harness | Claude Code | Opus | harness |
| Eta | harness | Claude Code | Sonnet | harness-eta |
| Theta | weather | Opencode | Qwen | weather-core |
| Iota | weather | Opencode | Qwen | weather-mediator |
| Kappa | weather | Opencode | Qwen | weather-terminal |

---

## 7. Quick Reference

```bash
# Generate ALL roles (after registry changes)
.venv/bin/python -m src.tools.generate_claude_md --all
.venv/bin/python -m src.tools.generate_agents_md --all

# Generate single role
.venv/bin/python -m src.tools.generate_claude_md --role Polaris
.venv/bin/python -m src.tools.generate_agents_md --role Polaris

# Launch agent
cd .claude/worktrees/<worktree> && opencode -m opencode/qwen3.6-plus-free
# First message: vetka_session_init role=<Callsign>
```

---

*"From free sailors to a disciplined fleet — one registry entry at a time."*
— Captain Polaris, 2026-03-31
