MARKER_163.MYCO.VETKA.CONTROLS_BUTTONS_ATLAS.V1
LAYER: L3
DOMAIN: UI|TOOLS|CHAT|AGENTS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md
LAST_VERIFIED: 2026-03-07

# MYCO VETKA Controls and Buttons Atlas (V1)

## Synopsis
Каталог контролов: кнопки, контекстные действия, key controls, search controls, scan controls. Для полного покрытия приложены raw-индексы всех интерактивов.

## Table of Contents
1. Quantitative inventory
2. Core control clusters
3. Control-to-intent contracts
4. Raw exhaustive index pointers
5. Cross-links
6. Status matrix

## Treatment
MYCO должен реагировать не на “экран вообще”, а на конкретный control-intent: что пользователь кликнул и что теперь логично сделать следующим шагом.

## Short Narrative
Одни кнопки меняют поверхность (chat/artifact/mycelium), другие меняют режим (search mode/context), третьи запускают ingestion/scan, четвертые меняют routing (model/key/favorite). Это и есть “скелет” проактивных подсказок.

## Full Spec
### Quantitative inventory (snapshot 2026-03-07)
- `client/src` TSX files: `213`.
- `window/panel/modal/standalone` files: `23`.
- `<button>` tags: `336`.
- Broad interactive markers (`<button|onClick|title`): `974`.
- Front socket listeners in `useSocket`: `81`.
- `CustomEvent(...)` emits in frontend: `107`.

### Top control-heavy files
| File | `<button>` count | Evidence |
|---|---:|---|
| `client/src/components/chat/ChatPanel.tsx` | 21 | `UI_CONTROL_INDEX_RAW_2026-03-07.txt` |
| `client/src/components/scanner/ScanPanel.tsx` | 17 | `UI_CONTROL_INDEX_RAW_2026-03-07.txt` |
| `client/src/components/mcc/MyceliumCommandCenter.tsx` | 17 | `UI_CONTROL_INDEX_RAW_2026-03-07.txt` |
| `client/src/App.tsx` | 12 | `UI_CONTROL_INDEX_RAW_2026-03-07.txt` |
| `client/src/WebShellStandalone.tsx` | 11 | `UI_CONTROL_INDEX_RAW_2026-03-07.txt` |
| `client/src/components/ModelDirectory.tsx` | 11 | `UI_CONTROL_INDEX_RAW_2026-03-07.txt` |
| `client/src/components/search/UnifiedSearchBar.tsx` | 10 | `UI_CONTROL_INDEX_RAW_2026-03-07.txt` |

### Core control clusters and contracts (`TAG:UI.CONTROL.*`)
| Cluster | Example controls | User intent | Evidence | MYCO hint (RU) |
|---|---|---|---|---|
| Global top controls | `Open chat`, `View artifact`, `Mycelium Command Center` | switch workspace | `client/src/App.tsx:1126`, `client/src/App.tsx:1162`, `client/src/App.tsx:1218` | "Ты переключил рабочую поверхность; продолжим с шагом для этой панели." |
| Tree context controls | `Directed/Knowledge/Media Edit Mode`, `Clean Folder from VETKA` | mode switch / cleanup | `client/src/App.tsx:1278`, `client/src/App.tsx:1311`, `client/src/App.tsx:1344`, `client/src/App.tsx:1397` | "Режим дерева сменен. Хочешь сразу перелететь и закрепить контекст?" |
| Phonebook controls | refresh, filter, select model, add key, favorite key/model | routing by model/provider/key | `client/src/components/ModelDirectory.tsx:656`, `client/src/components/ModelDirectory.tsx:208`, `client/src/components/ModelDirectory.tsx:531` | "Выбор модели/ключа меняет маршрут ответа и бюджет." |
| Key dropdown controls | auto-select, explicit key pick, star key, view all balances | dispatch key policy | `client/src/components/mcc/KeyDropdown.tsx:162`, `client/src/components/mcc/KeyDropdown.tsx:196`, `client/src/components/mcc/KeyDropdown.tsx:251` | "Можно оставить auto или зафиксировать ключ под задачу." |
| Unified search controls | context switch `vetka/web/file`, mode switch HYB/SEM/KEY/FILE, pin/open result | retrieval strategy | `client/src/components/search/UnifiedSearchBar.tsx:251`, `client/src/components/search/UnifiedSearchBar.tsx:208` | "Смена контекста поиска меняет источники и тип ранжирования." |
| Web shell controls | back/forward, live-preview toggle, save modal steps | browse/save web context | `client/src/WebShellStandalone.tsx:468`, `client/src/WebShellStandalone.tsx:535`, `client/src/WebShellStandalone.tsx:543` | "Можно сохранить страницу прямо в VETKA c путём в текущее рабочее дерево." |
| Scanner controls | select folder/add folder, pin scanned file, connector auth/scan/disconnect | ingest and index | `client/src/components/scanner/ScanPanel.tsx:1226`, `client/src/components/scanner/ScanPanel.tsx:1289`, `client/src/components/scanner/ScanPanel.tsx:1370`, `client/src/components/scanner/ScanPanel.tsx:1390` | "Скан запускает индекс. Могу подсказать, что закрепить в контексте сразу." |
| Artifact controls | add/remove favorite, add to VETKA, media control | artifact lifecycle | `client/src/components/artifact/ArtifactWindow.tsx:194`, `client/src/components/artifact/ArtifactWindow.tsx:218`, `client/src/components/artifact/ArtifactPanel.tsx:1781` | "Артефакт можно сразу закрепить, проиндексировать или отправить в следующий шаг." |

### Raw exhaustive indices
- All controls index: `docs/163_ph_myco_VETKA_help/UI_CONTROL_INDEX_RAW_2026-03-07.txt`.
- All surface index: `docs/163_ph_myco_VETKA_help/UI_SURFACE_INDEX_RAW_2026-03-07.txt`.
- All API route index: `docs/163_ph_myco_VETKA_help/API_ROUTE_INDEX_RAW_2026-03-07.txt`.

## Cross-links
See also:
- [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [Windows/Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [UI Capability Matrix](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [Search/Phonebook Guide](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)
- [Hint Library](./MYCO_VETKA_HELP_HINT_LIBRARY_V1.md)
- [Strict Coverage Audit](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)

## Status matrix
| Scope | Status | Evidence |
|---|---|---|
| High-impact control clusters | Implemented | this file |
| Exhaustive raw control dump | Implemented | `UI_CONTROL_INDEX_RAW_2026-03-07.txt` |
| Per-control bespoke MYCO hint text (all 300+) | Planned/Not Implemented | requires generation + UX placement |
