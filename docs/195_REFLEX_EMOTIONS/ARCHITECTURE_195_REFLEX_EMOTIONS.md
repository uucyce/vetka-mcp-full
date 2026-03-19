# Architecture: Phase 195.2 — REFLEX Emotions Layer

**Author:** Opus (Claude Code)
**Date:** 2026-03-19
**Status:** IMPLEMENTED (W1-W2 done, W3 verified 2026-03-19)
**Task:** `tb_1773893756_1`
**Related:** D1 (195.0 Protocol Guard), D2 (195.1 CORTEX Freshness)

---

## Problem Statement

REFLEX scores tools with 8 signals (semantic, cam, feedback, engram, stm, phase, hope, mgc) — all are **factual**. They answer "what matches?" and "what worked before?" but never ask:

- **"Should I explore this?"** — a tool was just updated, or I've never tried it
- **"Do I trust this?"** — it failed 3 times last session, but maybe the context was different
- **"Is this risky?"** — I'm about to edit files I don't own, without recon

Current behavior: agents optimize for highest score, repeat known patterns, avoid anything unfamiliar. This creates **exploitation bias** — agents never explore, never adapt, never learn new paths.

### Concrete Failures

1. **Tool updated, agent avoids it:** `vetka_read_file` fixed in Phase 193.8, but CORTEX still shows 0% success → agents avoid a working tool
2. **Agent repeats failed pattern:** keeps calling `preview_start` for CUT even after 5 failures, because semantic score is high
3. **Agent edits without caution:** modifies files owned by another agent, no signal warns about ownership risk

### Root Cause

REFLEX has no **adaptive behavioral layer**. It's a static ranker. Emotions are the missing meta-layer that modulates *how* the agent relates to its tools — not what the tools are, but what the agent's *relationship* with each tool should be.

---

## Design Decision: Post-Scoring Modulator (not new signals)

### Why NOT add 3 new REFLEX signals?

Adding curiosity/trust/caution as signals 9/10/11 would:
- Dilute existing 8 weights (must sum to 1.0) — every signal gets weaker
- Conflate different abstraction levels — emotions are about the agent's *state*, not the tool's *properties*
- Require rebalancing all weights with every emotion change

### The modulator approach

```
CURRENT:
  8 signals → weighted_sum → score → rank

AFTER:
  8 signals → weighted_sum → base_score
                                 ↓
  emotion_state(tool, agent, context) → modifier (0.5 – 1.5)
                                 ↓
  final_score = base_score × modifier → rank
```

Emotions don't change WHAT the tool is — they change HOW the agent approaches it.

---

## Three Emotional Dimensions

### 1. CURIOSITY (exploration drive)

**What it measures:** "How much should I want to try this tool?"

**High curiosity (→ boost):**
- Tool source file was modified recently (MGC mtime change) — ties into D2
- Tool has never been used by this agent (zero CORTEX history)
- Tool has high semantic match but zero usage history (promising but untested)
- New tool appeared in registry (first seen)

**Low curiosity (→ neutral):**
- Tool used successfully many times (well-known, no novelty)
- Tool hasn't changed since last use

**Decay:** Curiosity fades after N successful uses. A tool becomes "known" — no exploration needed.

```python
# Curiosity formula
def compute_curiosity(tool_id: str, agent_id: str, context: EmotionContext) -> float:
    """Returns 0.0-1.0 curiosity score."""

    freshness = context.tool_freshness.get(tool_id, 0.0)   # From D2 (195.1)
    usage_count = context.agent_usage_count(tool_id)
    has_semantic_match = context.semantic_score > 0.5

    # Never used → high curiosity
    if usage_count == 0:
        novelty = 0.9 if has_semantic_match else 0.6
    else:
        # Curiosity decays with familiarity (sigmoid)
        novelty = 1.0 / (1.0 + math.exp(0.5 * (usage_count - 5)))

    # Freshness boost (tool was updated)
    freshness_boost = freshness * 0.4  # Up to 0.4 extra

    return min(1.0, novelty + freshness_boost)
```

**Modifier effect:** `1.0 + curiosity * 0.3` → range [1.0, 1.3]
- Curiosity never penalizes, only boosts exploration

### 2. TRUST (reliability confidence)

**What it measures:** "How confident am I that this tool will work?"

**High trust (→ boost):**
- Consecutive successes in similar context
- Recent verifier approval
- Used by multiple agents successfully (social proof)

**Low trust (→ penalty):**
- Recent failures (sharp drop: 1 fail = -3 successes worth)
- Failures in current context (per-project, per-phase)
- Guard warnings active (from D1)

**Key insight:** Trust is **asymmetric** — harder to build, easier to lose. This models real trust dynamics.

```python
# Trust formula
def compute_trust(tool_id: str, agent_id: str, context: EmotionContext) -> float:
    """Returns 0.0-1.0 trust score."""

    history = context.get_tool_history(tool_id, agent_id, window_days=7)

    if not history:
        return 0.5  # Cold start: neutral trust

    # Asymmetric exponential moving average
    trust = 0.5  # Start neutral
    for event in history:  # chronological
        if event.success:
            trust += (1.0 - trust) * 0.15   # Slow gain
        else:
            trust -= trust * 0.35            # Fast loss (asymmetric!)

    # Context specificity: trust in CUT != trust in PULSE
    context_match = 1.0 if event.context == context.current_context else 0.7

    # Guard integration: active danger rule → cap trust
    if context.has_guard_warning(tool_id):
        trust = min(trust, 0.3)

    return max(0.0, min(1.0, trust * context_match))
```

**Modifier effect:** `0.5 + trust * 0.5` → range [0.5, 1.0]
- Low trust actively penalizes (down to 0.5× score)
- High trust returns to baseline (1.0×), not above — trust doesn't boost, it unlocks

### 3. CAUTION (risk awareness)

**What it measures:** "How careful should I be with this action?"

**High caution (→ dampen):**
- Tool has side effects (write/edit/delete vs read/search)
- Target files owned by another agent (from TaskBoard)
- No recon_docs in current task (ties into D1 Protocol Guard)
- First use of tool in this project/phase
- Tool is flagged with guard warnings

**Low caution (→ neutral):**
- Read-only tool
- Files are owned by current agent
- Recon complete, task well-documented

```python
# Caution formula
def compute_caution(tool_id: str, agent_id: str, context: EmotionContext) -> float:
    """Returns 0.0-1.0 caution score. High = be careful."""

    tool_meta = context.get_tool_metadata(tool_id)

    # Side effect risk
    is_mutating = tool_meta.category in ("file_op", "git", "edit", "delete")
    side_effect_risk = 0.7 if is_mutating else 0.1

    # Ownership risk
    target_files = context.get_tool_target_files(tool_id)
    owned_by_other = any(
        context.is_owned_by_other(f, agent_id) for f in target_files
    )
    ownership_risk = 0.8 if owned_by_other else 0.0

    # Protocol risk (from D1)
    has_recon = bool(context.current_task_recon_docs)
    protocol_risk = 0.5 if (is_mutating and not has_recon) else 0.0

    # Guard warnings
    guard_risk = 0.6 if context.has_guard_warning(tool_id) else 0.0

    return min(1.0, max(side_effect_risk, ownership_risk, protocol_risk, guard_risk))
```

**Modifier effect:** `1.0 - caution * 0.4` → range [0.6, 1.0]
- High caution dampens score (down to 0.6×)
- Low caution = no effect

---

## Combined Emotion Modifier

```python
def emotion_modifier(curiosity: float, trust: float, caution: float) -> float:
    """Combine three emotions into a single score modifier.

    Priority: caution > trust > curiosity
    (Safety overrides reliability overrides exploration)

    Returns: 0.3 – 1.5 (multiplicative modifier on base REFLEX score)
    """

    # Trust gate: unlocks base score
    trust_factor = 0.5 + trust * 0.5              # [0.5, 1.0]

    # Curiosity boost: exploration on top of trust
    curiosity_factor = 1.0 + curiosity * 0.3       # [1.0, 1.3]

    # Caution damper: safety override
    caution_factor = 1.0 - caution * 0.4           # [0.6, 1.0]

    # Combine: trust × curiosity × caution
    modifier = trust_factor * curiosity_factor * caution_factor

    # Clamp to safe range
    return max(0.3, min(1.5, modifier))
```

### Interaction Matrix

| Scenario | Curiosity | Trust | Caution | Modifier | Effect |
|----------|-----------|-------|---------|----------|--------|
| Known reliable tool, own files | 0.1 | 0.9 | 0.1 | 0.95× 1.03× 0.96 = **0.94** | Slight neutral |
| New tool, good semantic match | 0.9 | 0.5 | 0.3 | 0.75× 1.27× 0.88 = **0.84** | Mild boost from curiosity |
| Updated tool, was failing | 0.7 | 0.3 | 0.2 | 0.65× 1.21× 0.92 = **0.72** | Trust limits, curiosity helps |
| Write tool, no recon, other's files | 0.1 | 0.8 | 0.9 | 0.90× 1.03× 0.64 = **0.59** | Strong caution dampening |
| Brand new tool, first ever use | 0.9 | 0.5 | 0.4 | 0.75× 1.27× 0.84 = **0.80** | Balanced: curious but cautious |
| Failed 5x, guard warning | 0.1 | 0.1 | 0.8 | 0.55× 1.03× 0.68 = **0.39** | Nearly blocked |

### Priority Hierarchy: Caution > Trust > Curiosity

This is enforced by the modifier ranges:
- **Caution** can reduce final modifier to 0.3 (strongest effect)
- **Trust** can reduce to 0.5 (medium effect)
- **Curiosity** can only ADD up to 0.3 (weakest, never overrides safety)

A highly curious but dangerous tool will still be dampened. Curiosity opens doors; caution and trust decide if you walk through.

---

## Persistence: Emotion Memory

### Where to Store

**Option A: ENGRAM L1 entries** (chosen)
- Reuse existing infrastructure
- New category: `emotion_trust`, `emotion_curiosity`
- Natural TTL support (emotions should decay)
- Already wired into session_init pipeline

**Option B: Dedicated JSON file** (rejected)
- Another file to maintain
- Doesn't benefit from ENGRAM's TTL and category management
- No existing wiring

### Schema

```python
# New ENGRAM categories
CATEGORY_TTL = {
    ...
    "emotion_trust": 7 * 86400,       # 7 days — trust decays relatively fast
    "emotion_curiosity": 3 * 86400,   # 3 days — curiosity is ephemeral
    "emotion_caution": 14 * 86400,    # 14 days — caution persists longer
}

# ENGRAM key format for emotions
# "emotion:{agent_id}:{tool_id}:{context}"
# Example: "emotion:opus:vetka_read_file:CUT"

# ENGRAM value format (JSON in value field)
{
    "curiosity": 0.7,
    "trust": 0.4,
    "caution": 0.3,
    "last_event": "success",          # Last interaction type
    "consecutive_successes": 2,
    "consecutive_failures": 0,
    "total_uses": 5,
    "updated_at": 1773893756.0
}
```

### Cold Start Strategy

For new tool-agent pairs with no emotion history:
```python
DEFAULT_EMOTIONS = {
    "curiosity": 0.6,    # Mildly curious (encourage exploration)
    "trust": 0.5,        # Neutral (no evidence either way)
    "caution": 0.3,      # Slightly cautious (safe default)
}
# Default modifier: 0.75 × 1.18 × 0.88 = 0.78
# Slight overall dampening for unknown tools — sensible default
```

---

## Integration Points

### IP-E1: Emotion Computation (in reflex_scorer.py)

After `_weighted_sum()` returns `base_score`, apply emotion modifier:

```python
# In ReflexScorer.score()
def score(self, tool, context: ReflexContext) -> float:
    signals = self.score_signals(tool, context)
    base_score = self._weighted_sum(signals)

    # NEW: Emotion modulation
    if context.emotion_context:
        modifier = compute_emotion_modifier(tool.id, context.emotion_context)
        return min(1.0, max(0.0, base_score * modifier))

    return base_score
```

### IP-E2: Emotion Update (in reflex_feedback.py)

After recording tool success/failure, update emotion state:

```python
# In ReflexFeedback.record()
def record(self, tool_id, success, ...):
    # ... existing CORTEX recording ...

    # NEW: Update emotion state
    update_emotion_state(tool_id, agent_id, success=success, context=context)
```

### IP-E3: Emotion Loading (in reflex_integration.py)

Load emotion state into ReflexContext during session_init:

```python
# In reflex_session() (IP-6)
def reflex_session(session_data, phase_type, agent_type, current_task):
    # ... existing context building ...

    # NEW: Load emotion state for this agent
    context.emotion_context = load_emotion_context(agent_type, phase_type)
```

### IP-E4: Emotion Display (in session_tools.py)

Surface emotion state in session_init response:

```python
# In session_init response
"reflex_emotions": {
    "agent_mood": "exploratory",      # Summary label
    "tool_emotions": {
        "vetka_read_file": {"curiosity": 0.8, "trust": 0.3, "caution": 0.2},
        "vetka_edit_file": {"curiosity": 0.1, "trust": 0.9, "caution": 0.4},
    },
    "emotion_summary": "High curiosity for updated tools (3 tools refreshed). Low trust for vetka_read_file (recent failures)."
}
```

---

## Shared Interfaces with D1 and D2

### D1 (Protocol Guard) → Caution signal

```python
# Interface: D1 provides to D3
class ProtocolGuardInterface:
    def has_guard_warning(self, tool_id: str) -> bool:
        """Does this tool have an active guard warning?"""

    def get_protocol_violations(self, agent_id: str) -> List[str]:
        """What protocol violations has this agent committed?"""
        # "edit_without_read", "code_without_task", "no_recon_docs"

    def get_ownership_risk(self, tool_id: str, target_files: List[str], agent_id: str) -> float:
        """0.0-1.0 ownership risk score for this tool call."""
```

Caution consumes these to raise risk awareness.

### D2 (Tool Freshness) → Curiosity signal

```python
# Interface: D2 provides to D3
class ToolFreshnessInterface:
    def get_freshness_score(self, tool_id: str) -> float:
        """0.0-1.0 how recently the tool was updated. 1.0 = just updated."""

    def is_stale_failure(self, tool_id: str) -> bool:
        """Were failures recorded BEFORE the tool was last updated?"""

    def get_updated_tools(self, since_hours: int = 24) -> List[str]:
        """List of tool_ids updated in the last N hours."""
```

Curiosity consumes freshness to boost exploration of updated tools.

### D3 (Emotions) → D1 and D2

```python
# Interface: D3 provides to D1 and D2
class EmotionInterface:
    def get_trust_score(self, tool_id: str, agent_id: str) -> float:
        """Current trust level. D1 can use this to modulate warning severity."""

    def get_caution_score(self, tool_id: str, agent_id: str) -> float:
        """Current caution level. D2 can use this to decide freshness reset aggressiveness."""
```

---

## File Layout

```
src/services/reflex_emotions.py       # Core emotion module (NEW)
  - EmotionContext (dataclass)
  - EmotionState (dataclass)
  - compute_curiosity()
  - compute_trust()
  - compute_caution()
  - compute_emotion_modifier()
  - load_emotion_context()
  - update_emotion_state()
  - get_emotion_interface()            # Singleton

src/services/reflex_scorer.py          # MODIFY: add IP-E1
src/services/reflex_feedback.py        # MODIFY: add IP-E2
src/services/reflex_integration.py     # MODIFY: add IP-E3
src/mcp/tools/session_tools.py        # MODIFY: add IP-E4

tests/test_phase195_reflex_emotions.py # Full test suite (NEW)
```

---

## W3 Verification Report (2026-03-19)

### Test Results
- **147/147 REFLEX tests pass** (emotions: 36, scorer: 78, feedback: 26, guard: 7)
- 6 stale test files with ImportErrors (phase159/170/172, agents_routes) — pre-existing, unrelated

### Implementation Deviations (accepted)

| # | Spec vs Implementation | Decision |
|---|------------------------|----------|
| 1 | Singleton: `get_emotion_engine()` → `get_reflex_emotions()` | Accept — consistent with `get_reflex_scorer()` naming |
| 2 | Trust formula: raw ±delta → EMA-style proportional | Accept — EMA is more stable, prevents overshoot |
| 3 | IP-E3: explicit hook → transitive via `recommend()` | Accept — works, no functional gap |

### Known Gaps (Phase 2)

| # | Gap | Impact | Fix |
|---|-----|--------|-----|
| 1 | `score()` skips emotions, only `recommend()` applies modifier | Single-tool scoring bypasses emotions | Add emotion modifier to `score()` |
| 2 | `record_outcome()` (verifier path) doesn't update emotions | Verifier pass/fail doesn't affect trust | Wire IP-E2 into `record_outcome()` |
| 3 | EmotionContext shallow — no guard_warnings/foreign_files from D1 | Caution underestimates risk | Wire when D1 ships |
| 4 | EmotionContext no freshness from D2 | Curiosity doesn't respond to tool updates | Wire when D2 ships |

### D1/D2 Interface Status

- **D1 → D3 (Protocol Guard → Caution):** Interface defined, not wired. Caution currently uses local guard_warnings set.
- **D2 → D3 (Tool Freshness → Curiosity):** Interface defined, not wired. Curiosity uses tool_freshness dict (empty until D2 ships).
- **D3 → D1/D2 (Emotions → Guard/Freshness):** `get_reflex_emotions()` exposes `get_modifier_breakdown(tool_id)` for external consumers.

---

## Open Questions (for future phases)

1. **Emotion visualization:** Should the 3D DAG show emotion state as node color/glow?
2. **Cross-agent emotion transfer:** If Cursor trusts `vetka_edit_file`, should Opus inherit partial trust?
3. **Emotion explanations:** Should the agent see WHY curiosity is high? ("Tool updated 2h ago, source file changed")
4. **Manual emotion override:** Should user be able to say "trust this tool" and set trust=1.0?
5. **Emotion logging:** Track emotion changes over time for debugging/analysis?
