# Agent Experience Flywheel — автоматический сбор и переработка агентского опыта

**Date:** 2026-03-18
**Author:** Opus (Claude Code)
**Phase:** 189+ (cross-phase capability)
**Status:** ARCHITECTURE — ready for task decomposition
**Prerequisite docs:**
- `docs/187_MCC_evolution_autosearch/ARCHITECTURE_187_AUTORESEARCH_LOOP.md` — GAP analysis
- `docs/186_memory/VETKA_COGNITIVE_STACK_ARCHITECTURE.md` — cognitive stack (AURA, CORTEX, REFLEX, etc.)
- `docs/186_memory/VETKA_DYNAMIC_MEMORY_BLUEPRINT.md` — why program.md was cut

---

## 1. Problem Statement

Агенты накапливают ценный опыт за время работы:
- Какие инструменты сломаны (vetka_read_file → 422)
- Какие workaround'ы пришлось использовать (Read вместо vetka_read_file)
- Что работает хорошо (session_init, TaskBoard MCP)
- Идеи для улучшения системы

Этот опыт **умирает с контекстным окном**. Единственный способ его захватить сегодня — человек вручную спрашивает агента "что бы ты улучшил?" и копирует ответ. Это не масштабируется.

### Почему program.md не решение

Phase 186 audit показал: program.md = 5 дублей существующих систем. Отсекли правильно.
Но вместе с ним потерялся **auto-spawn loop** (Phase 187 GAP).

### Почему "напиши опыт при закрытии таска" не работает

- Опционально = никогда (агенты игнорируют)
- Свободная форма = пустота или мусор
- Нет feedback loop (написал → никто не прочитал → зачем писать)
- Тратит токены на каждый таск (60+ тасков на фазу)

---

## 2. Design Principles

1. **Автоматический сбор** — данные собираются без участия агента (REFLEX, errors, timing уже логируются)
2. **Structured debrief на merge** — не каждый таск, а при merge в main (= verified, meaningful work)
3. **Zero new storage** — всё идёт в существующие системы (CORTEX, Resource Learnings, AURA, TaskBoard)
4. **Budget-aware** — debrief = 3 structured вопроса, не свободная форма, ≤200 токенов ответа
5. **Feedback loop замкнут** — собранные данные влияют на session_init следующей сессии

---

## 3. Architecture: Three Layers

```
┌────────────────────────────────────────────────────────────────────┐
│                   AGENT EXPERIENCE FLYWHEEL                        │
│                                                                    │
│  LAYER 1: PASSIVE SIGNALS (automatic, zero tokens)                 │
│  ══════════════════════════════════════════════════                 │
│  Already collected, just need aggregation:                         │
│                                                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ CORTEX   │  │ ERRORS   │  │ TIMING   │  │ FRICTION │          │
│  │ feedback │  │ tool 422 │  │ latency  │  │ fallback │          │
│  │ log.jsonl│  │ log      │  │ per-phase│  │ patterns │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│       │              │              │              │                │
│       └──────────────┴──────┬───────┴──────────────┘                │
│                             │                                      │
│  LAYER 2: MERGE GATE DEBRIEF (on merge to main, structured)       │
│  ═══════════════════════════════════════════════════════           │
│                             │                                      │
│  ┌──────────────────────────▼──────────────────────────────┐      │
│  │  merge_debrief_prompt (injected into merge gate hook):   │      │
│  │                                                          │      │
│  │  Auto-collected signals for this branch:                 │      │
│  │  • Tools failed: vetka_read_file (3x, HTTP 422)          │      │
│  │  • Friction: agent used Read 12x as fallback             │      │
│  │  • Slow phases: coder avg 145s (expected 90s)            │      │
│  │  • CORTEX: vetka_search_files success=0.92               │      │
│  │                                                          │      │
│  │  Agent answers 3 questions (structured, not free-form):  │      │
│  │  Q1: "Top broken tool?" → "vetka_read_file"              │      │
│  │  Q2: "Best discovery?"  → "ELISION level 3 on STM"      │      │
│  │  Q3: "One improvement?" → "auto-inject arch_docs"        │      │
│  └──────────────────────────┬──────────────────────────────┘      │
│                             │                                      │
│  LAYER 3: AUTO-PROCESS (zero tokens, deterministic)                │
│  ══════════════════════════════════════════════════                 │
│                             │                                      │
│  ┌──────────────────────────▼──────────────────────────────┐      │
│  │  experience_processor():                                 │      │
│  │                                                          │      │
│  │  Passive signals →                                       │      │
│  │    • Tool errors → TaskBoard: auto-create fix tasks      │      │
│  │    • Friction → REFLEX: update tool scores               │      │
│  │    • Timing → CORTEX: adjust complexity estimates        │      │
│  │                                                          │      │
│  │  Debrief answers →                                       │      │
│  │    • Broken tool → TaskBoard: "fix: {tool} {error}"      │      │
│  │    • Discovery → Resource Learnings: store in Qdrant     │      │
│  │    • Improvement → TaskBoard: backlog task, priority=4   │      │
│  │                                                          │      │
│  │  AURA enrichment →                                       │      │
│  │    • Agent communication patterns → AURA store           │      │
│  │    • CAM surprise spikes → highlight in next session     │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                    │
│  OUTPUT → session_init returns:                                    │
│    experience_digest: {                                             │
│      feedback_rules: 4,                                            │
│      recent_learnings: ["ELISION L3 saves 60%", ...],              │
│      known_broken: ["vetka_read_file: 422"],                       │
│      improvement_backlog: 3                                        │
│    }                                                               │
└────────────────────────────────────────────────────────────────────┘
```

---

## 4. Layer 1: Passive Signal Collection (already exists, needs aggregation)

### 4.1 CORTEX feedback — ALREADY COLLECTED

**Source:** `data/reflex/feedback_log.jsonl`
**Format:** `{tool_id, phase_type, agent_role, success, useful, verifier_passed, execution_time_ms, timestamp}`

**What's missing:** Aggregation per-session/per-branch. Currently append-only with no session grouping.

**Fix:** Add `session_id` and `branch` fields to feedback records.

```python
# In reflex_integration.py, IP-3 (post-FC)
record = {
    "tool_id": tool_id,
    "success": success,
    "useful": useful,
    "execution_time_ms": duration,
    "session_id": current_session_id,    # NEW
    "branch": git_branch(),              # NEW
    "phase_type": phase_type,
    "timestamp": time.time()
}
```

### 4.2 Tool Errors — PARTIALLY COLLECTED

MCP tool errors are logged to Python logger but **not structured**.

**Fix:** Add error collector in MCP handler:

```python
# In mcp server error handler
error_log = {
    "tool_id": tool_name,
    "error_type": "HTTP_422",  # or timeout, validation, etc.
    "error_message": str(e)[:200],
    "session_id": session_id,
    "timestamp": time.time()
}
# Append to data/reflex/error_log.jsonl
```

### 4.3 Friction Detection — NEW (but cheap)

**Definition:** Agent called tool A, got error, then called tool B for same purpose.
**Example:** `vetka_read_file` → 422 → `Read` (Claude Code native) = friction signal.

**Implementation:** In REFLEX integration IP-3, detect pattern:
```python
if not success and last_successful_tool_for_same_intent:
    friction_record = {
        "broken_tool": tool_id,
        "fallback_tool": last_successful_tool,
        "intent": intent_tag,
        "session_id": session_id
    }
    # Append to data/reflex/friction_log.jsonl
```

**Cost:** Zero LLM tokens. Pure pattern matching on existing CORTEX data.

### 4.4 Timing Anomalies — ALREADY COLLECTED

`execution_time_ms` is in CORTEX feedback. Need aggregation:

```python
def detect_timing_anomalies(session_id: str) -> list:
    """Find phases that took >2x expected time."""
    session_records = [r for r in feedback_log if r["session_id"] == session_id]
    # Compare against historical median per (tool_id, phase_type)
    anomalies = []
    for r in session_records:
        median = get_historical_median(r["tool_id"], r["phase_type"])
        if r["execution_time_ms"] > median * 2:
            anomalies.append(r)
    return anomalies
```

---

## 5. Layer 2: Merge Gate Debrief

### 5.1 When It Triggers

**Trigger:** `task_board action=complete` on main branch (NOT worktree).

Why main merge specifically:
- Work is verified (passed tests, verifier)
- Agent has full context of what they did
- Prevents spam (worktree tasks don't trigger)
- Natural checkpoint — agent is already "closing" work

### 5.2 NOT Every Task — Smart Trigger

Debrief triggers when ANY of these conditions met:

```python
def should_trigger_debrief(task: dict, session_stats: dict) -> bool:
    """Decide if this task completion warrants a debrief."""

    # 1. Last task in phase (0 pending tasks remain for this phase_type)
    remaining = count_pending_tasks(phase_type=task["phase_type"])
    if remaining == 0:
        return True

    # 2. Session has accumulated enough signal (>= 5 tool errors)
    if session_stats.get("error_count", 0) >= 5:
        return True

    # 3. Session duration > 2 hours (long session = rich experience)
    if session_stats.get("duration_hours", 0) > 2:
        return True

    # 4. High friction score (>= 3 fallback patterns detected)
    if session_stats.get("friction_count", 0) >= 3:
        return True

    # 5. Explicit: agent or user calls phase_close
    # (handled separately)

    return False
```

### 5.3 Debrief Format — Structured, Not Free-Form

The debrief is **injected into the task completion response**, not a separate call.

When `should_trigger_debrief() == True`, the MCP response includes:

```json
{
    "success": true,
    "task_id": "tb_xxx",
    "status": "done",
    "debrief_requested": true,
    "debrief_context": {
        "auto_collected": {
            "tools_failed": [
                {"tool": "vetka_read_file", "count": 3, "error": "HTTP 422 file_path vs path"}
            ],
            "friction_patterns": [
                {"broken": "vetka_read_file", "fallback": "Read", "count": 12}
            ],
            "slow_phases": [
                {"phase": "coder", "avg_ms": 145000, "expected_ms": 90000}
            ],
            "top_tools": [
                {"tool": "vetka_search_files", "success_rate": 0.92, "calls": 28}
            ]
        },
        "questions": [
            "Q1: Which tool caused the most friction this session? (tool name + error)",
            "Q2: What discovery or workaround was most valuable? (1 sentence)",
            "Q3: One concrete improvement to the system? (1 sentence)"
        ]
    }
}
```

Agent sees auto-collected data + 3 questions. Answers in structured format:

```json
{
    "debrief_response": {
        "broken_tool": "vetka_read_file — param name mismatch file_path vs path",
        "best_discovery": "ELISION L3 on STM buffer saves 60% tokens for Bronze models",
        "improvement": "Auto-inject architecture_docs content into dispatch task_text"
    }
}
```

### 5.4 Token Budget

- Auto-collected context: ~150 tokens (pre-formatted, no LLM needed)
- 3 questions: ~50 tokens
- 3 answers: ~100 tokens
- **Total: ~300 tokens per debrief**
- Frequency: ~1-3 per phase (not every task)

Compare: free-form debrief would cost 500-1000 tokens and produce unstructured text.

### 5.5 Blocking vs Non-Blocking

**Recommendation: Soft-blocking.**

```python
if debrief_requested and not debrief_response:
    return {
        "success": True,
        "task_id": task_id,
        "status": "done",
        "warning": "Debrief requested but not provided. "
                   "Next task_board action will re-prompt. "
                   "Call: vetka_task_board action=debrief session_id=X answers={...}"
    }
```

The task closes regardless, but the system will re-prompt on next interaction.
For `phase_close` (explicit) — hard block: phase doesn't close without debrief.

---

## 6. Layer 3: Auto-Processing (zero tokens, deterministic)

### 6.1 Tool Errors → Fix Tasks

```python
async def process_tool_errors(errors: list) -> list:
    """Convert tool errors into TaskBoard fix tasks."""
    tasks_created = []
    for error_group in group_by_tool(errors):
        if error_group["count"] >= 2:  # At least 2 occurrences
            task = {
                "title": f"fix: {error_group['tool']} — {error_group['error_type']}",
                "description": (
                    f"Tool `{error_group['tool']}` failed {error_group['count']}x "
                    f"with error: {error_group['error_message']}\n\n"
                    f"Detected by: Agent Experience Flywheel (auto-generated)\n"
                    f"Source session: {error_group['session_id']}"
                ),
                "priority": 3,  # Not urgent, but should be fixed
                "phase_type": "fix",
                "tags": ["auto-generated", "flywheel", "tool-fix"],
                "source": "experience_flywheel"
            }
            tasks_created.append(task)
    return tasks_created
```

### 6.2 Friction → REFLEX Updates

```python
async def process_friction(friction_patterns: list):
    """Update REFLEX scores based on friction patterns."""
    for pattern in friction_patterns:
        # Downgrade broken tool
        cortex.record_outcome(
            tool_id=pattern["broken_tool"],
            success=False,
            useful=False,
            source="friction_detector"
        )
        # Upgrade fallback tool (it worked when primary didn't)
        cortex.record_outcome(
            tool_id=pattern["fallback_tool"],
            success=True,
            useful=True,
            source="friction_detector"
        )
```

### 6.3 Debrief → Learnings + Tasks

```python
async def process_debrief(debrief: dict, session_id: str):
    """Route debrief answers to appropriate systems."""

    # Q1: Broken tool → auto-create fix task (if not already exists)
    broken = debrief.get("broken_tool", "")
    if broken:
        existing = find_task_by_title(f"fix: {broken.split('—')[0].strip()}")
        if not existing:
            await task_board.add_task(
                title=f"fix: {broken}",
                priority=3,
                phase_type="fix",
                tags=["agent-reported", "flywheel"]
            )

    # Q2: Discovery → Resource Learnings (Qdrant)
    discovery = debrief.get("best_discovery", "")
    if discovery:
        await resource_learnings.store({
            "category": "optimization",
            "content": discovery,
            "session_id": session_id,
            "source": "agent_debrief"
        })

    # Q3: Improvement → backlog task
    improvement = debrief.get("improvement", "")
    if improvement:
        await task_board.add_task(
            title=f"improve: {improvement[:80]}",
            description=f"Agent suggestion from session {session_id}:\n{improvement}",
            priority=4,  # Backlog
            phase_type="build",
            tags=["agent-suggested", "flywheel"]
        )
```

### 6.4 AURA Enrichment (from passive signals)

```python
async def enrich_aura(session_stats: dict, agent_type: str):
    """Update AURA user preferences from session patterns."""

    # Tool usage patterns → AURA.tool_usage_patterns
    tool_counts = session_stats.get("tool_usage_counts", {})
    await aura_store.update_tool_patterns(agent_type, tool_counts)

    # CAM surprise spikes → store for next session
    surprises = session_stats.get("cam_surprises", [])
    high_surprises = [s for s in surprises if s["score"] > 0.7]
    if high_surprises:
        await aura_store.store_surprise_highlights(agent_type, high_surprises)
```

---

## 7. session_init Integration: Experience Digest

### 7.1 What Gets Added to session_init Response

```python
# In session_tools.py, after existing context assembly
experience_digest = await build_experience_digest(agent_type)

# Returns:
{
    "experience_digest": {
        "feedback_rules_active": 4,        # from Claude Code memory
        "recent_learnings": [              # from Resource Learnings (Qdrant)
            "ELISION L3 saves 60% on Bronze STM",
            "architecture_docs not injected in dispatch"
        ],
        "known_broken": [                  # from error_log.jsonl
            "vetka_read_file: HTTP 422 (file_path vs path)"
        ],
        "top_friction": [                  # from friction_log.jsonl
            "vetka_read_file → Read fallback (12x last session)"
        ],
        "improvement_backlog": 3,          # count of agent-suggested tasks
        "last_debrief": "2026-03-18T07:13:00Z"
    }
}
```

### 7.2 Token Budget for Experience Digest

Target: **≤ synopsis size** (~100-150 tokens in session_init response).

```
experience_digest:
  rules: 4 active
  learnings: ["ELISION L3 60% savings", "arch_docs not injected"]
  broken: ["vetka_read_file: 422"]
  backlog: 3 improvements pending
```

Compressed via ELISION L1: ~80 tokens.

---

## 8. Phase Close Ceremony

### 8.1 How to Detect "Last Task of Phase"

```python
def is_phase_complete(phase_type: str, project_id: str = None) -> bool:
    """Check if all tasks for current phase are done."""
    pending = task_board.get_queue(status="pending")

    # Filter by phase if project_id provided
    if project_id:
        pending = [t for t in pending if t.get("project_id") == project_id]

    # Filter by phase_type pattern (e.g., "189" prefix in title or tags)
    phase_tasks = [t for t in pending if is_same_phase(t, phase_type)]

    return len(phase_tasks) == 0
```

### 8.2 Explicit phase_close Action

```python
# New TaskBoard action
elif action == "phase_close":
    phase_id = arguments.get("phase_id")  # e.g., "189"

    # 1. Verify all tasks done
    remaining = count_remaining(phase_id)
    if remaining > 0:
        return {"error": f"{remaining} tasks still pending for phase {phase_id}"}

    # 2. Aggregate passive signals for entire phase
    phase_stats = aggregate_phase_signals(phase_id)

    # 3. REQUIRE debrief (hard block)
    return {
        "success": True,
        "phase_id": phase_id,
        "debrief_required": True,
        "phase_stats": phase_stats,
        "questions": [
            "Q1: Top 3 broken tools this phase?",
            "Q2: What architectural pattern worked best?",
            "Q3: What should change before next phase?"
        ],
        "instruction": "Call: vetka_task_board action=phase_debrief phase_id=X answers={...}"
    }
```

### 8.3 Phase Debrief Processing

```python
elif action == "phase_debrief":
    phase_id = arguments.get("phase_id")
    answers = arguments.get("answers")  # structured dict

    # 1. Store as Resource Learning (Qdrant)
    await resource_learnings.store({
        "category": "phase_retrospective",
        "phase_id": phase_id,
        "content": json.dumps(answers),
        "tools_failed": phase_stats["errors"],
        "tools_succeeded": phase_stats["top_tools"]
    })

    # 2. Auto-create fix tasks from broken tools
    fix_tasks = await process_tool_errors(phase_stats["errors"])

    # 3. Auto-create improvement tasks from suggestions
    improvement_tasks = await process_debrief(answers, session_id)

    # 4. Update REFLEX decay (successful tools decay slower)
    await update_decay_weights(phase_stats)

    # 5. Bump phase in digest
    await digest.advance_phase(phase_id)

    return {
        "success": True,
        "phase_closed": phase_id,
        "tasks_auto_created": len(fix_tasks) + len(improvement_tasks),
        "learnings_stored": True,
        "reflex_updated": True
    }
```

---

## 9. Data Flow Summary

```
DURING SESSION (passive, 0 tokens):
  tool call → CORTEX feedback + error_log + timing
  fallback  → friction_log
  CAM       → surprise spikes

ON MERGE TO MAIN (soft-block, ~300 tokens):
  auto_collected signals → formatted context
  3 structured questions → 3 short answers
  answers → Resource Learnings + fix tasks + backlog tasks

ON PHASE CLOSE (hard-block, ~500 tokens):
  aggregate all session signals for phase
  3 phase-level questions → 3 answers
  answers → Qdrant + auto-tasks + REFLEX decay update + digest advance

NEXT SESSION (session_init, ~100 tokens):
  experience_digest: rules + learnings + broken + friction + backlog count
```

---

## 10. What We DON'T Build

| Rejected Idea | Why |
|---------------|-----|
| program.md | 5/8 components are duplicates (Phase 186 audit) |
| Free-form debrief | Agents ignore it, unstructured output |
| Debrief on every task | Too expensive, too noisy |
| Separate experience DB | Zero new storage — use CORTEX, Resource Learnings, TaskBoard |
| LLM-powered analysis | Passive signals + deterministic processing = zero tokens for collection |
| Agent skill tracking | Premature — first get the flywheel spinning |

---

## 11. Implementation Plan

| Step | What | Where | Complexity | Depends On |
|------|------|-------|-----------|-----------|
| F1 | Add session_id + branch to CORTEX feedback records | `reflex_integration.py` | Easy | — |
| F2 | Add error_log.jsonl collector in MCP error handler | `mcp server` | Easy | — |
| F3 | Add friction detection (broken→fallback pattern) | `reflex_integration.py` | Medium | F1 |
| F4 | Aggregate signals per session: `build_session_stats()` | `reflex_feedback.py` (new func) | Medium | F1, F2 |
| F5 | `should_trigger_debrief()` logic | `task_board.py` | Easy | F4 |
| F6 | Inject debrief prompt in task completion response | `task_board_tools.py` | Medium | F5 |
| F7 | `action=debrief` handler: process answers → tasks + learnings | `task_board_tools.py` | Medium | F6 |
| F8 | `action=phase_close` + `action=phase_debrief` handlers | `task_board_tools.py` | Medium | F7 |
| F9 | `experience_digest` in session_init response | `session_tools.py` | Easy | F4 |
| F10 | AURA enrichment from session patterns | `aura_store.py` | Easy | F4 |

### Critical Path

```
F1 + F2 (parallel, easy) → F3 + F4 (parallel, medium) → F5 → F6 → F7 → F9
                                                                  ↓
                                                                 F8 (can lag)
                                                                  ↓
                                                                 F10 (independent)
```

### Token Budget (total system cost)

| Event | Frequency | Tokens | Monthly cost (est.) |
|-------|-----------|--------|-------------------|
| Passive collection | Every tool call | 0 | $0 |
| Merge debrief | ~3-5 per phase | ~300 | Negligible |
| Phase close debrief | ~1 per phase | ~500 | Negligible |
| Experience digest in session_init | Every session | ~100 | Negligible |

**Total: <1000 tokens per phase for experience collection.** Compare: one free-form "what would you improve?" costs ~500 tokens for one answer.

---

## 12. Files to Modify

| File | Changes |
|------|---------|
| `src/services/reflex_integration.py` | F1: session_id + branch in feedback; F3: friction detection |
| `src/services/reflex_feedback.py` | F4: aggregate per-session stats |
| `src/mcp/tools/task_board_tools.py` | F5-F8: debrief trigger + handlers |
| `src/mcp/tools/session_tools.py` | F9: experience_digest in response |
| `src/memory/aura_store.py` | F10: session pattern enrichment |
| `data/reflex/error_log.jsonl` | NEW file (append-only) |
| `data/reflex/friction_log.jsonl` | NEW file (append-only) |

### New MCP Actions

| Action | Trigger | Blocking? |
|--------|---------|-----------|
| `debrief` | Auto after merge to main (if conditions met) | Soft |
| `phase_close` | Explicit call by agent/user | Checks pending tasks |
| `phase_debrief` | After phase_close | Hard block |

---

## 13. Success Metrics

After 5 phases with flywheel active:

| Metric | Baseline (now) | Target |
|--------|----------------|--------|
| Broken tools detected | 0 (manual only) | Auto-detect in <1 session |
| Fix tasks auto-created | 0 | 2-5 per phase |
| Agent friction (fallback usage) | Unknown | Tracked, trending down |
| Cross-session learning | None (context dies) | 3-5 learnings per session_init |
| Time to fix broken tools | Days (until human notices) | Next phase (auto-task created) |
