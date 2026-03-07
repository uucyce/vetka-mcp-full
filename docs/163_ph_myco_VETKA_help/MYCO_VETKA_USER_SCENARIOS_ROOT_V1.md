MARKER_163.MYCO.VETKA.USER_SCENARIOS_ROOT.V1
LAYER: L2
DOMAIN: UI|CHAT|AGENTS|VOICE|TOOLS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md
LAST_VERIFIED: 2026-03-07

# MYCO VETKA User Scenarios Root (V1)

## Synopsis
Scenario tree for MYCO adaptation from MCC to VETKA: what user sees, what user can do, and which proactive hint should appear next.

## Table of Contents
1. L0-L3 scenario hierarchy
2. Scenario contracts
3. Edge cases and failure prompts
4. Cross-links
5. Status matrix

## Treatment
Each scenario includes observed UI state, user intent, backend path, and MYCO next-step hint.

## Short Narrative
New user opens VETKA, selects node, starts chat, mentions agent, runs workflow. MYCO should narrate possible actions before confusion starts.

## Full Spec
### L0: What I see / what I can do
- L0.1 Canvas + tree nodes (`TAG:UI.VETKA.WORKSPACE.CANVAS`)
- L0.2 Chat panel and input (`TAG:UI.VETKA.WORKSPACE.CHAT`)
- L0.3 Artifact panel + search (`TAG:UI.VETKA.WORKSPACE.CANVAS`)
- L0.4 Standalone windows (`mycelium`, `web-shell`, `artifact-window`, `artifact-media`) (`TAG:UI.ROUTE.WINDOW.MAP`)

### L1: Workspaces
- L1.1 Tree workspace in VETKA main App (`client/src/main.tsx:40`).
- L1.2 MCC helper workspace with top MYCO hint (`client/src/components/mcc/MyceliumCommandCenter.tsx:3667`).
- L1.3 Standalone MYCELIUM route for command center (`client/src/main.tsx:28`).
- L1.4 Standalone Web Shell browsing/saving route (`client/src/main.tsx:31`, `client/src/WebShellStandalone.tsx:543`).
- L1.5 Detached artifact/media windows (`client/src/main.tsx:37`, `client/src/main.tsx:34`).

### L2: Concrete actions
- L2.1 Ask MYCO in quick chat with `?` or `/myco` (`client/src/components/mcc/MiniChat.tsx:41`).
- L2.2 Send helper mode role to backend (`client/src/components/mcc/MiniChat.tsx:295`).
- L2.3 Backend switches to quick helper branch (`src/api/routes/chat_routes.py:409`).
- L2.4 Retrieval includes state-rich context (`src/api/routes/chat_routes.py:435`).
- L2.5 Helper response returns role `helper_myco` (`src/api/routes/chat_routes.py:479`).
- L2.6 Open phonebook (`ModelDirectory`) and pick model/source (`client/src/components/chat/ChatPanel.tsx:2407`, `client/src/components/ModelDirectory.tsx:208`).
- L2.7 Set preferred API key or auto-select key (`client/src/components/mcc/KeyDropdown.tsx:180`, `client/src/components/mcc/KeyDropdown.tsx:199`).
- L2.8 Switch unified search context between `vetka/`, `web/`, `file/` (`client/src/components/search/UnifiedSearchBar.tsx:251`).
- L2.9 Run web/internet search in `web/` context (`client/src/components/search/UnifiedSearchBar.tsx:252`, `src/api/routes/unified_search_routes.py:129`, `src/api/handlers/web_search_handler.py:43`).
- L2.10 Run filesystem search outside VETKA index in `file/` context (`client/src/components/search/UnifiedSearchBar.tsx:253`, `src/search/file_search_service.py:118`).
- L2.11 If user wants, ingest найденный path into VETKA scanner (`client/src/App.tsx:619`, `client/src/App.tsx:630`, `src/api/routes/watcher_routes.py:95`).
- L2.12 Open key dropdown and set preferred key vs auto-select (`client/src/components/mcc/KeyDropdown.tsx:162`, `client/src/components/mcc/KeyDropdown.tsx:196`).
- L2.13 Star key/model/file for fast routing (`client/src/store/useStore.ts:214`, `src/api/routes/tree_routes.py:1490`).
- L2.14 Open connector modal, auth provider, run cloud scan (`client/src/components/scanner/ScanPanel.tsx:1443`, `client/src/components/scanner/ScanPanel.tsx:1390`).

### L3: Edge cases / errors / MYCO prompts
- L3.1 Helper off mode should not spam guidance (`tests/test_phase162_p4_p1_myco_proactive_chat_contract.py:37`).
- L3.2 First click race on topbar activate guarded (`client/src/components/mcc/MyceliumCommandCenter.tsx:3425`).
- L3.3 Mention + group routing should not break flow (`src/api/handlers/group_message_handler.py:20`, `src/api/handlers/group_message_handler.py:83`).

### Scenario Catalog
| Scenario ID | User state | Action | Expected MYCO behavior | Status |
|---|---|---|---|---|
| SCN-VETKA-001 | User in main VETKA app | Select node and ask “what next?” | Context hint tied to selected node | Planned/Not Implemented |
| SCN-MCC-002 | User in MCC topbar | Click MYCO badge | Animated helper + top hint | Implemented |
| SCN-MCC-003 | User in mini chat | Send `?` | Role-aware immediate helper reply | Implemented |
| SCN-CHAT-004 | User sends helper context | POST `/api/chat/quick` | Quick local fastpath reply | Implemented |
| SCN-GROUP-005 | User uses @mention in group | Mention agent/model | Direct routing or hostess path | Implemented |
| SCN-PHONEBOOK-006 | User opens model directory | Choose model/source | Next messages route with selected model/source | Implemented |
| SCN-KEY-007 | User chooses key | Set provider/key mask | Dispatch uses selected_key instead of auto | Implemented |
| SCN-SEARCH-008 | User picks `web/` | Search internet | Unified/web results with provider health checks | Implemented |
| SCN-SEARCH-009 | User picks `file/` | Search local FS | Finds files beyond VETKA indexed tree | Implemented |
| SCN-SCAN-010 | User confirms ingest | Add/index folder/file | VETKA scanner + watcher events update graph | Implemented |
| SCN-KEY-011 | User opens key dropdown | Auto or explicit key select | Dispatch path includes selected key | Implemented |
| SCN-FAV-012 | User stars key/model/file | Persist favorites | Faster recurring routing and context restore | Implemented |
| SCN-WEB-013 | User opens web-shell | Browse and save webpage | Save modal writes artifact to VETKA path | Implemented |
| SCN-CONN-014 | User opens connector auth modal | OAuth/API key connect then scan | External source indexed into VETKA | Implemented |

## Cross-links
See also:
- [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [Architecture](./MYCO_VETKA_INFORMATION_ARCHITECTURE_V1.md)
- [UI-Capability Matrix](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [Chat and Agents](./MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1.md)
- [Hint Library](./MYCO_VETKA_HELP_HINT_LIBRARY_V1.md)
- [Gap Registry](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [Windows and Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [Controls and Buttons Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [Search Phonebook Keys Guide](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)

## Status matrix
| Layer | Implemented | Partially Implemented | Planned/Not Implemented |
|---|---|---|---|
| L0 | MCC visibility and helper cues | VETKA visibility without MYCO overlays | Full MYCO cues in VETKA App |
| L1 | MCC helper workspace | Shared backend reused by both | VETKA-native MYCO UI surface |
| L2 | Quick helper flow in MCC | Some contracts reusable in main app | VETKA event mapping and proactive panel |
| L3 | Off-mode and race guards in MCC | Cross-surface error harmonization | VETKA-specific hint/fallback pack |

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
