MARKER_163.MYCO.VETKA.GAP_AND_REMINDERS.V1
LAYER: L4
DOMAIN: UI|CHAT|MEMORY|VOICE|AGENTS|RAG
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_VETKA_GAP_AND_REMINDERS_V1.md
LAST_VERIFIED: 2026-03-07

# MYCO VETKA Gap and Reminder Registry (V1)

## Synopsis
Actionable gap registry for adapting MYCO from MCC to VETKA with reminder copy for product team.

## Table of Contents
1. Gap register
2. Reminder strategy for MYCO
3. Priority order
4. Cross-links
5. Status matrix

## Treatment
Each gap has explicit status, impact, code evidence, and reminder text that MYCO should deliver gently.

## Short Narrative
The system core is ready, but user-facing adaptation in VETKA main workspace is not complete. Registry helps the team close this without losing momentum.

## Full Spec
| Gap ID | Gap | Status | Impact | Evidence | MYCO reminder (RU) | MYCO reminder (EN) | Priority |
|---|---|---|---|---|---|---|---|
| GAP-163-001 | No dedicated MYCO UI in VETKA main `App.tsx` | Planned/Not Implemented | Users in main workspace do not get proactive helper | `client/src/main.tsx:40`; `client/src/App.tsx:246` | "В основной VETKA-поверхности мне еще некуда встроиться: нужен UI-контейнер MYCO." | "I still have no native slot in main VETKA surface: a MYCO UI container is needed." | P0 |
| GAP-163-002 | MCC event names not generalized for VETKA (`mcc-myco-*`) | Partially Implemented | Reuse possible but naming leaks context | `client/src/components/mcc/MiniChat.tsx:45`; `client/src/components/mcc/MyceliumCommandCenter.tsx:3427` | "События MYCO пока завязаны на MCC-префикс; стоит вынести общий event-contract." | "MYCO events are still MCC-prefixed; extract a shared event contract." | P1 |
| GAP-163-003 | VETKA main context -> MYCO quick payload mapping absent | Planned/Not Implemented | Retrieval quality and targeted hints unavailable in main UI | `client/src/components/mcc/MiniChat.tsx:298`; no analog in `client/src/App.tsx` | "Чтобы давать точные подсказки в VETKA, передавайте drill/state поля в quick payload." | "To provide precise hints in VETKA, pass drill/state fields into quick payload." | P0 |
| GAP-163-004 | Unified hint channel (topbar/bubble) missing in VETKA main | Planned/Not Implemented | No persistent proactive visibility | `client/src/components/mcc/MyceliumCommandCenter.tsx:3667`; no analog in `client/src/App.tsx` | "Нужен постоянный канал подсказок в VETKA (top hint/badge)." | "A persistent hint channel is needed in VETKA (top hint/badge)." | P1 |
| GAP-163-005 | Tests validate MCC contracts, not VETKA adaptation contracts | Planned/Not Implemented | Regressions likely during integration | `tests/test_phase162_p1_myco_helper_contract.py:14`; `tests/test_phase162_p4_p1_myco_proactive_chat_contract.py:13` | "Добавьте phase163-тесты для VETKA surface contracts до релиза адаптации." | "Add phase163 tests for VETKA surface contracts before adaptation release." | P0 |
| GAP-163-006 | Unified search shows `cloud/` and `social/` contexts but they are disabled | Planned/Not Implemented | Users see future contexts without runnable backend in this surface | `client/src/components/search/UnifiedSearchBar.tsx:254`; `client/src/components/search/UnifiedSearchBar.tsx:255` | "Cloud/Social уже видны в едином поиске, но пока недоступны — выбирай vetka/web/file." | "Cloud/Social are visible in unified search but not active yet — use vetka/web/file." | P1 |
| GAP-163-007 | Non-button clickable controls are not fully mapped to hint contracts | Partially Implemented | MYCO may miss hints on div/span/custom-click controls | `docs/163_ph_myco_VETKA_help/MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md:380`; `docs/163_ph_myco_VETKA_help/UI_CONTROL_INDEX_RAW_2026-03-07.txt` | "Кнопки покрыты, но часть некнопочных кликов еще без отдельного hint-контракта." | "Buttons are covered, but some non-button clicks still lack dedicated hint contracts." | P2 |
| GAP-163-008 | Long-tail surfaces were previously uncovered and are now documented; runtime bind still pending | Partially Implemented | Contracts exist, but main VETKA runtime bind still limits proactive use | `docs/163_ph_myco_VETKA_help/MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md:1`; `client/src/App.tsx:246` | "Подсценарии уже описаны, следующий шаг — runtime интеграция MYCO в main VETKA." | "Sub-scenarios are documented; next step is runtime MYCO integration in main VETKA." | P1 |

### Reminder strategy
- Productive tone: factual, short, non-blocking.
- Trigger by state: first entry to VETKA, empty selection, failed quick context, helper off mode.
- Frequency guard: no duplicate reminder in same state key window.

## Cross-links
See also:
- [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [Architecture](./MYCO_VETKA_INFORMATION_ARCHITECTURE_V1.md)
- [UI-Capability Matrix](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [Hint Library](./MYCO_VETKA_HELP_HINT_LIBRARY_V1.md)
- [Recon Report](./PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md)
- [Windows and Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [Controls and Buttons Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [Search Phonebook Keys Guide](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)
- [Strict Coverage Audit](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)
- [Long-tail Surfaces Scenarios](./MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md)
- [Button Hint Catalog](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)

## Status matrix
| Priority bucket | Count |
|---|---|
| P0 | 3 |
| P1 | 4 |
| P2+ | 1 |

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
- [MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)
- [MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1](./MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md)
- [PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07](./PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md)
