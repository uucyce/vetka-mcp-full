# "ENGRAM" в VETKA — что это на самом деле

> Описание для обсуждения с GPT: что мы построили под именем "Engram", почему это не Engram, и что делать дальше.

---

## Что у нас есть

**Файл:** `src/memory/engram_user_memory.py` (~820 строк)
**Класс:** `EngramUserMemory`
**Qdrant коллекция:** `vetka_user_memories`

### Суть модуля

User Preference Store — хранилище пользовательских предпочтений с двухуровневым кэшем:

```
Hot (RAM dict) ←──offload──→ Cold (Qdrant vector DB)
     O(1)                        O(log n)
```

### Что хранит

6 категорий пользовательских настроек:
- `communication_style` — как общаться (формальность, длина ответов)
- `viewport_patterns` — привычные zoom-уровни, LOD preferences
- `tree_structure` — предпочтения по визуализации дерева
- `project_highlights` — важные проекты/файлы пользователя
- `temporal_patterns` — временные паттерны использования
- `tool_usage_patterns` — какие инструменты пользователь предпочитает

### Как работает

1. **Запись:** `set_preference(user_id, category, key, value)` → RAM + Qdrant upsert
2. **Чтение:** `get_preference(user_id, category, key)` → RAM first (O(1)), Qdrant fallback
3. **Offload:** Если preference запрашивается >5 раз → promote из Qdrant в RAM
4. **Decay:** `confidence -= 0.05 * weeks_inactive` → prune при confidence < 0.1
5. **Spiral context:** Сжатый контекст для prompt injection (ELISION compression)

### Где используется

- `session_tools.py` — при session_init загружает user prefs для агента
- `jarvis_prompt_enricher.py` — инжектит preferences в промпты
- `vetka_mcp_bridge.py` — отдаёт preferences через MCP
- `llm_call_tool.py` — подстраивает LLM-вызовы под user style
- REFLEX signal #4 (`engram_pref`, weight 0.10) — буст tool-ов которые юзер предпочитает

### Мёртвый код (можно удалить)

`enhanced_engram_lookup()` — 5 "уровней" lookup, из которых levels 2-5 содержат:
- Mock surprise calculation (хардкод формулы)
- Placeholder Qdrant search (`qdrant_results = []`)
- Hardcoded `"contextual_relevance": 0.8`
- Recursive calls (level 5 → level 4 → level 3 → level 2 → level 1)

Этот код никогда не вызывается в продакшене. ~200 строк мёртвого кода.

---

## Почему это НЕ Engram

### DeepSeek Engram (оригинал, 2025)

DeepSeek Engram — это **модификация архитектуры трансформера**:

- **Где:** Внутри forward pass нейросети, между слоями
- **Что делает:** N-граммная детерминированная адресация. По входным токенам строит хеш-ключ и достаёт готовый паттерн из таблицы lookup. Без нейронных вычислений.
- **Зачем:** Освобождает ранние слои трансформера от реконструкции частых паттернов. Те же токены, но быстрее и с меньшим compute.
- **Ключевое свойство:** O(1), детерминированный результат. `hash(n-gram) → exact pattern`. Как dict в Python — всегда один и тот же ответ, мгновенно.
- **Аналогия:** Таблица умножения. Ты не считаешь 7x8 каждый раз — ты знаешь что 56. Engram = такая таблица для трансформера.

### Наш "ENGRAM" (что мы сделали)

- **Где:** Снаружи модели, как внешний Python сервис
- **Что делает:** Хранит user preferences (стиль общения, zoom-уровни) в dict + Qdrant
- **Зачем:** Персонализация — помнить как юзер предпочитает работать
- **Ключевое свойство:** RAM часть — O(1) по user_id (это единственное сходство). Но это не адресация по N-грамме контекста, это просто `dict["danila"]`.

### Таблица отличий

| Свойство | DeepSeek Engram | Наш "ENGRAM" |
|----------|----------------|-------------|
| Тип | Архитектурный модуль нейросети | Внешний Python сервис |
| Адресация | N-грамма входных токенов → hash → pattern | user_id → dict → preferences |
| Что возвращает | Паттерн для skip ранних слоёв | User preferences (zoom, style) |
| Детерминированность | Полная: одни токены → один паттерн | Частичная: только RAM hit |
| Цель | Ускорить inference модели | Персонализировать UX |
| Новая ось разреженности | Да (дополняет attention) | Нет (обычный кэш) |

---

## Что мы упускаем из идеи Engram

Настоящая ценность DeepSeek Engram для VETKA — **не в переименовании Qdrant-коллекции**, а в принципе:

> Для частых, повторяющихся паттернов — не ищи, а доставай по ключу.

### Применение к VETKA (двухуровневая память)

**Level 1 (True Engram):** Детерминированный кэш
```
Key: (agent_type, filename, action_type)
Value: конкретный урок/предупреждение

Примеры:
("*", "agent_pipeline.py", "modify") → "DANGER: self-modification, use sandbox"
("opus", "session_tools.py", "edit") → "JSON namespace bug, always use _json"
("*", "scorer.py", "pattern") → "scorer.py + feedback.py always change together"
```
- O(1), детерминированный, <1ms
- Auto-populated: когда Qdrant-урок match-ится ≥3 раз → promote to cache
- Max 200 entries, LRU eviction

**Level 2 (Qdrant Semantic):** Для нового/нестандартного
```
Query: "как работает pipeline timeout?"
→ embedding → cosine similarity → top-5 results
→ ~200ms, недетерминированный
```
- Для незнакомых ситуаций
- Уже существует (VetkaResourceLearnings)

**Граница:** L1 = "знаю точно" (как таблица умножения). L2 = "надо подумать" (как решение уравнения).

---

## Предлагаемое переименование

| Было | Стало | Почему |
|------|-------|--------|
| `EngramUserMemory` | `UserPreferenceStore` | Честное имя для того, что модуль делает |
| `engram_user_memory.py` | `user_preference_store.py` | Файл = модуль |
| `enhanced_engram_lookup()` | Удалить | Мёртвый код (levels 2-5 — placeholder) |
| `engram_cache.py` (НОВЫЙ) | `engram_cache.py` | Зарезервировано для НАСТОЯЩЕГО Engram (Level 1 cache) |

Результат: слово "Engram" используется только для настоящего детерминированного кэша.

---

## Вопросы для обсуждения с GPT

1. **Формат ключа L1:** `(agent, file, action)` — достаточно ли? Или нужна более гранулярная N-грамма (например, включая phase_type)?

2. **Auto-promotion threshold:** 3 match-а — правильный порог? Или лучше адаптивный (зависит от частоты запросов)?

3. **Scope:** L1 cache per-project или global? Уроки из одного проекта переносимы?

4. **Eviction:** LRU vs LFU vs temporal decay? DeepSeek использует статическую таблицу (без eviction). Нам нужен eviction потому что контекст меняется.

5. **Связь с REFLEX:** Должен ли REFLEX scorer иметь сигнал от L1 cache? Или L1 — это отдельный слой до REFLEX?

6. **Связь с CORTEX:** CORTEX уже отслеживает tool success rates. Можно ли CORTEX top-tools автоматически промоутить в L1?
