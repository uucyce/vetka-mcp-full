MARKER_163.MYCO.VETKA.INFORMATION_ARCHITECTURE.V1
LAYER: L1
DOMAIN: UI|VOICE|MEMORY|TOOLS|RAG|CHAT|AGENTS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_VETKA_INFORMATION_ARCHITECTURE_V1.md
LAST_VERIFIED: 2026-03-07

# MYCO VETKA Information Architecture (V1)

## Synopsis
VETKA architecture is already layered and MYCO-ready on backend contracts. The main gap is presentation and event wiring on VETKA main workspace (not MCC).

## Table of Contents
1. Product map
2. Domain architecture
3. Data and event flows
4. Dependency graph
5. Cross-links
6. Status matrix

## Treatment
This document links product domains into an adaptation graph: UI signals -> context payload -> MYCO retrieval -> helper response -> proactive hints.

## Short Narrative
VETKA is tree-mind + chat-mind + visual-mind. MYCO should listen to what user sees and clicks, then emit contextual hints. MCC already demonstrates this loop. VETKA needs same loop on main surface.

## Full Spec
### Product Map
- Core product frame: VETKA workspace and MYCELIUM side-surface (`README.md:3`, `README.md:14`).
- UI architecture section already documented in docs root (`docs/README.md:74`).

### Domain Architecture
- UI domain:
  - Main VETKA app entry: `client/src/main.tsx:40`.
  - MCC standalone route: `client/src/main.tsx:28`.
  - MCC helper state store: `client/src/store/useMCCStore.ts:152`.
  - Phonebook/model directory surface: `client/src/components/ModelDirectory.tsx:2`.
  - Key selector surface: `client/src/components/mcc/KeyDropdown.tsx:24`.
- Chat domain:
  - Quick MYCO path with role/mode trigger: `src/api/routes/chat_routes.py:409`.
- Memory/RAG domain:
  - hidden retrieval and payload build: `src/services/myco_memory_bridge.py:243`, `src/services/myco_memory_bridge.py:598`.
- Voice/context domain:
  - context packing bridge: `src/voice/jarvis_llm.py:387`, `src/orchestration/context_packer.py:296`.
- Agents domain:
  - mentions/direct routing: `src/api/handlers/mention/mention_handler.py:112`.
  - group dispatch and MCP mentions: `src/api/handlers/group_message_handler.py:83`.
- Search domain:
  - Contexted unified search (`vetka/web/file`) UI: `client/src/components/search/UnifiedSearchBar.tsx:251`.
  - Unified/file backend routes: `src/api/routes/unified_search_routes.py:129`, `src/api/routes/unified_search_routes.py:148`.
  - File search outside indexed tree policy: `src/search/file_search_service.py:118`.
  - Optional scan ingest after discovery: `src/api/routes/watcher_routes.py:95`, `client/src/App.tsx:619`.

### Event and Data Flow
- UI event capture:
  - MCC emits `mcc-myco-reply` and `mcc-myco-activate` (`client/src/components/mcc/MiniChat.tsx:45`, `client/src/components/mcc/MyceliumCommandCenter.tsx:3427`).
- Request contract:
  - chat quick sends `role: helper_myco` and context drill fields (`client/src/components/mcc/MiniChat.tsx:295`, `client/src/components/mcc/MiniChat.tsx:298`).
- Backend contract:
  - `is_myco` decision and hidden retrieval in `/chat/quick` (`src/api/routes/chat_routes.py:409`, `src/api/routes/chat_routes.py:435`).
- Response contract:
  - helper role and mode response (`src/api/routes/chat_routes.py:479`, `src/api/routes/chat_routes.py:480`).

### Dependency Graph (textual DAG)
- UI Context -> `TAG:CHAT.QUICK.MYCO.FASTPATH`
- `TAG:CHAT.QUICK.MYCO.FASTPATH` -> `TAG:MEMORY.MYCO.HIDDEN.INDEX`
- `TAG:MEMORY.MYCO.HIDDEN.INDEX` -> `TAG:RAG.MYCO.STATE_KEY.ENRICHMENT`
- `TAG:VOICE.JARVIS.CONTEXT.BRIDGE` -> `TAG:MEMORY.CONTEXTPACKER.JEPA.ELISION`
- `TAG:GAP.VETKA.UI.MYCO.SURFACE` blocks full adaptation

## Cross-links
See also:
- [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [Scenarios](./MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md)
- [UI-Capability Matrix](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [Chat and Agents](./MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1.md)
- [Context and Memory](./MYCO_VETKA_CONTEXT_MEMORY_STACK_V1.md)
- [Gap Registry](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [Windows and Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [Controls and Buttons Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [Search Phonebook Keys Guide](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)

## Status matrix
| Domain | Status | Evidence |
|---|---|---|
| UI architecture for VETKA workspace | Implemented | `docs/README.md:74`; `client/src/main.tsx:40` |
| MYCO-specific UI layer in MCC | Implemented | `client/src/components/mcc/MiniChat.tsx:50` |
| MYCO in VETKA main workspace | Planned/Not Implemented | `client/src/main.tsx:40`; no MYCO markers in `client/src/App.tsx` |
| Backend quick helper + hidden retrieval | Implemented | `src/api/routes/chat_routes.py:409`; `src/services/myco_memory_bridge.py:243` |

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
- [PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07](./PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md)
