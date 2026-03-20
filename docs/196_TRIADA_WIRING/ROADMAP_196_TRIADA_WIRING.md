# Roadmap: Phase 196 — Triada Wiring (D1 + D2 + D3)

**Commander:** Opus
**Date:** 2026-03-19
**Agents:** 2 parallel + Opus verify
**Est. total:** 1-1.5 hours
**Prerequisite phases:** 195.0 (Protocol Guard), 195.1 (CORTEX Freshness), 195.2 (REFLEX Emotions)

---

## Context

Phase 195 delivered three independent modules:

| Module | Code | What it does |
|--------|------|-------------|
| **D1: Protocol Guard** | `src/services/protocol_guard.py` + `SessionActionTracker` | Tracks agent actions (reads/edits/task claims), enforces Work Entry Protocol with 6 rules, surfaces `protocol_status` in session_init |
| **D2: CORTEX Freshness** | `src/services/tool_source_watch.py` | Maps 53 tools → 23 source files, detects updates via git, epoch-based failure discount (0.1^epochs), +0.3 CAM curiosity boost for 48h |
| **D3: REFLEX Emotions** | `src/services/reflex_emotions.py` | Post-scoring modulator: curiosity/trust/caution → modifier [0.3, 1.5] applied to base REFLEX score, ENGRAM persistence, mood label in session_init |

**Problem:** Each module works in isolation. The interfaces between them are designed (see Architecture docs) but NOT wired:

```
CURRENT (isolated):
  D1: Protocol Guard ──── protocol_status in session_init
  D2: Tool Freshness ──── freshness_report in session_init, CAM boost in scorer
  D3: REFLEX Emotions ─── emotions in session_init, modifier in scorer

  D3.EmotionContext.tool_freshness = {}     ← EMPTY, D2 data not flowing
  D3.EmotionContext.guard_warnings = set()  ← EMPTY, D1 data not flowing
  D1 ignores trust scores                   ← D3 data not flowing

AFTER (wired):
  D2 (freshness) ──→ D3 (curiosity)     : fresh tool → curiosity spike
  D1 (violations) ──→ D3 (caution)      : protocol violation → caution spike
  D3 (trust) ──→ D1 (severity)          : high trust → softer warnings
```

---

## What Exists (read these first!)

### Architecture docs (all three have "Shared Interfaces" sections):
1. `docs/195_REFLEX_EMOTIONS/ARCHITECTURE_195_REFLEX_EMOTIONS.md` — **primary**, has all three interface contracts
2. Protocol Guard architecture — inline in its roadmap/task descriptions
3. Tool Freshness architecture — inline in its task descriptions

### Key source files:
| File | What to read | Why |
|------|-------------|-----|
| `src/services/reflex_emotions.py` | `EmotionContext` dataclass, `load_emotion_context()`, `compute_curiosity()`, `compute_caution()` | These are the connection points |
| `src/services/tool_source_watch.py` | `scan_all()`, `get_freshness_events()` | D2 data source for curiosity |
| `src/services/protocol_guard.py` | `SessionActionTracker`, `ProtocolGuard`, rule check methods | D1 data source for caution |
| `src/services/reflex_integration.py` | `reflex_session()` (IP-6) | Where D2→D3 and D1→D3 wiring happens |
| `src/services/reflex_scorer.py` | `ReflexScorer.recommend()` | Where emotion modifier is applied |
| `src/services/reflex_feedback.py` | `record()`, `record_outcome()` | Where emotions update on feedback |

### Key dataclass — EmotionContext (in reflex_emotions.py):
```python
@dataclass
class EmotionContext:
    agent_id: str = ""
    phase_type: str = ""
    project_id: str = ""
    tool_freshness: Dict[str, float] = {}     # ← 196.1 populates from D2
    guard_warnings: Set[str] = set()           # ← 196.2 populates from D1
    current_task_recon_docs: List[str] = []
    tool_usage_history: Dict[str, List[dict]] = {}
    tool_metadata: Dict[str, dict] = {}
    file_ownership: Dict[str, str] = {}
```

---

## Execution Plan

### 196.1: D2 → D3 (Freshness → Curiosity) — Agent A

**Where to wire:** In `reflex_integration.py:reflex_session()` or in `reflex_emotions.py:load_emotion_context()`.

**What to do:**
1. Import `tool_source_watch.get_source_watch()` (or equivalent)
2. Call `scan_all()` or `get_freshness_events()` to get recently updated tools
3. For each updated tool, compute freshness score: `1.0` at update time, linear decay to `0.0` over 48h
4. Populate `EmotionContext.tool_freshness = {tool_id: score, ...}`
5. `compute_curiosity()` already uses `context.tool_freshness.get(tool_id, 0.0)` with `* 0.4` boost

**Test:** Create a mock fresh tool → verify curiosity is higher than for a stale tool.

**Files:** `src/services/reflex_emotions.py` or `src/services/reflex_integration.py`

---

### 196.2: D1 → D3 (Guard → Caution) — Agent A (same, sequential after 196.1)

**Where to wire:** Same location as 196.1.

**What to do:**
1. Import Protocol Guard's `SessionActionTracker` or `ProtocolGuard`
2. Get active warnings/violations for current agent: tools with guard warnings, protocol violations (edit_without_read, code_without_task, no_recon_docs)
3. Populate `EmotionContext.guard_warnings = {tool_id_1, tool_id_2, ...}`
4. `compute_caution()` already checks `context.guard_warnings` and caps trust at 0.3 for warned tools
5. Also populate `EmotionContext.current_task_recon_docs` from current task data

**Test:** Trigger "edit without read" → verify caution increases for write tools.

**Files:** `src/services/reflex_emotions.py` or `src/services/reflex_integration.py`

---

### 196.3: D3 → D1 (Trust → Warning Severity) — Agent B

**Where to wire:** In `protocol_guard.py` rule evaluation.

**What to do:**
1. Import `get_reflex_emotions()` from `reflex_emotions.py`
2. When evaluating a rule violation, check trust score for the tool
3. Modulate severity:
   - Trust > 0.7 → downgrade "block" to "warn" for minor violations
   - Trust < 0.3 → keep severity as-is (or upgrade "warn" to "block")
   - Trust 0.3-0.7 → no change
4. Never downgrade severity for critical violations (code_without_task, no_task_board)

**Test:** High-trust tool + minor violation → warn (not block). Low-trust + same violation → block.

**Files:** Protocol Guard source file

---

### 196.4: Phase 2 Gaps — Agent B (parallel with 196.3)

**What to fix:**
1. `ReflexScorer.score()` — add emotion modifier (currently only `recommend()` has it)
2. `ReflexFeedback.record_outcome()` — add emotion update (currently only `record()` has it)

**Files:** `src/services/reflex_scorer.py`, `src/services/reflex_feedback.py`

---

## Task Dependencies

```
196.1 (D2→D3) ─────┐
                     ├──→ 196.3 (D3→D1) — needs emotions populated to test trust flow
196.2 (D1→D3) ─────┘

196.4 (gap fixes) ──── independent, can run in parallel with everything
```

## Success Criteria

After Phase 196:
1. `session_init` emotions reflect real freshness data (not empty dicts)
2. Curiosity spikes when a tool source file was recently committed
3. Caution spikes when agent has protocol violations
4. Protocol Guard softens warnings for high-trust tools
5. All existing tests pass + new integration tests added
6. `score()` and `record_outcome()` participate in emotion flow
