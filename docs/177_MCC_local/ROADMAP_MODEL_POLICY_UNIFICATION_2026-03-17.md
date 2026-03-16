# PHASE 177 — Model Policy Unification Roadmap

**Date:** 2026-03-17  
**Status:** In Progress  
**Based on:** Grok research `RECON_GROK_MODEL_POLICY_UNIFICATION_2026-03-17.md`  
**Goal:** Unified ModelPolicy system for localguys

---

## Background

Grok proposed a unified ModelPolicy system merging:
- `LLMModelRegistry` — context_length, output_tps, provider
- `reflex_decay` — fc_reliability, max_tools, prefer_simple
- Auto-derivatives — tool_budget_class, role_fit, context_class, latency_class

**Current state after BG-002:**
- ✅ fc_reliability, max_tools, prefer_simple integrated
- ⚠️ _LOCALGUYS_MODEL_MATRIX still manual

---

## Implementation Plan

### Phase A1: Foundation

#### A1.1: Create model_policy.py
**Task:** `tb_1773703xxx_1`
- Create `src/services/model_policy.py`
- Define `ModelPolicy` dataclass
- Implement auto-derivation methods (tool_budget, role_fit, context_class, latency_class)
- Add `get_unified_policy()` and `get_all_policies()` functions
- Source: Grok proposal

#### A1.2: Add get_profile_sync to LLMModelRegistry  
**Task:** `tb_1773703xxx_2`
- Add sync method to `src/elsiya/llm_model_registry.py`
- Use existing `_profiles.get()` path (already sync)
- Enable synchronous access for ModelPolicy

### Phase A2: reflex_decay Updates

#### A2.1: Add new models to reflex_decay
**Task:** `tb_1773703xxx_3`
- Add gemma3:4b, gemma3:12b, mistral-nemo to MODEL_PROFILES
- Source: Grok values:
  - gemma3:4b: fc=0.72, max_tools=5, prefer_simple=True
  - gemma3:12b: fc=0.81, max_tools=9, prefer_simple=True
  - mistral-nemo: fc=0.84, max_tools=12, prefer_simple=False

### Phase A3: Integration

#### A3.1: Replace _LOCALGUYS_MODEL_MATRIX
**Task:** `tb_1773703xxx_4`
- Update `src/api/routes/mcc_routes.py`
- Replace manual dict with `get_unified_policy()`
- Simplify `_build_local_model_descriptor()`
- Remove duplicate _LOCALGUYS_MODEL_MATRIX dict

### Phase A4: Documentation

#### A4.1: Update MODEL_POLICY_MATRIX.md
**Task:** `tb_1773703xxx_5`
- Mark docs as auto-generated from code
- Reference `model_policy.py` as source of truth
- Add note: manual table deprecated

---

## Dependencies

```
A1.1 ─┬─► A1.2 ─► A3.1 ─► A4.1
      │
      └─► A2.1 ─► A3.1
```

---

## References

- Grok research: `docs/177_MCC_local/RECON_GROK_MODEL_POLICY_UNIFICATION_2026-03-17.md`
- Existing code: `src/api/routes/mcc_routes.py:734+`
- Existing code: `src/services/reflex_decay.py:106+`
- Existing code: `src/elisya/llm_model_registry.py:476+`
