# Grok Research Review — Model Policy Unification (2026-03-17)

**Date:** 2026-03-17  
**Grok Response:** Received  
**Status:** Analyzed

---

## Grok's Recommendations Summary

### 1. Create `src/services/model_policy.py` — NEW
- Unified dataclass `ModelPolicy` merging:
  - LLMModelRegistry (context_length, output_tps, provider)
  - reflex_decay (fc_reliability, max_tools, prefer_simple)
  - Auto-derivatives: tool_budget_class, role_fit, context_class, latency_class

### 2. Add new models to reflex_decay.py
- gemma3:4b, gemma3:12b, mistral-nemo

### 3. Replace _LOCALGUYS_MODEL_MATRIX in mcc_routes.py
- Use `get_unified_policy()` instead of manual dict

### 4. Add `get_profile_sync` to LLMModelRegistry
- Currently only async `get_profile()` exists

---

## Codebase Analysis

| Recommendation | Status | Notes |
|---------------|--------|-------|
| `model_policy.py` | ❌ NOT EXISTS | New file needed |
| `get_profile_sync` | ❌ NOT EXISTS | But sync path EXISTS in get_profile (line 497) |
| reflex_decay updates (gemma3, mistral) | ❌ NOT EXISTS | Need to add |
| Replace _LOCALGUYS_MODEL_MATRIX | ⚠️ PARTIAL | Already integrated reflex_decay (BG-002) |

---

## Current State (after BG-002)

```python
# mcc_routes.py:_build_local_model_descriptor()
llm_profile = await get_llm_registry().get_profile(model_id)  # async
reflex_profile = get_reflex_model_profile(model_id)           # sync
policy = dict(_LOCALGUYS_MODEL_MATRIX.get(model_id, {}))       # manual dict
```

**Already includes:**
- ✅ fc_reliability
- ✅ max_tools  
- ✅ prefer_simple

**Still manual:**
- ⚠️ _LOCALGUYS_MODEL_MATRIX (role_fit, prompt_style, tool_budget_class)

---

## Recommended Action Plan

### Option A: Full Grok Implementation (comprehensive)
1. Create `model_policy.py` with unified class
2. Add `get_profile_sync` or use existing sync path
3. Add new models to reflex_decay
4. Replace _LOCALGUYS_MODEL_MATRIX

### Option B: Minimal (current state is 80% there)
1. Add new models to reflex_decay (gemma3, mistral)
2. Auto-derive tool_budget_class from fc_reliability (simplify _LOCALGUYS_MODEL_MATRIX)
3. Update docs

### Decision Needed: Which path to take?

---

## References

- Grok prompt: Provided by user
- Code: `src/api/routes/mcc_routes.py:734+`
- Code: `src/services/reflex_decay.py:106+`
- Code: `src/elisya/llm_model_registry.py:476+`
