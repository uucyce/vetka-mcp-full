# PHASE 90.9.3: Reply Routing Issue Investigation
**Дата:** 2026-01-23
**Статус:** RECON
**Приоритет:** HIGH

## Проблема
Reply (ответ на сообщение) в групповом чате не работает:
- ✅ Solo chat: Reply работает (через @mention handler)
- ❌ Group chat: Reply падает на Architect (ChatGPT) с ошибкой 404
- ❌ OpenRouter fallback не срабатывает при 404

## Архитектура Reply в группах

### Phase 80.7: Reply Routing Introduction
Добавлен механизм reply_to_id:
- Frontend отправляет `reply_to_id` с сообщением
- Backend ищет оригинальное сообщение и его отправителя
- Маршрутизирует ответ конкретному агенту

```python
# src/api/handlers/group_message_handler.py:604-616
reply_to_id = data.get('reply_to')  # Phase 80.7
if reply_to_id:
    messages = manager.get_messages(group_id, limit=100)
    for msg in messages:
        if msg.get('id') == reply_to_id:
            original_sender = msg.get('sender_id', '')
            if original_sender.startswith('@'):
                reply_to_agent = original_sender  # Пример: '@Researcher'
```

### Прохождение через select_responding_agents()
```python
# src/services/group_chat_manager.py:198-211
if reply_to_agent:
    reply_to_normalized = reply_to_agent.lower().lstrip('@')
    for pid, p in participants.items():
        agent_id = p.get('agent_id', '').lower().lstrip('@')
        if agent_id == reply_to_normalized:
            if p.get('role') != 'observer':
                return [p]  # Вернуть агента для ответа
    # WARN: Если агент не найден, упадет на default selection
```

## MARKER_90.9.3_A: Критический баг - неправильная нормализация agent_id

**Локация:** `src/services/group_chat_manager.py:205`

Код нормализует `agent_id` ДВАЖДЫ:
```python
reply_to_normalized = reply_to_agent.lower().lstrip('@')  # '@Researcher' -> 'researcher'
agent_id_normalized = agent_id.lower().lstrip('@')        # '@Researcher' -> 'researcher'
# Сравнение: 'researcher' == 'researcher' ✅
```

Но есть один случай когда это НЕ работает:
- `reply_to_agent` = '@gpt-5.2-pro' (получено из msg.sender_id)
- `agent_id` в participants = 'Architect (gpt-5.2-pro)' или иное имя

**Проблема:** `display_name` и `agent_id` в participants NOT matching в структуре!

### MARKER_90.9.3_B: Model ID routing issue

**Локация:** `data/groups.json` + routing logic

В группах используются model_ids:
```json
{
  "participants": {
    "p1": {
      "agent_id": "@Researcher",
      "display_name": "Researcher (Grok 4)",
      "model_id": "grok-4"
    }
  }
}
```

Но когда reply приходит от этого агента, sender_id может быть:
1. `@Researcher` (корректное имя)
2. `@grok-4` (model_id, если неправильно передан)
3. Что-то другое

Если мэтчинг не сработал → fallback → **DEFAULT SELECTION** (Architect)

```python
# src/services/group_chat_manager.py:256-257
# WARN: If @mention exists but NOT found in participants
logger.info(f"Phase 80.27: @mention not found - skipping default (likely model/MCP)")
return []  # SHOULD be [], not default!
```

## MARKER_90.9.3_C: 404 Error from OpenRouter

**Локация:** `src/elisya/provider_registry.py:602`

OpenRouterProvider не обрабатывает 404:
```python
response.raise_for_status()  # Line 602
# Это выбросит HTTPStatusError для 404
```

404 от OpenRouter означает:
- Model не существует на OpenRouter
- Неправильный model_id отправлен
- Например: `grok-4` вместо `x-ai/grok-4`

## MARKER_90.9.3_D: Fallback logic NOT triggered

**Локация:** `src/orchestration/orchestrator_with_elisya.py:1205-1213`

```python
try:
    llm_response = await self._call_llm_with_tools_loop(
        prompt=prompt,
        agent_type=agent_type,
        model=model_name,
        provider=provider_enum
    )
except Exception as e:
    print(f"❌ {agent_type} LLM/Tool error: {str(e)}")
    output = f"Error in {agent_type}: {str(e)}"
```

**ПРОБЛЕМА:**
- Fallback к OpenRouter есть ВНУТРИ `_call_llm_with_tools_loop` (line 985-994)
- НО он ловит ТОЛЬКО `XaiKeysExhausted`
- 404 error от OpenRouter не перехватывается → Exception -> error message

## MARKER_90.9.3_E: Root cause analysis

**Цепочка ошибок:**

1. **Reply routing в group chat**
   - Frontend: `reply_to_id` = "msg-uuid"
   - Backend: Ищет original message
   - Получает: `sender_id` = "@Researcher" (example)

2. **select_responding_agents(reply_to_agent="@Researcher")**
   - Ищет в participants.agent_id где agent_id.lower().lstrip('@') == 'researcher'
   - НАХОДИТ ✅
   - Возвращает participant с model_id = "grok-4"

3. **call_agent() в orchestrator**
   - agent_type='Researcher'
   - model_id='grok-4'
   - Маршрутизирует в _run_agent_with_elisya_async()

4. **Routing detection in orchestrator (line 1141-1160)**
   ```python
   if agent_type in self.model_routing and self.model_routing[agent_type].get('provider') == 'manual':
       manual_model = self.model_routing[agent_type]['model']  # 'grok-4'
       detected_provider = ProviderRegistry.detect_provider(manual_model)  # XAI ✅
   ```
   - detect_provider('grok-4') = Provider.XAI ✅
   - Fallback check (line 1150-1154):
   ```python
   if real_provider == 'xai':
       if not APIKeyService().get_key('xai'):
           real_provider = 'openrouter'  # FALLBACK если нет xai key
   ```

5. **call_model_v2() с Provider.OPENROUTER**
   - model='grok-4' (остается без изменений!)
   - OpenRouter NE recognizes 'grok-4'
   - OpenRouter expects 'x-ai/grok-4'
   - 404 NOT FOUND

6. **OpenRouterProvider.call() (line 602)**
   ```python
   response.raise_for_status()  # Throws HTTPStatusError(404)
   ```
   - Exception propagates up
   - ТОЛЬКО XaiKeysExhausted перехватывается
   - 404 → generic Exception → error message

7. **Fallback to Architect happens when?**
   - `select_responding_agents()` не находит reply_to_agent → returns []
   - ИЛИ exception в orchestrator → error state → default agent selection

## MARKER_90.9.3_F: Solo chat works - почему?

**Solo chat flow** (через @mention):
- src/api/handlers/mention/mention_handler.py:238-241
  ```python
  response_text = await self._call_openrouter_model(
      model_to_use,  # 'grok-4' или 'x-ai/grok-4'?
      model_prompt
  )
  ```

- _call_openrouter_model (line 416-484)
  ```python
  for attempt in range(max_retries):
      api_key = get_openrouter_key()
      # ... POST request
      if resp.status_code in [401, 402]:
          rotate_openrouter_key(mark_failed=True)
          continue
      else:
          # 404 HANDLED? Let's check...
          print(f"OpenRouter error: {resp.status_code} - {resp.text}")
          response_text = f"Error: {resp.status_code}"
          break  # EXIT loop, return error message
  ```

**AHA!** Solo chat НЕ имеет fallback - он просто возвращает error message!
Но "Reply works in solo chat" означает что model_id корректный в solo?

→ НАДО ПРОВЕРИТЬ что именно передается в solo vs group chat!

## MARKER_90.9.3_G: Missing model_id correction

**Гипотеза:**
В solo chat, когда user пишет "@grok", parse_mentions() вероятно корректирует это:
- Пользователь вводит: "@grok"
- parse_mentions() находит это и преобразует в 'x-ai/grok-4' или 'grok-4'

А в group chat:
- reply_to_agent = "@Researcher"
- Берется model_id из participants = 'grok-4'
- В orchestrator НЕ происходит коррекция 'grok-4' → 'x-ai/grok-4'
- OpenRouter не может найти model

## MARKER_90.9.3_H: Fallback Logic MISSING

В call_model_v2() (line 862-889):
```python
try:
    result = await provider_instance.call(messages, model, tools, **kwargs)
    return result
except XaiKeysExhausted as e:
    # Phase 80.39: Fallback to OpenRouter with x-ai/ prefix
    openrouter_model = f"x-ai/{model}" if not model.startswith('x-ai/') else model
    result = await openrouter_provider.call(messages, openrouter_model, tools)
    return result
except ValueError as e:  # API key not found
    # Try OpenRouter fallback
    if provider in (Provider.OPENAI, Provider.ANTHROPIC, Provider.GOOGLE, Provider.XAI):
        openrouter_provider = registry.get(Provider.OPENROUTER)
        result = await openrouter_provider.call(messages, model, None)
        return result
except Exception as e:  # ← Generic exception handler
    print(f"[REGISTRY] {provider.value} failed: {e}")
    raise  # ← RE-RAISES exception! No fallback!
```

**ПРОБЛЕМА:** 404 httpx error от OpenRouter попадает в generic Exception handler и RE-RAISES!

## MARKER_90.9.3_I: Где Architect попадает по умолчанию?

**Гипотеза:** После error в call_agent():
```python
# orchestrator_with_elisya.py:2152-2158
except Exception as e:
    logger.error(f"[Orchestrator] call_agent failed: {e}")
    return {
        'output': '',
        'error': str(e),
        'status': 'error'
    }
```

Возвращается error status, но групповой chat handler может не заметить и fallback на default agent?

Надо проверить group_message_handler.py:748-754:
```python
if result.get('status') == 'done':
    response_text = result.get('output', '')
else:
    response_text = f"[Error: {result.get('error', 'Unknown error')}]"
```

Если error - просто выводит error, не переходит на другого агента.

**ВОПРОС:** Почему Architect?
→ Надо проверить какой agent был выбран для reply!

## Рекомендации по исправлению

### ISSUE 1: Model ID коррекция
```python
# LOCATION: src/orchestration/orchestrator_with_elisya.py:1155-1160
# FIX: Normalize model_id for OpenRouter fallback
if real_provider == 'openrouter':
    manual_model = f"x-ai/{manual_model}" if manual_model in ['grok-4', 'grok-3'] else manual_model
```

### ISSUE 2: 404 error handling
```python
# LOCATION: src/elisya/provider_registry.py:862-892
# FIX: Catch httpx HTTP errors and fallback
except httpx.HTTPStatusError as http_err:
    if http_err.response.status_code == 404:
        # Model not found on provider, try OpenRouter
        if provider != Provider.OPENROUTER:
            openrouter_provider = registry.get(Provider.OPENROUTER)
            openrouter_model = f"x-ai/{model}" if not model.startswith('x-ai/') else model
            return await openrouter_provider.call(messages, openrouter_model, None)
    raise
```

### ISSUE 3: Fallback for generic model errors
```python
# LOCATION: src/orchestration/orchestrator_with_elisya.py:1090-1110
# FIX: Handle 404 errors from any provider
except Exception as e:
    if '404' in str(e) or 'not found' in str(e).lower():
        print(f"Model not found, trying OpenRouter...")
        openrouter_provider = registry.get(Provider.OPENROUTER)
        openrouter_model = f"x-ai/{model}" if not model.startswith('x-ai/') else model
        return await openrouter_provider.call(messages, openrouter_model, None)
    raise
```

## Дополнительно: Solo vs Group Различия

| Компонент | Solo Chat | Group Chat |
|-----------|-----------|-----------|
| Entry point | @mention parsing | reply_to_id routing |
| Model source | parse_mentions() | participants[].model_id |
| Model validation | Inline в mention_handler | orchestrator routing |
| Error handling | Custom retry loop | Generic exception |
| Fallback provider | None (just error) |架构 default selection |

## Необходимые проверки

- [ ] Проверить что именно находится в `msg.sender_id` для @Researcher в replies
- [ ] Проверить структуру participants - как матчится agent_id с display_name
- [ ] Проверить что происходит в select_responding_agents если reply_to_agent не найден
- [ ] Проверить полное содержимое error message когда 404 происходит
- [ ] Проверить находится ли fallback в call_agent при HTTP errors

## Файлы для анализа

1. ✅ src/api/handlers/group_message_handler.py (604-627) - Reply routing
2. ✅ src/services/group_chat_manager.py (165-211) - Agent selection
3. ✅ src/orchestration/orchestrator_with_elisya.py (1121-1250) - LLM call logic
4. ✅ src/elisya/provider_registry.py (821-892) - Model calling + fallback
5. ⚠️ src/api/handlers/mention/mention_handler.py (238-484) - Solo @mention comparison
6. ⚠️ data/groups.json - Реальная структура participants и sender_id

---

**Статус:** ✅ RECON завершена
**Следующий шаг:** MARKER findings → Root cause validation → Fix implementation
