# Phase 117 — Баги и задачи для следующей сессии

**Дата:** 2026-02-07
**Контекст:** Phase 117 Provider Intelligence реализован, но обнаружены баги при реальном использовании.

---

## КРИТИЧЕСКИЕ БАГИ Phase 117

### BUG-1: OpenRouter показывает $9999.79 — фейковый баланс 🔴

**Симптом:** На UI два OpenRouter ключа показывают $9999.79, но ВСЕ 13 ключей получают 402 Payment Required.

**Причина:**
- OpenRouter API `/api/v1/auth/key` возвращает `limit_remaining` = кредитный лимит free-tier ($10,000)
- Мы парсим это как "баланс": `data.get('data', {}).get('limit_remaining')`
- Но это НЕ реальные деньги — это лимит кредита. Реально ключ пустой.
- OpenRouter free-tier: `limit = null`, `limit_remaining = 9999.79`, `usage = 0.21` — значит потратили $0.21, осталось до лимита $9999.79
- Но при этом 402 — потому что free-tier credit закончился, а `limit_remaining` считает от общего лимита аккаунта

**Файл:** `src/utils/unified_key_manager.py:465-469`

**Решение:**
- Нужно проверять `data.data.is_free_tier` или `data.data.limit == null`
- Для free-tier ключей: `balance = 0`, потому что реально credits = 0
- Для paid ключей: `balance = limit_remaining` — это правильно
- Дополнительно: если ключ получил 402, принудительно ставить `balance = 0`

---

### BUG-2: balance_percent не передаётся на фронтенд 🔴

**Симптом:** Balance bar показывает 0% всегда (fallback `|| 0`).

**Причина:** Фронтенд ожидает `balanceData.percent` (line 439 ModelDirectory.tsx), но API `/api/keys/balance` возвращает только `{balance, limit, used}` — БЕЗ `percent`.

**Файлы:**
- `src/api/routes/config_routes.py:608-610` — не вычисляет percent
- `client/src/components/ModelDirectory.tsx:439` — `balance_percent: balanceData.percent` → undefined

**Решение:**
- В `/api/keys/balance` добавить: `result[provider_name]['percent'] = round((balance / limit) * 100, 1)` если limit > 0
- ИЛИ вычислять на фронтенде: `balance_percent: limit > 0 ? (balance / limit) * 100 : 0`

---

### BUG-3: Баланс только для OpenRouter + Polza — нет для Gemini, xAI, Anthropic 🟡

**Симптом:** Gemini ключи показывают только "active", без баланса.

**Причина:** `BALANCE_ENDPOINTS` в unified_key_manager.py содержит только 2 провайдера:
- `openrouter` → `https://openrouter.ai/api/v1/auth/key`
- `polza` → `https://api.polza.ai/api/v1/account/balance`

Для Gemini, xAI, Anthropic, Mistral — нет endpoints. Это ожидаемо, но нужно исследовать.

---

### BUG-4: 402 не обнуляет баланс в UI 🟡

**Симптом:** Ключ получил 402, помечен rate-limited, но UI продолжает показывать $9999.79.

**Причина:** `fetch_provider_balance()` и стриминг — разные flow. Стриминг обнаруживает 402 и ставит cooldown, но не обновляет `balance` поле в APIKeyRecord. Balance fetch — отдельный async вызов, который не знает про 402 из стриминга.

**Решение:** В `_report_key_failure()` при 402 сразу ставить `record.balance = 0`.

---

### BUG-5: Баланс одинаковый для всех ключей одного провайдера 🟡

**Симптом:** Оба OpenRouter ключа (#12, #13) показывают одинаковый $9999.79.

**Причина:** `/api/keys/balance` fetch-ит баланс ОДНОГО (активного) ключа, а фронтенд применяет этот баланс ко ВСЕМ ключам провайдера (line 436-440 ModelDirectory.tsx).

**Решение:** Fetch balance для каждого ключа отдельно, или помечать в UI что баланс показан для конкретного ключа.

---

## ПОЛЕЗНЫЙ КОНТЕКСТ ДЛЯ СЛЕДУЮЩЕЙ СЕССИИ

### Архитектура Balance Flow (текущая, сломанная)

```
Frontend                     Backend
─────────                    ────────
GET /api/keys/balance    →   fetch_provider_balance('openrouter')
                             → httpx GET openrouter.ai/api/v1/auth/key (ONE key)
                             ← {balance: 9999.79, limit: null, used: 0.21}

← {balances: {
    openrouter: {
      balance: 9999.79,     ← FAKE: это credit limit, не реальные деньги
      limit: null,
      used: 0.21
    }
  }}

fetchBalances() merge:
  ALL keys get same balance  ← BUG: один fetch на все ключи
  balance_percent = undefined ← BUG: percent не вычислен
```

### Архитектура Balance Flow (желаемая)

```
Frontend                     Backend
─────────                    ────────
GET /api/keys/balance    →   for EACH key:
                               fetch_provider_balance(provider, key_index)
                               → httpx GET provider_api (per key)
                               ← {balance, limit, used, percent, is_paid}

                             + cross-reference with 402 status:
                               if key got 402 recently → balance = 0

← {balances: {
    openrouter: [
      {key_id: "12", balance: 0, percent: 0, status: "exhausted"},
      {key_id: "13", balance: 15.42, percent: 30.8, status: "active"}
    ],
    polza: [
      {key_id: "1", balance: 5.00, percent: 50, status: "active"}
    ]
  }}

fetchBalances() merge:
  EACH key gets own balance
  balance_percent calculated
  Color: blue >20%, dim ≤20%
```

### Коммит Phase 117

```
d5474aed Phase 117: Provider Intelligence — pipeline provider override, balance fetcher, UI balance bar
```

### Файлы к исправлению

| Файл | Что исправить |
|------|--------------|
| `src/utils/unified_key_manager.py` | BUG-1 (fake balance), BUG-4 (402→balance=0), BUG-5 (per-key fetch) |
| `src/api/routes/config_routes.py` | BUG-2 (percent calculation), BUG-5 (per-key response) |
| `client/src/components/ModelDirectory.tsx` | BUG-2 (percent merge), BUG-5 (per-key display) |
| `tests/test_phase117_provider.py` | Добавить тесты на BUG-1..5 |

---

## Backlog (из Phase 115-117)

| # | Priority | Task |
|---|----------|------|
| 1 | **P1** | BUG-1..5 баланс (Phase 117.1) |
| 2 | P2 | 103 print() → logger в user_message_handler.py |
| 3 | P2 | flask_config compat layer (3 ref) |
| 4 | P2 | chat_routes.py → FastAPI Depends() |
| 5 | P3 | 6 filesystem tests → mock для CI/CD |
| 6 | P3 | 14 pre-existing test failures |
| 7 | P3 | DELETE endpoint mismatch (frontend/backend) |
| 8 | P3 | Balance caching (TTL 5 min) |
| 9 | P4 | xAI/Anthropic balance via rate-limit headers |

---

## ПРОМПТ ДЛЯ ГРОКА: Исследование Balance API у провайдеров

```
Привет Грок! Нужно системное исследование по теме:

## Задача
Как узнать баланс/лимиты у различных LLM API провайдеров и агрегаторов?

## Контекст
В проекте VETKA есть агрегатор ключей (UnifiedKeyManager) который управляет ключами от:
- OpenRouter (13 ключей, free + paid)
- Polza AI (агрегатор, 1 ключ)
- Google Gemini (2 ключа)
- xAI/Grok (прямой)
- Anthropic Claude (прямой)
- Mistral (прямой)
- Ollama (локальный, баланс не нужен)
- DeepSeek (прямой)

Сейчас мы проверяем баланс только для OpenRouter и Polza, но обнаружили проблемы:

1. OpenRouter `/api/v1/auth/key` возвращает `limit_remaining` = кредитный лимит free-tier ($10k), что ОБМАНЫВАЕТ — показывает $9999 хотя реально 402 Payment Required. Как правильно определить реальный баланс? Как отличить free-tier от paid? Есть ли поле `is_free_tier` или аналог?

2. Polza AI `/api/v1/account/balance` — какой формат ответа реально? Какие поля? Нужна проверка.

3. Google Gemini — есть ли API для проверки квоты/лимитов? Через Google Cloud Billing API? Через IAM?

4. xAI (Grok API) — есть ли endpoint для баланса? Или только через console.x.ai?

5. Anthropic — есть ли API для проверки usage/limits? Или только dashboard?

6. Mistral — есть ли billing API?

7. DeepSeek — есть ли balance endpoint?

## Что нужно для каждого провайдера:

1. **Endpoint URL** (если есть)
2. **Метод аутентификации** (Bearer, API-Key header, etc.)
3. **Формат ответа** (JSON schema)
4. **Как отличить free от paid** (если применимо)
5. **Rate limits** проверки (как часто можно вызывать)
6. **Альтернативные методы** если прямого API нет:
   - Rate-limit headers (`x-ratelimit-remaining`, etc.)
   - Error codes как индикаторы (402 = нет денег, 429 = rate limit)
   - Google Cloud Billing API
   - Scraping dashboard (НЕ рекомендуется, но для полноты)

## Дополнительный вопрос:
Как делают другие инструменты (Cursor, Continue.dev, VS Code extensions, LiteLLM, RouteLLM)? Есть ли у них balance checking? Как они решают эту проблему?

## Формат ответа:
Таблица провайдеров с полями: Provider, Balance API, Auth, Response Format, Free/Paid Detection, Rate Limit, Alternative Methods.

Плюс отдельные секции с примерами curl для каждого провайдера у кого есть API.

## Важные файлы проекта для контекста:
- src/utils/unified_key_manager.py (lines 457-513) — текущий fetch_provider_balance()
- src/elisya/provider_registry.py — ProviderRegistry с 13+ провайдерами
- src/api/routes/config_routes.py (lines 598-614) — /api/keys/balance endpoint
```

---

*Phase 117.1 — Balance Intelligence — готов для следующей сессии.*
