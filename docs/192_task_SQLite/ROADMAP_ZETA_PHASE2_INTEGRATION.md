# Roadmap: Zeta Phase 2 — Integration & Agent Workflow
**Phase:** 195+ (Agent Infrastructure)
**Date:** 2026-03-22
**Author:** Opus (Zeta)
**Status:** RESEARCH + TASKS
**Depends on:** Zeta D1-D4 (complete), Experience Flywheel arch doc (189)

---

## Problem Statement

Zeta D1-D4 built the infrastructure:
- D1: `agent_registry.yaml` — role/domain/ownership definitions
- D2: Experience Guards — protocol_guard rule + ExperienceReportStore
- D3: CLAUDE.md Generator — auto-generate per-worktree instructions
- D4: Task Board — `role`/`domain` fields + warn-mode validation

**What's still missing:**

### 1. Architect → Task Creation Workflow Gap

When Commander (or any Architect agent) creates tasks, they **should now include
`role` and `domain`** fields. Currently:
- Tasks are created without role assignment → domain validation on claim is skipped
- No guidance in Architect's CLAUDE.md about using registry-aware fields
- Master Plan agents (Sous-Chef pattern) create batches of tasks but don't assign roles

**Solution:** Architect CLAUDE.md must include role assignment instructions.
The generator (D3) should inject registry info into Commander's template.

### 2. MCC Activity → Task Board Visibility Gap

MCC/Mycelium already tracks pipeline activity. Task Board already stores
`assigned_to`, `status`, `branch`. But there's no **real-time dashboard** showing:
- Which agent works on which files right now
- Which worktrees have active sessions
- Cross-domain conflict warnings before merge

**Solution:** `action=active_agents` on task board + conflict detection.

### 3. Experience Flywheel → Zeta Integration Gap

The Experience Flywheel architecture doc (189) designed a 3-layer system:
- Layer 1: Passive signals (CORTEX, errors, timing) — exists
- Layer 2: Merge gate debrief (structured questions) — NOT BUILT
- Layer 3: Resource learnings → session_init — NOT BUILT

Zeta D2 built the **ExperienceReportStore** (JSON storage + protocol guard).
The Flywheel's merge gate debrief is a natural extension.

**Solution:** Connect D2 ExperienceReportStore to Flywheel's debrief system.

### 4. Stale Tasks on Board

94 pending tasks, including:
- ~15 test artifacts (source=api, titles like "Test task", "Lane task")
- 2 now-done tasks that were still pending (195.1, 195.2 — just closed)
- Various stale P4 tasks from earlier phases

**Solution:** Bulk close test artifacts, review P4 stale tasks.

### 5. Gamma CLAUDE.md Incorrect

R4 recon found that `cut-ux` worktree has Alpha's profile instead of Gamma's.
`generate_claude_md --role Gamma` would fix this, but needs human confirmation.

---

## How Architect Should Create Tasks with Roles

### Current Workflow (without roles)
```
Architect reads roadmap → creates tasks:
  vetka_task_board action=add title="..." project_id=CUT
  → No role, no domain → any agent can claim → no domain validation
```

### New Workflow (with roles from registry)
```
Architect reads roadmap + agent_registry.yaml → creates tasks:
  vetka_task_board action=add title="..." project_id=CUT \
    role=Alpha domain=engine \
    allowed_paths=["client/src/store/useTimelineInstanceStore.ts"]
  → Domain validation on claim → ownership check on complete
```

### What Commander's CLAUDE.md Needs to Say

```markdown
## Task Creation with Roles

When creating CUT tasks, always specify role and domain:

| Domain | Role | Typical Files |
|--------|------|---------------|
| engine | Alpha | store/, hotkeys, timeline, tauri |
| media  | Beta  | scopes, color, render, effects, codecs |
| ux     | Gamma | MenuBar, DockviewLayout, panels/, workspace |
| qa     | Delta | e2e/, tests/, RECON docs |

Use: vetka_task_board action=add ... role=Alpha domain=engine

If task spans domains → leave role empty, note in description.
If unsure → leave role empty, agent auto-assigns on claim.
```

### How Master Plan Agents Should Work

The Sous-Chef pattern from the master plan:
```
SC-A (Emotions)  → role="" domain="" (cross-cutting, infra)
SC-B (Stale)     → role="" domain="" (maintenance)
SC-C (Debrief)   → role="" domain="" (cross-cutting)
SC-D (Triada)    → role="" domain="" (cross-cutting)
```

Cross-cutting tasks (infra, REFLEX, pipeline) → **no role needed**.
Domain-specific CUT tasks → role required.

---

## Integration with MCC / VETKA

### Already Connected (via Zeta D1-D4)
```
Task Board ←→ Agent Registry (D1)
  - On claim: validate domain match (warn mode)
  - On complete: validate allowed_paths (warn mode)
  - Fields: role, domain stored on each task

Protocol Guard ←→ Experience Lifecycle (D2)
  - Rule: experience_report_after_task
  - Session tracker: tasks_completed, experience_report_submitted
  - ExperienceReportStore: JSON in data/experience_reports/

CLAUDE.md Generator (D3) ←→ Agent Registry + Experience Reports
  - Reads agent_registry.yaml for role definitions
  - Reads experience reports for predecessor advice
  - Writes per-worktree CLAUDE.md
```

### Needs Connection (Phase 2 tasks)
```
MCC Pipeline ←→ Agent Registry
  - Dragon dispatch should read allowed_paths from registry by domain
  - Not blocking: Dragon already respects task.allowed_paths

Activity Dashboard ←→ Task Board
  - action=active_agents shows who's working where
  - Conflict detection: compare worktree diffs vs owned_paths

Experience Flywheel (189) ←→ Zeta D2
  - Merge gate debrief → ExperienceReportStore
  - Passive signals → auto-populated report fields
  - Resource learnings → session_init context
```

---

## Tasks

### Research (this task)
- **ZETA-INT-RECON:** Audit MCC↔TaskBoard activity display, stale tasks, Flywheel integration points

### Build Tasks (from this research)

| ID | Title | Role | Domain | Priority | Depends |
|----|-------|------|--------|----------|---------|
| new | ZETA-INT-1: Update Commander CLAUDE.md template with role assignment guide | Commander | architect | P2 | D3 |
| new | ZETA-INT-2: Bulk close test artifact tasks (~15 tasks) | — | — | P2 | — |
| new | ZETA-INT-3: Regenerate Gamma CLAUDE.md (fix Alpha→Gamma) | Commander | architect | P2 | D3 |
| new | ZETA-INT-4: Connect ExperienceReportStore to Flywheel merge debrief | — | — | P3 | D2, 189 arch |
| new | ZETA-INT-5: Pre-merge conflict detection via registry owned_paths | — | — | P3 | D1 |

### Existing Tasks (from master plan, need role tags)
- `tb_1773894237_2` — 195.2.1 Emotions core → no role (infra)
- `tb_1773894243_3` — 195.2.2 Emotions tests → no role (infra)
- `tb_1773894250_4` — 195.2.3 Emotions wiring → no role (infra)
- `tb_1773909812_7` — 196.1 Triada D2→D3 → no role (infra)
- `tb_1773909819_8` — 196.2 Triada D1→D3 → no role (infra)
- `tb_1773909824_9` — 196.3 Triada D3→D1 → no role (infra)
- `tb_1773909834_10` — 196.4 gaps → no role (infra)

These are all cross-cutting infrastructure → correct to have no role/domain.

---

## Constraints

1. **Master plan agent is already running** — don't create conflicting tasks
2. **Test artifact cleanup** — confirm with user before bulk close
3. **Gamma CLAUDE.md** — user must confirm before overwriting
4. **Flywheel integration** — requires reading 189 arch doc fully
5. **Backward compat** — tasks without role/domain must continue to work

---

*"The architect who assigns the right agent to the right domain prevents conflicts
that no merge ritual can fix."*
