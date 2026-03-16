# PHASE 177 — localguys Model Policy Matrix

**Date:** 2026-03-12  
**Updated:** 2026-03-17  
**Status:** ⚠️ DEPRECATED — Auto-generated from code  
**Tag:** `localguys`

> **IMPORTANT:** This document is deprecated. All policies are now auto-generated from `src/services/model_policy.py`.  
> See: `docs/177_MCC_local/ROADMAP_MODEL_POLICY_UNIFICATION_2026-03-17.md`

---

## History

- 2026-03-12: Initial manual matrix created
- 2026-03-17: **Superseded by unified ModelPolicy system**
  - Source of truth: `src/services/model_policy.py`
  - Auto-derives: tool_budget_class, role_fit, context_class, latency_class
  - Merges: LLMModelRegistry + reflex_decay

---

## Legacy Matrix (Outdated — Do Not Edit)

This table is kept for reference only. Values may be outdated.

| model_id | role_fit | capabilities | prompt_style | tool_budget_class | workflow_usage |
|---|---|---|---|---|---|
| `qwen3:8b` | `coder` primary | code, chat, reasoning-lite | concise, file-scoped, action-first | medium | `g3_localguys` default coder |
| `qwen2.5:7b` | `coder` fallback | code, chat | strict narrow instructions | medium | alternate coder |
| `qwen2.5:3b` | cheap `coder` / support | code-lite, chat | tiny context, single-step instructions | low | budget mode only |
| `deepseek-r1:8b` | `verifier` primary | reasoning, review | structured critique, no open-ended planning | low-medium | G3 critic/verifier |
| `phi4-mini:latest` | router / cheap verifier | chat, compact reasoning | short deterministic prompts | low | fallback verifier/router |
| `qwen2.5vl:3b` | `scout` visual | vision, chat | screenshot-driven, compare-first | low | visual recon only |
| `embeddinggemma:300m` | retrieval only | embeddings | no agent prompting | n/a | search/index/memory |
| `gemma3:4b` | support/general | chat, light reasoning | simple prompts, small scope | low | optional helper only |
| `gemma3:12b` | heavier generalist | chat, reasoning-lite | bounded tasks only | medium | optional hybrid use |
| `mistral-nemo:latest` | general fallback | chat, broad text work | explicit contract, low autonomy | medium | docs/support fallback |

---

## Current Implementation

See: `src/services/model_policy.py`

```python
from src.services.model_policy import get_unified_policy, get_all_policies

# Get policy for single model
policy = get_unified_policy("qwen3:8b")
print(policy.to_dict())

# Get all policies
all_policies = get_all_policies()
```

### Auto-Derived Fields

| Field | Source | Logic |
|-------|--------|-------|
| `tool_budget_class` | reflex_decay | fc ≥ 0.85 → medium, ≥ 0.75 → low-medium, < 0.75 → low |
| `role_fit` | model_policy.py | Hardcoded mapping per model_id |
| `context_class` | LLMModelRegistry | ≤8k → small, ≤32k → medium, >32k → large |
| `latency_class` | LLMModelRegistry | output_tps > 80 → fast, > 40 → balanced, else slow |

---

## Context classes (Reference)

- `small`: <= 8k effective working context
- `medium`: 8k-32k effective working context
- `large`: > 32k effective working context

---

## References

- Unified system: `docs/177_MCC_local/ROADMAP_MODEL_POLICY_UNIFICATION_2026-03-17.md`
- Implementation: `src/services/model_policy.py`
- reflex_decay: `src/services/reflex_decay.py`
- LLM registry: `src/elisya/llm_model_registry.py`
