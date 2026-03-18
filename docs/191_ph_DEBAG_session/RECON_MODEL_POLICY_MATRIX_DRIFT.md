# RECON: MODEL_POLICY_MATRIX.md vs reflex_decay.py Drift

**Date:** 2026-03-18
**Phase:** 191 — DEBUG Session
**Task:** tb_1773702691_14

---

## Files

- **Doc:** `docs/177_MCC_local/MODEL_POLICY_MATRIX.md`
- **Code:** `src/services/reflex_decay.py` (model profiles, decay config)
- **Code:** `src/services/model_policy.py` (budget class, LOCALGUYS_CATALOG)

## Drift Summary

| # | Problem | Location | Severity |
|---|---------|----------|----------|
| 1 | `max_tools` per model missing from doc | reflex_decay.py:112-239 | HIGH |
| 2 | `prefer_simple` flag missing from doc | reflex_decay.py:112-239 | HIGH |
| 3 | `PHASE_HALF_LIFE` values undocumented (45/14/30 days) | reflex_decay.py:36-43 | HIGH |
| 4 | `DecayConfig` numeric thresholds undocumented | reflex_decay.py:49-71 | HIGH |
| 5 | `fc_reliability` values not in model table | reflex_decay.py:112-239 | MEDIUM |
| 6 | `mistral-nemo:latest` vs `mistral-nemo` name mismatch | doc line 38 vs code line 233 | LOW |
| 7 | No Bronze/Silver/Gold tier structure in doc | reflex_decay.py comments | LOW |
| 8 | `DecayConfig` bounds (min 7d, max 90d) undocumented | reflex_decay.py:70-71 | MEDIUM |
| 9 | No canonical model list in one place | model_policy.py:205-218 | LOW |
| 10 | Doc legacy table says "Do Not Edit" but is stale | doc line 23 | META |

## Fix Strategy

**Option A (recommended):** Regenerate MODEL_POLICY_MATRIX.md from code — single script that reads reflex_decay.py ModelProfile dict + DecayConfig and outputs markdown table. Future-proof.

**Option B:** Manual sync — update doc with current values. Will drift again.

## DecayConfig Values (from code)

```python
PHASE_HALF_LIFE = {"research": 45.0, "fix": 14.0, "build": 30.0, "*": 30.0}

DecayConfig:
  success_boost_threshold = 0.8
  success_boost_multiplier = 2.0
  failure_threshold = 0.3
  failure_multiplier = 0.5
  min_half_life = 7.0   # 1 week
  max_half_life = 90.0  # 3 months
```

## Model Profiles (24 models in reflex_decay.py)

Key fields missing from doc: `fc_reliability`, `max_tools`, `prefer_simple`

Example drift:
- qwen3:8b → fc=0.82, max_tools=8, prefer_simple=True (not in doc)
- qwen3-235b → fc=0.92, max_tools=45, prefer_simple=False (not in doc)
- mistral-nemo → fc=0.84, max_tools=12 (doc says "mistral-nemo:latest")
