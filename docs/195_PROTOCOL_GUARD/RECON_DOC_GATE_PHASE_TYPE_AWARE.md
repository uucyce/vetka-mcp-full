# RECON: DOC_GATE Should Be phase_type-Aware

**Date:** 2026-03-20
**Severity:** LOW (protocol improvement)
**Phase:** 195

## Problem Statement

`DOC_GATE` (MARKER_190) требует `architecture_docs` или `recon_docs` для **всех** задач.
Единственный обход — `force_no_docs=true`, который пропускает без вопросов.

Это создаёт две проблемы:
1. **Research-задачи** (цель = создать документ) вынуждены использовать `force_no_docs`, хотя это их легитимный кейс
2. **Build/fix-задачи** могут злоупотреблять `force_no_docs` для обхода гейта без последствий

## Current Behavior

**File:** `src/mcp/tools/task_board_tools.py`, lines 292-312

```python
# MARKER_190.DOC_GATE: Universal doc requirement for all task types
arch_docs = [d for d in (payload.get("architecture_docs") or []) if str(d).strip()]
recon_docs = [d for d in (payload.get("recon_docs") or []) if str(d).strip()]
force_no_docs = bool(payload.pop("force_no_docs", False))

if not arch_docs and not recon_docs and not force_no_docs:
    # → REJECT with doc suggestions
```

**Decision matrix (current):**

| phase_type | Has docs? | force_no_docs? | Result |
|------------|-----------|----------------|--------|
| any        | yes       | —              | PASS   |
| any        | no        | true           | PASS (bypass) |
| any        | no        | false          | REJECT |

No differentiation by `phase_type`. `force_no_docs` is a blunt override.

## Proposed Behavior

**Smart gate based on `phase_type`:**

| phase_type | Has docs? | force_no_docs? | Result |
|------------|-----------|----------------|--------|
| **research** | no     | —              | **PASS** (auto-exempt: research creates docs) |
| **test**     | no     | —              | **PASS** (auto-exempt: tests validate, don't design) |
| build      | no        | true           | PASS (explicit bypass, log warning) |
| build      | no        | false          | REJECT |
| fix        | no        | true           | PASS (explicit bypass, log warning) |
| fix        | no        | false          | REJECT |

### Key Changes

1. **`phase_type in ("research", "test")` → auto-exempt** from doc gate (no `force_no_docs` needed)
2. **`phase_type in ("build", "fix")` + `force_no_docs`** → still allowed, but log a warning for audit
3. **Remove `force_no_docs` from research/test** — it becomes irrelevant

## Affected Code

| File | Lines | Change |
|------|-------|--------|
| `src/mcp/tools/task_board_tools.py` | 292-312 | Add `phase_type` check before doc gate |

## Implementation Sketch

```python
# After line 298 (force_no_docs = bool(...)):
phase_type = payload.get("phase_type", "")
doc_exempt_types = ("research", "test")

if not arch_docs and not recon_docs and not force_no_docs:
    if phase_type in doc_exempt_types:
        # Auto-exempt: research creates docs, tests validate
        pass
    else:
        # Existing REJECT logic
        suggested = _suggest_docs_for_title(search_query)
        return {"success": False, "error": "DOC_GATE: ...", ...}
```

## Risk Assessment

- **Low risk:** Only relaxes the gate for research/test, never for build/fix
- **No breaking changes:** `force_no_docs` still works for edge cases
- **Audit benefit:** Fewer false `force_no_docs` usages → cleaner signal when it IS used on build/fix tasks

## Test Plan

1. `research` task without docs → PASS (no `force_no_docs` needed)
2. `test` task without docs → PASS
3. `build` task without docs → REJECT
4. `fix` task without docs → REJECT
5. `build` task with `force_no_docs=true` → PASS (with warning log)
6. Existing tests pass
