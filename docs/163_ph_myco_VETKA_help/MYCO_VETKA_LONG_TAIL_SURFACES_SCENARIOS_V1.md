MARKER_163.MYCO.VETKA.LONG_TAIL_SURFACES_SCENARIOS.V1
LAYER: L3
DOMAIN: UI|CHAT|TOOLS|AGENTS|VOICE
STATUS: IMPLEMENTED
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md
LAST_VERIFIED: 2026-03-07

# MYCO VETKA Long-tail Surfaces Scenarios (V1)

## Synopsis
Контрактные подсценарии для ранее непокрытых 21 secondary surface: окна/полуокна/панели/попапы, включая вход, intent, expected MYCO guidance.

## Table of Contents
1. Coverage scope
2. Surface scenario matrix
3. MYCO response model for long-tail surfaces
4. Cross-links
5. Status matrix

## Treatment
Каждая поверхность описана как runtime-entry contract, чтобы MYCO мог реагировать на узкоспециализированные UI состояния, а не только на core path.

## Short Narrative
Main path уже описан. Этот документ закрывает “хвост”: компактные/вспомогательные панели, попапы mention/onboarding, viewer/toolbars и инженерные sub-panels, где пользователь часто теряется без прицельной подсказки.

## Full Spec
### Coverage scope
Источник: strict audit uncovered-list.
Evidence source: `docs/163_ph_myco_VETKA_help/MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md:35`.

### Surface scenario matrix
| Surface | Scenario trigger | User intent | Evidence | MYCO hint (RU) | Status |
|---|---|---|---|---|---|
| `VideoArtifactPlayer` | media artifact opened in detached/embedded mode | playback/fullscreen control | `client/src/components/artifact/viewers/VideoArtifactPlayer.tsx:59` | "Видео открыто. Могу подсказать быстрые команды playback/fullscreen и next edit step." | Implemented |
| `artifact/viewers/ArtifactViewer` | lightweight artifact view open | inspect text artifact quickly | `client/src/components/artifact/viewers/ArtifactViewer.tsx:62` | "Это быстрый просмотр артефакта; дальше можно отправить в approve/reject flow." | Implemented |
| `FloatingWindow` | floating wrapper opened | move/resize detached content | `client/src/components/artifact/FloatingWindow.tsx:25` | "Окно плавающее: можно зафиксировать его и продолжить в основном чате." | Implemented |
| `artifact/Toolbar` | artifact toolbar visible | save/approve/reject/open actions | `client/src/components/artifact/Toolbar.tsx:51` | "Toolbar активен: выбери действие над артефактом, я подскажу безопасный порядок." | Implemented |
| `artifact/ArtifactViewer` | pipeline artifact review | decision on artifact status | `client/src/components/artifact/ArtifactViewer.tsx:20` | "Проверь артефакт и заверши approve/reject, чтобы не блокировать поток." | Implemented |
| `devpanel/ArtifactViewer` | devpanel artifact tab open | approve/reject from devpanel | `client/src/components/devpanel/ArtifactViewer.tsx:15` | "Ты в dev artifact view: могу свести diff риска перед approve." | Implemented |
| `StreamPanel` | live event log expanded | monitor pipeline stream | `client/src/components/mcc/StreamPanel.tsx:17` | "Это live stream. Отмечу критичные события и следующий action." | Implemented |
| `MiniWindow` | draggable miniwindow opened | compact assistant/tools interaction | `client/src/components/mcc/MiniWindow.tsx:37` | "MiniWindow открыт: можно быстро ответить без потери основного фокуса." | Implemented |
| `WorkflowToolbar` (deprecated) | legacy surface reached | migration to active controls | `client/src/components/mcc/WorkflowToolbar.tsx:4` | "Это deprecated toolbar. Рекомендуемый путь — FooterActionBar." | Implemented |
| `OnboardingModal` | first-run project setup | initial project bootstrapping | `client/src/components/mcc/OnboardingModal.tsx:43` | "Онбординг: сначала источник проекта, затем sandbox, затем старт." | Implemented |
| `DetailPanel` | node detail panel open | inspect/edit role/model details | `client/src/components/mcc/DetailPanel.tsx:2` | "DetailPanel показывает текущую роль и модель. Могу предложить оптимизацию." | Implemented |
| `OnboardingOverlay` | guided overlay steps active | follow guided tour | `client/src/components/mcc/OnboardingOverlay.tsx:22` | "Следуй шагам оверлея, я поясню каждый шаг коротко." | Implemented |
| `TaskEditPopup` | inline task editor opened | edit task metadata quickly | `client/src/components/mcc/TaskEditPopup.tsx:39` | "Редактируй задачу точечно: заголовок, приоритет, критерий готовности." | Implemented |
| `RolesConfigPanel` | role-to-model config opened | tune role model mapping | `client/src/components/mcc/RolesConfigPanel.tsx:32` | "Настрой role→model map под тип задачи и бюджет." | Implemented |
| `MCCDetailPanel` (deprecated) | legacy detail panel reached | migration awareness | `client/src/components/mcc/MCCDetailPanel.tsx:4` | "Этот detail panel устарел; используй актуальный DetailPanel." | Implemented |
| `panels/ArchitectChat` | architect panel opened | planning/chat with architect role | `client/src/components/panels/ArchitectChat.tsx:36` | "Architect chat: сформулируй цель и ограничения, затем запусти план." | Implemented |
| `panels/BalancesPanel` | balances panel opened | key usage + budget control | `client/src/components/panels/BalancesPanel.tsx:65` | "Сначала проверь баланс ключей, затем запускай heavy pipeline." | Implemented |
| `panels/ArtifactViewer` | pipeline artifacts list opened | review staged artifacts | `client/src/components/panels/ArtifactViewer.tsx:2` | "Это staging артефактов: закрой approve/reject очередь." | Implemented |
| `ChatSidebar` | history sidebar opened | navigate/rename/favorite chats | `client/src/components/chat/ChatSidebar.tsx:42` | "История чатов: закрепи важные, чтобы быстро возвращаться к контексту." | Implemented |
| `MentionPopup` | `@` dropdown opened | precise mention target selection | `client/src/components/chat/MentionPopup.tsx:9` | "Выбери @mention адресно: это сокращает шум в ответах." | Implemented |
| `GroupCreatorPanel` | group creation/edit opened | compose team of agents/models | `client/src/components/chat/GroupCreatorPanel.tsx:39` | "Собираешь группу: проверь роли, модели и ожидаемый протокол взаимодействия." | Implemented |

### MYCO response model for long-tail surfaces
- Window-aware rule: MYCO first names current surface in one line.
- Intent-aware rule: MYCO offers 1-2 next actions only.
- Risk-aware rule: on deprecated surfaces, MYCO proposes active replacement path.

## Cross-links
See also:
- [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [Strict Coverage Audit](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)
- [Windows and Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [Controls and Buttons Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [Button Hint Catalog](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)
- [Cloud Social Search Contract](./MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md)
- [Hint Library](./MYCO_VETKA_HELP_HINT_LIBRARY_V1.md)

## Status matrix
| Scope | Status | Evidence |
|---|---|---|
| 21 long-tail surfaces scenario contracts | Implemented | this file |
| RU/EN hints for long-tail surfaces | Partially Implemented | RU provided, EN can be auto-generated next step |

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
