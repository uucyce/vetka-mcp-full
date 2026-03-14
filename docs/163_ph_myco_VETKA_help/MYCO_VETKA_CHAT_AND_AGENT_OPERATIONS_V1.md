MARKER_163.MYCO.VETKA.CHAT_AND_AGENT_OPERATIONS.V1
LAYER: L2
DOMAIN: CHAT|AGENTS|VOICE|TOOLS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1.md
LAST_VERIFIED: 2026-03-07

# MYCO VETKA Chat and Agent Operations (V1)

## Synopsis
Operational spec for solo chat, team chat, message send, @mentions, and voice/text distinctions with MYCO adaptation focus.

## Table of Contents
1. Solo chat
2. Team chat
3. Sending message
4. Agent call from "phone book" equivalent
5. @mention scenarios
6. Voice vs text
7. Cross-links
8. Status matrix

## Treatment
Document tracks factual implementation paths and names the exact adaptation points for VETKA-native MYCO.

## Short Narrative
User sends text or voice, optionally with @mention. Routing decides direct model call, hostess, or agent chain. MYCO quick helper branch exists and can be reused in VETKA.

## Full Spec
### Solo chat
- Core solo path in user handler (`TAG:CHAT.SOLO.SEND`): `src/api/handlers/user_message_handler.py:394`.
- Mention parse in solo path: `src/api/handlers/user_message_handler.py:1557`.
- MCP session init fire-and-forget on solo messages: `src/api/handlers/user_message_handler.py:918`.

### Team chat
- Group chat routing with hostess and mentions: `src/api/handlers/group_message_handler.py:20`.
- MCP external agent mentions map: `src/api/handlers/group_message_handler.py:83`.

### Sending message
- MCC MiniChat sends to quick endpoint for helper mode: `client/src/components/mcc/MiniChat.tsx:289`.
- Role injection contract: `client/src/components/mcc/MiniChat.tsx:295`.

### Phonebook (Model Directory) + API keys
- Phonebook surface is `ModelDirectory` (explicitly documented in component header): `client/src/components/ModelDirectory.tsx:2`.
- Chat panel opens this directory as left panel: `client/src/components/chat/ChatPanel.tsx:2407`.
- Directory loads unified model inventory (`/api/models/autodetect`) and status (`/api/models/status`): `client/src/components/ModelDirectory.tsx:208`, `client/src/components/ModelDirectory.tsx:256`.
- Key management drawer is built into phonebook surface: `client/src/components/ModelDirectory.tsx:4`, `client/src/components/ModelDirectory.tsx:1108`.
- Socket key ops are first-class events: `add_api_key`, `learn_key_type`, `get_key_status` (`client/src/hooks/useSocket.ts:637`, `src/api/handlers/key_handlers.py:33`, `src/api/handlers/key_handlers.py:172`).
- Favorite keys/models are supported and persisted through `/api/favorites`:
`client/src/store/useStore.ts:214`, `client/src/store/useStore.ts:314`, `src/api/routes/config_routes.py:800`, `src/api/routes/config_routes.py:811`.
- Dedicated model favorites API also exists (`/api/models/favorites`): `src/api/routes/model_routes.py:224`, `src/api/routes/model_routes.py:242`.
- Key selection for dispatch is explicit via `selectedKey` and key dropdown:
`client/src/store/useStore.ts:210`, `client/src/components/mcc/KeyDropdown.tsx:24`, `client/src/components/mcc/KeyDropdown.tsx:199`.

### What selection gives to user
- Selected model drives chat send pipeline (`model` in payload): `client/src/components/chat/MessageInput.tsx:190`.
- Selected key constrains dispatch path for MCC tasks and sends `selected_key` to backend:
`client/src/store/useMCCStore.ts:345`, `client/src/store/useMCCStore.ts:455`, `src/api/routes/task_routes.py:173`.
- Favorites reorder and speed up repeated routing choices:
`client/src/components/ModelDirectory.tsx:1065`, `client/src/components/ModelDirectory.tsx:1533`.

### Agent call from "phone book"
- Equivalent mechanism is @mention alias registry and parser (`TAG:AGENT.MENTION.DIRECT_MODEL`): `src/api/handlers/mention/mention_handler.py:88`, `src/api/handlers/mention/mention_handler.py:112`.
- In group mode, @mention can target MCP agents (`src/api/handlers/group_message_handler.py:83`).

### @mention scenarios
- Single model @mention direct route: `src/api/handlers/user_message_handler.py:1616`.
- Mention call with history context: `src/api/handlers/user_message_handler.py:1662`.
- @hostess special routing semantics: `src/api/handlers/user_message_handler.py:2408`.

### Voice vs text distinctions
- Voice response contract adaptation in solo handler: `src/api/handlers/user_message_handler.py:522`.
- Progressive voice chunks events: `src/api/handlers/user_message_handler.py:685`.
- Group voice contract stub + stream events: `src/api/handlers/group_message_handler.py:208`, `src/api/handlers/group_message_handler.py:297`.

### MYCO-specific adaptation note
- Quick helper backend works now in MCC route contract (`src/api/routes/chat_routes.py:409`).
- VETKA main chat currently has no MYCO surface trigger bindings in `App.tsx` path (`client/src/App.tsx:246`).

## Cross-links
See also:
- [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [Scenarios](./MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md)
- [UI-Capability Matrix](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [Context and Memory](./MYCO_VETKA_CONTEXT_MEMORY_STACK_V1.md)
- [Hint Library](./MYCO_VETKA_HELP_HINT_LIBRARY_V1.md)
- [Gap Registry](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [Search Phonebook Keys Guide](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)
- [Windows and Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)

## Status matrix
| Operation | Status | Evidence |
|---|---|---|
| Solo send pipeline | Implemented | `src/api/handlers/user_message_handler.py:394` |
| Group routing and mentions | Implemented | `src/api/handlers/group_message_handler.py:20`; `:83` |
| @mention direct model calls | Implemented | `src/api/handlers/mention/mention_handler.py:112` |
| MYCO helper in MCC mini chat | Implemented | `client/src/components/mcc/MiniChat.tsx:295` |
| MYCO helper trigger in VETKA main chat | Planned/Not Implemented | `client/src/App.tsx:246` |

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
