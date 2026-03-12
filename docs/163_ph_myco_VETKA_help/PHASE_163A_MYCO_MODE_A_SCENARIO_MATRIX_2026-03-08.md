MARKER_163A.MYCO.MODE_A.SCENARIO_MATRIX.V1
LAYER: L2
DOMAIN: UI|CHAT|TOOLS
STATUS: PLANNED
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08.md
LAST_VERIFIED: 2026-03-08

# PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08

## Synopsis
Scenario matrix for deterministic hints in VETKA main surface. Each row states what the user sees, what is actually actionable, what Mode A should say, what shortcuts are relevant, when the hint changes, and when it must stay silent.

## Table of Contents
1. Core surfaces
2. Transition rules
3. Silence cases
4. Cross-links
5. Status matrix

## Treatment
This matrix is for implementation and testing. Every scenario is intentionally tied to currently available UI behavior, not speculative features.

## Short Narrative
Mode A should not explain the whole product on every click. It should react to the active surface with one constrained payload: identify the surface, expose real actions, suggest one to three next steps, and stop until the state changes.

## Full Spec
| Scenario ID | User sees | Real actions available | Deterministic hint | Shortcut hints | State transition that changes hint | When MYCO stays silent | Evidence |
|---|---|---|---|---|---|---|---|
| S-A01 | Main tree, nothing selected | select node, search, open chat | "Выбери ноду или начни поиск: без фокуса подсказка будет общей." | `G` grab mode | node selected; search focused; chat opened | while typing in search | `client/src/App.tsx:458`; `client/src/App.tsx:1084` |
| S-A02 | Tree with selected node | open chat, pin file, focus camera, open artifact if file node | "Сейчас в фокусе нода. Следующий шаг: открыть чат, закрепить файл или открыть артефакт." | `G`, `Esc` | selection cleared; artifact opened; chat opened | repeated clicks on same selected node | `client/src/App.tsx:280`; `client/src/store/useStore.ts:174` |
| S-A03 | Chat panel open | send message, open history, open model directory, voice trigger | "Это чатовая поверхность. Можешь написать, открыть history, выбрать модель или включить voice." | voice trigger button | leftPanel changes; chat closes | while input has text | `client/src/App.tsx:1039`; `client/src/components/chat/ChatPanel.tsx:2398` |
| S-A04 | Chat history panel (`leftPanel=history`) | choose existing chat, close panel | "Это история чатов. Выбери ветку, чтобы вернуть контекст, или закрой панель." | none | chat selected; panel closed | while pointer stays inside same panel with no selection change | `client/src/components/chat/ChatPanel.tsx:2398` |
| S-A05 | Model directory (`leftPanel=models`) | choose model, add to group in group mode, close panel | "Это phonebook моделей. Выбор модели меняет реальный маршрут ответа." | none | model selected; panel closed | while user is filtering the directory | `client/src/components/chat/ChatPanel.tsx:2407`; `client/src/components/ModelDirectory.tsx:2` |
| S-A06 | Unified search open, empty query, `vetka/` | type query, switch context, switch mode | "Поиск пуст. Сначала выбери источник `vetka/web/file`, потом введи запрос." | context prefix patterns | query becomes non-empty; context changes | while user types | `client/src/components/search/UnifiedSearchBar.tsx:250`; `client/src/components/search/UnifiedSearchBar.tsx:290` |
| S-A07 | Unified search with `web/` | internet search, open live web window, preview artifact | "`web/` ищет интернет. Дальше можно открыть страницу или сохранить ее в VETKA." | none | result selected; context switches | on same results list with no hover/select change | `client/src/components/search/UnifiedSearchBar.tsx:252`; `client/src/App.tsx:475` |
| S-A08 | Unified search with `file/` | local FS search, open artifact, optionally ingest external file | "`file/` ищет по локальной ФС. Если файл вне индекса, можно добавить его в VETKA." | none | external file opened; ingest starts | while query changes every keystroke | `client/src/components/search/UnifiedSearchBar.tsx:253`; `client/src/components/artifact/ArtifactWindow.tsx:140` |
| S-A09 | User clicks disabled `cloud/` or `social/` context | return to active contexts only | "Этот режим уже виден, но пока не исполняется. Используй `vetka/web/file`." | none | context returns to enabled mode | after one explanation per state key | `client/src/components/search/UnifiedSearchBar.tsx:254`; `client/src/components/search/UnifiedSearchBar.tsx:255` |
| S-A10 | Artifact window open for VETKA file | inspect, favorite, edit/play depending on file type | "Артефакт открыт. Следующий шаг: просмотреть, закрепить в избранное или вернуться в чат с этим контекстом." | `Ctrl/Cmd+S`, `Ctrl/Cmd+Z` when editor supports | artifact file changes; artifact closes | if same artifact remains open and no new action occurs | `client/src/App.tsx:1050`; `client/src/components/artifact/ArtifactWindow.tsx:193` |
| S-A11 | Artifact window open for external file | add to VETKA, favorite when eligible | "Файл пока вне дерева VETKA. Можно добавить его в индекс и потом работать как с обычной нодой." | none | ingest completes; artifact closes | after dismissing same external-path hint | `client/src/components/artifact/ArtifactWindow.tsx:140`; `client/src/components/artifact/ArtifactWindow.tsx:154` |
| S-A12 | File drop to chat | chat opens, files pinned into chat flow | "Файлы отправлены в чатовый поток. Проверь, что чат открыт, и задай действие над ними." | none | pin complete; chat closes | once drop event already acknowledged | `client/src/App.tsx:765`; `client/src/App.tsx:777` |
| S-A13 | File drop to tree / browser ingest | add browser files, switch to scanner, camera fly | "Новые файлы можно индексировать и сразу перейти в scanner для контроля." | none | scanner opened; tree refreshed | while ingest is already running | `client/src/App.tsx:734`; `client/src/App.tsx:751`; `client/src/App.tsx:754` |
| S-A14 | Scanner surface becomes active | connect provider, scan, select targets | "Ты в scanner. Сначала подключи источник или выбери, что именно сканировать." | none | auth modal opens; scan starts | while long-running scan updates stream in place | `client/src/App.tsx:445`; `client/src/components/scanner/ScanPanel.tsx:1443` |
| S-A15 | Node context menu open | cleanup, mode-specific node actions | "Контекстное меню ноды открыто. Здесь точечные действия над текущим узлом." | none | menu closes; action selected | no repeated hint on mouse move inside menu | `client/src/App.tsx:905` |
| S-A16 | DevPanel open | inspect pipeline activity and dev controls | "Это dev surface. Используй его для системных действий, не для основного рабочего потока." | `Cmd/Ctrl+Shift+D` | dev panel closes | when panel remains open but no new event | `client/src/App.tsx:867`; `client/src/App.tsx:1065` |

### Silence cases
- Chat input non-empty.
- Search input focused with active typing.
- Same state key repeated.
- User dismissed hint for same state key.
- Long-running socket updates with no surface change.

## Cross-links
See also:
- [PHASE_163A_MYCO_MODE_A_RECON_REPORT_2026-03-08](./PHASE_163A_MYCO_MODE_A_RECON_REPORT_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_ARCHITECTURE_PROPOSAL_2026-03-08](./PHASE_163A_MYCO_MODE_A_ARCHITECTURE_PROPOSAL_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_TEST_STRATEGY_2026-03-08](./PHASE_163A_MYCO_MODE_A_TEST_STRATEGY_2026-03-08.md)
- [MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [MYCO_VETKA_BUTTON_HINT_CATALOG_V1](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)

## Status matrix
| Scenario band | Status | Evidence |
|---|---|---|
| Tree/search/chat/artifact core scenarios | Planned for Mode A, grounded in existing UI | rows `S-A01` to `S-A11` |
| Drop/scanner/dev/context-menu scenarios | Planned for Mode A, grounded in existing UI | rows `S-A12` to `S-A16` |
| Disabled/future contexts | Documented as explicit fallback behavior | row `S-A09` |
