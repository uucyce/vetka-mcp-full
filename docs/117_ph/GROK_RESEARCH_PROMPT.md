# Grok Research Prompt: LLM Provider Balance/Billing APIs

> Copy the content below the line into a Grok chat for systematic research.
> Date: 2026-02-07 | Phase: 117.1 Balance Intelligence

---

Привет Грок! Нужно глубокое системное исследование. Ты — единственный кто может это сделать качественно, потому что у тебя доступ к актуальной документации и коду на GitHub.

## Задача

Как программно узнать баланс/лимиты/квоту у различных LLM API провайдеров? Мне нужны **точные endpoints, JSON schemas ответов, и реальные curl-примеры.**

## Контекст проекта

Проект VETKA — AI-агрегатор с UnifiedKeyManager, управляющий 30+ API-ключами от 10+ провайдеров. Нужно показывать в UI реальный баланс каждого ключа.

**Текущая реализация (сломанная):**
```python
BALANCE_ENDPOINTS = {
    'openrouter': {
        'url': 'https://openrouter.ai/api/v1/auth/key',
        'auth': 'Bearer',
        'parse': lambda data: {
            'balance': data.get('data', {}).get('limit_remaining'),  # BUG!
            'limit': data.get('data', {}).get('limit'),
            'used': data.get('data', {}).get('usage')
        }
    },
    'polza': {
        'url': 'https://api.polza.ai/api/v1/account/balance',
        'auth': 'Bearer',
        'parse': lambda data: {
            'balance': data.get('balance'),
            'limit': data.get('limit'),
            'used': data.get('used')
        }
    }
}
```

## ЧАСТЬ 1: OPENROUTER — КРИТИЧЕСКИЙ БАГ

OpenRouter `/api/v1/auth/key` возвращает для free-tier ключа:
```json
{"data": {"limit": null, "limit_remaining": 9999.79, "usage": 0.21}}
```
Мы парсим `limit_remaining` как баланс, но это КРЕДИТНЫЙ ЛИМИТ free-tier ($10k), а не реальные деньги. Ключ реально пуст и отдаёт 402.

**Вопросы:**
1. Какой ПОЛНЫЙ JSON schema ответа `/api/v1/auth/key`? Все поля без исключения.
2. Есть ли поле `is_free_tier`, `tier`, `plan_type` или аналог для отличия free от paid?
3. Для free-tier: как программно определить что credits исчерпаны? Есть ли `credits_remaining`, `free_credits_used`?
4. Для paid-tier: `limit_remaining` — это реальный баланс? Или нужно смотреть другое поле?
5. Что возвращает endpoint когда ключ реально пуст ($0)?
6. Есть ли другие endpoints? `/api/v1/credits/remaining`? `/api/v1/account/billing`?
7. Rate limits на этот endpoint — можно ли вызывать каждые 30 секунд?
8. Поискай на GitHub issues OpenRouter — есть ли обсуждения этой проблемы?

## ЧАСТЬ 2: BALANCE API У КАЖДОГО ПРОВАЙДЕРА

Для КАЖДОГО провайдера ниже мне нужно:
- **Endpoint URL** (если есть прямой balance/billing API)
- **Метод аутентификации** (Bearer, x-api-key, ?key= query param, etc.)
- **Полный JSON schema ответа**
- **Rate limits** на balance endpoint
- **Альтернативы** если прямого API нет:
  - Rate-limit headers из ответов на обычные запросы
  - Error codes как индикаторы (402, 429, 403, 503)
  - Cloud console billing APIs
- **Отличие free от paid tier**
- **curl пример** (с placeholder для ключа)

### 2.1 Google Gemini (generativelanguage.googleapis.com)

- Есть ли billing/quota API? Через Google Cloud Billing API (`cloudbilling.googleapis.com`)?
- Через Service Usage API (`serviceusage.googleapis.com/v1/services/generativelanguage.googleapis.com`)?
- Какие rate-limit headers возвращает Gemini в ответах? `x-ratelimit-*`? `x-goog-*`?
- Как отличить free-tier (API Key) от paid (Vertex AI / Cloud Billing)?
- Gemini возвращает 429 при превышении квоты — какие конкретно headers в этом ответе?

### 2.2 xAI / Grok (api.x.ai)

- Какой актуальный домен? `api.x.ai`? `api.xai.com`?
- Есть ли `/v1/account/balance` или `/v1/billing` endpoint?
- $25/month free credit — как проверить остаток?
- Rate-limit headers в ответах? `x-ratelimit-remaining-requests`?
- 402 при исчерпании free credit — какой точно response body?

### 2.3 Anthropic (api.anthropic.com)

- Есть ли billing/usage endpoint? `/v1/usage`? `/v1/billing`?
- `anthropic-ratelimit-requests-limit`, `anthropic-ratelimit-requests-remaining` — полный список headers?
- `anthropic-ratelimit-tokens-limit`, `anthropic-ratelimit-tokens-remaining` — в каких endpoint?
- Как определить tier (free trial / scale / build)?
- 429 response — какие поля в body?

### 2.4 Mistral (api.mistral.ai)

- Billing endpoint? `/v1/billing/usage`?
- Rate-limit headers?
- Free-tier vs paid detection?

### 2.5 DeepSeek (api.deepseek.com)

- Balance/billing endpoint? Видел `/user/balance` — правда?
- Auth: `Authorization: Bearer sk-xxx`?
- Response schema?

### 2.6 OpenAI (api.openai.com)

- `/v1/dashboard/billing/credit_grants` — ещё работает или deprecated?
- `/v1/organization/usage` — актуальный?
- Какой текущий способ проверить баланс через API?
- Rate-limit headers: `x-ratelimit-remaining-requests`, `x-ratelimit-remaining-tokens` — полный список?

### 2.7 NanoGPT (nano-gpt.com)

- Это агрегатор — есть ли balance API?

### 2.8 Perplexity (api.perplexity.ai)

- Billing endpoint?
- Rate-limit headers?

### 2.9 Polza AI (api.polza.ai)

- `/api/v1/account/balance` — какой точный response schema? Поля?
- Rate limits?

## ЧАСТЬ 3: КАК ЭТО ДЕЛАЮТ ДРУГИЕ

Мне критически важно знать подходы существующих инструментов:

### LiteLLM (github.com/BerriAI/litellm)
- Есть ли у них balance checking per key?
- Как реализован key rotation при 402/429? Найди конкретный файл и функцию.
- `litellm.budget_manager` — что он делает? Как трекает usage?
- `litellm.Router` — как обрабатывает failed keys?

### Cursor IDE
- Как Cursor показывает "usage remaining" в Settings > Models?
- Вызывает ли он provider APIs или трекает usage локально?
- Как обрабатывает quota exhaustion?

### Continue.dev (github.com/continuedev/continue)
- Multi-provider key management — как показывают баланс?
- Есть ли balance checking code?
- Файл/модуль отвечающий за provider health?

### RouteLLM (github.com/lm-sys/RouteLLM)
- Balance-aware routing? Cost-aware routing?

### OpenLIT / Helicone / Langfuse
- Как proxy-сервисы трекают billing per key?

## ЧАСТЬ 4: ЖЕЛАЕМЫЙ ФОРМАТ ОТВЕТА

### Таблица 1: Provider Balance APIs
| Provider | Balance Endpoint | Auth Method | Key Response Fields | Free/Paid Detection | Rate Limit | Reliability |
|----------|-----------------|-------------|--------------------|--------------------|-----------|------------|

### Таблица 2: Rate-Limit Headers
| Provider | Header | Type (requests/tokens) | In Which Responses | Example Value |
|----------|--------|----------------------|-------------------|--------------|

### Таблица 3: Error Codes как Balance Signals
| Provider | 402 | 429 | 403 | Other Codes | Response Body on Error |
|----------|-----|-----|-----|-------------|----------------------|

### Секция: Подходы других инструментов
- LiteLLM: подход + ключевые файлы
- Cursor: подход
- Continue.dev: подход
- Общие паттерны

### Секция: Рекомендуемая архитектура для VETKA
На основе исследования, какой лучший паттерн для multi-provider balance системы? Учитывая:
- Провайдеры С balance API (OpenRouter, Polza, OpenAI?, DeepSeek?)
- Провайдеры БЕЗ balance API (Gemini, xAI, Anthropic, Mistral)
- Error-code-based inference (402 → balance=0)
- Rate-limit header tracking как proxy для "здоровья" ключа
- Caching strategy (как часто опрашивать)

### Секция: curl примеры
Для каждого провайдера где есть API — готовый curl с placeholder `$API_KEY`.
