# Rename Plan: "ENGRAM" → правильные имена

> Устраняем терминологическую путаницу. DeepSeek Engram = детерминированная N-граммная адресация. Наш "ENGRAM" = user preferences cache.

## Что переименовываем

### 1. Класс: EngramUserMemory → UserPreferenceStore

| Было | Стало | Файл |
|------|-------|------|
| `EngramUserMemory` | `UserPreferenceStore` | `src/memory/engram_user_memory.py` → `src/memory/user_preference_store.py` |
| `get_engram_user_memory()` | `get_user_preference_store()` | Та же фабрика |
| `_engram_instance` | `_preference_store_instance` | Singleton |
| `engram_lookup()` | `preference_lookup()` | Функция поиска по RAM |
| `enhanced_engram_lookup()` | Удалить целиком | Levels 2-5 — mock/placeholder код |

### 2. Qdrant коллекция: vetka_user_memories (оставить как есть)

Имя коллекции `vetka_user_memories` — уже корректное. Не содержит слова "engram". Не трогаем.

### 3. Импорты (15+ файлов)

Все файлы, которые делают `from src.memory.engram_user_memory import ...`:

```
src/mcp/tools/session_tools.py
src/memory/jarvis_prompt_enricher.py
src/orchestration/orchestrator_with_elisya.py
src/mcp/vetka_mcp_bridge.py
src/bridge/shared_tools.py
src/mcp/tools/llm_call_tool.py
src/services/user_memory_updater.py
```

### 4. Комментарии и MARKER-ы

| Было | Стало |
|------|-------|
| `MARKER_108_7_ENGRAM_ELISION` | `MARKER_108_7_PREFS_ELISION` |
| `MARKER_ENGRAM_QDRANT_FIX` | `MARKER_PREFS_QDRANT_FIX` |
| `[EngramUserMemory]` в логах | `[UserPrefs]` |
| `[Engram Lookup]` в логах | `[PrefLookup]` |

### 5. Что НЕ переименовываем

- `data/engram_cache.json` — это будет **настоящий** Engram (Level 1, детерминированный кэш). Имя зарезервировано.
- `src/memory/engram_cache.py` — будущий модуль True Engram. Имя зарезервировано.

## Порядок переименования

1. Создать `src/memory/user_preference_store.py` (копия engram_user_memory.py с новыми именами)
2. В `engram_user_memory.py` — оставить re-export для обратной совместимости:
   ```python
   # DEPRECATED: use user_preference_store.py
   from src.memory.user_preference_store import UserPreferenceStore as EngramUserMemory
   from src.memory.user_preference_store import get_user_preference_store as get_engram_user_memory
   ```
3. Постепенно обновить импорты в 7 файлах
4. Удалить `enhanced_engram_lookup()` (levels 2-5 — мёртвый код)
5. Удалить `engram_user_memory.py` после миграции всех импортов

## Риск

Низкий. Это rename + deprecation shim. Функциональность не меняется.
