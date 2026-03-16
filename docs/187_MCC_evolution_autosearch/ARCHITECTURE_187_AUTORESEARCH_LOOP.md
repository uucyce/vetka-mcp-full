# Phase 187: AutoResearch Loop Architecture

**Status:** CONSERVED (low priority, all building blocks exist)
**Author:** Opus (Architect-Commander) + Tony (gap discovery)
**Date:** 2026-03-16
**Origin:** Tony identified missing connector between existing subsystems

---

## TL;DR

VETKA already has all building blocks for Karpathy-style autoresearch:
- **REFLEX** (self-improving tool selection with feedback decay)
- **Heartbeat** (autonomous task dispatch from chat triggers)
- **Eval** (quality gate with numeric threshold)
- **ENGRAM auto-promotion** (experience → reflex, L2→L1)

**Missing link:** eval → auto-spawn next research task → loop.
One connector function in heartbeat closes the entire cycle.

---

## 1. What We Have (Component Map)

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTORESEARCH LOOP                         │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ HEARTBEAT│───→│ PIPELINE │───→│   EVAL   │              │
│  │ dispatch │    │ execute  │    │ score it │              │
│  └──────────┘    └──────────┘    └────┬─────┘              │
│       ↑                               │                     │
│       │         ┌──────────┐          │                     │
│       │         │  REFLEX  │←─────────┘ IP-5 feedback      │
│       │         │  CORTEX  │                                │
│       │         └──────────┘                                │
│       │                                                     │
│       └─── ? ── AUTO-SPAWN ── ? ──────┘                    │
│            ↑                                                │
│         THIS IS THE GAP                                     │
│         (was in program.md, cut with it)                    │
└─────────────────────────────────────────────────────────────┘
```

### 1.1 REFLEX — Self-Improving Tool Selection

**Status:** ACTIVE (Phases 172-178, 187.3)

| Layer | What | File | Status |
|-------|------|------|--------|
| Registry | Tool catalog + metadata | `src/reflex/registry.py` | ACTIVE |
| Scorer | 8-signal weighted scoring (<5ms) | `src/reflex/scorer.py` | ACTIVE (3/8 signals live) |
| Feedback CORTEX | Append-only JSONL + decay | `src/reflex/feedback.py` | ACTIVE (134 entries) |
| Integration | 7 injection points in pipeline | `src/reflex/integration.py` | 4/7 wired |
| Preferences | Pin/ban/custom weights | `src/reflex/preferences.py` | ACTIVE |
| Decay | Phase-specific half-lives | `src/reflex/decay.py` | ACTIVE |
| Filter | Model-tier tool limiting | `src/reflex/filter.py` | Feature-flagged |

**Feedback formula:**
```
score = success_rate × 0.40 + usefulness × 0.35 + verifier_pass × 0.25
```

**Signal weights (Phase 187.3 rebalance):**
```
Semantic=0.22  Feedback=0.18  Phase=0.18  STM=0.15
CAM=0.12       AURA=0.07      HOPE=0.05   MGC=0.03
```

Stubbed signals: CAM, AURA, STM, HOPE, MGC (always default values).

**Docs:**
- [`docs/172_vetka_tools/REFLEX_ARCHITECTURE_BLUEPRINT_2026-03-10.md`](../172_vetka_tools/REFLEX_ARCHITECTURE_BLUEPRINT_2026-03-10.md)
- [`docs/172_vetka_tools/REFLEX_TOOL_MEMORY_ARCHITECTURE_2026-03-13.md`](../172_vetka_tools/REFLEX_TOOL_MEMORY_ARCHITECTURE_2026-03-13.md)
- [`docs/172_vetka_tools/PHASE_173_REFLEX_ACTIVE_ROADMAP_2026-03-11.md`](../172_vetka_tools/PHASE_173_REFLEX_ACTIVE_ROADMAP_2026-03-11.md)
- [`docs/172_vetka_tools/REFLEX_ROADMAP_CHECKLIST_2026-03-10.md`](../172_vetka_tools/REFLEX_ROADMAP_CHECKLIST_2026-03-10.md)

### 1.2 Heartbeat — Autonomous Dispatch

**Status:** ACTIVE (Phases 117, 130, 140, 183)

- Monitors chats → parses @triggers → dispatches via TaskBoard
- Session ID correlation (Phase 183.1)
- Localguys stall detection + nudge/resume
- Multi-chat cursors, deduplication, event-driven wakeup
- **Does NOT feed outcomes back to REFLEX**

**Docs:**
- [`docs/unpluged_search/PH117_Dragon_Heartbeat_Engine.md`](../unpluged_search/PH117_Dragon_Heartbeat_Engine.md)
- [`docs/unpluged_search/RESEARCH_005_Heartbeat_Monitoring_Phase130.md`](../unpluged_search/RESEARCH_005_Heartbeat_Monitoring_Phase130.md)
- [`docs/182_ph_MCC_git/HANDOFF_183.md`](../182_ph_MCC_git/HANDOFF_183.md)

### 1.3 Eval — Quality Gate

**Status:** ACTIVE (Phases 101, 183.5)

- `eval_delta` — numeric quality threshold for pipeline pass/fail
- Verifier role closes REFLEX feedback loop (IP-5)
- EvalAgent (Haiku) scores responses post-execution
- Reaction tracking (thumbs up/down) → per-model quality decay

**Docs:**
- [`docs/unpluged_search/PH101_EvalAgent_Reactions_Loop.md`](../unpluged_search/PH101_EvalAgent_Reactions_Loop.md)
- [`docs/182_ph_MCC_git/ARCHITECTURE_182_TASKBOARD_AS_GIT.md`](../182_ph_MCC_git/ARCHITECTURE_182_TASKBOARD_AS_GIT.md)

### 1.4 Memory Auto-Promotion (L2→L1)

**Status:** IMPLEMENTED (Phase 186)

```
CORTEX records outcome
  → Resource Learnings extracts pattern → Qdrant L2
    → Matched ≥3 times → ENGRAM promotes to L1 (O(1))
      → Next query: instant deterministic answer
```

**Docs:**
- [`docs/186_memory/VETKA_COGNITIVE_STACK_ARCHITECTURE.md`](../186_memory/VETKA_COGNITIVE_STACK_ARCHITECTURE.md)
- [`docs/186_memory/VETKA_DYNAMIC_MEMORY_BLUEPRINT.md`](../186_memory/VETKA_DYNAMIC_MEMORY_BLUEPRINT.md)

### 1.5 TaskBoard as VCS

**Status:** ACTIVE (Phases 182-184)

- ActionRegistry logs every agent action with run_id/session_id
- Workflow: agent pickup → execute → submit → verify → merge → auto-close
- Qdrant semantic search of past actions (Phase 183.2, stubbed)

**Docs:**
- [`docs/182_ph_MCC_git/ARCHITECTURE_182_TASKBOARD_AS_GIT.md`](../182_ph_MCC_git/ARCHITECTURE_182_TASKBOARD_AS_GIT.md)
- [`docs/182_ph_MCC_git/ROADMAP_182_184.md`](../182_ph_MCC_git/ROADMAP_182_184.md)

---

## 2. The Gap: Auto-Spawn Loop

### 2.1 What Was Cut

`program.md` was intentionally removed (Phase 186) — marked as "дубль digest" in cognitive stack architecture. But it carried the auto-research scheduling logic with it. The plan was:

```
program.md tracked:
  - Current research goals
  - Eval results from past runs
  - Next auto-generated tasks based on gaps

Without it, the cycle breaks at: Eval → ??? → Next Task
```

### 2.2 What Needs to Be Built

**One function** in heartbeat or pipeline completion callback:

```python
async def autoresearch_loop(pipeline_result, eval_score, task_meta):
    """
    Called after pipeline completes + eval scores it.
    If eval_score < threshold, auto-generates follow-up research task.
    """
    if eval_score >= AUTORESEARCH_THRESHOLD:  # e.g. 0.7
        return  # Good enough, no follow-up needed

    # Generate follow-up task
    follow_up = {
        "title": f"AutoResearch: deepen {task_meta['topic']}",
        "description": f"Previous attempt scored {eval_score:.2f}. "
                       f"Gaps identified: {pipeline_result.get('gaps', [])}",
        "phase_type": "research",
        "priority": 3,  # Not urgent, auto-generated
        "tags": ["autoresearch", f"parent:{task_meta['task_id']}"],
        "parent_task_id": task_meta["task_id"],
    }
    await task_board.add_task(**follow_up)
```

### 2.3 Integration Points

| Where | What | Effort |
|-------|------|--------|
| `mycelium_heartbeat.py:on_pipeline_complete()` | Add autoresearch check | Small |
| `agent_pipeline.py` (after IP-5 verifier) | Emit eval_score to callback | Small |
| `task_board.py` | Support `parent_task_id` linking | Already exists |
| New: `src/orchestration/autoresearch.py` | Loop policy (threshold, max depth, cooldown) | Medium |

### 2.4 Safety Guards (Must Have)

- **Max depth:** No more than N auto-spawned follow-ups per original task (prevent infinite loops)
- **Cooldown:** Minimum interval between auto-spawns (prevent spam)
- **Budget cap:** Total token/cost limit per autoresearch chain
- **Human review gate:** After N auto-iterations, require human approval
- **Kill switch:** `AUTORESEARCH_ENABLED=false` env flag

---

## 3. Comparison with Existing Systems

| System | Memory | Eval | Auto-Loop | Self-Improving |
|--------|--------|------|-----------|----------------|
| **Anthropic Memory.md** | Manual file edits | No | No | No |
| **Karpathy AutoSearch** | Concept only | Concept | Concept | Concept |
| **Cursor** | .cursorrules | No | No | No |
| **VETKA (current)** | 3-layer REFLEX + ENGRAM + Qdrant | eval_delta + Verifier | **No (gap)** | Tool selection only |
| **VETKA (with loop)** | Same | Same | **Yes** | Tool selection + task generation |

---

## 4. Karpathy Alignment

| Karpathy Concept | VETKA Equivalent | Status |
|------------------|-------------------|--------|
| Loss signal | REFLEX feedback score | ACTIVE |
| Data flywheel | CORTEX (bad↓ good↑) | ACTIVE |
| Attention allocation | ENGRAM L1 auto-promotion | IMPLEMENTED |
| Natural forgetting | Decay engine (phase-specific half-lives) | ACTIVE |
| Auto-eval | eval_delta + Verifier IP-5 | ACTIVE |
| Auto-search loop | heartbeat → eval → auto-spawn | **GAP** |

---

## 5. Dependent Signals (Stubbed, Not Blocking)

These REFLEX signals are stubbed but would enhance autoresearch quality:

| Signal | What It Does | Why It Matters for AutoResearch |
|--------|-------------|--------------------------------|
| CAM (surprise) | Novelty detection | Focus research on unexpected gaps |
| AURA (user prefs) | User tool preferences | Align auto-tasks with user style |
| STM (short-term) | Recent context | Avoid repeating recent research |
| HOPE (zoom/LOD) | Abstraction level | Research breadth vs depth |
| MGC (cache heat) | Hot files | Focus on actively changing areas |

These are independent improvements — can be wired separately from the main loop.

---

## 6. File Index

### Core Implementation Files
- `src/reflex/` — Registry, Scorer, Feedback, Integration, Filter, Decay, Preferences
- `src/orchestration/mycelium_heartbeat.py` — Heartbeat engine
- `src/orchestration/agent_pipeline.py` — Pipeline with REFLEX IPs
- `src/orchestration/action_registry.py` — Action logging with session/run IDs
- `src/orchestration/feedback_loop_v2.py` — Feedback loop with reactions

### Data Files
- `data/reflex/tool_catalog.json` — Tool registry
- `data/reflex/feedback_log.jsonl` — CORTEX feedback log
- `data/reflex/user_preferences.json` — User pin/ban/weights
- `data/heartbeat_state.json` — Heartbeat state persistence
- `data/heartbeat_cursors.json` — Multi-chat cursors

### Test Coverage
- `tests/test_reflex_*.py` — 11+ test files
- `tests/test_heartbeat_daemon.py` — 13 tests
- `tests/test_phase183_session_id.py` — 7 tests

---

*Conserved by Opus. Thanks Tony for spotting the gap.*
*"Experience is the son of difficult mistakes" — Pushkin*
