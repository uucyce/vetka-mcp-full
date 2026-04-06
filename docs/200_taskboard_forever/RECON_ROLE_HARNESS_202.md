# RECON: Role Harness Audit — Phase 202
## Agent Registry, AGENTS.md Pipeline, Role Naming Matrix

**Date:** 2026-04-02
**Phase:** 202
**Author:** Eta (Harness Engineer 2)
**Task:** tb_1775138684_85698_1
**Status:** COMPLETED — fixes applied

---

## 1. Audit Findings

### BUG-1 (FIXED): Mistral-1/2/3 under `external_agents:` — invisible to registry

**Root cause:** `add_role.sh` used `cat >> registry.yaml` — blind append to EOF.
The file ends with `external_agents:` section, so all new entries landed there.
`agent_registry.py` only reads `data.get("roles", [])` — `external_agents:` is silently ignored.

**Impact:** `session_init role=Mistral-1` → "Unknown callsign" → fallback to Commander identity.
All 3 Mistral agents (weather-mistral-1, cut-qa-5, weather-mistral-2) were misidentified.

**Fix:** Moved Mistral-1/2/3 from `external_agents:` to `roles:` in agent_registry.yaml.
Verified: `AgentRegistry.get_by_callsign("Mistral-1")` → `Mistral Weather Agent 1 [weather]`.

---

### BUG-2 (FIXED): AGENTS.md for Mistral-1/2/3 = generic 265-line project content

**Root cause:** `generate_agents_md --role Mistral-1` was silently failing (BUG-1 cascade) and
leaving the old generic root AGENTS.md (Commander identity) in the worktree.

**Impact:** Agents launched thinking they are Commander (no owned_paths, no domain, no task filter).

**Fix:** After BUG-1 fix, regenerated AGENTS.md for all 3 roles:
- `.claude/worktrees/weather-mistral-1/AGENTS.md` → 814 bytes (role-specific)
- `.claude/worktrees/cut-qa-5/AGENTS.md` → 867 bytes (role-specific)
- `.claude/worktrees/weather-mistral-2/AGENTS.md` → 814 bytes (role-specific)

---

### BUG-3: Naming matrix — callsigns don't reflect function

**Status:** Documented, architectural decision deferred to Commander.

**Problem:** `Mistral-1`, `Mistral-2`, `Mistral-3` give no information about:
- What domain they work in (weather vs qa)
- What function they perform (coder vs verifier)
- What model they run on

**Proposed naming convention** (for new roles going forward):

```
{Fleet}-{Domain}-{Index}
```

| Pattern | Example | Meaning |
|---------|---------|---------|
| `Qwen-QA-1` | Lambda | Qwen fleet, QA domain, instance 1 |
| `Qwen-Weather-1` | Theta | Qwen fleet, Weather domain, instance 1 |
| `Mistral-Weather-1` | Mistral-1 | Mistral fleet, Weather domain, instance 1 |
| `Mistral-QA-1` | Mistral-2 | Mistral fleet, QA domain, instance 1 |

**Current callsigns are not renamed** — breaking change to branches/worktrees. Use `role_title` for human display.

---

### BUG-4 (FIXED): `add_role.sh` — blind append to EOF

**Root cause:** `cat >> "$REGISTRY"` appends at end of file regardless of YAML structure.

**Fix (add_role.sh v2):**
- Python-based insertion BEFORE `shared_zones:` marker
- Duplicate callsign validation (exits with error if already exists)
- Exit-code check on `generate_claude_md` and `generate_agents_md` — fails loudly
- `.venv/bin/python3` consistently (no bare `python3` calls)
- `--dry-run` mode for safe testing

---

### BUG-5: No task_board integration for role provisioning

**Status:** Architectural proposal, not yet implemented.

**Proposed:** New `action=provision_role` in task board:
1. Commander creates task: `type=provision, callsign=Xi, domain=qa`
2. Agent sees task, calls `vetka_task_board action=provision_role callsign=Xi`
3. Task board runs `add_role.sh` and returns worktree path
4. Agent self-boots in new worktree with correct identity

This removes the manual step entirely from Commander's workflow.

---

## 2. Fleet State (post-fix)

### Registry — 17 roles in `roles:` section

| Callsign | Domain | Tool | Worktree | AGENTS.md |
|----------|--------|------|----------|-----------|
| Alpha | engine | claude_code | cut-engine | ✅ CLAUDE.md |
| Beta | media | claude_code | cut-media | ✅ CLAUDE.md |
| Gamma | ux | claude_code | cut-ux | ✅ CLAUDE.md |
| Delta | qa | claude_code | cut-qa | ✅ CLAUDE.md |
| Epsilon | qa | claude_code | cut-qa-2 | ✅ CLAUDE.md |
| Lambda | qa | opencode | cut-qa-3 | ✅ AGENTS.md |
| Mu | qa | opencode | cut-qa-4 | ✅ AGENTS.md |
| Zeta | harness | claude_code | harness | ✅ CLAUDE.md |
| Eta | harness | claude_code | harness-eta | ✅ CLAUDE.md |
| Commander | architect | claude_code | pedantic-bell | ✅ CLAUDE.md |
| Polaris | architect | opencode | captain | ✅ AGENTS.md |
| Theta | weather | opencode | weather-core | ✅ AGENTS.md |
| Iota | weather | opencode | weather-mediator | ✅ AGENTS.md |
| Kappa | weather | opencode | weather-terminal | ✅ AGENTS.md |
| **Mistral-1** | weather | opencode | weather-mistral-1 | ✅ FIXED |
| **Mistral-2** | qa | opencode | cut-qa-5 | ✅ FIXED |
| **Mistral-3** | weather | opencode | weather-mistral-2 | ✅ FIXED |

**All 17 worktrees** have registry symlink → main (verified).

---

## 3. Architecture — Role Identity Pipeline

```
Commander: add_role.sh --callsign Xi --domain qa --worktree cut-qa-6
                │
                ├─ 1. Validate callsign unique in agent_registry.yaml
                ├─ 2. Insert role into roles: section (Python, before shared_zones:)
                ├─ 3. git branch + git worktree add
                ├─ 4. ln -sf registry.yaml → worktree symlink
                ├─ 5. generate_claude_md --role Xi  (writes CLAUDE.md)
                │      generate_agents_md --role Xi  (writes AGENTS.md)
                └─ 6. USER_GUIDE_MULTI_AGENT.md update

Agent boots in worktree:
  Claude Code → reads CLAUDE.md → vetka_session_init role=Xi
  Opencode    → reads AGENTS.md → vetka_session_init role=Xi
                                        │
                                        └─ MCP reads registry from main (symlink)
                                           Returns: role_context, owned_paths, tasks
```

### Key invariants

1. **`roles:` is the ONLY source of truth** — `external_agents:` is for read-only browser agents (Gemini/Kimi/GPT), not active coders
2. **Every worktree MUST have a registry symlink** — prevents stale copy problem
3. **AGENTS.md + CLAUDE.md must be regenerated after any registry change** — `generate_agents_md --all && generate_claude_md --all`
4. **Worktree files NEVER commit to main** — `.claude/worktrees/` in `.gitignore`, AGENTS_MD_GUARD in merge_request

---

## 4. Proposed Task Matrix for Delta Tests

For `test_add_role_validation.py`:

```python
# T1: add_role.sh --dry-run succeeds for new callsign
# T2: add_role.sh fails if callsign already in registry
# T3: After add_role.sh, new callsign found by AgentRegistry.get_by_callsign()
# T4: New role INSIDE roles: section (before shared_zones: line)
# T5: generate_agents_md produces role-specific content (not generic 265-line)
# T6: Registry symlink created in worktree
# T7: AGENTS.md line count < 100 (role-specific, not generic)
```

---

## 5. Quick Reference

```bash
# Add new role (safe, validates, inserts in roles: section)
scripts/release/add_role.sh \
  --callsign Xi \
  --domain qa \
  --worktree cut-qa-6 \
  --tool-type opencode \
  --model-tier sonnet \
  --role-title "QA Agent 6 / Qwen"

# Regenerate all AGENTS.md + CLAUDE.md after registry changes
cd /path/to/vetka_live_03
.venv/bin/python3 -m src.tools.generate_agents_md --all
.venv/bin/python3 -m src.tools.generate_claude_md --all

# Fix stale registry symlinks
for wt in .claude/worktrees/*/; do
  rm -f "$wt/data/templates/agent_registry.yaml"
  ln -sf "$(pwd)/data/templates/agent_registry.yaml" "$wt/data/templates/"
done

# Verify all roles visible
.venv/bin/python3 -c "
from src.services.agent_registry import AgentRegistry
from pathlib import Path
r = AgentRegistry(Path('data/templates/agent_registry.yaml'))
print(f'{len(r.roles)} roles:', [x.callsign for x in r.roles])
"
```

---

*Harness Audit completed by Eta, 2026-04-02*
