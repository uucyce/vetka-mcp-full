MARKER_163.MYCO.VETKA.MASTER_INDEX.V1
LAYER: L0
DOMAIN: UI|VOICE|MEMORY|TOOLS|RAG|CHAT|AGENTS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_VETKA_MASTER_INDEX_V1.md
LAST_VERIFIED: 2026-03-08

# MYCO for VETKA Master Index (V1)

## Synopsis
MYCO moved from MCC-only helper to a VETKA-wide proactive guide target. This index is the entry map for adaptation: what already works (mostly in MCC + backend fastpath), what is reusable in VETKA, and what still needs UI integration in main VETKA surface.

## Table of Contents
1. L0-L4 map
2. Deliverables tree
3. Canonical TAG dictionary
4. Verification map (docs -> code -> UI -> tests)
5. Cross-links
6. Status matrix

## Treatment
L0 gives navigation and glossary. L1/L2 documents explain capabilities and scenarios. L3 adds edge cases, proactive hints, and gaps. L4 keeps traceability: file:line evidence and implementation status.

## Short Narrative
User opens VETKA main app, sees tree/chat/artifact/search. MYCO should read current focus and suggest next best step. Today this behavior is mature in MCC; backend contracts exist. Adaptation is mostly a surface integration and contract reuse task for VETKA UI.

## Full Spec
### Level Map (L0-L4)
- L0: Product entry and mental model.
- L1: Capability domains (UI, chat, agents, voice, memory, tools, RAG).
- L2: User actions and event contracts.
- L3: Edge cases, proactive hints, fallbacks.
- L4: Evidence, tests, status matrices.

### Deliverables Tree
- `MYCO_VETKA_MASTER_INDEX_V1.md` (this file)
- `MYCO_CORE_SCENARIO_ARCHITECTURE_V1.md`
- `MYCO_VETKA_INFORMATION_ARCHITECTURE_V1.md`
- `MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md`
- `MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md`
- `MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1.md`
- `MYCO_VETKA_CONTEXT_MEMORY_STACK_V1.md`
- `MYCO_VETKA_HELP_HINT_LIBRARY_V1.md`
- `MYCO_VETKA_GAP_AND_REMINDERS_V1.md`
- `MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md`
- `MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md`
- `MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md`
- `MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md`
- `MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md`
- `MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md`
- `MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md`
- `PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md`
- `PHASE_163A_MYCO_MODE_A_RECON_REPORT_2026-03-08.md`
- `PHASE_163A_MYCO_MODE_A_ARCHITECTURE_PROPOSAL_2026-03-08.md`
- `PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08.md`
- `PHASE_163A_MYCO_MODE_A_NARROW_MVP_CUT_2026-03-08.md`
- `PHASE_163A_MYCO_MODE_A_TEST_STRATEGY_2026-03-08.md`
- `PHASE_163A_MYCO_MODE_A_IMPLEMENTATION_PLAN_2026-03-08.md`
- `PHASE_163A_MYCO_MODE_A_VERIFY_REPORT_2026-03-08.md`
- `PHASE_163B_MYCO_VOICE_RUNTIME_SHORT_REPORT_2026-03-08.md`
- `PHASE_163B1_MYCO_PERSONA_VOICE_BASELINE_REPORT_2026-03-08.md`

### Canonical TAG Dictionary
- `TAG:UI.VETKA.ROOT.ROUTER` main app router entry.
- `TAG:UI.MCC.MYCO.MODE` helper mode state in MCC.
- `TAG:UI.MCC.MYCO.TOP_HINT` top proactive hint bubble.
- `TAG:UI.MCC.MYCO.MINICHAT` helper behavior in compact/expanded chat.
- `TAG:UI.VETKA.WORKSPACE.CANVAS` tree/canvas interaction in main VETKA.
- `TAG:UI.VETKA.WORKSPACE.CHAT` chat panel interaction in main VETKA.
- `TAG:UI.MODEL_DIRECTORY.PHONEBOOK` model phonebook surface.
- `TAG:UI.KEY.SELECTOR.PREFERRED` preferred API key selection flow.
- `TAG:UI.FAVORITES.KEY_MODEL` favorites for key/model routing.
- `TAG:SEARCH.UNIFIED.CONTEXT.SWITCH` `vetka/web/file` context switching.
- `TAG:SEARCH.UNIFIED.MODE.HYB_SEM_KEY_FILE` search mode behavior matrix.
- `TAG:SEARCH.FILE.EXTERNAL_ROOTS` file search outside indexed VETKA tree.
- `TAG:SCAN.INGEST.USER_CONFIRM` optional user-driven ingest into watcher/scanner.
- `TAG:UI.ROUTE.WINDOW.MAP` route-level windows inventory.
- `TAG:UI.TAURI.WINDOW.MAP` native window command inventory.
- `TAG:UI.PANEL.HALF_WINDOW.MAP` embedded panel/half-window inventory.
- `TAG:UI.CONTROL.BUTTON.ATLAS` control/button interaction map.
- `TAG:UI.CONTROL.BUTTON.CATALOG` full button-level hint catalog.
- `TAG:UI.SURFACE.LONG_TAIL.SCENARIO` long-tail surface scenario contracts.
- `TAG:SEARCH.UNIFIED.SINGLE_WINDOW` unified search one-window operating model.
- `TAG:SEARCH.CLOUD.UNAVAILABLE.REDIRECT` cloud mode fallback message.
- `TAG:SEARCH.SOCIAL.UNAVAILABLE.REDIRECT` social mode fallback message.
- `TAG:UI.FAVORITES.KEY_MODEL_FILE` favorites for keys/models/files.
- `TAG:CHAT.QUICK.MYCO.FASTPATH` `/api/chat/quick` MYCO branch.
- `TAG:CHAT.SOLO.SEND` solo message send path.
- `TAG:CHAT.GROUP.MENTION.ROUTING` group mention routing.
- `TAG:AGENT.MENTION.DIRECT_MODEL` direct model call via @mention.
- `TAG:VOICE.JARVIS.CONTEXT.BRIDGE` voice stack context bridge.
- `TAG:MEMORY.MYCO.HIDDEN.INDEX` hidden MYCO retrieval/memory index.
- `TAG:MEMORY.CONTEXTPACKER.JEPA.ELISION` unified context packer flow.
- `TAG:RAG.MYCO.STATE_KEY.ENRICHMENT` retrieval enrichment with state keys.
- `TAG:MYCO.HELP.PROACTIVE.NEXT_STEP` proactive “next best step” hints.
- `TAG:MYCO.CORE.SCENARIO_AUTHORING` canonical authoring method for MYCO-core scenarios.
- `TAG:GAP.VETKA.UI.MYCO.SURFACE` missing MYCO surface in main VETKA UI.

### Verification Map (Docs -> Code -> UI -> Tests)
- Product foundations: `README.md:3`, `README.md:10`, `README.md:14`, `docs/README.md:25`, `docs/README.md:74`.
- MCC MYCO UI state: `client/src/store/useMCCStore.ts:83`, `client/src/store/useMCCStore.ts:152`.
- MCC MYCO proactive UI: `client/src/components/mcc/MiniChat.tsx:50`, `client/src/components/mcc/MiniChat.tsx:295`, `client/src/components/mcc/MyceliumCommandCenter.tsx:2404`.
- MYCO backend fastpath: `src/api/routes/chat_routes.py:409`, `src/api/routes/chat_routes.py:435`, `src/api/routes/chat_routes.py:479`.
- MYCO hidden memory: `src/services/myco_memory_bridge.py:243`, `src/services/myco_memory_bridge.py:598`, `src/services/myco_memory_bridge.py:649`.
- VETKA main vs MCC route split: `client/src/main.tsx:28`, `client/src/main.tsx:40`.
- Contracts/tests: `tests/test_phase162_p1_myco_helper_contract.py:14`, `tests/test_phase162_p4_p1_myco_proactive_chat_contract.py:13`, `tests/test_phase162_p4_p4_node_role_workflow_matrix_contract.py:17`.

## Cross-links
See also:
- [MYCO Core Scenario Architecture](./MYCO_CORE_SCENARIO_ARCHITECTURE_V1.md)
- [Phase 163.A Recon Report](./PHASE_163A_MYCO_MODE_A_RECON_REPORT_2026-03-08.md)
- [Phase 163.A Architecture Proposal](./PHASE_163A_MYCO_MODE_A_ARCHITECTURE_PROPOSAL_2026-03-08.md)
- [Phase 163.A Scenario Matrix](./PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08.md)
- [Phase 163.A Narrow MVP Cut](./PHASE_163A_MYCO_MODE_A_NARROW_MVP_CUT_2026-03-08.md)
- [Phase 163.A Test Strategy](./PHASE_163A_MYCO_MODE_A_TEST_STRATEGY_2026-03-08.md)
- [Phase 163.A Implementation Plan](./PHASE_163A_MYCO_MODE_A_IMPLEMENTATION_PLAN_2026-03-08.md)
- [Phase 163.A Verify Report](./PHASE_163A_MYCO_MODE_A_VERIFY_REPORT_2026-03-08.md)
- [Phase 163.B Voice Runtime Short Report](./PHASE_163B_MYCO_VOICE_RUNTIME_SHORT_REPORT_2026-03-08.md)
- [Phase 163.B1 Persona Voice Baseline Report](./PHASE_163B1_MYCO_PERSONA_VOICE_BASELINE_REPORT_2026-03-08.md)
- [Architecture](./MYCO_VETKA_INFORMATION_ARCHITECTURE_V1.md)
- [Scenarios](./MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md)
- [UI-Capability Matrix](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [Chat and Agents](./MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1.md)
- [Context and Memory](./MYCO_VETKA_CONTEXT_MEMORY_STACK_V1.md)
- [Hint Library](./MYCO_VETKA_HELP_HINT_LIBRARY_V1.md)
- [Gap Registry](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [Windows and Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [Controls and Buttons Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [Button Hint Catalog](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)
- [Long-tail Surfaces Scenarios](./MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md)
- [Search Phonebook Keys Guide](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)
- [Cloud Social Search Contract](./MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md)
- [Strict Coverage Audit](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)
- [Recon Report](./PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md)

## Status matrix
| Scope | Status | Evidence |
|---|---|---|
| MCC-level MYCO helper UX | Implemented | `client/src/components/mcc/MiniChat.tsx:50`; `client/src/components/mcc/MyceliumCommandCenter.tsx:2404` |
| Backend MYCO quick path and memory bridge | Implemented | `src/api/routes/chat_routes.py:409`; `src/services/myco_memory_bridge.py:243` |
| VETKA main UI MYCO surface | Planned/Not Implemented | `client/src/main.tsx:28`; `client/src/main.tsx:40` |
| MYCO adaptation docs for VETKA | Implemented | this phase-163 folder |

## Global cross-links
- [MYCO_VETKA_MASTER_INDEX_V1](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [MYCO_CORE_SCENARIO_ARCHITECTURE_V1](./MYCO_CORE_SCENARIO_ARCHITECTURE_V1.md)
- [MYCO_VETKA_INFORMATION_ARCHITECTURE_V1](./MYCO_VETKA_INFORMATION_ARCHITECTURE_V1.md)
- [MYCO_VETKA_USER_SCENARIOS_ROOT_V1](./MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md)
- [MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1](./MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1.md)
- [MYCO_VETKA_CONTEXT_MEMORY_STACK_V1](./MYCO_VETKA_CONTEXT_MEMORY_STACK_V1.md)
- [MYCO_VETKA_HELP_HINT_LIBRARY_V1](./MYCO_VETKA_HELP_HINT_LIBRARY_V1.md)
- [MYCO_VETKA_GAP_AND_REMINDERS_V1](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [MYCO_VETKA_BUTTON_HINT_CATALOG_V1](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)
- [MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1](./MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md)
- [MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)
- [MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1](./MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md)
- [MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)
- [PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07](./PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md)
- [PHASE_163A_MYCO_MODE_A_RECON_REPORT_2026-03-08](./PHASE_163A_MYCO_MODE_A_RECON_REPORT_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_ARCHITECTURE_PROPOSAL_2026-03-08](./PHASE_163A_MYCO_MODE_A_ARCHITECTURE_PROPOSAL_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08](./PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_NARROW_MVP_CUT_2026-03-08](./PHASE_163A_MYCO_MODE_A_NARROW_MVP_CUT_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_TEST_STRATEGY_2026-03-08](./PHASE_163A_MYCO_MODE_A_TEST_STRATEGY_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_IMPLEMENTATION_PLAN_2026-03-08](./PHASE_163A_MYCO_MODE_A_IMPLEMENTATION_PLAN_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_VERIFY_REPORT_2026-03-08](./PHASE_163A_MYCO_MODE_A_VERIFY_REPORT_2026-03-08.md)
- [PHASE_163B_MYCO_VOICE_RUNTIME_SHORT_REPORT_2026-03-08](./PHASE_163B_MYCO_VOICE_RUNTIME_SHORT_REPORT_2026-03-08.md)
