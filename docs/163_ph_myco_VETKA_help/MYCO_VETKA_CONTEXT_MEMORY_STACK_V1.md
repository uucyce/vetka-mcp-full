MARKER_163.MYCO.VETKA.CONTEXT_MEMORY_STACK.V1
LAYER: L3
DOMAIN: MEMORY|RAG|VOICE|CHAT|TOOLS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_VETKA_CONTEXT_MEMORY_STACK_V1.md
LAST_VERIFIED: 2026-03-07

# MYCO VETKA Context and Memory Stack (V1)

## Synopsis
Stack map for ContextPacker + JEPA + ELISION + ENGRAM + STM + CAM with activation points and bottlenecks.

## Table of Contents
1. Stack layers
2. Activation timeline
3. Bottlenecks
4. Cross-links
5. Status matrix

## Treatment
This is operational stack documentation for MYCO help mode and Jarvis voice/text context path.

## Short Narrative
Context enters from UI/voice payload, is compacted and ranked by ContextPacker, enriched by memory and retrieval, then rendered as actionable helper hints.

## Full Spec
### Stack layers
- ContextPacker:
  - class and pack entry (`TAG:MEMORY.CONTEXTPACKER.JEPA.ELISION`): `src/orchestration/context_packer.py:67`, `src/orchestration/context_packer.py:296`.
- JEPA usage:
  - fallback and modality-sensitive path in packer (`src/orchestration/context_packer.py:165`, `src/orchestration/context_packer.py:337`).
- ELISION/CAM signal in Jarvis:
  - CAM advice inserted into context (`src/voice/jarvis_llm.py:733`).
  - CAM/open_chat/pinned included in system prompt build (`src/voice/jarvis_llm.py:256`, `src/voice/jarvis_llm.py:282`, `src/voice/jarvis_llm.py:292`).
- STM/open chat snapshot:
  - compact open chat context handling (`src/api/handlers/jarvis_handler.py:1144`).
- ENGRAM and hidden MYCO memory:
  - hidden retrieval and runtime persistence (`src/services/myco_memory_bridge.py:243`, `src/services/myco_memory_bridge.py:649`).

### Activation timeline
- Step 1: Client context gets compacted in handler (`src/api/handlers/jarvis_handler.py:1127`).
- Step 2: Voice/text context goes through packer (`src/voice/jarvis_llm.py:387`).
- Step 3: MYCO quick path enriches retrieval query with state fields (`src/api/routes/chat_routes.py:435`).
- Step 4: helper reply produced in local fastpath (`src/api/routes/chat_routes.py:480`).

### Bottlenecks and constraints
- Missing VETKA main-surface MYCO trigger means stack is underused outside MCC.
- State-key enrichment quality depends on context payload completeness from UI.
- Hidden memory is backend-only and intentionally invisible in UI.

### Phase evidence in docs
- Unified context recon: `docs/157_ph/MARKER_157_7_3R_FULL_RECON_UNIFIED_CONTEXT_STACK_2026-03-07.md:12`.

## Cross-links
See also:
- [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [Architecture](./MYCO_VETKA_INFORMATION_ARCHITECTURE_V1.md)
- [Chat and Agents](./MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1.md)
- [UI-Capability Matrix](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [Gap Registry](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [Windows and Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [Controls and Buttons Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [Search Phonebook Keys Guide](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)

## Status matrix
| Layer | Status | Evidence |
|---|---|---|
| ContextPacker in runtime | Implemented | `src/orchestration/context_packer.py:296` |
| Jarvis CAM/open_chat/pinned bridge | Implemented | `src/voice/jarvis_llm.py:256`; `:292` |
| MYCO hidden memory bridge | Implemented | `src/services/myco_memory_bridge.py:243` |
| VETKA-native MYCO context UI producers | Partially Implemented | MCC producers exist; main VETKA producers not mapped to MYCO |

## Global cross-links
- [MYCO_VETKA_MASTER_INDEX_V1](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [MYCO_VETKA_INFORMATION_ARCHITECTURE_V1](./MYCO_VETKA_INFORMATION_ARCHITECTURE_V1.md)
- [MYCO_VETKA_USER_SCENARIOS_ROOT_V1](./MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md)
- [MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1](./MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1.md)
- [MYCO_VETKA_CONTEXT_MEMORY_STACK_V1](./MYCO_VETKA_CONTEXT_MEMORY_STACK_V1.md)
- [MYCO_VETKA_HELP_HINT_LIBRARY_V1](./MYCO_VETKA_HELP_HINT_LIBRARY_V1.md)
- [MYCO_VETKA_GAP_AND_REMINDERS_V1](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)
- [MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)
- [MYCO_VETKA_BUTTON_HINT_CATALOG_V1](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)
- [MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1](./MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md)
- [MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1](./MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md)
- [PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07](./PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md)
