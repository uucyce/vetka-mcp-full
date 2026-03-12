# PHASE 164 — P1 Implementation Report (2026-03-08)

Status: completed  
Scope: shared role-aware instruction core + architect/myco bind

## Marker Lock
1. `MARKER_164.P1.SHARED_ROLE_AWARE_INSTRUCTION_CORE.V1`
2. `MARKER_164.P1.PROJECT_ARCH_GUIDANCE_BIND.V1`
3. `MARKER_164.P1.TASK_ARCH_GUIDANCE_BIND.V1`
4. `MARKER_164.P1.CONTEXT_TOOLS_HINT_INJECTION.V1`

## Implemented
1. Added shared instruction core in backend quick chat route:
- `_normalize_guidance_context(context)`
- `_resolve_architect_guidance_scope(normalized)`
- `_build_role_aware_instruction_packet(role, context)`
- `_build_architect_quick_system_prompt(context)`

File:
- [chat_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/chat_routes.py)

2. Bound shared core to MYCO quick replies:
- MYCO reply now consumes packet-generated `next_actions` and `tools` hints.

3. Bound shared core to Architect quick path:
- `ChatRequest.system_prompt` now injects role-aware prompt with project/task scope and context-tools hints.

## Tests
- Added:
  - [test_phase164_p1_role_aware_instruction_core.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/test_phase164_p1_role_aware_instruction_core.py)

## Verification target
- `pytest -q tests/test_phase164_p1_role_aware_instruction_core.py`
- `pytest -q tests/test_phase162_p1_myco_helper_contract.py`

