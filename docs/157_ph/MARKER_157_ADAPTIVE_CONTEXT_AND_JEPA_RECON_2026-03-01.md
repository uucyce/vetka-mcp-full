# MARKER_157_ADAPTIVE_CONTEXT_AND_JEPA_RECON_2026-03-01

## Scope
- Stabilize context budgeting without provider-specific hardcode.
- Validate MGC warning root cause and fix status.
- Define JEPA-driven improvements for VETKA pre-prompting and Knowledge Levels.

## Recon Findings

### 1) `context_length_exceeded` root cause (confirmed)
- Incident model: `upstage/solar-pro-3:free` via OpenRouter stream.
- Provider error payload showed:
  - model context max: `131072`
  - request total: `137910`
  - completion reservation: `46080`
- Conclusion:
  - This is not key-limit exhaustion.
  - Failure was context budgeting mismatch (input too large + oversized completion budget).

### 2) MGC runtime warning root cause (confirmed)
- Warning:
  - `RuntimeWarning: coroutine 'MGCCache.get' was never awaited`
- Source:
  - `src/api/handlers/message_utils.py` in sync path `_batch_get_mgc_scores()`.
- Cause:
  - async `MGCCache.get()` was called from sync ranking function.
- Fix:
  - switched to synchronous hot-tier lookup via `mgc_cache.gen0`.

## Implemented Technical Changes (Phase 157)

### A) Adaptive max_tokens (provider-agnostic)
- File: `src/elisya/provider_registry.py`
- Added:
  - `_estimate_message_tokens(messages)`
  - `_resolve_adaptive_max_tokens(model, messages, requested_max_tokens)`
- Applied centrally in:
  - `call_model_v2(...)`
  - `call_model_v2_stream(...)`
- Policy:
  - takes model `context_length` from `LLMModelRegistry` (dynamic profile cache / open APIs / defaults)
  - computes prompt token estimate
  - reserves safety margin
  - clamps output to min/default/hard-cap bounds
- Result:
  - no OpenRouter-specific hardcoded budget.
  - same control path now serves OpenRouter + other providers.

### B) Payload alignment
- File: `src/elisya/provider_registry.py`
- OpenRouter/OpenAI payloads now accept centrally resolved `max_tokens`.
- Streaming OpenRouter uses dynamic `max_tokens` from central resolver.

### C) MGC sync fix
- File: `src/api/handlers/message_utils.py`
- `_batch_get_mgc_scores()` now reads Gen0 entries directly and avoids un-awaited async calls.

## Validation Guards
- Added: `tests/test_phase157_adaptive_budget_guards.py`
  - adaptive resolver is called in both call paths (stream + non-stream)
  - stream OpenRouter uses dynamic max tokens (not fixed 2048)
  - MGC sync scorer no longer calls async `cache.get(...)`

## JEPA / Knowledge Mode Upgrade Plan (from `Convolutional_neural_network_GROK.txt`)

## Objective
- Improve retrieval quality while reducing context pressure by moving raw artifacts into hierarchical JEPA summaries.

## Proposed Architecture (VETKA-first, low-risk)
- L0 (local): artifact/file snippets near viewport focus.
- L1 (cluster): folder/topic-level semantic aggregate.
- L2 (global): DAG-level intent/state summary for orchestration prompt.

### Data flow
1. Collect viewport + pinned + selected node metadata.
2. Build JEPA embeddings (existing MCC JEPA adapter/runtime path).
3. Aggregate embeddings per level:
   - L0: nearest neighbors for immediate user intent.
   - L1: cluster centroids + top edges.
   - L2: compact global trajectory/state.
4. Inject into prompt as bounded sections:
   - `JEPA_LOCAL_CONTEXT`
   - `JEPA_CLUSTER_CONTEXT`
   - `JEPA_GLOBAL_CONTEXT`
5. Keep raw file excerpts only for top-K explainability snippets.

### Prompting rules
- Do not append full raw pinned content when JEPA summary exists and confidence is high.
- Cap each level independently:
  - L0: detail-biased, short horizon.
  - L1: structural, medium horizon.
  - L2: strategic, minimal text.
- On low confidence: fallback to current pinned/json context path.

### Operational KPI targets
- Reduce prompt token footprint on large pinned sets by 35-60%.
- Reduce `context_length_exceeded` events to near-zero for 128k models.
- Maintain or improve top-1 relevance in tree/chat response quality.

## Next Actions (execution order)
1. Add runtime metric logging:
   - input tokens, resolved max_tokens, context_length, overflow headroom.
2. Add adaptive-retry:
   - if provider returns `context_length_exceeded`, retry once with tighter context compression.
3. Introduce JEPA 3-level context composer in `message_utils` (feature-flagged).
4. A/B test:
   - baseline (current) vs JEPA-level prompting on same chat sessions.

## Notes
- `requirements.txt` remains intentionally deferred (as agreed) until architecture stabilization completes.
