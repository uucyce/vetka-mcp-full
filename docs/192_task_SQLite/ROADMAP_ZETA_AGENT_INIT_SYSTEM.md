# Roadmap: Agent Initialization System (Zeta)
**Phase:** 192+ (TaskBoard + Agent Infrastructure)
**Date:** 2026-03-22
**Author:** Architect-Commander (pedantic-bell)
**Agent:** Zeta (new, non-CUT worktree)
**Status:** RESEARCH REQUIRED

---

## Problem Statement

CUT runs 4-5 Opus agents in parallel worktrees. Currently each agent receives its
context through:
1. Shared CLAUDE.md (same for all agents — generic)
2. Commander's dispatch messages (manual, user relays)
3. Task board claim (no role binding)

**What's missing:**
- Agent doesn't automatically know its ROLE when starting in a worktree
- No automatic binding between `project_id` + `role/domain` + `worktree`
- Experience reports are written but not systematically fed to successors
- Task board doesn't enforce role-based file ownership
- No feedback guard requiring experience report before session end

**Current state (manual v0):**
Commander created per-worktree CLAUDE.md files (2026-03-22) with role-specific
instructions, predecessor advice, and file ownership. This works but is MANUAL —
Commander must update each file after every session.

## Vision

```
Agent starts in worktree
  → CLAUDE.md auto-loaded (role, files, advice) ← DONE (v0, manual)
  → Task board knows agent's role + allowed_paths ← PARTIAL (field exists)
  → On task claim: role validated against task domain ← NOT DONE
  → On task complete: experience report REQUIRED ← NOT DONE (REFLEX/Guard)
  → Experience feeds into NEXT agent's CLAUDE.md ← NOT DONE (manual today)
```

## Research Tasks for Zeta (PHASE 1 — RECON)

### R1: Task Board Code Audit
**Goal:** Understand current task board internals + what to extend
**Files to study:**
- `src/orchestration/task_board.py` — core TaskBoard class
- `src/mcp/tools/task_board_tools.py` — MCP tool handler
- `src/api/routes/task_board_routes.py` — REST API
- `data/task_board.json` — live data (READ ONLY, DO NOT EDIT)
- `docs/192_task_SQLite/ARCHITECTURE_TASKBOARD_SQLITE.md` — SQLite migration plan
- `docs/192_task_SQLite/ROADMAP_192_TASKBOARD_SQLITE.md` — SQLite roadmap

**Questions:**
1. How does `assigned_to` field work? What values does it accept?
2. How does `allowed_paths` enforcement work (if at all)?
3. What hooks exist on task claim/complete?
4. Where does `agent_type` come from?
5. How does `branch` detection work in `action=complete`?

**⚠️ CAUTION:** Task board is LIVE PRODUCTION infrastructure. 40+ tasks, multiple
agents depend on it. DO NOT modify task_board.py without full test coverage.

### R2: MCC (Multi-Claude Coordination) Audit
**Goal:** Understand existing role definitions in MCC/Mycelium
**Files to study:**
- `data/templates/model_presets.json` — tier/role presets
- `src/orchestration/mycelium_*.py` — pipeline orchestration
- `src/orchestration/mcc_*.py` — multi-claude coordination (if exists)
- Search for: "Architect", "Developer", "QA", "role" in orchestration/

**Questions:**
1. How are roles defined in MCC? (Architect, Developer, QA, Researcher)
2. Can we map MCC roles → CUT agent callsigns (Alpha=Developer, Delta=QA)?
3. How does Mycelium pipeline select agent tier?

### R3: REFLEX / Guard System Audit
**Goal:** Understand feedback guard layer — can it enforce experience reports?
**Files to study:**
- Search for "reflex", "guard", "feedback" in src/
- `src/orchestration/reflex_*.py` (if exists)
- Memory files in `~/.claude/projects/*/memory/`

**Questions:**
1. Does REFLEX currently intercept task completion?
2. Can we add a guard that REQUIRES experience report before closing session?
3. How does program.md / CLAUDE.md update loop work?

### R4: Worktree ↔ Role Binding Design
**Goal:** Design the mapping system
**Inputs:**
- Current worktree CLAUDE.md files (5 files, manually created)
- Task board project_id field
- Agent callsign convention (Alpha/Beta/Gamma/Delta/Epsilon)

**Design questions:**
1. Should role live in CLAUDE.md (file-based) or task board (DB-based)?
2. How to handle: agent claims task → worktree ALREADY has role → task domain matches?
3. How to handle: agent claims task → domain MISMATCH → reject or warn?
4. How to auto-generate CLAUDE.md from experience reports + task board data?
5. If worktree already activated, skip CLAUDE.md reload on subsequent task claims (no hardcodes, test all if/else)

## Architecture Deliverables (PHASE 2 — after recon)

### D1: Agent Registry Schema
```
agent_registry:
  project_id: "CUT"
  roles:
    - callsign: "Alpha"
      domain: "engine"
      worktree: "cut-engine"
      branch: "claude/cut-engine"
      owned_paths: ["client/src/store/useTimeline*", ...]
      predecessor_docs: ["feedback/EXPERIENCE_ALPHA_*.md"]
      roadmap: "ROADMAP_A_ENGINE_DETAIL.md"
    - callsign: "Beta"
      ...
```

### D2: Experience Lifecycle
```
Agent session start
  → Load CLAUDE.md (role + predecessor advice)
  → Claim task (validate domain match)
  → Work...
  → Complete task
  → GUARD: "Write experience report before /exit"
  → Experience report → feeds next CLAUDE.md generation
```

### D3: CLAUDE.md Generator
Script/tool that takes:
- Agent registry (D1)
- Latest experience reports
- Latest feedback consensus doc
- Task board state
→ Generates per-worktree CLAUDE.md automatically

### D4: Task Board Extensions
- `role` field on task (maps to agent callsign)
- `domain` field on task (engine/media/ux/qa)
- Validation: `allowed_paths` enforced on commit (not just documented)
- Guard: experience report check on session end

## Priority

```
P0 — IMMEDIATE (this session):
  Write per-worktree CLAUDE.md for Alpha/Beta/Gamma/Delta ← DONE by Commander
  Prepare dispatches for new agents ← DONE by Commander

P1 — NEXT (Zeta's first task):
  R1-R4 recon with MARKER tags
  Architecture doc for agent init system
  New tasks from recon findings

P2 — BUILD:
  D1: Agent registry schema
  D2: Experience lifecycle guards
  D3: CLAUDE.md generator script

P3 — INTEGRATE:
  D4: Task board extensions
  Mycelium pipeline integration
  Automated experience → CLAUDE.md loop
```

## Constraints

1. **Task board is LIVE** — any changes must be backward-compatible
2. **No hardcodes** — all if/else paths must be tested
3. **Worktree isolation** — agent init must work even if worktree just created
4. **MCC compatibility** — role definitions should align with existing MCC/Mycelium presets
5. **Experience is NOT code** — don't put experience reports in code, keep them in docs/feedback/

---

*"The best agent is one who already knows what their predecessor learned."*
