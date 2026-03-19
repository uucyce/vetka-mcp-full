# DEBUG: REFLEX Duplicate Singleton — Split Brain Risk

**Phase:** 193 (post-guard integration)
**Date:** 2026-03-19
**Severity:** HIGH — singleton data divergence in CORTEX feedback
**Found by:** Agent B (Phase 193 feedback), confirmed by Opus recon

---

## Problem

Two identical REFLEX packages exist in the codebase:

```
src/reflex/           ← OLD package (10 modules, stale)
src/services/reflex_* ← CURRENT production (11 modules, actively developed)
```

**5 files are byte-for-byte identical.** 4 files have diverged — `src/services/` versions are significantly enhanced with MARKER_182, 186, 191, 193 improvements.

### The Bug

`src/memory/failure_feedback.py` imports from the OLD path:
```python
from src.reflex.feedback import get_reflex_feedback  # ← OLD singleton
```

Every other module (222 imports) uses:
```python
from src.services.reflex_feedback import get_reflex_feedback  # ← CURRENT singleton
```

**Result:** Two separate `_feedback_instance` singletons. Failures recorded by `failure_feedback.py` go into one instance, REFLEX Guard reads from another. The self-healing loop from Phase 193 is broken for this path.

---

## Scope: Full Duplication Map

### Identical files (5):
| src/reflex/ | src/services/ | Lines |
|-------------|---------------|-------|
| experiment.py | reflex_experiment.py | 280 |
| feedback.py | reflex_feedback.py | 542 |
| filter.py | reflex_filter.py | 210 |
| preferences.py | reflex_preferences.py | 196 |
| streaming.py | reflex_streaming.py | 358 |

### Diverged files (4 — services version is ENHANCED):
| src/reflex/ | src/services/ | Delta |
|-------------|---------------|-------|
| decay.py (386) | reflex_decay.py (420) | +34 lines: qwen3.5, gemma3, mistral-nemo models |
| integration.py (391) | reflex_integration.py (450) | +59 lines: run_id, session_id, Guard filter (193.2) |
| registry.py (222) | reflex_registry.py (322) | +100 lines: tool_memory overlay (177.REFLEX) |
| scorer.py (577) | reflex_scorer.py (830) | +253 lines: enhanced scoring |

### Only in src/services/ (2 — NEW modules):
- `reflex_guard.py` (394 lines) — Phase 193
- `reflex_tool_memory.py` (297 lines) — Phase 177

### Singleton Split Risk:
| Singleton | src/reflex | src/services | Split? |
|-----------|-----------|-------------|--------|
| `_feedback_instance` | feedback.py:528 | reflex_feedback.py:528 | **YES** (failure_feedback.py uses old) |
| `_registry_instance` | registry.py:208 | reflex_registry.py:293 | Potential |
| `_store_instance` | preferences.py:182 | reflex_preferences.py:182 | Potential |
| `_scorer_instance` | scorer.py:563 | reflex_scorer.py:816 | Potential |

---

## Fix Plan

### Decision: Keep `src/services/reflex_*` (production), delete `src/reflex/`

**Rationale:**
- 222 imports use `src.services.reflex_*`
- Only 1 import uses `src.reflex.*`
- All tests (11 files) use `src.services.reflex_*`
- New features (Guard, Tool Memory) only in services
- Services versions are enhanced, src/reflex is stale

### Tasks

#### Task 1: Fix the critical import (5 min, 1 agent)
Update `src/memory/failure_feedback.py`:
```python
# BEFORE (broken):
from src.reflex.feedback import get_reflex_feedback
# AFTER (correct):
from src.services.reflex_feedback import get_reflex_feedback
```
Verify: grep for any remaining `from src.reflex` imports.

#### Task 2: Delete src/reflex/ package (5 min, same agent)
```bash
rm -rf src/reflex/
```
Verify: `python -c "from src.services.reflex_feedback import get_reflex_feedback"` works.
Verify: `grep -r "from src.reflex" src/` returns nothing.

#### Task 3: Run full test suite (5 min, same agent)
```bash
python -m pytest tests/test_reflex_*.py tests/test_phase193_reflex_guard.py -v
```
All 11 reflex test files + 16 guard tests must pass.

#### Task 4: Verify singleton unity (5 min, same agent)
```python
# This must return True — same object, not two copies:
from src.services.reflex_feedback import get_reflex_feedback
from src.memory.failure_feedback import record_failure_feedback
# After fix, failure_feedback uses same singleton as guard/scorer
```

---

## Why This Happened

`src/reflex/` was likely the original package structure. When services were refactored into `src/services/`, the reflex modules were copied with `reflex_` prefix but the old package wasn't deleted. Over time, `src/services/` evolved (Phases 177-193) while `src/reflex/` remained stale. Nobody noticed because only 1 file still imported from the old path.

---

## Agent Feedback Summary (Phase 193 session)

| Agent | Observation | Status |
|-------|------------|--------|
| Agent B | Import path разнобой: `src.reflex.feedback` vs `src.services.reflex_feedback` — two singletons, CORTEX data diverges | **CONFIRMED — this doc** |
| Agent A | CORTEX TTL 60s — guard doesn't learn within single fc_loop run | Valid, v2 improvement |
| Agent A | GuardContext vs kwargs sprawl in execute_fc_loop | Valid, refactor later |
| Agent C | `_maybe_promote_to_danger()` is a stub | **False alarm** — function exists at line 190 |
| Agent C | `_make_guard()` should move to conftest.py | Good idea, do when tests grow |
| Agent C | Add e2e test with full `__init__` (no `_make_guard`) | Valid, add in next test wave |
| Agent C | Document source naming convention | Minor, do when touching docs |
