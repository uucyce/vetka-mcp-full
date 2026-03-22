# Handoff: Zeta → Master Plan Agent
**Date:** 2026-03-22
**From:** Opus (Zeta session)
**To:** Master Plan agent (Sous-Chef orchestrator)
**Status:** Zeta D1-D4 complete, Phase 2 tasks created

---

## What Zeta Built (you should know this)

### 1. Agent Registry (`data/templates/agent_registry.yaml`)
- 5 roles: Alpha (engine), Beta (media), Gamma (ux), Delta (qa), Commander (architect)
- Per-role: `owned_paths`, `blocked_paths`, `predecessor_docs`, `key_docs`
- Shared zones: files where 2+ agents overlap (useCutHotkeys, DockviewLayout, useCutEditorStore)
- **Python loader:** `from src.services.agent_registry import get_agent_registry`

### 2. Task Board Extensions (`src/orchestration/task_board.py`)
- New fields on tasks: `role` (callsign) + `domain` (engine/media/ux/qa/architect)
- **On claim:** warn if agent's domain doesn't match task domain (non-blocking)
- **On complete:** warn if files outside allowed_paths (non-blocking)
- Backward-compatible: tasks without role/domain work exactly as before

### 3. Experience Lifecycle (`src/services/experience_report.py`)
- `ExperienceReportStore`: JSON reports in `data/experience_reports/`
- Protocol Guard rule: `experience_report_after_task` (warns if tasks completed without report)
- Session tracker: tracks `tasks_completed` and `experience_report_submitted`

### 4. CLAUDE.md Generator (`src/tools/generate_claude_md.py`)
- Auto-generates per-worktree CLAUDE.md from registry + experience reports
- Template: `data/templates/claude_md_template.j2`
- Usage: `.venv/bin/python -m src.tools.generate_claude_md --all`

---

## What This Means for Your Master Plan

### Your Sous-Chef Tasks DON'T Need Roles

Your SC-A (Emotions), SC-B (Stale tests), SC-C (Debrief), SC-D (Triada) — all
cross-cutting infrastructure. The `role`/`domain` system is for **CUT domain work**
(engine/media/ux/qa). Infrastructure tasks should have `role=""` and `domain=""`.

This is correct behavior. Don't add roles to infrastructure tasks.

### When Your Tasks WOULD Need Roles

If you create tasks that touch specific CUT domain files:
```
# This needs role=Alpha domain=engine
"Fix timeline playback bug in useTimelineInstanceStore.ts"

# This does NOT need a role (cross-cutting)
"195.2.1: reflex_emotions.py — Emotion core"
```

### Your Existing Tasks on the Board

These are yours and are already correct (no roles needed):
- `tb_1773894237_2` — 195.2.1 Emotions core ← SC-A
- `tb_1773894243_3` — 195.2.2 Emotions tests ← SC-A
- `tb_1773894250_4` — 195.2.3 Emotions wiring ← SC-A
- `tb_1773909812_7` — 196.1 Triada D2→D3 ← SC-D
- `tb_1773909819_8` — 196.2 Triada D1→D3 ← SC-D
- `tb_1773909824_9` — 196.3 Triada D3→D1 ← SC-D
- `tb_1773909834_10` — 196.4 gaps ← SC-D

### Already Done (don't recreate)
- **195.1 SessionActionTracker** — DONE (extended by Zeta D2 with experience tracking)
- **195.2 ProtocolGuard** — DONE (extended by Zeta D2 with experience_report_after_task rule)

These were pending on the board but have been closed.

---

## How Our Work Connects

```
YOUR WORK (Master Plan)              ZETA WORK (Agent Init)
════════════════════════              ═════════════════════════

SC-A: REFLEX Emotions ──────────┐
  195.2.1: emotions core        │    Agent Registry (D1)
  195.2.2: tests                │      ↑ reads owned_paths
  195.2.3: wiring               │      │
                                │    Task Board Extensions (D4)
SC-C: Experience Debrief ───────┼──→   ↑ role/domain validation
  D5: auto-debrief              │      │
  D6: recon relevance           │    Experience Guards (D2)
                                │      ↑ protocol_guard + store
SC-D: Triada Wiring ────────────┤      │
  196.1: D2→D3 (freshness→emo) │    CLAUDE.md Generator (D3)
  196.2: D1→D3 (guard→emo)     │      ↑ reads experience reports
  196.3: D3→D1 (emo→guard)     │      │
  196.4: gaps                   │    ┌──────────────────────┐
                                └──→ │ CLOSED LOOP:         │
                                     │ Agent works → report │
                                     │ → generator reads    │
                                     │ → next agent smarter │
                                     └──────────────────────┘
```

### Key Integration Point: SC-C (Debrief) ↔ Zeta D2

Your D5 (auto-debrief) and my D2 (ExperienceReportStore) solve the SAME problem
from different angles:
- **Flywheel (189 arch doc):** merge gate debrief with structured questions
- **Zeta D2:** ExperienceReportStore + protocol guard enforcement

Recommendation: **D5 should USE ExperienceReportStore** as its storage backend
rather than creating a new system. The store is already wired into:
- Protocol Guard (warns if no report submitted)
- Session tracker (tracks submission state)
- CLAUDE.md Generator (reads reports for predecessor advice)

### Key Integration Point: SC-D (Triada) ↔ Zeta D2

Your 196.2 wires Protocol Guard → Emotions (guard warnings feed Caution).
Zeta added a 7th rule to Protocol Guard (`experience_report_after_task`).
This means 196.2 will automatically pick up the new rule — no extra work needed.

---

## Workflow Patterns (for your Sous-Chef dispatches)

You have 3 waves. Here's which orchestration pattern fits each:

| Wave | Tasks | Pattern | Why |
|------|-------|---------|-----|
| Wave 1 | SC-A + SC-B + SC-C | Parallel worktrees | Independent, no cross-deps |
| Wave 2 | SC-D | Sequential (after SC-A) | Depends on Emotions core |
| Wave 3 | Commander verify | Solo review | Integration check |

This maps to **Commander Fleet** pattern (Level 2 in the orchestration hierarchy).
Not Mycelium pipeline (too heavyweight for code changes that are already designed).

---

## Files You Should Read

1. `data/templates/agent_registry.yaml` — role/ownership map
2. `src/services/agent_registry.py` — Python loader (if you need to validate paths)
3. `src/services/experience_report.py` — ExperienceReportStore API
4. `docs/192_task_SQLite/ARCHITECTURE_ZETA_AGENT_INIT_SYSTEM.md` — full recon findings
5. `docs/189_mcc_taskboard_integration/ARCHITECTURE_AGENT_EXPERIENCE_FLYWHEEL_2026-03-18.md` — debrief design

---

## TL;DR

1. Your infrastructure tasks don't need `role`/`domain` — that's for CUT domain work
2. 195.1 and 195.2 are DONE — don't recreate
3. Your D5 (auto-debrief) should use `ExperienceReportStore` from Zeta D2
4. Your 196.2 (guard→emotions) automatically includes the new experience rule
5. We're building the same closed loop from different sides — let's not duplicate

---

*"Two architects building the same bridge from opposite banks
must agree on where the keystone goes."*
