MARKER_163.MYCO.VETKA.UI_CAPABILITY_IMPLEMENTATION_MATRIX.V1
LAYER: L3
DOMAIN: UI|CHAT|MEMORY|TOOLS|RAG
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md
LAST_VERIFIED: 2026-03-07

# MYCO VETKA UI ↔ Capability ↔ Implementation Matrix (V1)

## Synopsis
Traceability matrix for MYCO adaptation: UI element -> user intent -> backend path -> dependencies -> status -> evidence -> hint text.

## Table of Contents
1. Matrix
2. Priority interpretation
3. Cross-links
4. Status matrix

## Treatment
Rows are written as implementation contracts, not ideas.

## Short Narrative
Matrix is designed for onboarding and delivery: team sees what works now, what can be reused from MCC, and what must be built for VETKA-first MYCO.

## Full Spec
| UI element | User intent | Backend path | Memory/context dependencies | Status | Evidence (file:line) | MYCO hint text |
|---|---|---|---|---|---|---|
| Model Directory (phonebook) | Choose model/provider route | `/api/models/autodetect`, `/api/models/status` | current chat/group context | Implemented | `client/src/components/ModelDirectory.tsx:2`; `client/src/components/ModelDirectory.tsx:208`; `client/src/components/chat/ChatPanel.tsx:2407` | RU: "Открой phonebook и выбери модель под задачу: это меняет маршрут ответа." EN: "Open phonebook and pick a model for this task: it changes response routing." |
| API key selector | Choose preferred key/provider | socket `add_api_key/get_key_status` + task `selected_key` | selected key state | Implemented | `client/src/components/mcc/KeyDropdown.tsx:24`; `client/src/hooks/useSocket.ts:637`; `src/api/handlers/key_handlers.py:172`; `src/api/routes/task_routes.py:173` | RU: "Выбранный ключ задает провайдера и бюджет выполнения." EN: "Selected key sets provider and execution budget path." |
| Favorite key/model persistence | Save favorite routing setup | `/api/favorites`, `/api/models/favorites` | ENGRAM preference write | Implemented | `client/src/store/useStore.ts:214`; `client/src/store/useStore.ts:314`; `src/api/routes/config_routes.py:800`; `src/api/routes/model_routes.py:224` | RU: "Добавь в избранное, чтобы держать рабочие ключи и модели сверху." EN: "Star keys/models to keep working options pinned to top." |
| Favorite files/nodes/artifacts | Save preferred working files | `/api/tree/favorites`, artifact/tree favorites reads | node/artifact highlights state | Implemented | `src/api/routes/tree_routes.py:1478`; `client/src/components/artifact/ArtifactPanel.tsx:296`; `client/src/components/chat/ChatPanel.tsx:788` | RU: "Избранные файлы и артефакты ускоряют возврат к рабочему контексту." EN: "Favorite files/artifacts speed up return to working context." |
| VETKA root app | Enter main workspace | n/a (frontend shell) | route context only | Implemented | `client/src/main.tsx:40` | RU: "Ты в VETKA. Выбери ноду, и я подскажу next step." EN: "You are in VETKA. Pick a node and I will suggest the next step." |
| MYCELIUM route | Open MCC surface | n/a | pathname `/mycelium` | Implemented | `client/src/main.tsx:28` | RU: "Это MCC-поверхность, тут MYCO уже активен." EN: "This is MCC surface; MYCO is already active here." |
| Web Shell route | Open standalone web browsing/save surface | `/api/search/web-preview`, `/api/artifacts/save-webpage` | active URL + selected save target path | Implemented | `client/src/main.tsx:31`; `client/src/WebShellStandalone.tsx:543`; `src/api/routes/unified_search_routes.py:164`; `src/api/routes/artifact_routes.py:294` | RU: "Открыл web-shell: можно просмотреть страницу и сохранить в VETKA." EN: "Web-shell opened: preview page and save it into VETKA." |
| Detached artifact window route | Open artifact in separate window | Tauri `open_artifact_window` | detached window label + file path payload | Implemented | `client/src/main.tsx:37`; `client/src-tauri/src/main.rs:66`; `client/src/ArtifactStandalone.tsx:41` | RU: "Артефакт вынесен в отдельное окно — удобно для параллельной работы." EN: "Artifact is detached into a separate window for parallel work." |
| Detached media window route | Open media artifact in separate window | Tauri `open_artifact_media_window` | media seek + in-vetka flag | Implemented | `client/src/main.tsx:34`; `client/src-tauri/src/main.rs:67`; `client/src/ArtifactMediaStandalone.tsx:39` | RU: "Медиа открыто отдельно: можно управлять воспроизведением независимо." EN: "Media is detached: playback can be controlled independently." |
| MCC helper mode toggle | Enable/disable helper | `/api/chat/quick` (role switch) | helper mode persistence | Implemented | `client/src/store/useMCCStore.ts:83`; `client/src/components/mcc/MiniChat.tsx:295` | RU: "Включи helper mode для проактивных подсказок." EN: "Enable helper mode for proactive guidance." |
| MiniChat trigger | Ask MYCO quickly | `/api/chat/quick` | quick command parsing | Implemented | `client/src/components/mcc/MiniChat.tsx:41` | RU: "Напиши `?` или `/myco` для мгновенной подсказки." EN: "Type `?` or `/myco` for instant guidance." |
| Quick MYCO fastpath | Return helper reply | `src/api/routes/chat_routes.py` | payload + retrieval + state keys | Implemented | `src/api/routes/chat_routes.py:409`; `src/api/routes/chat_routes.py:435`; `src/api/routes/chat_routes.py:479` | RU: "Я беру контекст экрана и даю короткий план действий." EN: "I read your screen context and return a short action plan." |
| Hidden MYCO memory bridge | Pull focused hidden context | `src/services/myco_memory_bridge.py` | hidden index + ENGRAM snapshot | Implemented | `src/services/myco_memory_bridge.py:243`; `src/services/myco_memory_bridge.py:598`; `src/services/myco_memory_bridge.py:649` | RU: "Я помню скрытые опоры проекта и подмешиваю их в подсказку." EN: "I use hidden project anchors to enrich guidance." |
| Unified Search context selector | Switch between `vetka/`, `web/`, `file/` | `/api/search/unified`, `/api/search/file` | viewport context for rerank | Implemented | `client/src/components/search/UnifiedSearchBar.tsx:251`; `client/src/components/search/UnifiedSearchBar.tsx:252`; `client/src/components/search/UnifiedSearchBar.tsx:253`; `src/api/routes/unified_search_routes.py:129`; `src/api/routes/unified_search_routes.py:148` | RU: "Смены контекста поиска меняют источники и режимы." EN: "Search context switch changes sources and modes." |
| Search mode controls | Choose HYB/SEM/KEY/FILE behavior | unified/file search backend | context-supported modes | Implemented | `client/src/components/search/UnifiedSearchBar.tsx:178`; `client/src/components/search/UnifiedSearchBar.tsx:208`; `src/api/handlers/unified_search.py:266` | RU: "HYB для общего охвата, FILE/filename для точного файла." EN: "Use HYB for broad recall, FILE/filename for exact file lookup." |
| Search cloud/social contexts | Show future contexts in one search window | unified capabilities | not enabled (`available: false`) | Planned/Not Implemented | `client/src/components/search/UnifiedSearchBar.tsx:254`; `client/src/components/search/UnifiedSearchBar.tsx:255` | RU: "Cloud/Social в меню уже видны, но пока не активны." EN: "Cloud/Social appear in menu but are not active yet." |
| External FS discover + optional scan | Find files outside current VETKA index, then ingest by user action | `/api/search/file` + `/api/watcher/add|index-file|add-from-browser` | OS provider roots + watcher events | Implemented | `src/search/file_search_service.py:118`; `src/search/file_search_service.py:124`; `client/src/App.tsx:619`; `client/src/App.tsx:630`; `client/src/App.tsx:713`; `src/api/routes/watcher_routes.py:95` | RU: "Нашел файл вне индекса? По твоему подтверждению добавим в сканер VETKA." EN: "Found file outside index? On your confirmation we ingest it into VETKA scanner." |
| Scanner connector auth/scan | Connect cloud/social providers and run scans | `/api/connectors/*` | connector auth state + selected ids | Implemented | `client/src/components/scanner/ScanPanel.tsx:1370`; `client/src/components/scanner/ScanPanel.tsx:1390`; `src/api/routes/connectors_routes.py:505`; `src/api/routes/connectors_routes.py:720` | RU: "Подключи провайдер и запусти scan, затем закрепи важное в контексте." EN: "Connect provider, run scan, then pin important files to context." |
| Top MYCO hint bubble (MCC) | Always-on proactive cue | local event + quick contract | drill state + node role/family | Implemented | `client/src/components/mcc/MyceliumCommandCenter.tsx:2404`; `client/src/components/mcc/MyceliumCommandCenter.tsx:3667` | RU: "Твой следующий шаг уже в верхней плашке." EN: "Your next best step is already in the top hint." |
| Main VETKA proactive MYCO widget | Contextual guidance in App.tsx | expected `/api/chat/quick` | selected node + chat + viewport | Planned/Not Implemented | `client/src/App.tsx:246` (main surface exists; no MYCO markers) | RU: "Нужна адаптация: подключить MYCO к текущей VETKA сцене." EN: "Adaptation needed: bind MYCO to current VETKA scene." |
| Mention in solo chat | Direct model/agent targeting | `user_message_handler.py` + mention handler | chat history + pinned context | Implemented | `src/api/handlers/user_message_handler.py:1557`; `src/api/handlers/mention/mention_handler.py:112` | RU: "Используй @mention для точного вызова модели." EN: "Use @mention for precise model routing." |
| Group mention routing | Team/agent orchestration | `group_message_handler.py` | group context + voice locks | Implemented | `src/api/handlers/group_message_handler.py:20`; `src/api/handlers/group_message_handler.py:83` | RU: "В группах @mention запускает адресный роутинг." EN: "In groups, @mention triggers targeted routing." |

## Cross-links
See also:
- [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [Scenarios](./MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md)
- [Chat and Agents](./MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1.md)
- [Context and Memory](./MYCO_VETKA_CONTEXT_MEMORY_STACK_V1.md)
- [Gap Registry](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [Windows and Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [Controls and Buttons Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [Search Phonebook Keys Guide](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)

## Status matrix
| Type | Count |
|---|---|
| Implemented rows | 20 |
| Partially Implemented rows | 0 |
| Planned/Not Implemented rows | 2 |

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
