# Roadmap: Phase 195.2 — REFLEX Emotions Layer

**Commander:** Opus
**Date:** 2026-03-19
**Agents:** 2 parallel + Opus review
**Est. total:** 2-3 hours
**Architecture:** [ARCHITECTURE_195_REFLEX_EMOTIONS.md](ARCHITECTURE_195_REFLEX_EMOTIONS.md)
**Dependencies:** D1 (195.0 Protocol Guard), D2 (195.1 CORTEX Freshness) — soft deps, interfaces defined

---

## Problem Statement

REFLEX scores tools with 8 factual signals but has no **behavioral adaptation**. Agents exploit known patterns, avoid updated tools, and never modulate risk awareness. The Emotions Layer adds three post-scoring modifiers — Curiosity, Trust, Caution — that change HOW the agent relates to its tools, not WHAT the tools are.

**Key formula:** `final_score = base_score × emotion_modifier(curiosity, trust, caution)`

---

## Execution Plan: 2 Agents + Opus

### Why 2 (not 3)?

The emotion module is architecturally cohesive — splitting the core across 3 agents would create excessive coupling. Instead:

- **Agent A (Core + Integration):** `reflex_emotions.py` + wiring into scorer/feedback/integration
- **Agent B (Tests + Session Display):** Full test suite + session_init emotion display
- **Opus:** Architecture review, interface validation with D1/D2, final verification

```
Timeline:
  ┌─ Agent A: Emotion core + integration (W1→W2) ─────────────────┐
  │  reflex_emotions.py + IP-E1/E2/E3                              │
  │                                                                  ├──→ Opus: W3
  │  ┌─ Agent B: Tests + session display (W1→W2) ────────────┐    │     Integration
  │  │  test suite + IP-E4 (session_init emotions)             │    │     verify
  │  └─────────────────────────────────────────────────────────┘    │
  └──────────────────────────────────────────────────────────────────┘
```

---

## Wave 1 — Foundation (parallel)

### Agent A: W1 — `reflex_emotions.py` core module

**Task:** `195.2.1: reflex_emotions.py — Emotion core with curiosity/trust/caution`

**What to do:**
1. Create `src/services/reflex_emotions.py`
2. Implement dataclasses:
   ```python
   @dataclass
   class EmotionContext:
       agent_id: str = ""
       phase_type: str = ""
       project_id: str = ""
       tool_freshness: Dict[str, float] = field(default_factory=dict)   # From D2
       guard_warnings: Set[str] = field(default_factory=set)            # From D1
       current_task_recon_docs: List[str] = field(default_factory=list)
       tool_usage_history: Dict[str, List[dict]] = field(default_factory=dict)
       tool_metadata: Dict[str, dict] = field(default_factory=dict)
       file_ownership: Dict[str, str] = field(default_factory=dict)     # file → agent

   @dataclass
   class EmotionState:
       curiosity: float = 0.6       # Cold start default
       trust: float = 0.5
       caution: float = 0.3
       last_event: str = ""         # "success" | "failure" | "new"
       consecutive_successes: int = 0
       consecutive_failures: int = 0
       total_uses: int = 0
       updated_at: float = 0.0
   ```

3. Implement three compute functions:
   - `compute_curiosity(tool_id, agent_id, context) -> float`
     - Zero usage → 0.9 (with semantic match) or 0.6
     - Familiarity decay: `1/(1 + exp(0.5 * (usage - 5)))` sigmoid
     - Freshness boost: `freshness * 0.4`
   - `compute_trust(tool_id, agent_id, context) -> float`
     - Asymmetric EMA: success +0.15, failure -0.35
     - Context specificity (same project = 1.0, other = 0.7)
     - Guard warning cap: max 0.3
     - Cold start: 0.5
   - `compute_caution(tool_id, agent_id, context) -> float`
     - Side-effect risk (mutating tool → 0.7)
     - Ownership risk (other agent's files → 0.8)
     - Protocol risk (mutating + no recon → 0.5)
     - Guard risk (active warning → 0.6)
     - Take max of all risks

4. Implement `compute_emotion_modifier(curiosity, trust, caution) -> float`:
   ```python
   trust_factor = 0.5 + trust * 0.5           # [0.5, 1.0]
   curiosity_factor = 1.0 + curiosity * 0.3   # [1.0, 1.3]
   caution_factor = 1.0 - caution * 0.4       # [0.6, 1.0]
   return clamp(trust_factor * curiosity_factor * caution_factor, 0.3, 1.5)
   ```

5. Implement persistence via ENGRAM:
   - `load_emotion_state(tool_id, agent_id) -> EmotionState`
   - `save_emotion_state(tool_id, agent_id, state: EmotionState)`
   - Key format: `emotion:{agent_id}:{tool_id}`
   - Categories: `emotion_trust` (7d TTL), `emotion_curiosity` (3d TTL), `emotion_caution` (14d TTL)

6. Implement `load_emotion_context(agent_id, phase_type, project_id) -> EmotionContext`
   - Builds context from CORTEX feedback, TaskBoard ownership, guard state

7. Implement `get_emotion_engine()` singleton

**Files:** `src/services/reflex_emotions.py`
**Constraint:** Pure logic module. No imports from session_tools, fc_loop, or scorer. Import from engram_cache and reflex_feedback only.

---

### Agent B: W1 — Test suite

**Task:** `195.2.2: Test suite for REFLEX Emotions`

**What to do:**
1. Create `tests/test_phase195_reflex_emotions.py`
2. Tests for curiosity:
   - `test_curiosity_high_for_never_used_tool` — zero usage → ≥ 0.6
   - `test_curiosity_decays_with_usage` — after 10 uses → < 0.3
   - `test_curiosity_boost_from_freshness` — freshness=0.8 → higher curiosity
   - `test_curiosity_never_negative` — always ≥ 0.0
3. Tests for trust:
   - `test_trust_starts_neutral` — cold start → 0.5
   - `test_trust_grows_with_success` — 5 successes → > 0.7
   - `test_trust_drops_sharply_on_failure` — 3 successes + 1 failure → < 0.5
   - `test_trust_asymmetric` — gain rate < loss rate
   - `test_trust_capped_by_guard_warning` — guard warning → max 0.3
   - `test_trust_context_specific` — different context → 0.7 multiplier
4. Tests for caution:
   - `test_caution_high_for_mutating_tools` — edit tool → ≥ 0.7
   - `test_caution_low_for_read_tools` — search tool → ≤ 0.2
   - `test_caution_high_for_foreign_files` — other agent's files → ≥ 0.8
   - `test_caution_high_without_recon` — mutating + no recon → ≥ 0.5
5. Tests for modifier:
   - `test_modifier_range` — always in [0.3, 1.5]
   - `test_modifier_caution_dominates` — high caution overrides high curiosity
   - `test_modifier_trust_gates` — zero trust → modifier < 0.5
   - `test_modifier_cold_start` — default emotions → ~0.78
6. Tests for persistence:
   - `test_emotion_save_load_roundtrip` — save + load = same state
   - `test_emotion_ttl_decay` — old emotions expire via ENGRAM TTL
7. Integration scenario tests:
   - `test_scenario_updated_tool_gets_boost` — freshness + curiosity → score increases
   - `test_scenario_failing_tool_gets_dampened` — failures → trust drops → score drops
   - `test_scenario_risky_edit_cautioned` — edit without recon → score drops

**Files:** `tests/test_phase195_reflex_emotions.py`
**Note:** Use fixtures, tmp_path, mocks for ENGRAM. Reference `tests/test_phase193_reflex_guard.py` for style.

---

## Wave 2 — Integration (parallel)

### Agent A: W2 — Wire emotions into REFLEX pipeline

**Task:** `195.2.3: Wire emotions into reflex_scorer + reflex_feedback + reflex_integration`

**What to do:**
1. **IP-E1** in `src/services/reflex_scorer.py`:
   - In `ReflexScorer.score()`, after `_weighted_sum()`, apply emotion modifier
   - Add `emotion_context: Optional[EmotionContext]` field to `ReflexContext`
   - If emotion_context is None, skip (backward compatible)
   ```python
   base_score = self._weighted_sum(signals)
   if context.emotion_context:
       from src.services.reflex_emotions import compute_emotion_modifier_for_tool
       modifier = compute_emotion_modifier_for_tool(tool.id, context.emotion_context)
       return min(1.0, max(0.0, base_score * modifier))
   return base_score
   ```

2. **IP-E2** in `src/services/reflex_feedback.py`:
   - In `record()`, after recording feedback, update emotion state
   ```python
   # After CORTEX recording
   try:
       from src.services.reflex_emotions import get_emotion_engine
       engine = get_emotion_engine()
       engine.update_on_feedback(tool_id, agent_role, success=success, context=context_str)
   except Exception:
       pass  # Emotion failures never break feedback recording
   ```

3. **IP-E3** in `src/services/reflex_integration.py`:
   - In `reflex_session()` (IP-6), load emotion context before scoring
   ```python
   # Before scorer.recommend()
   try:
       from src.services.reflex_emotions import load_emotion_context
       context.emotion_context = load_emotion_context(agent_type, phase_type, project_id)
   except Exception:
       context.emotion_context = None
   ```

4. Add `emotion_context` field to `ScoredTool.overlay` for transparency:
   ```python
   overlay["emotions"] = {"curiosity": 0.7, "trust": 0.4, "caution": 0.2, "modifier": 0.85}
   ```

**Files:** `src/services/reflex_scorer.py`, `src/services/reflex_feedback.py`, `src/services/reflex_integration.py`
**Critical:** All emotion code wrapped in try/except. Emotion failures NEVER break existing pipeline.

---

### Agent B: W2 — Session display + integration tests

**Task:** `195.2.4: Emotion display in session_init + integration tests`

**What to do:**
1. **IP-E4** in `src/mcp/tools/session_tools.py`:
   - Add `"reflex_emotions"` section to session_init response
   ```python
   "reflex_emotions": {
       "agent_mood": _compute_mood_label(emotions),  # "exploratory" | "cautious" | "confident" | "wary"
       "tool_emotions": {
           "vetka_read_file": {"curiosity": 0.8, "trust": 0.3, "caution": 0.2, "modifier": 0.85},
           ...
       },
       "emotion_summary": "High curiosity for 3 updated tools. Low trust for vetka_read_file."
   }
   ```

2. Implement `_compute_mood_label(emotions)`:
   - "exploratory" — avg curiosity > 0.6
   - "cautious" — avg caution > 0.6
   - "confident" — avg trust > 0.7
   - "wary" — avg trust < 0.3
   - "balanced" — default

3. Add integration tests to `tests/test_phase195_reflex_emotions.py`:
   - `test_emotion_modifier_applied_to_score` — mock scorer, verify base_score × modifier
   - `test_emotion_updated_on_feedback` — record success → trust increases
   - `test_emotion_in_session_init` — mock session_init → emotions section present
   - `test_emotion_backward_compatible` — no emotion_context → score unchanged
   - `test_emotion_failure_doesnt_break_pipeline` — emotion exception → pipeline continues

**Files:** `src/mcp/tools/session_tools.py`, `tests/test_phase195_reflex_emotions.py`

---

## Wave 3 — Verify + D1/D2 Interfaces (Opus)

### Opus: W3 — Integration verification + interface contracts

**Task:** `195.2.5: Integration verify + D1/D2 interface contracts`

**What to do:**
1. Run full test suite: `python -m pytest tests/ -v`
2. Verify emotion flow end-to-end:
   - Load session_init → check emotions section
   - Simulate tool success → check trust increase
   - Simulate tool failure → check trust decrease
   - Add freshness signal → check curiosity boost
3. Document D1/D2 shared interfaces (create if not done by those teams):
   - `ProtocolGuardInterface` (from D1 → caution)
   - `ToolFreshnessInterface` (from D2 → curiosity)
   - `EmotionInterface` (from D3 → D1/D2)
4. Validate interaction matrix with real data
5. Update CLAUDE.md if needed
6. Update architecture doc with any changes

---

## Task Summary

| Wave | Task ID | Title | Agent | Depends On | Est. |
|------|---------|-------|-------|------------|------|
| W1 | 195.2.1 | reflex_emotions.py core module | Agent A | — | 50min |
| W1 | 195.2.2 | Test suite | Agent B | — | 40min |
| W2 | 195.2.3 | Wire into scorer/feedback/integration | Agent A | 195.2.1 | 40min |
| W2 | 195.2.4 | Session display + integration tests | Agent B | 195.2.1, 195.2.2 | 35min |
| W3 | 195.2.5 | Integration verify + D1/D2 interfaces | Opus | all | 25min |

```
Parallel execution:
  Time 0    ├── A: 195.2.1 (emotion core) ── 50min ──├── A: 195.2.3 (integration) ── 40min ──┐
            │                                         │                                         │
            ├── B: 195.2.2 (test suite)   ── 40min ──├── B: 195.2.4 (display+tests) ── 35min ──├── Opus: 195.2.5
            │                                                                                    │   25min
            │                                                                                    │
  Total wall time: ~1h 55min (vs ~3h 10min sequential)                                          │
```

---

## Agent Instructions

### For Agent A (core + integration):
```
Read these files FIRST:
1. docs/195_REFLEX_EMOTIONS/ARCHITECTURE_195_REFLEX_EMOTIONS.md
2. src/services/reflex_scorer.py (understand 8 signals, _weighted_sum, ScoredTool)
3. src/services/reflex_feedback.py (understand record(), aggregation)
4. src/services/reflex_integration.py (understand IP-6 reflex_session)
5. src/memory/engram_cache.py (understand EngramEntry, categories, TTL)

Your job: Create reflex_emotions.py (W1), then wire IP-E1/E2/E3 into pipeline (W2).
DO NOT touch: session_tools.py, tests.
ALL emotion code MUST be wrapped in try/except — never break existing pipeline.
```

### For Agent B (tests + display):
```
Read these files FIRST:
1. docs/195_REFLEX_EMOTIONS/ARCHITECTURE_195_REFLEX_EMOTIONS.md
2. tests/test_phase193_reflex_guard.py (test style reference)
3. src/mcp/tools/session_tools.py (understand session_init response)

Your job: Write comprehensive test suite (W1), then add session_init display (W2).
DO NOT touch: reflex_emotions.py, reflex_scorer.py, reflex_feedback.py, reflex_integration.py.
Import from src/ to test.
Use tmp_path + mocks for isolation.
```

---

## Success Criteria

After all waves complete:

1. `session_init` returns `reflex_emotions` section with per-tool curiosity/trust/caution
2. Tool scores are visibly modulated by emotion modifier (check `ScoredTool.overlay.emotions`)
3. Trust drops after failures, recovers after successes (asymmetric)
4. Curiosity spikes for freshly updated tools (integration with D2 when available)
5. Caution dampens scores for risky operations (integration with D1 when available)
6. All emotion code is fault-tolerant — exception in emotions never breaks REFLEX
7. Full test suite passes: `python -m pytest tests/test_phase195_reflex_emotions.py -v`
8. Backward compatible: no behavior change when emotion_context is None

---

## The Vision

```
BEFORE (REFLEX without emotions):
  Agent sees: tool X, score 0.87 → calls it → fails → calls it again → fails → ...

AFTER (REFLEX with emotions):
  Agent sees: tool X, score 0.87 × 0.39 (modifier) = 0.34
              "trust: 0.1 (5 recent failures), caution: 0.8 (no recon docs)"
  Agent thinks: "This tool has low trust and high caution. Let me find an alternative."
  → Tries tool Y instead → succeeds → trust for Y grows → ecosystem adapts
```

The agent doesn't just pick the highest-scored tool. It develops a **relationship** with its tools — exploring new ones, trusting proven ones, being careful with risky ones. This is the foundation for truly adaptive agent behavior.
