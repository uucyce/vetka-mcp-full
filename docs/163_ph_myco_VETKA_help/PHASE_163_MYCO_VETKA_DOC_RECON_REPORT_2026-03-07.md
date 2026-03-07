MARKER_163.MYCO.VETKA.DOC_RECON_REPORT.V1
LAYER: L4
DOMAIN: UI|VOICE|MEMORY|TOOLS|RAG|CHAT|AGENTS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md
LAST_VERIFIED: 2026-03-07

# Phase 163 MYCO VETKA Doc Recon Report (2026-03-07)

## Synopsis
Recon completed across required sources with explicit adaptation lens: MYCO existed in MCC and now must be adapted to VETKA main workspace.

## Table of Contents
1. Scope checked
2. Verified findings
3. Priority closures
4. Deliverables produced
5. Cross-links
6. Status matrix

## Treatment
Evidence-first report with file:line traceability and closure priorities.

## Short Narrative
VETKA already has strong core architecture and reusable helper backend. MCC proves proactive MYCO behavior. The critical next move is attaching this behavior to VETKA main surface events and UI containers.

## Full Spec
### Scope checked
- Docs: `docs/157_ph/*`, `docs/161_ph_MCC_TRM/*`, `docs/162_ph_MCC_MYCO_HELPER/*`, `docs/contracts/*`.
- Backend: `src/api/routes/chat_routes.py`, `src/api/routes/mcc_routes.py`, `src/services/myco_memory_bridge.py`, `src/orchestration/context_packer.py`, `src/voice/jarvis_llm.py`, `src/api/handlers/*`.
- Frontend: `client/src/main.tsx`, `client/src/App.tsx`, `client/src/components/mcc/*`, store/hooks.
- Tests: phase162 contracts and related chat/group flows.

### Verified findings
- MYCO helper mode/state is implemented in MCC store/UI (`client/src/store/useMCCStore.ts:152`, `client/src/components/mcc/MiniChat.tsx:295`).
- Proactive MCC top hint and role/workflow matrix are implemented (`client/src/components/mcc/MyceliumCommandCenter.tsx:2404`).
- Backend quick helper path with hidden retrieval exists (`src/api/routes/chat_routes.py:409`, `src/api/routes/chat_routes.py:435`).
- Hidden memory payload/retrieval/persist functions implemented (`src/services/myco_memory_bridge.py:243`, `:598`, `:649`).
- VETKA main app route exists separately from MCC route (`client/src/main.tsx:40` vs `client/src/main.tsx:28`).
- VETKA main app currently has no MYCO markerized helper surface (`client/src/App.tsx:246` as main entry area; no MYCO contracts).
- Route windows are explicit and enumerable (`/`, `/mycelium`, `/web-shell`, `/artifact-window`, `/artifact-media`):
`client/src/main.tsx:28`, `client/src/main.tsx:31`, `client/src/main.tsx:34`, `client/src/main.tsx:37`, `client/src/main.tsx:40`.
- Native Tauri window command layer is explicit for open/close/fullscreen/web/artifact:
`client/src-tauri/src/main.rs:55`, `client/src-tauri/src/commands.rs:103`, `client/src-tauri/src/commands.rs:195`, `client/src-tauri/src/commands.rs:260`.
- Control surface scale verified by raw inventory:
`336` button tags and `974` interactive markers in `client/src` (snapshot 2026-03-07).

### Priority closures
- P0: Bind VETKA main UI state events to MYCO quick payload contract.
- P0: Add VETKA-native MYCO widget/channel for proactive hints.
- P0: Add phase163 tests for VETKA MYCO adaptation contracts.
- P1: Normalize `mcc-myco-*` event naming into shared MYCO event namespace.
- P1: Align hint copy and locale handling across MCC and VETKA surfaces.

### Control-question coverage (2026-03-07)
- Phonebook usage and model selection are now explicitly captured with evidence:
`client/src/components/ModelDirectory.tsx:2`, `client/src/components/chat/ChatPanel.tsx:2407`.
- API key flows and status are documented with socket/backend contracts:
`client/src/hooks/useSocket.ts:637`, `src/api/handlers/key_handlers.py:33`, `src/api/handlers/key_handlers.py:172`.
- Favorite key/model persistence and impact are documented:
`client/src/store/useStore.ts:214`, `src/api/routes/config_routes.py:800`, `src/api/routes/model_routes.py:224`.
- Unified search contexts and modes are documented:
`client/src/components/search/UnifiedSearchBar.tsx:251`, `client/src/components/search/UnifiedSearchBar.tsx:178`, `src/api/routes/unified_search_routes.py:129`.
- Internet search mode is documented:
`client/src/components/search/UnifiedSearchBar.tsx:252`, `src/api/handlers/web_search_handler.py:43`.
- Filesystem search beyond current VETKA index is documented:
`client/src/components/search/UnifiedSearchBar.tsx:253`, `src/search/file_search_service.py:118`, `src/search/file_search_service.py:124`.
- Optional user-driven ingestion/scanning path after discovery is documented:
`client/src/App.tsx:619`, `client/src/App.tsx:630`, `src/api/routes/watcher_routes.py:95`.

### Strict critic re-check (2026-03-07, second pass)
- Long-tail coverage gap detected: 21 UI sub-surfaces were not contract-documented in phase-163 narrative docs.
- Formalized in strict audit doc:
`docs/163_ph_myco_VETKA_help/MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md`.
- Conclusion: core onboarding and control questions are covered; full long-tail UI coverage remains PARTIAL.

### Deliverables produced
- `MYCO_VETKA_MASTER_INDEX_V1.md`
- `MYCO_VETKA_INFORMATION_ARCHITECTURE_V1.md`
- `MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md`
- `MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md`
- `MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1.md`
- `MYCO_VETKA_CONTEXT_MEMORY_STACK_V1.md`
- `MYCO_VETKA_HELP_HINT_LIBRARY_V1.md`
- `MYCO_VETKA_GAP_AND_REMINDERS_V1.md`
- `MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md`
- `MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md`
- `MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md`
- `MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md`
- this final report
- raw inventories:
  - `UI_CONTROL_INDEX_RAW_2026-03-07.txt`
  - `UI_SURFACE_INDEX_RAW_2026-03-07.txt`
  - `API_ROUTE_INDEX_RAW_2026-03-07.txt`

## Cross-links
See also:
- [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [Architecture](./MYCO_VETKA_INFORMATION_ARCHITECTURE_V1.md)
- [Scenarios](./MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md)
- [UI-Capability Matrix](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [Chat and Agents](./MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1.md)
- [Context and Memory](./MYCO_VETKA_CONTEXT_MEMORY_STACK_V1.md)
- [Hint Library](./MYCO_VETKA_HELP_HINT_LIBRARY_V1.md)
- [Gap Registry](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [Windows and Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [Controls and Buttons Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [Search Phonebook Keys Guide](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)
- [Strict Coverage Audit](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)

## Status matrix
| Workstream | Status |
|---|---|
| Fact recon by required sources | Implemented |
| Doc corpus creation (12 files + 3 raw indices) | Implemented |
| VETKA MYCO UI adaptation in code | Planned/Not Implemented |

DAG poetry in word, TREE mind in the WORLD

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
