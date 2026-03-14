# MARKER_157_7_3R_VETKA_JARVIS_UNIFIED_CONTEXT_PACKING_IMPL_REPORT_2026-03-07

Status: `IMPLEMENTED`
Date: `2026-03-07`

## Goal
Replace ad-hoc Jarvis file-snippet limits with existing unified context stack used by chat-grade paths.

## Markers
- `MARKER_157_7_3R_REMOVE_ADHOC_FILE_FACTS.V1`
- `MARKER_157_7_3R_STAGE_MODEL_AWARE_CONTEXT_PACK.V1`
- `MARKER_157_7_3R_PROVIDER_ADAPTIVE_BUDGET_BIND.V1`

## What changed

### 1) Removed ad-hoc hard-limited file-facts path
Files:
- `src/voice/jarvis_llm.py`
- `src/api/handlers/jarvis_handler.py`

Removed runtime pieces:
- `_safe_read_text_snippet(...)`
- `_build_file_facts_from_context(...)`
- `_MAX_FILE_FACTS / _MAX_FILE_BYTES / _MAX_FILE_SNIPPET_CHARS`
- trace field `file_facts_count`

### 2) Unified model-aware context repacking per stage model
File:
- `src/voice/jarvis_llm.py`

Added:
- `_repack_context_for_model(...)`

Behavior:
- each stage/model call reuses `ContextPacker.pack(...)` with current `model_name`,
- context fields (`json_context`, `pinned_context`, `viewport_summary`, `jepa_context`, `context_packer_trace`) are refreshed for that model,
- no new local token/char/file caps were introduced in Jarvis path.

### 3) Prompt content now prefers packed/unified context
File:
- `src/voice/jarvis_llm.py`

Behavior:
- system prompt now uses packed blocks:
  - `Structured runtime context (ELISION)`
  - `Pinned context`
  - `Viewport summary`
  - `JEPA context`
- no direct raw viewport dump as primary path.

### 4) Provider adaptive budget remains centralized
Reference:
- `src/elisya/provider_registry.py::_resolve_adaptive_max_tokens(...)`

Behavior:
- output budget is still resolved centrally from model profile context length,
- Jarvis calls through `call_model_v2(...)` continue to inherit this provider-agnostic adaptive output budget.

## Recon summary (hard-limit audit in voice path)

### Removed new ad-hoc limits (this patch)
- all `file_facts` hard limits in Jarvis runtime.

### Existing central limits (kept, not newly introduced)
- context assembly/model-family budgets in `src/api/handlers/message_utils.py`
- elision levels/config in `src/memory/jarvis_prompt_enricher.py`
- provider adaptive output budget in `src/elisya/provider_registry.py`

These are project-wide mechanisms and remain as source-of-truth.

## Validation
Executed:
- `python -m py_compile src/voice/jarvis_llm.py src/api/handlers/jarvis_handler.py`
- `pytest -q tests/test_phase157_5_memory_contract.py tests/test_phase157_3_1_stage_machine_basics.py`

Result:
- `7 passed, 1 warning`

## Notes
- MYCELIUM code was not modified.
- Transfer was applied only in VETKA-JARVIS runtime path.
