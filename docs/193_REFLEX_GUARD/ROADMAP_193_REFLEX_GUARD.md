# Roadmap: Phase 193 — REFLEX Feedback Guard Layer

**Commander:** Opus
**Date:** 2026-03-19
**Agents:** 3 parallel + Opus review
**Est. total:** 2-3 hours
**Problem:** Agents repeat identical mistakes because REFLEX is a pure scoring engine — it recommends tools but never checks feedback rules or blocks dangerous combos.

---

## Problem Statement

REFLEX has 8 scoring signals but ZERO guard signals. The `feedback` signal (weight 0.18) measures historical success rate — it does NOT check if a tool is forbidden in a given context.

**Concrete failure:**
- User records feedback: "Never use Preview for CUT"
- REFLEX still recommends `preview_start` with score 0.87 (good semantic match)
- Agent calls `preview_start` → fails → user is frustrated
- Repeat ∞

**Root cause:** Feedback memories exist at 4 layers (CORTEX, FailureFeedback, ENGRAM L1, User CLAUDE.md) but none are checked as a PRE-CALL gate.

---

## Architecture: What Exists vs What's Missing

```
CURRENT (broken):
  session_init → REFLEX scorer → score-ranked list → agent calls whatever

AFTER (Phase 193):
  session_init → REFLEX scorer → guard_check() → filtered list + warnings → agent sees dangers
                                      ↑
                           ENGRAM L1 danger entries
                           CORTEX failure history (>N fails)
                           User feedback rules (new)

  fc_loop → agent picks tool → pre_call_guard() → BLOCK if danger match
                                      ↑
                           Same sources, hard gate
```

---

## Execution Plan: 3 Agents

### Why 3?

Three independent surfaces need the guard layer. No file conflicts:

- **Agent A (Core Guard):** `reflex_guard.py` — new module, the guard logic itself
- **Agent B (ENGRAM + session_init):** Wire ENGRAM L1 danger entries into session_init output
- **Agent C (Tests):** Full test suite + integration tests
- **Opus:** Reviews, merges, final verification

```
Timeline:
  ┌─ Agent A: Guard module (W1→W2) ───────────────────────────┐
  │  reflex_guard.py + wire into reflex_integration.py         │
  │                                                             ├──→ Opus: Integration
  │  ┌─ Agent B: ENGRAM injection (W1→W2) ───────────────┐    │     review + merge
  │  │  session_init enrichment + danger collector         │    │
  │  └─────────────────────────────────────────────────────┘    │
  │  ┌─ Agent C: Tests (W1→W2) ──────────────────────────┐    │
  │  │  test suite + integration tests                     │    │
  │  └─────────────────────────────────────────────────────┘    │
  └─────────────────────────────────────────────────────────────┘
```

---

## Wave 1 — Foundation (parallel, all 3 agents)

### Agent A: W1 — `reflex_guard.py` core module

**Task:** `193.1: reflex_guard.py — Feedback Guard core with danger registry`

**What to do:**
1. Create `src/services/reflex_guard.py`
2. Implement `FeedbackGuard` class:
   ```python
   class FeedbackGuard:
       def __init__(self):
           self._danger_rules: List[DangerRule] = []
           self._failure_thresholds: Dict[str, int] = {}
           self._load_danger_rules()

       def check_tool(self, tool_id: str, context: GuardContext) -> GuardResult:
           """Check if tool is safe to use in this context.
           Returns: GuardResult(allowed=bool, warnings=[], blocked_reason="")
           """

       def filter_recommendations(self, recs: List[dict], context: GuardContext) -> List[dict]:
           """Filter/demote dangerous tools from recommendation list.
           Adds 'warning' and 'blocked' fields to each rec.
           """

       def get_active_dangers(self, agent_type: str, phase_type: str) -> List[DangerRule]:
           """Get all active danger rules for current context."""
   ```
3. Implement `DangerRule` dataclass:
   ```python
   @dataclass
   class DangerRule:
       tool_pattern: str        # "preview_start" or "preview_*" (glob)
       context_pattern: str     # "CUT" or "*" (any phase)
       reason: str              # "Never use preview for CUT"
       source: str              # "engram_l1" | "cortex_failure" | "user_feedback"
       severity: str            # "block" | "warn" | "demote"
       created_at: float
   ```
4. Implement `_load_danger_rules()`:
   - Source 1: ENGRAM L1 entries with `category="danger"` → block
   - Source 2: CORTEX feedback where `success_rate < 0.2` AND `call_count >= 3` → warn
   - Source 3: Static rules file `data/reflex_guard_rules.json` (for user-defined rules)
5. Implement `get_feedback_guard()` singleton pattern

**Files:** `src/services/reflex_guard.py`, `data/reflex_guard_rules.json`
**Constraint:** Pure logic module. No imports from session_tools or fc_loop.

---

### Agent B: W1 — ENGRAM L1 danger collector + session_init enrichment

**Task:** `193.2: ENGRAM danger collector + session_init warnings injection`

**What to do:**
1. Add to `src/memory/engram_cache.py`:
   ```python
   def get_danger_entries(self, agent_type: str = "*", phase_type: str = "*") -> List[EngramEntry]:
       """Get all non-expired danger-category entries matching agent/phase."""

   def get_all_by_category(self, category: str) -> List[EngramEntry]:
       """Get all entries of a specific category."""
   ```
2. Add to `src/services/reflex_integration.py` in `reflex_session()` (IP-6):
   - After scoring, call `guard.filter_recommendations(scored, context)`
   - Add `"warnings"` field to each recommendation that has a danger match
   - Add `"blocked_tools"` top-level key to session context
3. Update `src/mcp/tools/session_tools.py` session_init response:
   - Add `"reflex_warnings"` section with active danger rules
   - Add `"blocked_tools"` list so agent sees what's blocked
   - Format: `{"tool": "preview_start", "reason": "Failed 5/5 times for CUT", "source": "cortex"}`

**Files:** `src/memory/engram_cache.py`, `src/services/reflex_integration.py`, `src/mcp/tools/session_tools.py`
**Constraint:** Don't modify reflex_guard.py or tests.

---

### Agent C: W1 — Test suite

**Task:** `193.3: Test suite for Feedback Guard`

**What to do:**
1. Create `tests/test_phase193_reflex_guard.py`:
   - `test_guard_blocks_danger_tool` — tool with danger ENGRAM entry is blocked
   - `test_guard_warns_low_success_tool` — tool with <20% success rate gets warning
   - `test_guard_allows_safe_tool` — normal tool passes through
   - `test_filter_recommendations_removes_blocked` — blocked tools removed from list
   - `test_filter_recommendations_adds_warnings` — warned tools get warning field
   - `test_danger_rule_glob_matching` — `preview_*` matches `preview_start`
   - `test_static_rules_loaded` — rules from JSON file are loaded
   - `test_context_pattern_matching` — rule for "CUT" doesn't block "PULSE"
   - `test_engram_danger_collector` — `get_danger_entries()` returns only danger category
   - `test_session_init_includes_warnings` — mock session_init returns blocked_tools

**Files:** `tests/test_phase193_reflex_guard.py`
**Note:** Use fixtures for guard, engram cache. Mock CORTEX feedback.

---

## Wave 2 — Integration (parallel)

### Agent A: W2 — Wire guard into fc_loop pre-call gate

**Task:** `193.4: Pre-call guard gate in fc_loop.py`

**What to do:**
1. In `src/tools/fc_loop.py`, add pre-call check:
   ```python
   # Before executing tool call:
   from src.services.reflex_guard import get_feedback_guard
   guard = get_feedback_guard()
   result = guard.check_tool(tool_name, context)
   if not result.allowed:
       # Return error to LLM instead of executing
       tool_result = {"error": f"BLOCKED by feedback guard: {result.blocked_reason}"}
       # Log the block
   elif result.warnings:
       # Log warnings but allow execution
   ```
2. Add guard context building from available pipeline info (agent_type, phase_type, project_id)
3. Ensure guard errors never crash fc_loop (try/except with fallback to allow)

**Files:** `src/tools/fc_loop.py`
**Critical:** Guard failures must NEVER break the pipeline. Always `try/except → allow`.

---

### Agent B: W2 — Auto-populate danger rules from failure history

**Task:** `193.5: Auto-promote repeated failures to danger rules`

**What to do:**
1. In `src/memory/failure_feedback.py`, add to `record_failure_feedback()`:
   ```python
   # After recording CORTEX failure, check if threshold crossed
   _maybe_promote_to_danger(tool_id, phase_type, agent_type)
   ```
2. Implement `_maybe_promote_to_danger()`:
   - Query CORTEX for tool's failure count in last 7 days
   - If failures >= 3 AND success_rate < 0.2 → create ENGRAM L1 danger entry
   - Log: `[FailureFeedback] Auto-promoted {tool_id} to ENGRAM danger (3+ failures)`
3. This creates a self-healing loop:
   ```
   Tool fails → CORTEX records → threshold crossed → ENGRAM danger → Guard blocks → Agent stops repeating
   ```

**Files:** `src/memory/failure_feedback.py`
**Constraint:** Don't create duplicate danger entries. Check ENGRAM first.

---

### Agent C: W2 — Integration tests + fc_loop guard tests

**Task:** `193.6: Integration tests — guard in session_init + fc_loop`

**What to do:**
1. Add to `tests/test_phase193_reflex_guard.py`:
   - `test_fc_loop_blocks_dangerous_tool` — mock fc_loop, verify tool blocked
   - `test_fc_loop_allows_safe_tool` — normal tool executes
   - `test_guard_error_doesnt_crash_fc_loop` — guard exception → tool allowed
   - `test_auto_promote_failure_to_danger` — 3 failures → ENGRAM entry created
   - `test_auto_promote_skips_if_already_danger` — no duplicates
   - `test_full_cycle` — create failures → auto-promote → guard blocks → verify

**Files:** `tests/test_phase193_reflex_guard.py`

---

## Wave 3 — Cleanup + Verify (Opus)

### Opus: W3 — Integration verification

**Task:** `193.7: Integration verify + live test`

**What to do:**
1. Run full test suite
2. Manually test:
   - Add danger rule via ENGRAM: `preview_start` for CUT
   - Call session_init → verify `reflex_warnings` present
   - Verify REFLEX recommendations demote the blocked tool
3. Verify auto-promote: create fake failures → check ENGRAM populated
4. Clean up any dead code from old REFLEX paths
5. Update CLAUDE.md if needed

---

## Task Summary

| Wave | Task ID | Title | Agent | Depends On | Est. |
|------|---------|-------|-------|------------|------|
| W1 | 193.1 | reflex_guard.py core module | Agent A | — | 40min |
| W1 | 193.2 | ENGRAM danger collector + session_init | Agent B | — | 40min |
| W1 | 193.3 | Test suite | Agent C | — | 30min |
| W2 | 193.4 | fc_loop pre-call gate | Agent A | 193.1 | 30min |
| W2 | 193.5 | Auto-promote failures to danger | Agent B | 193.1, 193.2 | 30min |
| W2 | 193.6 | Integration tests | Agent C | 193.4, 193.5 | 30min |
| W3 | 193.7 | Integration verify + live test | Opus | all | 20min |

```
Parallel execution:
  Time 0    ├── A: 193.1 (guard core)     ── 40min ──├── A: 193.4 (fc_loop gate) ── 30min ──┐
            │                                         │                                       │
            ├── B: 193.2 (ENGRAM+session) ── 40min ──├── B: 193.5 (auto-promote) ── 30min ──├── Opus: 193.7
            │                                         │                                       │   20min
            ├── C: 193.3 (test suite)     ── 30min ──├── C: 193.6 (integ tests)  ── 30min ──┘
            │
  Total wall time: ~1h 30min (vs ~3h 40min sequential)
```

## Self-Healing Loop (the goal)

```
1. Agent calls tool → fails
2. FailureFeedback records in CORTEX
3. After 3+ failures → auto-promote to ENGRAM L1 danger
4. Next session_init → FeedbackGuard filters recommendations
5. Agent sees warning: "BLOCKED: preview_start failed 5/5 times for CUT"
6. fc_loop pre-call gate blocks if agent ignores warning
7. Agent forced to find alternative → learns new path
```

No memory.md reading required. No "please remember" instructions.
The system enforces the rule at infrastructure level.

## Agent Instructions

### For Agent A (guard core + fc_loop):
```
Read these files FIRST:
1. docs/193_REFLEX_GUARD/ROADMAP_193_REFLEX_GUARD.md
2. src/services/reflex_integration.py (understand IP points)
3. src/services/reflex_scorer.py (understand scoring flow)
4. src/tools/fc_loop.py (understand tool execution)

Your job: Create reflex_guard.py (W1), then wire into fc_loop (W2).
DO NOT touch: engram_cache.py, session_tools.py, failure_feedback.py, tests.
```

### For Agent B (ENGRAM + session_init + auto-promote):
```
Read these files FIRST:
1. docs/193_REFLEX_GUARD/ROADMAP_193_REFLEX_GUARD.md
2. src/memory/engram_cache.py (understand L1 cache)
3. src/mcp/tools/session_tools.py (understand session_init)
4. src/memory/failure_feedback.py (understand failure loop)
5. src/services/reflex_integration.py:reflex_session() (IP-6)

Your job: Add danger collector to ENGRAM (W1), enrich session_init (W1),
then add auto-promote in failure_feedback (W2).
DO NOT touch: reflex_guard.py, fc_loop.py, tests.
```

### For Agent C (tests):
```
Read these files FIRST:
1. docs/193_REFLEX_GUARD/ROADMAP_193_REFLEX_GUARD.md
2. tests/test_phase192_sqlite_migration.py (test style reference)

Your job: Write comprehensive test suite (W1), then integration tests (W2).
DO NOT touch: any src/ files.
Import from src/ to test.
Use tmp_path + mocks for isolation.
```
