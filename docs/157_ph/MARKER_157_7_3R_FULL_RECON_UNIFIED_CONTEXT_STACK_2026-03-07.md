# MARKER_157_7_3R_FULL_RECON_UNIFIED_CONTEXT_STACK_2026-03-07

Status: `RECON + IMPLEMENTATION COMPLETED`
Date: `2026-03-07`

## Request focus
1. No ad-hoc hardcoded context limits in Jarvis.
2. Use existing unified stack from chat-grade paths.
3. Verify JEPA + ELISION + model/provider-aware budgeting chain.
4. Extend roadmap and keep markered implementation.

## Existing unified stack (source-of-truth)

### A) Context assembly and compression
- `src/api/handlers/message_utils.py`
  - `build_json_context(...)` (structured runtime context)
  - model-family budgets via `get_context_budget_for_model(...)`
- `src/memory/jarvis_prompt_enricher.py`
  - ELISION compression (`compress_context(...)`)
  - viewport-aware enrichment (`enrich_prompt_with_viewport(...)`)

### B) JEPA overflow path
- `src/orchestration/context_packer.py`
  - unified `pack(...)` orchestrates pinned + viewport + json context
  - JEPA semantic fallback under pressure + hysteresis
  - trace: `packing_path`, `jepa_mode`, `jepa_latency_ms`, token pressure signals

### C) Provider/model adaptive budgeting
- `src/elisya/provider_registry.py`
  - `_resolve_adaptive_max_tokens(...)`
  - computes output budget using model context length from `llm_model_registry`
  - provider-agnostic and central for `call_model_v2(...)`

## Gap found in previous Jarvis path
- ad-hoc file snippet path (`file_facts`) had local hard caps and bypassed unified context strategy.
- stage models (gemma/deepseek/llama) did not repack context per model before each generation.

## Implemented fix (this phase)

### MARKER_157_7_3R_REMOVE_ADHOC_FILE_FACTS.V1
- removed file-facts runtime path and related local hard limits.

### MARKER_157_7_3R_STAGE_MODEL_AWARE_CONTEXT_PACK.V1
- added per-stage model-aware repack in Jarvis generation path:
  - every `generate(...)` call repacks via `ContextPacker.pack(...)` with current model.

### MARKER_157_7_3R_PROVIDER_ADAPTIVE_BUDGET_BIND.V1
- preserved provider adaptive output budgeting centrally via `call_model_v2(...)`.

## Files changed
- `src/voice/jarvis_llm.py`
- `src/api/handlers/jarvis_handler.py`
- docs:
  - `docs/157_ph/MARKER_157_7_3_VETKA_JARVIS_FILE_FACTS_IMPL_REPORT_2026-03-07.md` (superseded marker)
  - `docs/157_ph/MARKER_157_7_VETKA_JARVIS_CONTEXT_TOOL_RECON_2026-03-07.md` (roadmap update)
  - this file

## Validation
- `python -m py_compile src/voice/jarvis_llm.py src/api/handlers/jarvis_handler.py`
- `pytest -q tests/test_phase157_5_memory_contract.py tests/test_phase157_3_1_stage_machine_basics.py`
- result: `7 passed, 1 warning`

## Next implementation block
1. `157.7.4` Voice Tool Loop MVP (`retrieve_context/read_file/workflow_probe`) with trace fields.
2. `157.7.5` Proactive action-pack state matrix (MYCO transfer).
3. `157.7.6` Dedicated VETKA-JARVIS hidden RAG base + memory coupling policy (ENGRAM/STM/CAM).
