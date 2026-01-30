# HAIKU 4 INDEX: Solo vs Group Chat Critical Audit

## 📋 ДОКУМЕНТЫ СЕРИИ

Этот аудит состоит из 4 документов:

### 1. **HAIKU_4_SOLO_VS_GROUP_CRITICAL.md** (ГЛАВНЫЙ ОТЧЕТ)
**ЧИТАЙ ПЕРВЫМ!** Детальный анализ всех различий.

- Executive Summary: Что отличается
- Call Sites: Где вызывается модель в solo vs group
- Роли и System Prompts: Как работают ролевые системы
- Message Format: Структуры сообщений
- Provider Selection: Как выбирается провайдер
- Таблица различий: Быстрое сравнение
- Рекомендации по унификации: Что нужно изменить

**Время чтения:** 20-30 минут

---

### 2. **HAIKU_4_FLOW_DIAGRAMS.md** (ДИАГРАММЫ)
**ЧИТАЙ ПОСЛЕ** главного отчета для визуального понимания.

- Solo Chat Flow: Полный поток для прямого чата
- Group Chat Flow: Полный поток для группового чата
- Сравнение обоих потоков: Side-by-side анализ
- Call Stack Reference: Стеки вызовов
- Message Format Examples: Реальные примеры сообщений
- Streaming Comparison: Как streaming работает в обоих
- Error Handling: Обработка ошибок
- Execution Timeline: Временные графики
- Where to Make Changes: Куда вносить изменения

**Время чтения:** 15-20 минут

---

### 3. **HAIKU_4_FIX_MARKERS.md** (МАРКЕРЫ ДЛЯ РАЗРАБОТЧИКА)
**ИСПОЛЬЗУЙ** при разработке для точного понимания что менять.

- Critical Fix Locations: Основные места для изменений
  - FILE 1: user_message_handler.py (MARKER-UMH-001 до 004)
  - FILE 2: chat_handler.py (MARKER-CH-001 до 002)
  - FILE 3: orchestrator_with_elisya.py (MARKER-ORCH-001 до 002)
  - FILE 4: provider_registry.py (MARKER-PR-001 до 002)
  - FILE 5: group_message_handler.py (MARKER-GMH-001)

- Implementation Roadmap: Пошаговый план реализации
- Success Criteria: Критерии успеха
- Potential Issues: Возможные проблемы
- Implementation Checklist: Чек-лист для разработчика

**Время чтения:** 10-15 минут

---

### 4. **HAIKU_4_INDEX.md** (ЭТОТ ФАЙЛ)
Навигация по всем документам и быстрые ссылки.

---

## 🎯 БЫСТРЫЙ СТАРТ

### Если у тебя есть 5 минут:
1. Прочитай **Executive Summary** в HAIKU_4_SOLO_VS_GROUP_CRITICAL.md

### Если у тебя есть 30 минут:
1. Прочитай **HAIKU_4_SOLO_VS_GROUP_CRITICAL.md** полностью
2. Посмотри диаграммы в HAIKU_4_FLOW_DIAGRAMS.md

### Если ты разработчик (начинаешь работу):
1. Прочитай HAIKU_4_SOLO_VS_GROUP_CRITICAL.md полностью
2. Изучи HAIKU_4_FLOW_DIAGRAMS.md - диаграммы важны
3. Открой HAIKU_4_FIX_MARKERS.md рядом с редактором кода
4. Используй маркеры для навигации по коду

### Если ты архитектор (планируешь рефактор):
1. Начни с Executive Summary в HAIKU_4_SOLO_VS_GROUP_CRITICAL.md
2. Прочитай раздел "Рекомендации по унификации"
3. Изучи "Миграционный путь"
4. Используй "Implementation Roadmap" в HAIKU_4_FIX_MARKERS.md

---

## 🔑 КЛЮЧЕВЫЕ ВЫВОДЫ

### Основная Проблема
**Solo и Group используют СОВЕРШЕННО РАЗНЫЕ СИСТЕМЫ!**

```
SOLO Chat:
- Прямые вызовы ollama.chat() или httpx.post()
- Нет ролей (все = "helpful assistant")
- Нет Elisya state
- Message format: [{"role": "user", "content": full_prompt}]

GROUP Chat:
- Через orchestrator.call_agent()
- Роли: PM, Dev, QA, Architect, Researcher
- С Elisya state для context fusion
- Message format: [{"role": "system", ...}, {"role": "user", ...}]
```

### Главное Решение
**Сделать Solo chat использовать GROUP систему!**

```
УНИФИЦИРОВАННАЯ СИСТЕМА:
- ВСЕ модели вызываются через orchestrator.call_agent()
- ВСЕ используют call_model_v2() в provider_registry
- ВСЕ используют message format с system role
- ВСЕ используют ProviderRegistry.detect_provider()
```

---

## 📊 СТАТИСТИКА ДОКУМЕНТОВ

### Файлы, Требующие Изменений (Priority)

| Файл | Маркеры | Priority | Difficulty | Time |
|------|---------|----------|-----------|------|
| user_message_handler.py | UMH-001-004 | CRITICAL | HIGH | 2-3h |
| chat_handler.py | CH-001-002 | CRITICAL | MEDIUM | 1-2h |
| orchestrator_with_elisya.py | ORCH-001-002 | HIGH | MEDIUM | 1-2h |
| provider_registry.py | PR-001-002 | HIGH | LOW | 30m |
| group_message_handler.py | GMH-001 | MEDIUM | LOW | 30m |
| **TOTAL** | **15 markers** | - | - | **6-9h** |

### Документы Этого Аудита

| Документ | Страницы | Размер | Фокус |
|----------|---------|--------|-------|
| HAIKU_4_SOLO_VS_GROUP_CRITICAL.md | ~8-10 | ~15KB | Анализ различий |
| HAIKU_4_FLOW_DIAGRAMS.md | ~6-8 | ~12KB | Визуальные потоки |
| HAIKU_4_FIX_MARKERS.md | ~8-10 | ~14KB | Маркеры для разработки |
| HAIKU_4_INDEX.md (этот) | ~3-5 | ~4KB | Навигация |

---

## 🎓 КАК ИСПОЛЬЗОВАТЬ МАРКЕРЫ

### Пример: Когда нужно менять MARKER-UMH-001

1. **Найди маркер** в HAIKU_4_FIX_MARKERS.md:
   ```
   #### MARKER-UMH-001: Replace Ollama Direct Call (Line ~355-362)
   ```

2. **Открой файл** в редакторе:
   ```bash
   code /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py
   ```

3. **Перейди на строку** (Ctrl+G или Cmd+G):
   ```
   Go to line 355
   ```

4. **Найди CURRENT CODE** в маркере
5. **Сравни** с тем что в файле
6. **Примени FIX TO** код из маркера
7. **Протестируй** изменение

---

## 🚀 ПОРЯДОК РЕАЛИЗАЦИИ

### Phase 1: Preparation
```
[ ] Создать feature branch
[ ] Прочитать все документы
[ ] Создать тесты для текущего поведения
```

### Phase 2: Core Changes (CRITICAL)
```
[ ] MARKER-CH-001: Update build_model_prompt()
[ ] MARKER-UMH-001: Replace Ollama direct call
[ ] MARKER-UMH-002: Replace OpenRouter direct call
[ ] MARKER-UMH-004: Use unified message format
[ ] MARKER-ORCH-002: Verify message building
```

### Phase 3: Cleanup
```
[ ] MARKER-UMH-003: Remove duplicate provider detection
[ ] MARKER-ORCH-001: Add "Assistant" agent type
[ ] MARKER-PR-001: Document message format
[ ] MARKER-PR-002: Verify provider detection
```

### Phase 4: Testing
```
[ ] Test solo chat with all providers
[ ] Test streaming
[ ] Test error handling
[ ] Test group chat (regression)
[ ] Performance testing
```

---

## 📈 КРИТИЧНОСТЬ МАРКЕРОВ

### TIER 1: MUST FIX (Блокирующие)
- **MARKER-UMH-001:** Ollama direct call
- **MARKER-UMH-002:** OpenRouter direct call
- **MARKER-CH-001:** build_model_prompt() format
- **MARKER-ORCH-002:** Message building verification

### TIER 2: SHOULD FIX (Важные)
- **MARKER-ORCH-001:** Add "Assistant" agent type
- **MARKER-PR-001:** Document message format
- **MARKER-UMH-004:** Unified message format

### TIER 3: NICE TO FIX (Улучшения)
- **MARKER-UMH-003:** Remove duplicate detection
- **MARKER-PR-002:** Verify provider detection
- **MARKER-GMH-001:** Remove system_prompt duplication

---

## 🔗 ПЕРЕКРЕСТНЫЕ ССЫЛКИ

### Если ты работаешь на файле:

**user_message_handler.py:**
- MARKER-UMH-001 (Ollama)
- MARKER-UMH-002 (OpenRouter)
- MARKER-UMH-003 (Provider detection)
- MARKER-UMH-004 (Message format)
- LINE ~355: Ollama call
- LINE ~567: OpenRouter call
- LINE ~300: Provider detection

**chat_handler.py:**
- MARKER-CH-001 (build_model_prompt)
- MARKER-CH-002 (detect_provider)
- LINE 110: build_model_prompt definition
- LINE 49: detect_provider definition

**orchestrator_with_elisya.py:**
- MARKER-ORCH-001 (Agent types)
- MARKER-ORCH-002 (Message building)
- LINE 2242: call_agent definition
- LINE ~1200: _run_agent_with_elisya_async (FIND THIS!)

**provider_registry.py:**
- MARKER-PR-001 (Documentation)
- MARKER-PR-002 (Provider detection)
- LINE 856: call_model_v2 definition
- LINE 884: Provider detection

**group_message_handler.py:**
- MARKER-GMH-001 (system_prompt handling)
- LINE 758: get_agent_prompt
- LINE 793: call_agent

---

## ❓ FAQ

**Q: Почему solo и group такие разные?**
A: Они разработаны в разное время. Solo - старый path, Group - новый с Elisya. Нужна унификация.

**Q: Будет ли это быстро?**
A: Нет. Solo станет немного медленнее (orchestrator overhead), но группа станет быстрее (лучше кеширование).

**Q: Можно ли сделать это постепенно?**
A: Да! Use feature flag для gradual rollout.

**Q: Какие риски?**
A: Streaming может сломаться, error handling может быть другой, performance может деградировать.

**Q: Что если я напутаю?**
A: Отреверти, прочитай маркеры еще раз, проконсультируйся.

---

## 📚 ДОКУМЕНТАЦИЯ ПО КОМПОНЕНТАМ

### call_agent()
- Файл: orchestrator_with_elisya.py:2242-2331
- Используется: group_message_handler.py:793
- Документация: HAIKU_4_SOLO_VS_GROUP_CRITICAL.md Section 1.2

### call_model_v2()
- Файл: provider_registry.py:856-903
- Используется: _run_agent_with_elisya_async()
- Документация: HAIKU_4_SOLO_VS_GROUP_CRITICAL.md Section 4.2

### build_model_prompt()
- Файл: chat_handler.py:110-157
- Используется: user_message_handler.py:326, 529, 861
- Документация: HAIKU_4_SOLO_VS_GROUP_CRITICAL.md Section 1.1

### detect_provider()
- Файл: chat_handler.py:49-87 (wrapper)
- Оригинал: provider_registry.py (ProviderRegistry.detect_provider)
- Используется: По всему коду
- Документация: HAIKU_4_SOLO_VS_GROUP_CRITICAL.md Section 4

### get_agent_prompt()
- Файл: role_prompts.py (импортируется)
- Используется: group_message_handler.py:758
- Документация: HAIKU_4_SOLO_VS_GROUP_CRITICAL.md Section 2.2

---

## 🎯 МЕТРИКИ УСПЕХА

Когда рефактор УСПЕШЕН:

```
CODE METRICS:
✅ Одна точка входа для LLM calls (orchestrator.call_agent)
✅ Нет дублирования кода provider detection
✅ Нет hardcoded HTTP endpoints в handlers
✅ Message format consistent везде

FUNCTIONALITY METRICS:
✅ Solo chat работает с всеми провайдерами
✅ Group chat продолжает работать
✅ Streaming работает в обоих
✅ Error handling consistent

PERFORMANCE METRICS:
✅ Solo не замедлился более чем на 10%
✅ Group не замедлился
✅ Streaming latency не увеличилась

TEST METRICS:
✅ 100% регрессионных тестов pass
✅ Новые тесты для unified system pass
✅ Integration тесты pass
```

---

## 📞 КОГО СПРОСИТЬ

- **Вопросы об архитектуре:** Смотри HAIKU_4_SOLO_VS_GROUP_CRITICAL.md
- **Вопросы о потоках:** Смотри HAIKU_4_FLOW_DIAGRAMS.md
- **Вопросы о деталях кода:** Смотри HAIKU_4_FIX_MARKERS.md
- **Вопросы об реализации:** Используй маркеры в HAIKU_4_FIX_MARKERS.md

---

## 📝 ВЕРСИОНИРОВАНИЕ

- **Документ:** HAIKU 4 Index
- **Версия:** 1.0
- **Создано:** Phase 92
- **Для:** VETKA Live v0.3
- **Состояние:** ГОТОВО К ИСПОЛЬЗОВАНИЮ
- **Последняя проверка:** 2026-01-25

---

## 🏁 НАЧНИТЕ ОТСЮДА

1. **Прочитайте:** HAIKU_4_SOLO_VS_GROUP_CRITICAL.md (~20 min)
2. **Посмотрите:** HAIKU_4_FLOW_DIAGRAMS.md (~15 min)
3. **Используйте:** HAIKU_4_FIX_MARKERS.md при разработке
4. **Следуйте:** Implementation Checklist в HAIKU_4_FIX_MARKERS.md

**Время для полного понимания:** ~1-2 часа

**Время для реализации:** ~6-9 часов

**Валидация и тестирование:** ~2-4 часов

**TOTAL:** ~1-2 недели work

---

## ✅ ЧТО ДАЛЬШЕ

После прочтения этого документа:

1. [ ] Создай feature branch
2. [ ] Прочитай все 4 документа
3. [ ] Создай план реализации
4. [ ] Начни с TIER 1 маркеров
5. [ ] Тестируй каждый маркер
6. [ ] Создай PR
7. [ ] Code review
8. [ ] Merge и deploy

**Good luck! 🚀**
