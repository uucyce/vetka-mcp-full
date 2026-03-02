# MARKER_157_MEMORY_FLOW_AUDIT_2026-03-01

## Scope
- Audit only (no runtime behavior changes).
- Target flow: `message -> context assembly -> provider call`.
- Required focus: ELISION, CAM/ARC, MGC, MemoryManager central participation.

## Source Baseline
- `docs/103_ph/MEMORY_INTEGRATION_ANALYSIS.md`
- `docs/93_ph/MEMORY_SYSTEMS_SUMMARY.md`
- `src/orchestration/memory_manager.py`

## Verified Runtime Flags (current environment)
- `VETKA_JSON_CONTEXT_COMPRESSED=True`
- `VETKA_JSON_CONTEXT_LEGEND_MODE=auto`
- `VETKA_JSON_CONTEXT_INCLUDE_DEPS=True`
- `VETKA_JSON_CONTEXT_INCLUDE_SEMANTIC=True`

Command used:
```bash
./.venv/bin/python -c "from src.api.handlers import message_utils as m; print(m.VETKA_JSON_CONTEXT_COMPRESSED, m.VETKA_JSON_CONTEXT_LEGEND_MODE, m.VETKA_JSON_CONTEXT_INCLUDE_DEPS, m.VETKA_JSON_CONTEXT_INCLUDE_SEMANTIC)"
```

---

## Path A: Direct Chat Path (most frequent in VETKA UI)

### A1. Message -> Context assembly
In `user_message_handler`, standard direct flow builds prompt context via:
- `build_pinned_context(...)` (`src/api/handlers/user_message_handler.py:1012`)
- `build_viewport_summary(...)` (`src/api/handlers/user_message_handler.py:1019`)
- `build_json_context(...)` (`src/api/handlers/user_message_handler.py:1028`)
- `build_model_prompt(...)` (`src/api/handlers/user_message_handler.py:1054`)

### A2. ELISION participation in Path A
ELISION is active in JSON context builder by default:
- env-backed default: `VETKA_JSON_CONTEXT_COMPRESSED` (`src/api/handlers/message_utils.py:122-124`)
- compression gate in builder signature: `compressed=VETKA_JSON_CONTEXT_COMPRESSED` (`src/api/handlers/message_utils.py:1242`)
- actual ELISION transform call: `_compress_json_context(...)` (`src/api/handlers/message_utils.py:1422-1424`)
- minified output path when compressed: (`src/api/handlers/message_utils.py:1440-1443`)

Conclusion for Path A:
- ELISION **is** participating in `json_context` creation.
- `json_context` is injected into final prompt (`src/api/handlers/chat_handler.py:155-163`).

### A3. CAM/MGC participation in Path A
`build_pinned_context` uses unified ranking with CAM/MGC weights:
- weighting docstring includes CAM/MGC (`src/api/handlers/message_utils.py:725-732`)
- CAM contribution is in relevance pipeline (via unified ranking path)
- MGC scoring path exists and was recently fixed to sync-safe Gen0 read:
  - `_batch_get_mgc_scores` (`src/api/handlers/message_utils.py:538`)
  - no async `cache.get` call in sync path (`src/api/handlers/message_utils.py:554-557`)

### A4. Provider call in Path A
Direct provider route uses:
- `call_model_v2(...)` non-stream (`src/api/handlers/user_message_handler.py:1086`)
- `call_model_v2_stream(...)` stream (`src/api/handlers/user_message_handler.py:1433`)
- adaptive completion budget is enforced in both:
  - non-stream (`src/elisya/provider_registry.py:1610-1614`)
  - stream (`src/elisya/provider_registry.py:1813-1817`)

---

## Path B: Orchestrator Agent Path (single-agent/pipeline style)

### B1. Entry
`OrchestratorWithElisya.call_agent(...)`:
- function entry (`src/orchestration/orchestrator_with_elisya.py:2336`)

### B2. ARC participation
ARC gap detection runs before agent call when context is present:
- detect call (`src/orchestration/orchestrator_with_elisya.py:2398-2403`)
- prompt injection on hit (`src/orchestration/orchestrator_with_elisya.py:2405-2407`)

### B3. ELISION participation
In `_run_agent_with_elisya_async`, large prompts are ELISION-compressed:
- gate `len(prompt) > 5000` (`src/orchestration/orchestrator_with_elisya.py:1298`)
- compressor call `compress(..., level=2)` (`src/orchestration/orchestrator_with_elisya.py:1302-1304`)
- compressed prompt passed to LLM loop (`src/orchestration/orchestrator_with_elisya.py:1341-1343`)

### B4. CAM/Memory service participation
Orchestrator initialization includes central services:
- Memory service and memory manager binding (`src/orchestration/orchestrator_with_elisya.py`, init section)
- CAM integration service (`src/orchestration/orchestrator_with_elisya.py`, init section)

---

## MemoryManager Centralization Check

`MemoryManager` remains active triple-write core (`src/orchestration/memory_manager.py`):
- Qdrant + Weaviate + changelog design preserved
- graceful degradation behavior preserved
- Qdrant init via HTTP URL client path preserved

Important architectural note:
- In **direct chat path (Path A)**, the call does not pass through `orchestrator.call_agent`.
- Therefore ARC gap detection and orchestrator-level ELISION compression are **not guaranteed** on every direct message.
- CAM/MGC still participate through `message_utils` context ranking in Path A.

---

## Findings (Audit Outcome)

1. ELISION is not missing globally.
- It is active in `build_json_context` (Path A) and orchestrator prompt compression (Path B).

2. Perceived "ELISION not working" can come from path mismatch.
- If user flow stays in direct model route, only JSON-context ELISION applies.
- Orchestrator-level full-prompt ELISION and ARC are path-dependent.

3. CAM/MGC are present in direct path through context ranking.
- This keeps memory influence in standard VETKA requests even without full orchestrator route.

4. `MemoryManager` is central in orchestration/services layer, but not every UI message traverses all memory subsystems equally.

---

## Risk Notes

- `build_pinned_context` metadata currently includes `compression: elision` (`src/api/handlers/message_utils.py:862`) while the pinned XML body itself is primarily ranking + truncation, not ELISION-key/path compression. This can confuse diagnostics.
- Multiple routes to provider call can create expectation mismatch ("same memory stack always"), while actual stack differs by path.

---

## Marker Verdict

- `MARKER_157_AUDIT_ELISION_ACTIVE_PATH_A`: PASS
- `MARKER_157_AUDIT_ELISION_ACTIVE_PATH_B`: PASS
- `MARKER_157_AUDIT_CAM_MGC_DIRECT_PATH`: PASS
- `MARKER_157_AUDIT_ARC_ALWAYS_ON`: FAIL (path-dependent)
- `MARKER_157_AUDIT_MEMORY_MANAGER_CENTRAL`: PASS (service layer), PARTIAL (not uniform per UI route)

