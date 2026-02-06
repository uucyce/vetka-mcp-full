# Phase 117 — Provider Intelligence: Research Report

**Date:** 2026-02-06
**Orchestrator:** Claude Opus 4 (architect/commander)
**Scouts:** 9 Haiku (H1-H9) → 3 Sonnet verifiers (S1-S3)
**External research:** Grok-4.1 (VETKA chat, semantic + codebase search)

---

## Executive Summary

**Инфраструктура для провайдеров на 95% готова. Баланс — 0% реализован.**

Вся цепочка routing уже работает: `MCP → LLMCallTool → ProviderRegistry → Provider → UnifiedKeyManager`. Параметр `model_source` поддерживается в LLMCallTool (Phase 111.11), но **НЕ прокинут** через agent_pipeline.py. Баланс не проверяется ни у одного провайдера.

---

## Разведка: Результаты и Верификация

### Scout Reliability

| Scout | Область | Точность | Sonnet |
|-------|---------|----------|--------|
| H1 | UnifiedKeyManager | 100% | S1 |
| H2 | ProviderRegistry | 95% (12 unique, не 13) | S1 |
| H3 | APIKeyDetector | 100% | S1 |
| H4 | agent_pipeline models | 100% | S2 |
| H5 | pipeline_prompts.json | 100% | S2 |
| H6 | MCP bridge handler | 90% (vetka_call_model ИМЕЕТ model_source) | S2 |
| H7 | config_routes.py | 100% | S3 |
| H8 | ModelDirectory.tsx | 90% (routes в config_routes, не main.py) | S3 |
| H9 | Balance patterns | 60% (нет balance, только validation) | S1 |

**Средняя точность скаутов: 93%**

---

## Направление 1: vetka_provider_status (единый MCP tool)

### Что ЕСТЬ

| Компонент | Файл | Строки | Статус |
|-----------|------|--------|--------|
| APIKeyRecord.get_status() | unified_key_manager.py | 124-135 | Возвращает: masked, alias, active, available, success_count, failure_count, cooldown_hours |
| get_keys_status(provider) | unified_key_manager.py | 435-438 | Список статусов по провайдеру |
| 24h cooldown | unified_key_manager.py | 36, 91-107 | mark_rate_limited() + is_available() |
| Key rotation | unified_key_manager.py | 260-274 | Круговая ротация с фильтром cooldown |
| Provider endpoints (doctor) | doctor_tool.py | 250-262 | URL-ы для validation (НЕ баланс) |
| httpx async client | doctor_tool.py | 283-284 | httpx.AsyncClient с timeout 10s |

### Чего НЕТ

| Gap | Severity | Детали |
|-----|----------|--------|
| Balance API calls | CRITICAL | Ни один провайдер не проверяется на баланс |
| Response JSON parsing | CRITICAL | doctor_tool проверяет только status_code, не .json() |
| Balance caching | HIGH | Нет кеширования, нужен TTL 5 мин |
| Unified balance schema | HIGH | Каждый провайдер возвращает разный формат |

### Provider Balance APIs (исследование)

| Provider | Endpoint | Формат ответа | Статус |
|----------|----------|---------------|--------|
| OpenRouter | `GET /api/v1/auth/key` | `{data: {limit_remaining, usage}}` | Готов к интеграции |
| Polza AI | `GET /v1/account/balance` | `{balance: float}` (предположительно) | Нужно проверить |
| OpenAI | `GET /v1/dashboard/billing/usage` | Только paid accounts | Ограничен |
| xAI | Нет public endpoint | Rate-limit через headers | Недоступен |
| Anthropic | Нет public endpoint | Rate-limit через headers | Недоступен |

### Архитектурное решение

**Рекомендация S1: Гибридный подход**

Phase 1 (быстро): Расширить doctor_tool для OpenRouter + Polza
Phase 2 (полноценно): Выделить в отдельный vetka_provider_status MCP tool

```
vetka_provider_status(provider?: string)
  ↓
UnifiedKeyManager.get_keys_status() → local state (instant)
  +
Balance fetcher (async httpx) → remote state (5s timeout, 5min cache)
  ↓
Response: {
  provider: str,
  keys: [{masked, active, available, success_count, failure_count, cooldown_hours}],
  balance: float | null,      ← NEW
  balance_limit: float | null, ← NEW
  valid: bool,
  recommendation: "healthy" | "low_balance" | "rotate" | "add_key"
}
```

---

## Направление 2: Pipeline Provider Override + Presets

### Что ЕСТЬ

| Компонент | Файл | Строки | Статус |
|-----------|------|--------|--------|
| Model selection (config) | pipeline_prompts.json | 7-29 | 4 роли: architect(claude), researcher(grok), coder(claude), verifier(claude) |
| _config.default_router | pipeline_prompts.json | 3 | "openrouter" |
| model_fallback | pipeline_prompts.json | каждая роль | meta-llama/llama-3.1-8b-instruct:free |
| LLMCallTool model_source | llm_call_tool.py | 576 | ПОДДЕРЖИВАЕТСЯ — arguments.get('model_source') |
| ProviderRegistry source | provider_registry.py | 1372-1380 | Priority 1: explicit source > model name |

### Чего НЕТ

| Gap | Severity | Детали |
|-----|----------|--------|
| Pipeline provider param | CRITICAL | AgentPipeline.__init__ не принимает provider |
| model_source pass-through | CRITICAL | 3 вызова tool.execute() без model_source (lines 1041, 1105, 1190) |
| MCP schema provider | HIGH | vetka_mycelium_pipeline schema без provider param |
| Presets system | MEDIUM | Нет шаблонов команд |

### Ключевая находка S2

> **LLMCallTool УЖЕ поддерживает model_source!** (Phase 111.11)
> Нужно только прокинуть его через agent_pipeline.

### Data flow (после реализации)

```
MCP Schema: vetka_mycelium_pipeline(task, provider?, preset?)
  ↓
Bridge handler: extract provider + load preset
  ↓
AgentPipeline(chat_id, auto_write, provider, preset_models) ← NEW params
  ↓
3 LLM calls: tool.execute({model, model_source: self.provider}) ← ADD model_source
  ↓
LLMCallTool → detect_provider(model, source=model_source) ← ALREADY WORKS
  ↓
ProviderRegistry → correct provider API
```

### Presets: отдельный файл (рекомендация S2)

```json
// data/templates/model_presets.json (NEW)
{
  "version": "1.0",
  "default_preset": "balanced",
  "presets": {
    "polza_research": {
      "description": "Research team on Polza AI",
      "architect": "claude-sonnet-4",
      "researcher": "grok-4",
      "coder": "claude-sonnet-4",
      "provider": "polza"
    },
    "budget": {
      "description": "Free models for testing",
      "architect": "meta-llama/llama-3.1-8b-instruct:free",
      "researcher": "meta-llama/llama-3.1-8b-instruct:free",
      "coder": "meta-llama/llama-3.1-8b-instruct:free",
      "provider": "openrouter"
    },
    "quality": {
      "description": "Best models for critical tasks",
      "architect": "claude-opus-4-5",
      "researcher": "grok-4",
      "coder": "claude-opus-4-5",
      "provider": null
    }
  }
}
```

---

## Направление 3: UI Панель ключей — расширить баланс-баром

### ВАЖНО: НЕ создавать новую панель. Расширить существующую.

### Что ЕСТЬ

| Компонент | Файл | Строки | Статус |
|-----------|------|--------|--------|
| Keys drawer (Phase 57) | ModelDirectory.tsx | 1003-1437 | Полнофункциональная панель |
| Key card | ModelDirectory.tsx | 1283-1389 | Provider + status + masked key + delete |
| APIKeyInfo interface | ModelDirectory.tsx | 40-45 | id, provider, key, status |
| /api/keys endpoint | config_routes.py | 486-568 | Masked keys по провайдерам |
| /api/keys/status | config_routes.py | 258-269 | km.get_stats() (counts only) |
| Smart detect | config_routes.py | 332 | Auto-detect provider from key |

### Чего НЕТ

| Gap | Severity | Детали |
|-----|----------|--------|
| Balance field in response | CRITICAL | /api/keys не возвращает balance |
| Balance bar in UI | HIGH | Нет визуального индикатора |
| balance в APIKeyInfo | HIGH | Interface без balance поля |

### Баг найден S3

> **DELETE endpoint mismatch:** Frontend вызывает `/api/keys/{provider}/{keyId}`, backend имеет `/api/keys/{provider}` (без keyId). Потенциальный баг.

### Минимальные изменения (3 файла, ~25 строк)

**1. Backend** — unified_key_manager.py:124-135:
```python
# Добавить к get_status() return dict:
'balance': self.balance,           # NEW field
'balance_limit': self.balance_limit # NEW field
```

**2. Backend** — config_routes.py:522-560:
```python
# Добавить к каждому key dict:
'balance': key_record.balance,
'balance_percent': calculate_percent(key_record)
```

**3. Frontend** — ModelDirectory.tsx:
```typescript
// Interface (line 40-45):
interface APIKeyInfo {
  ...existing...
  balance?: number;        // NEW
  balance_percent?: number; // NEW
}

// After line 1358 (after masked key span):
{apiKey.balance !== undefined && (
  <div style={{height: 3, background: '#0a0a0a', borderRadius: 2, marginTop: 4}}>
    <div style={{
      width: `${apiKey.balance_percent || 0}%`,
      height: '100%',
      background: apiKey.balance_percent > 20 ? '#484' : '#844'
    }} />
  </div>
)}
```

---

## Implementation Roadmap

### Phase 117.1: Provider Status MCP Tool
- Новый tool: vetka_provider_status
- Объединяет key status (local) + balance (remote)
- Начать с OpenRouter (endpoint известен)
- **Effort: S** (1-2 часа)

### Phase 117.2: Pipeline Provider Override
- Добавить provider + preset к MCP schema
- Прокинуть model_source через AgentPipeline
- Создать model_presets.json
- **Effort: M** (2-3 часа)

### Phase 117.3: UI Balance Bar
- РАСШИРИТЬ существующую панель (НЕ новую)
- Добавить balance к /api/keys response
- Тонкий status bar под каждым ключом
- **Effort: S** (1 час)

### Phase 117.4: Integration Test
- Тест с реальным Polza API ключом
- Verify balance отображается в UI
- Pipeline работает с provider override
- **Effort: XS** (30 мин)

---

## Remaining TODO (Phase 115-116 backlog)

| # | Priority | Task | Source |
|---|----------|------|--------|
| 1 | P2 | 103 print() → logger в user_message_handler.py | Phase 116 SONNET-B |
| 2 | P2 | flask_config compat layer убрать (3 ref) | Phase 116 S3 |
| 3 | P2 | chat_routes.py → FastAPI Depends() | Phase 116 S3 |
| 4 | P3 | 6 тестов с filesystem → мокать для CI/CD | Phase 116 S3 |
| 5 | P3 | Sync path deprecated в PinnedFilesService | Phase 116 S3 |
| 6 | P3 | 14 pre-existing test failures | Phase 116 test run |
| 7 | P3 | DELETE endpoint mismatch (frontend/backend) | Phase 117 S3 |

---

## Key Files Map

```
BACKEND:
├── src/utils/unified_key_manager.py     — Key storage, rotation, cooldown
├── src/elisya/provider_registry.py      — Provider detection, routing
├── src/elisya/api_key_detector.py       — Key format auto-detection (45+ providers)
├── src/mcp/tools/llm_call_tool.py       — LLM call with model_source support
├── src/mcp/tools/doctor_tool.py         — Key validation, httpx patterns
├── src/mcp/vetka_mcp_bridge.py          — MCP tool schemas + handlers
├── src/orchestration/agent_pipeline.py  — Mycelium pipeline (needs provider)
├── src/api/routes/config_routes.py      — /api/keys/* endpoints
├── data/templates/pipeline_prompts.json — Role model configs
└── data/templates/model_presets.json    — Team presets (TO CREATE)

FRONTEND:
└── client/src/components/ModelDirectory.tsx — Keys panel (extend with balance bar)
```

---

**Report Status:** COMPLETE
**Phase 117 Research:** Ready for implementation approval.
