# Architecture: Role-First Agent Initialization
**Phase:** 196 — Role-First Init
**Date:** 2026-03-23
**Author:** Eta (Recon) + Commander (Danila)
**Status:** ARCHITECTURE DEFINED

---

## 1. Problem Statement

### Current State (broken)
```
Agent connects → MCP tries to GUESS who they are:
  1. VETKA_MCP_CWD env var (not set in .mcp.json)
  2. os.getcwd() (returns main repo, not worktree)
  3. git rev-parse --show-toplevel (fails if cwd wrong)
  4. Title-prefix parsing (only on action=complete, too late)
  → _role = None → CLAUDE.md not regenerated → agent has no identity
```

**Root cause:** Identity is inferred from transport (git branch), not declared explicitly.

### Target State (role-first)
```
Agent connects → session_init(role="Alpha")
  → Registry validates role
  → Session bound to role
  → All task board ops auto-attributed
  → No branch detection needed
  → Works with Claude Code, Codex, Cursor, any client
```

**Principle:** Role is the **primary key**, git branch is just **transport**.

---

## 2. Architecture Model

### Two Orthogonal Axes

```
MYCELIUM PIPELINE (per-subtask — WHAT stage):
  architect → researcher → coder → verifier

CUT FLEET (per-session — WHERE/WHO):
  Commander, Alpha, Beta, Gamma, Delta, Zeta, Eta
```

### Mapping

```yaml
pipeline_roles:            # WHAT (stage in pipeline)
  - architect              # → Commander
  - researcher             # → Dragon (Mycelium auto-tier)
  - coder                  # → Alpha, Beta, Gamma (domain-split)
  - verifier               # → Delta, Epsilon

fleet_roles:               # WHERE (domain ownership)
  - Commander: { pipeline_stage: architect, domain: all }
  - Alpha:     { pipeline_stage: coder,    domain: engine }
  - Beta:      { pipeline_stage: coder,    domain: media }
  - Gamma:     { pipeline_stage: coder,    domain: ux }
  - Delta:     { pipeline_stage: verifier, domain: qa }
  - Epsilon:   { pipeline_stage: verifier, domain: qa }
  - Zeta:      { pipeline_stage: null,     domain: harness }  # meta
  - Eta:       { pipeline_stage: null,     domain: recon }    # meta
```

### Why Two Axes
- **Pipeline stage** = what function the agent performs (design, code, verify)
- **Fleet role** = what files/domain the agent owns
- They are **orthogonal**: Alpha is always a coder in engine domain, but Mycelium
  can also spin up a one-shot coder for a subtask — that's a pipeline role, not a fleet role
- New coders added trivially: `Theta: { stage: coder, domain: audio }`

---

## 3. Role-First Session Protocol

### 3.1 Session Init with Role

```python
# NEW: role parameter in session_init
session_init(role="Alpha")  # explicit
session_init()              # → returns available roles, task board LOCKED
```

**Response when role is provided:**
```json
{
  "session_id": "uuid",
  "role": {
    "callsign": "Alpha",
    "domain": "engine",
    "pipeline_stage": "coder",
    "branch": "claude/cut-engine",
    "owned_paths": ["..."],
    "blocked_paths": ["..."]
  },
  "role_context": {
    "predecessor_advice": "...(injected, not just path)...",
    "pending_tasks": [...],
    "memory": { "engram": [...], "mgc": [...] }
  },
  "task_board": "UNLOCKED"
}
```

**Response when role is NOT provided:**
```json
{
  "session_id": "uuid",
  "role": null,
  "available_roles": ["Alpha", "Beta", "Gamma", "Delta", "Commander", "Zeta", "Eta"],
  "task_board": "READ_ONLY",
  "message": "Specify role= to unlock task board. Without role, you can read but not claim/complete."
}
```

### 3.2 Session-Bound Role Attribution

Once role is set via `session_init(role=X)`, ALL subsequent operations in this session
are automatically attributed:

```
session_init(role="Alpha")
  ↓ session stores: { session_id → role=Alpha, domain=engine, branch=claude/cut-engine }

task_board action=claim task_id=tb_xxx
  → auto: assigned_to=Alpha, agent_type=claude_code, domain=engine
  → ownership check: task files ⊆ Alpha.owned_paths?

task_board action=complete task_id=tb_xxx
  → auto: branch=claude/cut-engine (from session role, NOT git detection)
  → auto: commit attributed to Alpha
  → no branch detection needed at all
```

### 3.3 Ownership Enforcement

```
BEFORE (advisory):
  - owned_paths stored but NOT enforced
  - agent could touch any file

AFTER (enforced):
  - action=complete validates: touched files ⊆ role.owned_paths ∪ role.shared_zones
  - violation → warning (soft) or block (hard, configurable)
  - cross-domain commits flagged in task history
```

---

## 4. What Changes

### 4.1 agent_registry.yaml — Add pipeline_stage

```yaml
roles:
  - callsign: "Alpha"
    domain: "engine"
    pipeline_stage: "coder"        # NEW
    role_title: "Engine Architect"
    worktree: "cut-engine"
    branch: "claude/cut-engine"
    # ... rest unchanged
```

### 4.2 session_tools.py — Role parameter + session binding

```python
async def handle_session_init(arguments: dict) -> dict:
    role_name = arguments.get("role")  # NEW: explicit role

    if role_name:
        registry = get_agent_registry()
        role = registry.get_by_callsign(role_name)
        if not role:
            return {"error": f"Unknown role: {role_name}. Available: {registry.list_callsigns()}"}

        # Bind role to session
        session_store.set_role(session_id, role)

        # Auto-regenerate CLAUDE.md (no branch detection needed!)
        write_claude_md(role.callsign, registry=registry)

        # Inject predecessor advice (content, not just path)
        predecessor = load_predecessor_advice(role)

        # Inject L2 memory
        engram = load_engram_for_role(role)
        mgc = load_mgc_for_role(role)

        context["role_context"] = { ... }
        context["task_board"] = "UNLOCKED"
    else:
        context["task_board"] = "READ_ONLY"
        context["available_roles"] = registry.list_callsigns()
```

### 4.3 task_board_tools.py — Auto-attribution from session

```python
async def handle_task_board(arguments: dict) -> dict:
    action = arguments["action"]
    session_role = session_store.get_role(session_id)  # from session_init

    if action in ("claim", "complete", "add") and not session_role:
        return {"error": "Task board is READ_ONLY. Call session_init(role=...) first."}

    if action == "claim":
        arguments.setdefault("assigned_to", session_role.callsign)
        arguments.setdefault("domain", session_role.domain)

    if action == "complete":
        arguments.setdefault("branch", session_role.branch)
        # No _detect_git_branch() needed!
```

### 4.4 What Gets Removed

```
REMOVED (no longer needed):
  - VETKA_MCP_CWD env var detection chain (session_tools.py:631-661)
  - _detect_git_branch() fallback cascade (task_board_tools.py:516-545)
  - Title-prefix branch inference
  - Worktree name matching via git rev-parse
  - .gitattributes merge=ours guards for CLAUDE.md

KEPT:
  - agent_registry.yaml (enhanced with pipeline_stage)
  - generate_claude_md.py (triggered by role, not branch)
  - Branch field on task (still useful for git ops, but set from role, not detected)
```

---

## 5. Memory Architecture (VETKA stores role memory)

```
VETKA Memory (persistent, role-scoped):
  ├── ENGRAM (per-role learnings)
  │     key: "Alpha:engine:lesson_xyz"
  │     → survives session, survives agent replacement
  │
  ├── MGC (compressed, garbage-collected)
  │     → old irrelevant memories pruned automatically
  │     → "only MGC discards the chaff" — Danila
  │
  └── Experience Reports (per-role, per-session)
        → debrief Q&A answers
        → injected into next session_init(role=same)

Claude Code Memory (~/.claude/projects/.../memory/):
  → User preferences (Danila's feedback)
  → NOT role-specific, applies to all sessions

CLAUDE.md:
  → Generated from role + registry + experience
  → Even if overwritten by merge, session_init regenerates it
  → Role is the source of truth, CLAUDE.md is just a cache
```

---

## 6. Migration Path

1. **Phase 196.1** — Add `role` param to session_init, backward-compatible (optional)
2. **Phase 196.2** — Session role store + task board auto-attribution
3. **Phase 196.3** — Ownership enforcement (soft warnings first)
4. **Phase 196.4** — Remove branch detection chain (cleanup)
5. **Phase 196.5** — Predecessor advice + L2 memory injection into session_init response

Backward compatible: `session_init()` without role still works (READ_ONLY mode).
Agents can migrate one by one.

---

## 7. Files Affected

| File | Change | Complexity |
|------|--------|-----------|
| `data/templates/agent_registry.yaml` | Add `pipeline_stage` field | Low |
| `src/services/agent_registry.py` | Parse new field, add `list_callsigns()` | Low |
| `src/mcp/tools/session_tools.py` | `role` param, session binding, memory injection | High |
| `src/mcp/tools/task_board_tools.py` | Auto-attribution from session role | Medium |
| `src/orchestration/task_board.py` | Accept role-sourced branch (no detection) | Low |
| `src/services/session_tracker.py` | Store role per session | Medium |
| `src/tools/generate_claude_md.py` | Trigger from role, not branch | Low |
| `.mcp.json` (all worktrees) | Remove VETKA_MCP_CWD (not needed) | Low |

---

## 8. Success Criteria

- [ ] `session_init(role="Alpha")` returns full role context with predecessor advice
- [ ] `session_init()` without role returns READ_ONLY + available roles list
- [ ] `task_board action=claim` auto-sets assigned_to from session role
- [ ] `task_board action=complete` auto-sets branch from session role (no git detection)
- [ ] Ownership violation produces warning in task history
- [ ] Works identically from Claude Code, Codex, Cursor, or raw MCP client
- [ ] Branch detection chain removed, zero fallback cascades
