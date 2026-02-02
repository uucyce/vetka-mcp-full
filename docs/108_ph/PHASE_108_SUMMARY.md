# PHASE 108 - ROUTING FIXES SUMMARY

## СТАТУС: ✅ COMPLETED (Step 1)
**Дата:** 2026-02-02
**Автор:** Claude Sonnet 4.5

---

## ЧТО ИСПРАВЛЕНО

### 1. MARKER_FALLBACK_BUG (P0) ✅
**Проблема:** Система молча переключалась на OpenRouter при любой ошибке API
**Решение:** Убран автоматический fallback, теперь возвращается явная ошибка
**Файл:** `src/elisya/provider_registry.py`

### 2. MARKER_REPLY_HANDLER (P0) ✅
**Проблема:** Reply к MCP агенту (@claude_code) вызывал random group agent
**Решение:** Добавлена проверка MCP agents, skip group routing для MCP replies
**Файл:** `src/api/handlers/group_message_handler.py`

### 3. MARKER_MCP_ROUTING (P1) ✅
**Проблема:** Regex `r'@(\w+)'` не захватывал @gpt-5.2, @grok-4
**Решение:** Обновлён regex на `r'@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)'`
**Файлы:** 5 файлов обновлено

### 4. MARKER_AUTHOR_FORMAT (P1) ✅
**Проблема:** Предполагалась inconsistency в sender_id формате
**Решение:** Проверка показала, что формат УЖЕ унифицирован. Добавлена документация.
**Файл:** `src/services/group_chat_manager.py`

---

## МАРКЕРЫ

- `MARKER_108_ROUTING_FIX_1` - provider_registry.py (fallback fix)
- `MARKER_108_ROUTING_FIX_2` - group_message_handler.py (MCP reply fix)
- `MARKER_108_ROUTING_FIX_3` - group_chat_manager.py (sender_id docs)
- `MARKER_108_ROUTING_FIX_4` - 5 files (regex fix)

---

## ИЗМЕНЁННЫЕ ФАЙЛЫ

1. `src/elisya/provider_registry.py` - убран OpenRouter fallback
2. `src/api/handlers/group_message_handler.py` - MCP reply handling + regex
3. `src/services/group_chat_manager.py` - sender_id documentation
4. `src/orchestration/langgraph_nodes.py` - regex fix
5. `src/api/routes/debug_routes.py` - regex fix

---

## ТЕСТИРОВАНИЕ

✅ API fallback теперь возвращает явную ошибку
✅ Reply к MCP agent не вызывает group agents
✅ Hyphenated model names (@gpt-5.2, @grok-4) работают
✅ sender_id формат унифицирован

---

## NEXT STEPS (Phase 108.2)

- [ ] Frontend error notifications для API failures
- [ ] MCP agent presence indicator в UI
- [ ] @mention autocomplete для model names
- [ ] Rate limiting для MCP agent replies

---

Полный отчёт: `docs/108_ph/PHASE_108_ROUTING_FIX_REPORT.md`
