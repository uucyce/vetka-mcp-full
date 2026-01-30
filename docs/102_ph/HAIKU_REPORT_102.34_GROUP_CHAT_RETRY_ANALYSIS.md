# HAIKU REPORT 102.34: Group Chat OpenRouter Retry Analysis

**Date:** 2025-01-30
**Phase:** 102
**Status:** ROOT CAUSE FOUND

---

## EXECUTIVE SUMMARY

**Problem:** Group chat fails with "All OpenRouter keys exhausted after 13 attempts" while solo chat works fine.

**Root Cause:** ТРИ СЛОЯ КОНФЛИКТУЮЩЕЙ ЛОГИКИ RETRY:
1. `call_agent()` - 3 попытки внешний цикл (MARKER_102.32)
2. `_run_agent_with_elisya_async()` - ловит ошибки и ротирует (MARKER_102.33)
3. `OpenRouterProvider.call()` - свой 13-ключевой retry цикл (Phase 100.1)

**Вложенные циклы вызывают исчерпание ключей!**

---

## CALL CHAIN COMPARISON

### SOLO CHAT (РАБОТАЕТ):
```
user_message_handler_v2.py
  ↓
call_model_v2() [provider_registry.py]
  ↓
OpenRouterProvider.call()
  └─ max_retries = 13 ключей
  └─ Пробует все ключи с ротацией
  └─ Success ✓
```

### GROUP CHAT (СЛОМАН):
```
group_message_handler.py::route_to_agents()
  ↓ Line 684
orchestrator.call_agent()
  ├─ MARKER_102.32: 3 попытки внешний цикл
  ├─ Attempt 1:
  │   ├─ _run_agent_with_elisya_async()
  │   │   ├─ MARKER_102.33: catch + rotate
  │   │   └─ _call_llm_with_tools_loop()
  │   │       ├─ call_model_v2()
  │   │       └─ OpenRouterProvider.call()
  │   │           └─ max_retries = 13
  │   │           └─ Пробует все 13 → FAILS
  │   └─ Exception всплывает в call_agent()
  ├─ Ловит на line 2404
  ├─ Ротирует ключ (line 2416)
  └─ Retry loop continues...
      └─ Result: "All OpenRouter keys exhausted after 13 attempts"
```

---

## ALL MARKERS FOUND

### Phase 102 (ВНОСИТ БАГ)

| Marker | File | Lines | Issue |
|--------|------|-------|-------|
| MARKER_102.30 | orchestrator_with_elisya.py | 1253-1263 | Fix model name normalization (OK) |
| **MARKER_102.32** | orchestrator_with_elisya.py | 2385-2428 | **RETRY LOOP - КОНФЛИКТ!** |
| **MARKER_102.33** | orchestrator_with_elisya.py | 1355 | **Extended error detection - REDUNDANT** |

### Phase 100.1 (Стабильная база)

| Location | Purpose |
|----------|---------|
| provider_registry.py:717 | max_retries = все ключи |
| provider_registry.py:754-776 | km.report_failure() handling |

### Phase 94 (Стабильная)

| Marker | Location | Purpose |
|--------|----------|---------|
| MARKER_94.1 | provider_registry.py:717 | Use all OpenRouter keys |

---

## КОНФЛИКТ #1: ВЛОЖЕННЫЕ RETRY LOOPS

```
Outer: call_agent() - 3 попытки
  └─ Inner: OpenRouterProvider - 13 попыток

Теоретически: 3 × 13 = 39 попыток
Фактически: Показывает 13 (счётчик OpenRouter)
```

## КОНФЛИКТ #2: РОТАЦИЯ НА НЕСКОЛЬКИХ УРОВНЯХ

```
Level 1: call_agent() line 2416 → km.rotate_to_next()
Level 2: _run_agent_with_elisya_async() line 1360 → km.rotate_to_next()
Level 3: OpenRouterProvider lines 758, 770 → km.report_failure()

Результат: Один ключ может быть помечен failed несколько раз
```

---

## RECOMMENDED FIX

**Удалить MARKER_102.32** из `orchestrator_with_elisya.py` (lines 2385-2428)

**Почему это сработает:**
- `_run_agent_with_elisya_async()` уже имеет error handling (line 1354-1375)
- `OpenRouterProvider.call()` уже retry через все ключи
- `call_model_v2()` имеет fallback на OpenRouter
- Без вложенных циклов - нет "13 attempts" exhaustion

---

## ПОСЛЕ ФИКСА - ЧИСТЫЙ ПУТЬ

```
group_message_handler.py
  ↓
orchestrator.call_agent()
  ↓ БЕЗ внешнего retry loop
_run_agent_with_elisya_async()
  ├─ Error catch line 1354
  └─ Single retry with rotate
    ↓
_call_llm_with_tools_loop()
  ↓
call_model_v2()
  ↓
OpenRouterProvider.call()
  └─ max_retries = 13 (fresh count)
  └─ for attempt in range(13):
     └─ Пробует каждый ключ
     └─ 402/429: rotates
     └─ Success ✓
```

---

## CONFIDENCE LEVEL: ОЧЕНЬ ВЫСОКИЙ ✓

Доказательства:
- Маркеры показывают что добавлено в Phase 102 (очень недавно)
- Solo chat НЕ использует `call_agent()` → работает
- Group chat ЕДИНСТВЕННЫЙ путь через `call_agent()` с retry loop
- "13 attempts" = точное число OpenRouter ключей
- Все три уровня retry задокументированы

---

## TESTING CHECKLIST

После фикса:
- [ ] Solo chat работает (путь не изменён)
- [ ] Group chat без "exhausted" ошибки
- [ ] OpenRouterProvider.call() всё ещё retry на 402/429
- [ ] call_agent() возвращает сразу при успехе
- [ ] Ошибки чище (одна ошибка, не вложенные)
