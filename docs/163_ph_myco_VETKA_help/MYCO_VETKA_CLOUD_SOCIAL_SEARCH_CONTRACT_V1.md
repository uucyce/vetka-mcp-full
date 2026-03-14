MARKER_163.MYCO.VETKA.CLOUD_SOCIAL_SEARCH_CONTRACT.V1
LAYER: L3
DOMAIN: UI|SEARCH|RAG|TOOLS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md
LAST_VERIFIED: 2026-03-07

# MYCO VETKA Cloud/Social Search Contract (V1)

## Synopsis
Контракт для режимов `cloud/` и `social/` в unified search: текущее состояние, UX-ожидания, fallback-поведение MYCO до полной реализации.

## Table of Contents
1. Runtime truth
2. UX contract before implementation
3. API readiness contract
4. MYCO proactive fallback messages
5. Cross-links
6. Status matrix

## Treatment
Документ фиксирует не только “planned”, но и обязательное поведение интерфейса и MYCO в переходный период.

## Short Narrative
`cloud/` и `social/` уже видны пользователю в едином поиске, поэтому MYCO обязан пояснять статус и направлять в рабочие альтернативы (`vetka/web/file`) без тупиков.

## Full Spec
### Runtime truth
- Contexts listed in UI with `available: false`:
  - `cloud/`: `client/src/components/search/UnifiedSearchBar.tsx:254`
  - `social/`: `client/src/components/search/UnifiedSearchBar.tsx:255`
- Fallback modes defined for these contexts (keyword only):
  - `client/src/components/search/UnifiedSearchBar.tsx:230`, `client/src/components/search/UnifiedSearchBar.tsx:231`
- Backend capabilities route currently explicit for `vetka/web/file` only:
  - `src/api/handlers/unified_search.py:266`

### UX contract before implementation
- If user selects unavailable context:
  - show explicit disabled state (already present in menu metadata),
  - MYCO emits short redirect hint to nearest working context.
- Nearest working context decision:
  - `cloud/` -> suggest scanner connectors path + `file/` fallback,
  - `social/` -> suggest `web/` for public sources + connectors roadmap note.

### API readiness contract (planned)
- Required future capabilities response shape:
  - `{success, context, supported_modes, provider_health, availability_reason}`
- Required reason codes:
  - `NOT_IMPLEMENTED`, `MISSING_PROVIDER_KEY`, `CONNECTOR_NOT_LINKED`, `POLICY_RESTRICTED`.

### MYCO proactive fallback messages
- `TAG:SEARCH.CLOUD.UNAVAILABLE.REDIRECT`
  - RU: "Cloud-поиск пока недоступен в этом релизе. Продолжим через file/ или подключим connector scan." 
  - EN: "Cloud search is not available in this release yet. Continue via file/ or run connector scan."
- `TAG:SEARCH.SOCIAL.UNAVAILABLE.REDIRECT`
  - RU: "Social-поиск пока в roadmap. Для текущей задачи используй web/ и уточни источник." 
  - EN: "Social search is roadmap-only for now. Use web/ and specify source constraints."

## Cross-links
See also:
- [Search Phonebook Keys Guide](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)
- [UI Capability Matrix](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [Gap Registry](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [Help Hint Library](./MYCO_VETKA_HELP_HINT_LIBRARY_V1.md)
- [Long-tail Surfaces Scenarios](./MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md)
- [Button Hint Catalog](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)
- [Strict Coverage Audit](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)

## Status matrix
| Scope | Status | Evidence |
|---|---|---|
| UI visibility of cloud/social contexts | Implemented | `client/src/components/search/UnifiedSearchBar.tsx:254` |
| Search execution in cloud/social contexts | Planned/Not Implemented | no runtime branch in `src/api/handlers/unified_search.py:266` |
| MYCO fallback guidance contract | Implemented | this file |

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
- [MYCO_VETKA_BUTTON_HINT_CATALOG_V1](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)
- [MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1](./MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md)
- [MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)
- [MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1](./MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md)
- [MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)
- [PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07](./PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md)
