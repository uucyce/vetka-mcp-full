MARKER_163.MYCO.VETKA.SEARCH_PHONEBOOK_KEYS_GUIDE.V1
LAYER: L2
DOMAIN: UI|TOOLS|CHAT|RAG
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md
LAST_VERIFIED: 2026-03-07

# MYCO VETKA Search + Phonebook + Keys Operating Guide (V1)

## Synopsis
Операционный гайд по контрольным вопросам: телефонная книжка моделей, API keys, favorite key/model/file, единое окно поиска и режимы (`vetka/web/file`), поиск вне VETKA и опциональный scan ingest.

## Table of Contents
1. Phonebook/model directory
2. API keys and preferred key
3. Favorites (key/model/file)
4. Unified search single-window modes
5. Outside-VETKA file discovery and optional scan
6. Cross-links
7. Status matrix

## Treatment
Каждый раздел описывает: где кликнуть, что это даёт, backend path, и что должен говорить MYCO.

## Short Narrative
Пользователь не обязан помнить инфраструктуру. MYCO объясняет: где выбрать модель/ключ, когда нужен `web/` vs `file/`, и когда стоит предложить ingest в индекс.

## Full Spec
### 1) Phonebook/model directory (`TAG:UI.MODEL_DIRECTORY.PHONEBOOK`)
- Где открыть:
  - В chat left panel (`leftPanel === 'models'`): `client/src/components/chat/ChatPanel.tsx:2407`.
- Что внутри:
  - Автодетект инвентаря моделей: `/api/models/autodetect` (`client/src/components/ModelDirectory.tsx:208`).
  - Статус моделей `/api/models/status` (`client/src/components/ModelDirectory.tsx:256`).
  - Refresh inventory (`client/src/components/ModelDirectory.tsx:656`).
- Что дает пользователю:
  - Выбор `model + source/provider` меняет маршрут ответа и доступные capabilities (`client/src/components/ModelDirectory.tsx:395`).
- MYCO hint:
  - RU: "Открой phonebook, выбери модель и источник: это зафиксирует маршрут ответа под текущую задачу."

### 2) API keys and preferred key (`TAG:UI.KEY.SELECTOR.PREFERRED`)
- Key operations:
  - Add/detect/add-smart/remove key: `client/src/components/ModelDirectory.tsx:504`, `client/src/components/ModelDirectory.tsx:535`, `client/src/components/ModelDirectory.tsx:563`.
  - Socket key events `add_api_key`, `learn_key_type`, `get_key_status`: `src/api/handlers/key_handlers.py:33`, `src/api/handlers/key_handlers.py:118`, `src/api/handlers/key_handlers.py:172`.
- Preferred key selection:
  - `KeyDropdown` control in MCC surface (`client/src/components/mcc/KeyDropdown.tsx:24`).
  - Auto-select key mode (`client/src/components/mcc/KeyDropdown.tsx:162`).
  - Explicit key selection (`client/src/components/mcc/KeyDropdown.tsx:196`).
- Что это дает:
  - При dispatch в backend уходит `selected_key` (`src/api/routes/task_routes.py:165`, `src/api/routes/task_routes.py:173`).
  - То есть выбор ключа влияет на провайдера, лимиты и фактический execution path.
- MYCO hint:
  - RU: "Нужна стабильность/бюджет? Зафиксируй key. Нужна гибкость? Оставь auto-select."

### 3) Favorites key/model/file (`TAG:UI.FAVORITES.KEY_MODEL_FILE`)
- Keys/models favorites:
  - Store + persistence to `/api/favorites`: `client/src/store/useStore.ts:214`, `client/src/store/useStore.ts:314`, `src/api/routes/config_routes.py:800`, `src/api/routes/config_routes.py:811`.
- Model-level favorites API:
  - `GET/POST/DELETE /api/models/favorites`: `src/api/routes/model_routes.py:224`, `src/api/routes/model_routes.py:242`, `src/api/routes/model_routes.py:250`.
- File/node favorites:
  - `GET /api/tree/favorites`, `PUT /api/tree/favorite`: `src/api/routes/tree_routes.py:1478`, `src/api/routes/tree_routes.py:1490`.
- Что это дает:
  - Быстрая стабилизация “рабочего набора” и сокращение переключений контекста.
- MYCO hint:
  - RU: "Добавь key/model/file в избранное, чтобы следующий запуск не начинать с ручной сборки окружения."

### 4) Unified search single-window modes (`TAG:SEARCH.UNIFIED.SINGLE_WINDOW`)
- One search surface:
  - `UnifiedSearchBar` (`client/src/components/search/UnifiedSearchBar.tsx:1`).
- Context switch:
  - `vetka/`, `web/`, `file/` enabled (`client/src/components/search/UnifiedSearchBar.tsx:251`, `:252`, `:253`).
  - `cloud/`, `social/` listed but unavailable (`client/src/components/search/UnifiedSearchBar.tsx:254`, `:255`).
- Modes:
  - `hybrid`, `semantic`, `keyword`, `filename` (`client/src/components/search/UnifiedSearchBar.tsx:178`).
  - Context-based supported modes (`client/src/components/search/UnifiedSearchBar.tsx:226`).
- Backend contract:
  - `POST /api/search/unified`, `GET /api/search/capabilities`, `POST /api/search/file`: `src/api/routes/unified_search_routes.py:129`, `:141`, `:148`.
  - Capabilities by context in handler: `src/api/handlers/unified_search.py:266`.
- MYCO hint:
  - RU: "`vetka/` для project memory, `web/` для интернета, `file/` для ОС-файлов вне текущего индекса."

### 5) Outside-VETKA file discovery and optional scan (`TAG:SEARCH.FILE.EXTERNAL_ROOTS`)
- External roots policy:
  - file search may traverse broader roots than current indexed tree (`src/search/file_search_service.py:117`, `src/search/file_search_service.py:124`).
- Optional ingest flow after discovery:
  - Add folder to watcher: `/api/watcher/add` (`src/api/routes/watcher_routes.py:95`).
  - Index single file: `/api/watcher/index-file` (route listed in watcher docs, called from app): `client/src/App.tsx:630`.
  - Browser fallback ingest: `/api/watcher/add-from-browser` (`client/src/App.tsx:713`).
- UX sequence in app drop flow:
  - Local folder/file routes to watcher/index (`client/src/App.tsx:619`, `client/src/App.tsx:630`).
  - If unresolved browser paths remain, fallback to add-from-browser (`client/src/App.tsx:709`, `client/src/App.tsx:713`).
- MYCO hint:
  - RU: "Файл найден вне индекса. Хочешь, добавим его в VETKA сканер сейчас, чтобы стал частью дерева и поиска?"

## Cross-links
See also:
- [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [User Scenarios Root](./MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md)
- [UI Capability Matrix](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [Controls Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [Windows/Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [Long-tail Surfaces Scenarios](./MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md)
- [Button Hint Catalog](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)
- [Hint Library](./MYCO_VETKA_HELP_HINT_LIBRARY_V1.md)
- [Cloud Social Search Contract](./MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md)
- [Strict Coverage Audit](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)

## Status matrix
| Capability | Status | Evidence |
|---|---|---|
| Phonebook open/select flow | Implemented | `client/src/components/chat/ChatPanel.tsx:2407`, `client/src/components/ModelDirectory.tsx:208` |
| Key detect/select/preferred flow | Implemented | `src/api/handlers/key_handlers.py:33`, `client/src/components/mcc/KeyDropdown.tsx:196` |
| Favorites key/model/file | Implemented | `src/api/routes/config_routes.py:800`, `src/api/routes/tree_routes.py:1490` |
| Unified search modes in one bar | Implemented | `client/src/components/search/UnifiedSearchBar.tsx:251`, `src/api/routes/unified_search_routes.py:129` |
| Cloud/social search contexts in UI | Planned/Not Implemented | `client/src/components/search/UnifiedSearchBar.tsx:254`, `:255` (`available: false`) |
| Optional ingest after external file discover | Implemented | `client/src/App.tsx:619`, `client/src/App.tsx:713`, `src/api/routes/watcher_routes.py:95` |
