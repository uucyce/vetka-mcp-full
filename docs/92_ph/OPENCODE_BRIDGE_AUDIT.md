# OPENCODE DESKTOP → VETKA BRIDGE AUDIT

**Phase 92 | Date: 2026-01-23**
**Status: РАЗВЕДКА ЗАВЕРШЕНА**
**Результат: НАЙДЕН БАГ В СТРОКЕ 872**

---

## ПРОБЛЕМА

OpenCode Desktop не может через bridge звонить на OpenRouter модели.
Считает что лимиты XAI кончились.
**В VETKA всё работает отлично!** (Grok, ChatGPT, всё ок)

---

## КРИТИЧЕСКИЙ БАГ

### 📍 MARKER-PROVIDER-004: provider_registry.py:872

```python
# ТЕКУЩИЙ КОД (баг):
openrouter_model = f"x-ai/{model}" if not model.startswith('x-ai/') else model

# ПРОБЛЕМА:
# Если model = 'xai/grok-beta':
#   - Проверка 'not model.startswith("x-ai/")' = True (потому что 'xai/' ≠ 'x-ai/')
#   - Результат: 'x-ai/xai/grok-beta' ❌ (двойной префикс!)

# ДОЛЖНО БЫТЬ:
openrouter_model = f"x-ai/{model.replace('xai/', '')}" if not model.startswith('x-ai/') else model
# Или:
openrouter_model = model if model.startswith(('x-ai/', 'xai/')) else f"x-ai/{model}"
```

---

## ВСЕ МАРКЕРЫ

### MCP BRIDGE (vetka_mcp_bridge.py)

| Маркер | Файл:Строка | Описание |
|--------|-------------|----------|
| MARKER-MCP-001 | vetka_mcp_bridge.py:754-765 | Model name передаётся AS-IS без преобразования |
| MARKER-MCP-002 | llm_call_tool.py:215 | Нормализация алиасов (grok→grok-4) |
| MARKER-MCP-003 | llm_call_tool.py:257 | Provider detection через detect_provider() |

### PROVIDER REGISTRY (provider_registry.py)

| Маркер | Файл:Строка | Описание |
|--------|-------------|----------|
| MARKER-PROVIDER-001 | provider_registry.py:25-28 | XaiKeysExhausted exception |
| MARKER-PROVIDER-002 | provider_registry.py:651 | XaiProvider НЕ очищает model name |
| MARKER-PROVIDER-003 | provider_registry.py:677-706 | Механизм fallback при 403 |
| **MARKER-PROVIDER-004** | **provider_registry.py:866-875** | **БАГ: x-ai/xai/ двойной префикс** |
| MARKER-PROVIDER-005 | provider_registry.py:801-803 | detect_provider xai patterns |
| MARKER-PROVIDER-006 | provider_registry.py:884 | ValueError fallback БЕЗ преобразования |

### LLM CALL TOOL (llm_call_tool.py)

| Маркер | Файл:Строка | Описание |
|--------|-------------|----------|
| MARKER-LLM-001 | llm_call_tool.py:95-112 | Детекция провайдера |
| MARKER-LLM-002 | llm_call_tool.py:114-122 | Нормализация aliases |
| MARKER-LLM-003 | llm_call_tool.py:212-301 | Вызов call_model_v2 |
| MARKER-LLM-004 | llm_call_tool.py:34-93 | Входной формат schema |
| MARKER-LLM-005 | provider_registry.py:786-810 | CANONICAL detect_provider |
| MARKER-LLM-006 | provider_registry.py:821-893 | call_model_v2 сигнатура |
| MARKER-LLM-007 | open_router_bridge.py:67-95 | OpenRouter Bridge invoke() |

---

## ПОТОК ДАННЫХ

```
OpenCode Desktop
    ↓
[1] Отправляет: model = "xai/grok-beta" или "grok-4"
    ↓
[2] vetka_mcp_bridge.py → LLMCallTool.execute()
    ↓
[3] _normalize_model_name(): "grok" → "grok-4" (aliases)
    ↓
[4] _detect_provider(): "grok-4" → Provider.XAI
    ↓
[5] call_model_v2(model="grok-4", provider=Provider.XAI)
    ↓
[6] XaiProvider.call() → 403 Forbidden (keys exhausted)
    ↓
[7] raise XaiKeysExhausted
    ↓
[8] ⚠️ СТРОКА 872: fallback к OpenRouter
    openrouter_model = f"x-ai/{model}"
    Если model="xai/grok-beta" → "x-ai/xai/grok-beta" ❌
    ↓
[9] OpenRouter API получает неправильный формат → ERROR
```

---

## ПОЧЕМУ В VETKA РАБОТАЕТ?

1. VETKA orchestrator явно указывает `Provider.OPENROUTER`
2. Fallback логика (строка 872) гарантирует правильный формат для `grok-*`
3. Model name приходит как `grok-4` (без `xai/` префикса)

## ПОЧЕМУ В OPENCODE НЕ РАБОТАЕТ?

1. OpenCode может отправлять `xai/grok-beta` (с префиксом)
2. detect_provider() возвращает `Provider.XAI` ✓
3. XaiProvider пытается вызвать x.ai API напрямую
4. 403 → fallback к OpenRouter
5. **БАГ строка 872:** `"x-ai/" + "xai/grok-beta"` = `"x-ai/xai/grok-beta"` ❌

---

## ВТОРОЙ БАГ

### 📍 MARKER-PROVIDER-006: provider_registry.py:884

```python
except ValueError as e:
    # API key not found - try OpenRouter as fallback
    result = await openrouter_provider.call(messages, model, None, **kwargs)
    #                                        ^^^^^ БЕЗ преобразования!
```

Если XAI key не найден (ValueError), OpenRouter вызывается с `model` AS-IS.
Нет преобразования `xai/grok-beta` → `x-ai/grok-beta`.

---

## РЕКОМЕНДАЦИИ

### Фикс 1: Строка 872 (XaiKeysExhausted fallback)

```python
# БЫЛО:
openrouter_model = f"x-ai/{model}" if not model.startswith('x-ai/') else model

# СТАЛО:
# Убираем любой xai/ префикс перед добавлением x-ai/
clean_model = model.replace('xai/', '').replace('x-ai/', '')
openrouter_model = f"x-ai/{clean_model}"
```

### Фикс 2: Строка 884 (ValueError fallback)

```python
# БЫЛО:
result = await openrouter_provider.call(messages, model, None, **kwargs)

# СТАЛО:
# Тот же паттерн для консистентности
clean_model = model.replace('xai/', '').replace('x-ai/', '')
openrouter_model = f"x-ai/{clean_model}" if provider == Provider.XAI else model
result = await openrouter_provider.call(messages, openrouter_model, None, **kwargs)
```

---

## ФАЙЛЫ ДЛЯ ИСПРАВЛЕНИЯ

| Файл | Строка | Действие |
|------|--------|----------|
| `src/elisya/provider_registry.py` | 872 | Фикс двойного префикса x-ai/xai/ |
| `src/elisya/provider_registry.py` | 884 | Добавить преобразование для XAI |

---

## СТАТУС

- [x] Разведка завершена
- [x] Баг найден (строка 872)
- [x] Второй баг найден (строка 884)
- [ ] Фикс применён (ЖДЁТ ПОДТВЕРЖДЕНИЯ)

**КОД НЕ МЕНЯЛСЯ. ТОЛЬКО МАРКЕРЫ.**
