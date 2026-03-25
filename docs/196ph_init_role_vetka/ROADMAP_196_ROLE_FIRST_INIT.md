# Roadmap: Phase 196 — Role-First Agent Initialization
**Date:** 2026-03-23
**Author:** Eta (Recon) + Commander (Danila)
**Architecture:** [ARCHITECTURE_196_ROLE_FIRST_INIT.md](./ARCHITECTURE_196_ROLE_FIRST_INIT.md)

---

## Overview

Replace branch-detection guessing with explicit role declaration.
Role is primary key. No role = no task board writes. Git branch = transport, not identity.

---

## Phase 196.1 — Role Parameter + Registry Enhancement
**Priority:** P1 | **Complexity:** Medium | **Domain:** harness

### Tasks:
1. **196.1.1** — Add `pipeline_stage` field to `agent_registry.yaml` for all roles
   - File: `data/templates/agent_registry.yaml`
   - Add: `pipeline_stage: coder|verifier|architect|null` per role
   - Docs: [ARCHITECTURE_196](./ARCHITECTURE_196_ROLE_FIRST_INIT.md) §4.1

2. **196.1.2** — Parse `pipeline_stage` in `agent_registry.py`, add `list_callsigns()`
   - File: `src/services/agent_registry.py`
   - Add field to `AgentRole` dataclass
   - Add `AgentRegistry.list_callsigns() -> list[str]`
   - Docs: [ARCHITECTURE_196](./ARCHITECTURE_196_ROLE_FIRST_INIT.md) §4.1

3. **196.1.3** — Add `role` parameter to `session_init` (backward-compatible)
   - File: `src/mcp/tools/session_tools.py`
   - `role` param: optional string, validated against registry
   - If valid: bind to session, return role_context
   - If invalid: error with available roles
   - If missing: return READ_ONLY mode + available roles list
   - Docs: [ARCHITECTURE_196](./ARCHITECTURE_196_ROLE_FIRST_INIT.md) §3.1

---

## Phase 196.2 — Session Role Store + Task Board Auto-Attribution
**Priority:** P1 | **Complexity:** High | **Domain:** harness

### Tasks:
4. **196.2.1** — Session role storage in `session_tracker.py`
   - File: `src/services/session_tracker.py`
   - Store: `{ session_id → role_callsign, domain, branch }`
   - Method: `set_role(session_id, role)`, `get_role(session_id) -> AgentRole`
   - Persist across MCP calls within same session
   - Docs: [ARCHITECTURE_196](./ARCHITECTURE_196_ROLE_FIRST_INIT.md) §3.2

5. **196.2.2** — Task board auto-attribution from session role
   - File: `src/mcp/tools/task_board_tools.py`
   - On `claim`: auto-set `assigned_to`, `domain`, `role` from session
   - On `complete`: auto-set `branch` from session role (NOT git detection)
   - On `add`: auto-set `role`, `domain` from session
   - READ_ONLY gate: block claim/complete/add without session role
   - Docs: [ARCHITECTURE_196](./ARCHITECTURE_196_ROLE_FIRST_INIT.md) §4.3

6. **196.2.3** — CLAUDE.md regeneration triggered by role (not branch detection)
   - File: `src/tools/generate_claude_md.py`
   - `write_claude_md(callsign)` already exists — wire to session_init role path
   - Remove branch-based trigger, use role-based trigger
   - Docs: [ARCHITECTURE_196](./ARCHITECTURE_196_ROLE_FIRST_INIT.md) §4.2

---

## Phase 196.3 — Ownership Enforcement
**Priority:** P2 | **Complexity:** Medium | **Domain:** harness

### Tasks:
7. **196.3.1** — File ownership validation on `action=complete`
   - File: `src/orchestration/task_board.py`
   - On complete: compare `git diff --name-only` with `role.owned_paths`
   - Violation: log warning in task `status_history`, don't hard-block (soft mode)
   - Config flag: `ownership_enforcement: soft|hard|off`
   - Docs: [ARCHITECTURE_196](./ARCHITECTURE_196_ROLE_FIRST_INIT.md) §3.3

8. **196.3.2** — Cross-domain commit flagging
   - File: `src/orchestration/task_board.py`
   - If committed files touch another role's `owned_paths`: flag in history
   - Alert Commander via task board event
   - Docs: [ARCHITECTURE_196](./ARCHITECTURE_196_ROLE_FIRST_INIT.md) §3.3

---

## Phase 196.4 — Cleanup (Remove Branch Detection Chain)
**Priority:** P3 | **Complexity:** Low | **Domain:** harness
**Depends on:** 196.1, 196.2 fully deployed

### Tasks:
9. **196.4.1** — Remove VETKA_MCP_CWD detection chain from `session_tools.py`
   - Lines 631-661: remove branch detection fallback cascade
   - Role comes from `arguments["role"]`, not git branch
   - Docs: [ARCHITECTURE_196](./ARCHITECTURE_196_ROLE_FIRST_INIT.md) §4.4

10. **196.4.2** — Remove `_detect_git_branch()` fallback from `task_board_tools.py`
    - Lines 516-545: remove auto-infer branch from title/assigned_to
    - Branch comes from session role, set once
    - Docs: [ARCHITECTURE_196](./ARCHITECTURE_196_ROLE_FIRST_INIT.md) §4.4

11. **196.4.3** — Remove `.gitattributes merge=ours` guards for CLAUDE.md
    - No longer needed: CLAUDE.md regenerated on session_init from role
    - Even if merge overwrites, next session_init fixes it
    - Docs: [ARCHITECTURE_196](./ARCHITECTURE_196_ROLE_FIRST_INIT.md) §4.4

---

## Phase 196.5 — Context Injection (Predecessor + L2 Memory)
**Priority:** P2 | **Complexity:** Medium | **Domain:** harness
**Note:** Overlaps with ZETA-RECON-1 and ZETA-RECON-2 tasks

### Tasks:
12. **196.5.1** — Inject predecessor advice content into session_init response
    - File: `src/mcp/tools/session_tools.py`
    - Load latest `EXPERIENCE_{callsign}_*.md` → extract top 5 lessons
    - Include in response `role_context.predecessor_advice` (content, not path)
    - Docs: [ARCHITECTURE_196](./ARCHITECTURE_196_ROLE_FIRST_INIT.md) §5

13. **196.5.2** — Inject ENGRAM/MGC L2 memory into session_init response
    - File: `src/mcp/tools/session_tools.py`
    - Query Qdrant for role-scoped ENGRAM entries
    - Query MGC cache for hot entries
    - Include in response `role_context.memory`
    - Docs: [ARCHITECTURE_196](./ARCHITECTURE_196_ROLE_FIRST_INIT.md) §5,
      [HANDOFF_ZETA_F4_MEMORY_WIRING.md](../192_task_SQLite/HANDOFF_ZETA_F4_MEMORY_WIRING.md)

---

## Phase 196.6 — Proactive Debrief (Zero Manual Effort)
**Priority:** P2 | **Complexity:** Medium | **Domain:** harness
**Found by:** ETA-RECON-2 — debrief chain fully broken (0 reports saved)

### Problem
Debrief questions shown on complete, but answers die with LLM context.
`data/experience_reports/` is empty. No mechanism to capture answers back.
Stop hook exists but not configured.

### Tasks:
14. **196.6.1** — Auto-capture debrief answers in `action=complete` (q1/q2/q3 fields)
    - File: `src/mcp/tools/task_board_tools.py`
    - Add optional q1_bugs/q2_worked/q3_idea to complete arguments
    - If present: auto-create ExperienceReport → store.submit() → smart_debrief
    - Backward-compatible: fields optional
    - Task ID: `tb_1774252103_1`

15. **196.6.2** — Configure Claude Code Stop hook for `auto_experience_save.py`
    - File: `.claude/settings.json`
    - Hook on Stop event → passive signal collection on terminal close
    - Zero agent effort — fires automatically
    - Task ID: `tb_1774252110_1`

16. **196.6.3** — Passive session metrics on every `action=complete`
    - File: `src/mcp/tools/task_board_tools.py`, `src/services/session_tracker.py`
    - Every complete → auto ExperienceReport with passive data (tasks, files, timing, CORTEX)
    - No agent input needed. Agent answers enrich but base report always created.
    - Task ID: `tb_1774252118_1`

---

## Phase 196.5 — Context Injection (DONE by Zeta)
**Status:** COMPLETED — commits df744451 (ENGRAM/MGC) + e31c100f (predecessor advice)
- ~~196.5.1~~ predecessor advice injection → DONE
- ~~196.5.2~~ ENGRAM/MGC injection → DONE

---

## Dependency Graph

```
196.1.1 ─→ 196.1.2 ─→ 196.1.3 ─→ 196.2.1 ─→ 196.2.2
                                      │          │
                                      ↓          ↓
                                   196.2.3    196.3.1 ─→ 196.3.2
                                                │
                                                ↓
                                   196.4.1, 196.4.2, 196.4.3 (parallel)

196.6.3 ─→ 196.6.1 (passive first, then answers)
196.6.2 (independent, can do anytime)

196.5.1, 196.5.2 — DONE (Zeta, commits df744451 + e31c100f)
```

## Assignment Recommendations

| Task Block | Best Agent | Reason |
|-----------|-----------|--------|
| 196.1 (registry + session_init) | Zeta | harness domain, owns session_tools.py |
| 196.2 (session store + task board) | Zeta | owns task_board_tools.py |
| 196.3 (ownership enforcement) | Zeta or Eta | harness/recon |
| 196.4 (cleanup) | Zeta | removing code in owned files |
| ~~196.5 (context injection)~~ | ~~Zeta~~ | **DONE** |
| 196.6 (proactive debrief) | Zeta | owns task_board_tools.py + experience pipeline |
