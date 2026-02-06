# GROK AUDIT REQUEST — Phase 115 Gap Analysis

**Context:** У тебя запинен отчёт Phase 115. Мне нужен точечный gap-анализ — где именно в коде нужны фиксы, и какие строки менять. Экономь токены, давай конкретику.

---

## ЗАДАНИЕ 1: Provider Persistence Bug (BUG-3)

**Проблема:** После перезагрузки сервера модели теряют provider info (Grok@POLZA → fallback openrouter).

**Что уже есть:**
- `model_source` передаётся с фронта (Phase 111.9-111.11)
- В group_chat_manager.py:54 — `model_source: Optional[str]` уже в GroupParticipant
- В user_message_handler.py:249 — `model_source = data.get("model_source")` принимается

**Что проверить (конкретные файлы):**
1. `src/api/handlers/user_message_handler.py` — строки 448-499 и 678-680. **Вопрос:** `model_source` попадает ли в `chat_history.add_message()` в metadata сообщения? Или теряется?
2. `src/chat/chat_history_manager.py` — строка 308-320. Структура чата. **Вопрос:** есть ли поле для `model_source` в message schema?
3. `client/src/hooks/useSocket.ts` — как `selectedModelSource` восстанавливается при загрузке чата? Или каждый раз null?
4. `client/src/components/chat/ChatPanel.tsx` — при загрузке истории чата, берётся ли `model_source` из сохранённых сообщений?

**Предложенный формат:** `@Grok_4.1_fast_POLZA` — модель + провайдер в одном поле. Хорошая ли это идея или лучше отдельные поля?

---

## ЗАДАНИЕ 2: Tools Security Gate (BUG-7)

**Проблема:** `requires_approval` определён но не проверяется.

**Что проверить:**
1. `src/mcp/tools/edit_file_tool.py:64` — `requires_approval = True`
2. `src/mcp/tools/git_tool.py:147` — `requires_approval = True`
3. `src/mcp/vetka_mcp_bridge.py` — найди метод `call_tool()` (около строки 1016-1262). **Вопрос:** где вставить проверку `if tool.requires_approval and not dry_run: return error`?
4. `src/mcp/tools/llm_call_tool.py:527` — `tools = arguments.get('tools')` передаётся без валидации. Нужен ли allowlist для function calling?

**Вчерашний фикс Phase 114.6:** Мы добавили MARKER_114.6 — `tools` теперь передаются в OpenRouter payload. Проверь что tools проходят корректно до модели и обратно, нет ли обрезки `tool_calls` в response.

---

## ЗАДАНИЕ 3: Pinned Files Persistence (BUG-4)

**Проблема:** Global CAM pins хранятся в памяти, теряются при рестарте.

**Что проверить:**
1. `src/api/routes/cam_routes.py:103` — `_pinned_files: Dict[str, dict] = {}` — это module-level dict, исчезает при перезапуске.
2. Есть ли уже сериализация в `data/` для pins? Или нужно делать с нуля?
3. `src/mcp/tools/pinned_files_tool.py:182` — `from src.api.routes.cam_routes import _pinned_files` — прямой импорт module-level dict. Это ок или нужен singleton service?

**Вопрос:** лучше сохранять в `data/pinned_files.json` или добавить в существующую `data/chat_history.json` как top-level поле `"global_pins": {}`?

---

## ЗАДАНИЕ 4: Flask Cleanup — Приоритет и Risk

**Что проверить:**
1. `src/api/routes/chat_routes.py:74-93` — 15+ вызовов `flask_config.get()`. **Вопрос:** если заменить на `Depends()` из `src/dependencies.py`, сломается ли что-то? Есть ли зависимости которых нет в dependencies.py?
2. `src/dependencies.py:247` — `get_flask_config()` — кто его вызывает? Можно ли удалить?
3. `src/orchestration/key_management_api.py` — весь файл Flask. Используется ли он хоть где-то (import)?

**Главный вопрос:** flask_config заполняется в `src/initialization/components_init.py`. При рестарте компоненты инициализируются заново. Может ли это вызывать потерю runtime state (модели, провайдеры)?

---

## ЗАДАНИЕ 5: Chat Auto-Creation (BUG-1)

**Что проверить:**
1. `src/api/handlers/user_message_handler.py` — найди ВСЕ вызовы `get_or_create_chat()`. Их ~7 штук (строки 362, 375, 552, 785, 871, 1198, 1259). **Вопрос:** какие из них создают "паразитные" чаты? Особенно строка 375 (`context_type='topic'`) и 552.
2. `client/src/components/canvas/FileCard.tsx:916` — `vetka-open-chat` event. Это триггерит создание нового чата при клике на файл?
3. `main.py:541-542` — `handle_create_chat_node`. Кто вызывает этот socket event?

---

## ЗАДАНИЕ 6: Проверь вчерашний фикс tools (Phase 114.6-114.7)

**Что проверить:**
1. `src/mcp/tools/llm_call_tool.py` — метод `_call_openrouter_sync()` (около строки 392-510). Tools правильно передаются в body? Ответ с `tool_calls` парсится?
2. `src/bridge/shared_tools.py` — строка 1096-1159. Унификация tool names (Phase 114.7). Все пути чата используют одинаковые tool definitions?
3. Есть ли места где tools теряются (обрезка, ignore)?

---

## FORMAT ответа

Для каждого задания дай:
```
### ЗАДАНИЕ N: [название]
**GAP:** что конкретно не реализовано (файл:строка)
**FIX:** что нужно изменить (псевдокод или конкретные строки)
**RISK:** что может сломаться
**EFFORT:** S/M/L
```

Не нужны общие советы. Нужны конкретные строки кода и точные локации гэпов.
