MARKER_163.MYCO.VETKA.BUTTON_HINT_CATALOG.V1
LAYER: L4
DOMAIN: UI|TOOLS|CHAT|AGENTS
STATUS: IMPLEMENTED
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md
LAST_VERIFIED: 2026-03-07

# MYCO VETKA Button Hint Catalog (V1)

## Synopsis
Полный каталог кнопок (<button>) из client/src с привязкой к файлу/строке и базовой MYCO подсказкой.

## Table of Contents
1. Generation method
2. Catalog
3. Coverage notes
4. Cross-links
5. Status matrix

## Treatment
Каталог автосгенерирован по фактическим <button> в UI-коде.

## Short Narrative
Это полный кнопочный слой для проактивных подсказок MYCO по кликам пользователя.

## Full Spec
### Generation method
- Source query: rg -n "<button" client/src --glob '*.tsx'
- Total button tags (snapshot): 336

### Catalog
| ID | File:line | Title/Context | MYCO hint (RU) | Status |
|---|---|---|---|---|
| BTN-0001 | client/src/App.tsx:1126 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0002 | client/src/App.tsx:1162 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0003 | client/src/App.tsx:1218 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0004 | client/src/App.tsx:1278 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0005 | client/src/App.tsx:1311 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0006 | client/src/App.tsx:1344 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0007 | client/src/App.tsx:1397 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0008 | client/src/App.tsx:1468 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0009 | client/src/App.tsx:1482 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0010 | client/src/App.tsx:1604 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0011 | client/src/App.tsx:1704 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0012 | client/src/App.tsx:1727 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0013 | client/src/components/activity/ActivityMonitor.tsx:161 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0014 | client/src/components/activity/ActivityMonitor.tsx:167 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0015 | client/src/components/activity/ActivityMonitor.tsx:173 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0016 | client/src/components/activity/ActivityMonitor.tsx:179 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0017 | client/src/components/activity/ActivityMonitor.tsx:185 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0018 | client/src/components/activity/ActivityMonitor.tsx:230 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0019 | client/src/components/voice/SmartVoiceInput.tsx:341 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0020 | client/src/WebShellStandalone.tsx:468 | Back | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0021 | client/src/WebShellStandalone.tsx:469 | Forward | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0022 | client/src/WebShellStandalone.tsx:535 | save to vetka | Сохранение изменит рабочее состояние. Уточни путь и формат перед подтверждением. | Implemented |
| BTN-0023 | client/src/WebShellStandalone.tsx:542 | save to vetka | Сохранение изменит рабочее состояние. Уточни путь и формат перед подтверждением. | Implemented |
| BTN-0024 | client/src/WebShellStandalone.tsx:604 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0025 | client/src/WebShellStandalone.tsx:605 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0026 | client/src/WebShellStandalone.tsx:608 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0027 | client/src/WebShellStandalone.tsx:609 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0028 | client/src/WebShellStandalone.tsx:640 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0029 | client/src/WebShellStandalone.tsx:665 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0030 | client/src/WebShellStandalone.tsx:666 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0031 | client/src/components/ModelDirectory.tsx:656 | Refresh model list | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0032 | client/src/components/ModelDirectory.tsx:678 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0033 | client/src/components/ModelDirectory.tsx:742 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0034 | client/src/components/ModelDirectory.tsx:796 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0035 | client/src/components/ModelDirectory.tsx:1066 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0036 | client/src/components/ModelDirectory.tsx:1114 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0037 | client/src/components/ModelDirectory.tsx:1239 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0038 | client/src/components/ModelDirectory.tsx:1283 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0039 | client/src/components/ModelDirectory.tsx:1367 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0040 | client/src/components/ModelDirectory.tsx:1534 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0041 | client/src/components/ModelDirectory.tsx:1560 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0042 | client/src/components/scanner/ScanPanel.tsx:1127 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0043 | client/src/components/scanner/ScanPanel.tsx:1134 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0044 | client/src/components/scanner/ScanPanel.tsx:1154 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0045 | client/src/components/scanner/ScanPanel.tsx:1226 | Select folder to scan | Запускается скан или индексация. После завершения можно закрепить важные результаты. | Implemented |
| BTN-0046 | client/src/components/scanner/ScanPanel.tsx:1248 | Add folder to scan | Запускается скан или индексация. После завершения можно закрепить важные результаты. | Implemented |
| BTN-0047 | client/src/components/scanner/ScanPanel.tsx:1289 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0048 | client/src/components/scanner/ScanPanel.tsx:1370 | Browse Google Drive tree | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0049 | client/src/components/scanner/ScanPanel.tsx:1381 | Browse Google Drive tree | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0050 | client/src/components/scanner/ScanPanel.tsx:1390 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0051 | client/src/components/scanner/ScanPanel.tsx:1406 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0052 | client/src/components/scanner/ScanPanel.tsx:1455 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0053 | client/src/components/scanner/ScanPanel.tsx:1464 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0054 | client/src/components/scanner/ScanPanel.tsx:1473 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0055 | client/src/components/scanner/ScanPanel.tsx:1516 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0056 | client/src/components/scanner/ScanPanel.tsx:1523 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0057 | client/src/components/scanner/ScanPanel.tsx:1550 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0058 | client/src/components/scanner/ScanPanel.tsx:1556 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0059 | client/src/components/mcc/PlaygroundBadge.tsx:174 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0060 | client/src/components/search/UnifiedSearchBar.tsx:896 | Voice input | Это media/voice control. Подскажу оптимальную последовательность playback шагов. | Implemented |
| BTN-0061 | client/src/components/search/UnifiedSearchBar.tsx:911 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0062 | client/src/components/search/UnifiedSearchBar.tsx:966 | Clear search | Поиск активирован. Выбери контекст vetka/web/file и режим запроса. | Implemented |
| BTN-0063 | client/src/components/search/UnifiedSearchBar.tsx:1082 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0064 | client/src/components/search/UnifiedSearchBar.tsx:1151 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0065 | client/src/components/search/UnifiedSearchBar.tsx:1208 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0066 | client/src/components/search/UnifiedSearchBar.tsx:1242 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0067 | client/src/components/search/UnifiedSearchBar.tsx:1436 | View content | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0068 | client/src/components/search/UnifiedSearchBar.tsx:1448 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0069 | client/src/components/search/UnifiedSearchBar.tsx:1475 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0070 | client/src/components/voice/VoiceButton.tsx:288 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0071 | client/src/components/voice/VoiceButton.tsx:342 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0072 | client/src/components/canvas/FileCard.tsx:1349 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0073 | client/src/components/canvas/FileCard.tsx:1520 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0074 | client/src/components/canvas/FileCard.tsx:1557 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0075 | client/src/components/ui/Panel.tsx:110 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0076 | client/src/components/mcc/RolesConfigPanel.tsx:233 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0077 | client/src/components/mcc/RolesConfigPanel.tsx:246 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0078 | client/src/components/mcc/MiniBalance.tsx:166 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0079 | client/src/components/chat/ChatSidebar.tsx:420 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0080 | client/src/components/chat/ChatSidebar.tsx:518 | Rename chat | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0081 | client/src/components/chat/ChatSidebar.tsx:528 | Rename chat | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0082 | client/src/components/chat/ChatSidebar.tsx:538 | Delete chat | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0083 | client/src/components/chat/ChatSidebar.tsx:568 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0084 | client/src/components/chat/ChatSidebar.tsx:581 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0085 | client/src/components/mcc/RailsActionBar.tsx:159 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0086 | client/src/components/chat/GroupCreatorPanel.tsx:386 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0087 | client/src/components/chat/GroupCreatorPanel.tsx:568 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0088 | client/src/components/chat/GroupCreatorPanel.tsx:596 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0089 | client/src/components/chat/GroupCreatorPanel.tsx:639 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0090 | client/src/components/chat/GroupCreatorPanel.tsx:693 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0091 | client/src/components/chat/GroupCreatorPanel.tsx:718 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0092 | client/src/components/chat/GroupCreatorPanel.tsx:824 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0093 | client/src/components/chat/GroupCreatorPanel.tsx:841 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0094 | client/src/components/mcc/MyceliumCommandCenter.tsx:3446 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0095 | client/src/components/mcc/MyceliumCommandCenter.tsx:3516 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0096 | client/src/components/mcc/MyceliumCommandCenter.tsx:3547 | Draft tab setup in progress | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0097 | client/src/components/mcc/MyceliumCommandCenter.tsx:3565 | Create and open a new project tab | Открывается новая поверхность или объект. Проверь цель и продолжим в новом контексте. | Implemented |
| BTN-0098 | client/src/components/mcc/MyceliumCommandCenter.tsx:3604 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0099 | client/src/components/mcc/MyceliumCommandCenter.tsx:3756 | Use live baseline DAG | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0100 | client/src/components/mcc/MyceliumCommandCenter.tsx:3773 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0101 | client/src/components/mcc/MyceliumCommandCenter.tsx:3788 | Set as primary DAG version | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0102 | client/src/components/mcc/MyceliumCommandCenter.tsx:3804 | Run algorithmic DAG auto-compare (3 presets) | Запускается workflow/task действие. Проверим модель, ключ и ограничения перед стартом. | Implemented |
| BTN-0103 | client/src/components/mcc/MyceliumCommandCenter.tsx:3822 | Show compare matrix | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0104 | client/src/components/mcc/MyceliumCommandCenter.tsx:3840 | Save current DAG as version | Сохранение изменит рабочее состояние. Уточни путь и формат перед подтверждением. | Implemented |
| BTN-0105 | client/src/components/mcc/MyceliumCommandCenter.tsx:3864 | Set best compare result as primary DAG version | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0106 | client/src/components/mcc/MyceliumCommandCenter.tsx:3962 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0107 | client/src/components/mcc/MyceliumCommandCenter.tsx:3978 | Set version as primary | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0108 | client/src/components/mcc/MyceliumCommandCenter.tsx:4235 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0109 | client/src/components/mcc/MyceliumCommandCenter.tsx:4353 | Toggle focus restore policy | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0110 | client/src/components/mcc/MyceliumCommandCenter.tsx:4704 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0111 | client/src/components/ui/FilePreview.tsx:171 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0112 | client/src/components/ui/FilePreview.tsx:186 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0113 | client/src/components/VoiceSettings.tsx:331 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0114 | client/src/components/mcc/FirstRunView.tsx:203 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0115 | client/src/components/mcc/FirstRunView.tsx:210 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0116 | client/src/components/mcc/FirstRunView.tsx:217 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0117 | client/src/components/mcc/FirstRunView.tsx:246 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0118 | client/src/components/mcc/FirstRunView.tsx:247 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0119 | client/src/components/mcc/FirstRunView.tsx:262 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0120 | client/src/components/mcc/FirstRunView.tsx:263 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0121 | client/src/components/mcc/FirstRunView.tsx:264 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0122 | client/src/components/mcc/HeartbeatChip.tsx:90 | Heartbeat settings | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0123 | client/src/components/mcc/HeartbeatChip.tsx:130 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0124 | client/src/components/mcc/HeartbeatChip.tsx:152 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0125 | client/src/components/mcc/HeartbeatChip.tsx:203 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0126 | client/src/components/chat/CompoundMessage.tsx:47 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0127 | client/src/components/mcc/ToastContainer.tsx:70 | Dismiss | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0128 | client/src/components/mcc/LeagueSelector.tsx:135 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0129 | client/src/components/mcc/LeagueSelector.tsx:186 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0130 | client/src/components/mcc/LeagueSelector.tsx:200 | Clone current preset as new | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0131 | client/src/components/mcc/LeagueSelector.tsx:214 | Clone current preset as new | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0132 | client/src/components/artifact/ArtifactPanel.tsx:894 | Live web page mode | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0133 | client/src/components/artifact/ArtifactPanel.tsx:909 | Markdown fallback mode | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0134 | client/src/components/artifact/ArtifactPanel.tsx:937 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0135 | client/src/components/artifact/ArtifactPanel.tsx:978 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0136 | client/src/components/artifact/ArtifactPanel.tsx:1532 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0137 | client/src/components/artifact/ArtifactPanel.tsx:1619 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0138 | client/src/components/artifact/ArtifactPanel.tsx:1671 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0139 | client/src/components/artifact/ArtifactPanel.tsx:1723 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0140 | client/src/components/mcc/NodePicker.tsx:117 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0141 | client/src/components/mcc/MiniTasks.tsx:83 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0142 | client/src/components/mcc/MiniTasks.tsx:142 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0143 | client/src/components/mcc/MiniTasks.tsx:158 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0144 | client/src/components/mcc/MiniTasks.tsx:337 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0145 | client/src/components/mcc/MiniContext.tsx:268 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0146 | client/src/components/mcc/MiniContext.tsx:290 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0147 | client/src/components/mcc/MiniContext.tsx:388 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0148 | client/src/components/mcc/MiniContext.tsx:481 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0149 | client/src/components/mcc/MiniContext.tsx:498 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0150 | client/src/components/mcc/MiniContext.tsx:542 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0151 | client/src/components/chat/MentionPopup.tsx:123 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0152 | client/src/components/chat/MentionPopup.tsx:162 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0153 | client/src/components/chat/MentionPopup.tsx:177 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0154 | client/src/components/chat/MentionPopup.tsx:221 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0155 | client/src/components/devpanel/ArtifactViewer.tsx:340 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0156 | client/src/components/devpanel/ArtifactViewer.tsx:359 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0157 | client/src/components/artifact/ArtifactWindow.tsx:194 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0158 | client/src/components/artifact/ArtifactWindow.tsx:218 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0159 | client/src/components/mcc/WizardContainer.tsx:51 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0160 | client/src/components/mcc/WizardContainer.tsx:85 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0161 | client/src/components/mcc/WizardContainer.tsx:113 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0162 | client/src/components/mcc/WizardContainer.tsx:132 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0163 | client/src/components/mcc/WizardContainer.tsx:143 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0164 | client/src/components/mcc/WizardContainer.tsx:170 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0165 | client/src/components/mcc/WizardContainer.tsx:189 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0166 | client/src/components/mcc/WizardContainer.tsx:193 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0167 | client/src/components/mcc/WizardContainer.tsx:214 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0168 | client/src/components/mcc/WizardContainer.tsx:215 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0169 | client/src/components/artifact/Toolbar.tsx:136 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0170 | client/src/components/chat/MessageInput.tsx:904 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0171 | client/src/components/mcc/SandboxDropdown.tsx:129 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0172 | client/src/components/mcc/SandboxDropdown.tsx:207 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0173 | client/src/components/mcc/SandboxDropdown.tsx:225 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0174 | client/src/components/artifact/FloatingWindow.tsx:113 | Maximize | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0175 | client/src/components/artifact/FloatingWindow.tsx:127 | Close | Действие закроет текущий поток. Сохранить состояние перед выходом? | Implemented |
| BTN-0176 | client/src/components/artifact/ArtifactViewer.tsx:174 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0177 | client/src/components/artifact/ArtifactViewer.tsx:193 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0178 | client/src/components/chat/ChatPanel.tsx:2595 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0179 | client/src/components/chat/ChatPanel.tsx:2657 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0180 | client/src/components/chat/ChatPanel.tsx:2692 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0181 | client/src/components/chat/ChatPanel.tsx:2730 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0182 | client/src/components/chat/ChatPanel.tsx:2775 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0183 | client/src/components/chat/ChatPanel.tsx:2806 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0184 | client/src/components/chat/ChatPanel.tsx:2841 | Close | Действие закроет текущий поток. Сохранить состояние перед выходом? | Implemented |
| BTN-0185 | client/src/components/chat/ChatPanel.tsx:2891 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0186 | client/src/components/chat/ChatPanel.tsx:2941 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0187 | client/src/components/chat/ChatPanel.tsx:2967 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0188 | client/src/components/chat/ChatPanel.tsx:3006 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0189 | client/src/components/chat/ChatPanel.tsx:3190 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0190 | client/src/components/chat/ChatPanel.tsx:3239 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0191 | client/src/components/chat/ChatPanel.tsx:3279 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0192 | client/src/components/chat/ChatPanel.tsx:3343 | Clear all pins | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0193 | client/src/components/chat/ChatPanel.tsx:3435 | Open artifact | Открывается новая поверхность или объект. Проверь цель и продолжим в новом контексте. | Implemented |
| BTN-0194 | client/src/components/chat/ChatPanel.tsx:3467 | Unpin | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0195 | client/src/components/chat/ChatPanel.tsx:3652 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0196 | client/src/components/chat/ChatPanel.tsx:3727 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0197 | client/src/components/chat/ChatPanel.tsx:3777 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0198 | client/src/components/chat/ChatPanel.tsx:3799 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0199 | client/src/components/mcc/OnboardingOverlay.tsx:113 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0200 | client/src/components/mcc/OnboardingOverlay.tsx:127 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0201 | client/src/components/artifact/viewers/ImageViewer.tsx:45 | Zoom In | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0202 | client/src/components/artifact/viewers/ImageViewer.tsx:48 | Zoom Out | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0203 | client/src/components/artifact/viewers/ImageViewer.tsx:51 | Reset | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0204 | client/src/components/mcc/MiniWindow.tsx:557 | Minimize | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0205 | client/src/components/mcc/MiniWindow.tsx:571 | Expand | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0206 | client/src/components/mcc/MiniWindow.tsx:687 | Minimize | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0207 | client/src/components/mcc/MiniWindow.tsx:701 | Collapse | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0208 | client/src/components/mcc/MiniWindow.tsx:715 | Close | Действие закроет текущий поток. Сохранить состояние перед выходом? | Implemented |
| BTN-0209 | client/src/components/mcc/MiniWindow.tsx:820 | Restore | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0210 | client/src/components/mcc/MiniWindow.tsx:835 | Expand | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0211 | client/src/components/mcc/FooterActionBar.tsx:136 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0212 | client/src/components/mcc/FooterActionBar.tsx:205 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0213 | client/src/components/mcc/FooterActionBar.tsx:244 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0214 | client/src/components/artifact/viewers/VideoArtifactPlayer.tsx:751 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0215 | client/src/components/artifact/viewers/VideoArtifactPlayer.tsx:809 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0216 | client/src/components/artifact/viewers/VideoArtifactPlayer.tsx:822 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0217 | client/src/components/artifact/viewers/VideoArtifactPlayer.tsx:844 | Settings | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0218 | client/src/components/artifact/viewers/VideoArtifactPlayer.tsx:861 | Fullscreen | Это media/voice control. Подскажу оптимальную последовательность playback шагов. | Implemented |
| BTN-0219 | client/src/components/mcc/RedoFeedbackInput.tsx:74 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0220 | client/src/components/mcc/RedoFeedbackInput.tsx:116 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0221 | client/src/components/mcc/TaskEditPopup.tsx:111 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0222 | client/src/components/mcc/TaskEditPopup.tsx:160 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0223 | client/src/components/mcc/TaskEditPopup.tsx:188 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0224 | client/src/components/mcc/TaskEditPopup.tsx:211 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0225 | client/src/components/mcc/TaskEditPopup.tsx:227 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0226 | client/src/components/mcc/MCCDetailPanel.tsx:119 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0227 | client/src/components/mcc/MCCDetailPanel.tsx:122 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0228 | client/src/components/panels/TaskFilterBar.tsx:136 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0229 | client/src/components/chat/MessageBubble.tsx:491 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0230 | client/src/components/chat/MessageBubble.tsx:612 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0231 | client/src/components/chat/MessageBubble.tsx:629 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0232 | client/src/components/chat/MessageBubble.tsx:712 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0233 | client/src/components/chat/MessageBubble.tsx:836 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0234 | client/src/components/chat/MessageBubble.tsx:873 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0235 | client/src/components/chat/MessageBubble.tsx:909 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0236 | client/src/components/chat/MessageBubble.tsx:999 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0237 | client/src/components/chat/MessageBubble.tsx:1023 | Add reaction | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0238 | client/src/components/chat/MessageBubble.tsx:1043 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0239 | client/src/components/chat/MessageBubble.tsx:1083 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0240 | client/src/components/mcc/KeyDropdown.tsx:114 | API key selector for dispatch | Это шаг авторизации или выбора ключа. Проверь провайдера и режим выбора. | Implemented |
| BTN-0241 | client/src/components/mcc/KeyDropdown.tsx:162 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0242 | client/src/components/mcc/KeyDropdown.tsx:196 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0243 | client/src/components/mcc/KeyDropdown.tsx:251 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0244 | client/src/components/mcc/HeartbeatToggle.tsx:37 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0245 | client/src/components/mcc/NodeStreamView.tsx:154 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0246 | client/src/components/mcc/NodeStreamView.tsx:157 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0247 | client/src/components/mcc/NodeStreamView.tsx:160 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0248 | client/src/components/panels/TaskEditor.tsx:187 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0249 | client/src/components/panels/TaskEditor.tsx:203 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0250 | client/src/components/panels/BalancesPanel.tsx:200 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0251 | client/src/components/panels/BalancesPanel.tsx:216 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0252 | client/src/components/mcc/MiniChat.tsx:364 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0253 | client/src/components/mcc/MiniChat.tsx:397 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0254 | client/src/components/mcc/MiniChat.tsx:462 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0255 | client/src/components/mcc/MiniChat.tsx:635 | Disable helper and return MYCO to top bar | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0256 | client/src/components/mcc/MiniChat.tsx:664 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0257 | client/src/components/mcc/MiniChat.tsx:800 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0258 | client/src/components/panels/DevPanel.tsx:97 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0259 | client/src/components/mcc/MCCTaskList.tsx:185 | Add to queue | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0260 | client/src/components/mcc/MCCTaskList.tsx:311 | Task drill-down | Запускается workflow/task действие. Проверим модель, ключ и ограничения перед стартом. | Implemented |
| BTN-0261 | client/src/components/mcc/MCCTaskList.tsx:333 | Edit task | Запускается workflow/task действие. Проверим модель, ключ и ограничения перед стартом. | Implemented |
| BTN-0262 | client/src/components/mcc/MCCTaskList.tsx:356 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0263 | client/src/components/mcc/MCCTaskList.tsx:365 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0264 | client/src/components/mcc/MCCTaskList.tsx:401 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0265 | client/src/components/mcc/FilterBar.tsx:103 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0266 | client/src/components/panels/PipelineStats.tsx:159 | Expand to Stats tab | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0267 | client/src/components/panels/PipelineStats.tsx:183 | Collapse back to MCC | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0268 | client/src/components/mcc/WorkflowToolbar.tsx:284 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0269 | client/src/components/mcc/WorkflowToolbar.tsx:315 | New workflow | Запускается workflow/task действие. Проверим модель, ключ и ограничения перед стартом. | Implemented |
| BTN-0270 | client/src/components/mcc/WorkflowToolbar.tsx:320 | Save workflow | Сохранение изменит рабочее состояние. Уточни путь и формат перед подтверждением. | Implemented |
| BTN-0271 | client/src/components/mcc/WorkflowToolbar.tsx:352 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0272 | client/src/components/mcc/WorkflowToolbar.tsx:372 | Load workflow | Запускается workflow/task действие. Проверим модель, ключ и ограничения перед стартом. | Implemented |
| BTN-0273 | client/src/components/mcc/WorkflowToolbar.tsx:428 | Undo (Ctrl+Z) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0274 | client/src/components/mcc/WorkflowToolbar.tsx:435 | Redo (Ctrl+Shift+Z) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0275 | client/src/components/mcc/WorkflowToolbar.tsx:447 | Validate workflow | Запускается workflow/task действие. Проверим модель, ключ и ограничения перед стартом. | Implemented |
| BTN-0276 | client/src/components/mcc/WorkflowToolbar.tsx:454 | AI: generate workflow from description | Запускается workflow/task действие. Проверим модель, ключ и ограничения перед стартом. | Implemented |
| BTN-0277 | client/src/components/mcc/WorkflowToolbar.tsx:490 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0278 | client/src/components/mcc/WorkflowToolbar.tsx:509 | Import n8n or ComfyUI workflow JSON | Запускается workflow/task действие. Проверим модель, ключ и ограничения перед стартом. | Implemented |
| BTN-0279 | client/src/components/mcc/WorkflowToolbar.tsx:519 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0280 | client/src/components/mcc/CaptainBar.tsx:114 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0281 | client/src/components/mcc/CaptainBar.tsx:133 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0282 | client/src/components/mcc/CaptainBar.tsx:152 | Dismiss | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0283 | client/src/components/mcc/PipelineResultsViewer.tsx:173 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0284 | client/src/components/mcc/PipelineResultsViewer.tsx:229 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0285 | client/src/components/mcc/PipelineResultsViewer.tsx:238 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0286 | client/src/components/mcc/PipelineResultsViewer.tsx:249 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0287 | client/src/components/mcc/PipelineResultsViewer.tsx:256 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0288 | client/src/components/mcc/PipelineResultsViewer.tsx:308 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0289 | client/src/components/mcc/PresetDropdown.tsx:89 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0290 | client/src/components/mcc/DetailPanel.tsx:524 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0291 | client/src/components/mcc/DetailPanel.tsx:734 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0292 | client/src/components/panels/ArtifactViewer.tsx:292 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0293 | client/src/components/panels/ArtifactViewer.tsx:311 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0294 | client/src/components/panels/ArtifactViewer.tsx:330 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0295 | client/src/components/panels/ArtifactViewer.tsx:489 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0296 | client/src/components/panels/ArtifactViewer.tsx:513 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0297 | client/src/components/panels/ArtifactViewer.tsx:535 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0298 | client/src/components/panels/ArtifactViewer.tsx:637 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0299 | client/src/components/panels/ArtifactViewer.tsx:814 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0300 | client/src/components/panels/ActivityLog.tsx:494 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0301 | client/src/components/panels/ActivityLog.tsx:512 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0302 | client/src/components/panels/ActivityLog.tsx:530 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0303 | client/src/components/mcc/OnboardingModal.tsx:231 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0304 | client/src/components/mcc/OnboardingModal.tsx:290 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0305 | client/src/components/mcc/OnboardingModal.tsx:306 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0306 | client/src/components/mcc/OnboardingModal.tsx:363 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0307 | client/src/components/mcc/OnboardingModal.tsx:405 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0308 | client/src/components/mcc/OnboardingModal.tsx:421 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0309 | client/src/components/mcc/OnboardingModal.tsx:472 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0310 | client/src/components/mcc/OnboardingModal.tsx:494 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0311 | client/src/components/mcc/MiniStats.tsx:392 | Open diagnostics | Открывается новая поверхность или объект. Проверь цель и продолжим в новом контексте. | Implemented |
| BTN-0312 | client/src/components/mcc/MiniStats.tsx:628 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0313 | client/src/components/panels/StatsDashboard.tsx:212 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0314 | client/src/components/panels/StatsDashboard.tsx:226 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0315 | client/src/components/panels/StatsWorkspace.tsx:64 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0316 | client/src/components/panels/StatsWorkspace.tsx:78 | Force runtime health probe (bypass short cache) | Запускается workflow/task действие. Проверим модель, ключ и ограничения перед стартом. | Implemented |
| BTN-0317 | client/src/components/panels/StatsWorkspace.tsx:171 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0318 | client/src/components/panels/StatsWorkspace.tsx:186 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0319 | client/src/components/panels/TaskDrillDown.tsx:204 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0320 | client/src/components/panels/LeagueTester.tsx:87 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0321 | client/src/components/panels/LeagueTester.tsx:178 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0322 | client/src/components/panels/RoleEditor.tsx:101 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0323 | client/src/components/panels/ArchitectChat.tsx:222 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0324 | client/src/components/panels/ArchitectChat.tsx:274 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0325 | client/src/components/panels/TaskCard.tsx:656 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0326 | client/src/components/panels/TaskCard.tsx:681 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0327 | client/src/components/panels/TaskCard.tsx:706 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0328 | client/src/components/panels/TaskCard.tsx:731 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0329 | client/src/components/panels/TaskCard.tsx:773 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0330 | client/src/components/panels/TaskCard.tsx:896 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0331 | client/src/components/panels/TaskCard.tsx:914 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0332 | client/src/components/panels/TaskCard.tsx:936 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0333 | client/src/components/panels/TaskCard.tsx:953 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0334 | client/src/components/panels/TaskCard.tsx:1030 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0335 | client/src/components/panels/TaskCard.tsx:1046 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |
| BTN-0336 | client/src/components/panels/TaskCard.tsx:1062 | (no title; contextual action in component) | Кнопка выполняет локальное действие этой панели; при необходимости поясню следующий шаг. | Implemented |

### Coverage notes
- Catalog includes all <button> tags in client/src.
- Non-button clickable controls are still tracked separately in raw control index.

## Cross-links
See also:
- [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [Controls and Buttons Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [Long-tail Surfaces Scenarios](./MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md)
- [Cloud Social Search Contract](./MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md)
- [Strict Coverage Audit](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)
- [Help Hint Library](./MYCO_VETKA_HELP_HINT_LIBRARY_V1.md)

## Status matrix
| Scope | Status | Evidence |
|---|---|---|
| <button> catalog coverage | Implemented | this file |
| Non-button click catalog coverage | Partially Implemented | `UI_CONTROL_INDEX_RAW_2026-03-07.txt` |

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
