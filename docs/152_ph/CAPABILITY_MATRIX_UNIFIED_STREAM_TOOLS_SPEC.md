# Capability Matrix: Unified Stream + Tools (VETKA + Mycelium)

MARKER_152.CAP_MATRIX.UNIFIED_STREAM_TOOLS.SPEC

Date: 2026-02-17  
Scope: единая спецификация для VETKA chat и Mycelium runtime

## 1) Цель

Убрать расхождение между:
- потоковой генерацией (`stream`),
- вызовами инструментов (`tool calling`),
- фактическими возможностями модели/провайдера.

Итог: один контракт поведения, чтобы UI всегда показывал правду: что реально поддерживается и что реально было выполнено.

## 2) Ключевая проблема

Сейчас в проекте есть частичная поддержка:
- capability логика размазана по `provider_registry.py`, роутерам и хэндлерам;
- stream-путь и tool-loop реализованы раздельно;
- из-за этого возможны “ложные ожидания” в чате (кажется, что tools были использованы, хотя в конкретной stream-ветке они не исполнялись).

## 3) Единая модель Capability Matrix

Матрица хранит **фактические** флаги поддержки и операционные лимиты.

```json
{
  "model_id": "x-ai/grok-4.1-fast",
  "provider": "polza|openai|anthropic|ollama|openrouter|xai|...",
  "capabilities": {
    "stream_tokens": true,
    "tool_calling": true,
    "tool_calling_in_stream": false,
    "vision_input": false,
    "audio_input": false,
    "json_mode": true
  },
  "limits": {
    "context_window": 131072,
    "recommended_input_tokens": 24000,
    "recommended_output_tokens": 4000,
    "max_tools_per_turn": 8,
    "max_tool_round_trips": 4
  },
  "routing_policy": {
    "stream_mode": "native|provider_proxy|fallback_non_stream",
    "tool_mode": "native|fc_loop|disabled",
    "on_tool_in_stream_unsupported": "buffer_tool_phase_then_resume|switch_non_stream|disable_tools"
  },
  "observability": {
    "emit_tool_events": true,
    "emit_stream_meta": "dev_only",
    "emit_capability_snapshot": true
  }
}
```

## 4) Runtime-решение (единый оркестратор)

Для любого запроса строится `ExecutionPlan` из матрицы:

1. Detect provider/model.
2. Load capability snapshot.
3. Выбрать режим:
   - `stream + tools` (если `tool_calling_in_stream=true`);
   - `stream + no tools` (если stream есть, tools в stream нет);
   - `tool loop -> final stream` (если tools нужны, но в stream не поддержаны);
   - `non-stream tool loop` (fallback).
4. Выполнить с единым event-контрактом.

## 5) Единый socket-контракт событий

Обязательные события:
- `stream_start`
- `stream_token`
- `tool_start`
- `tool_result`
- `tool_error`
- `stream_end`

Обязательные поля:
- `tool_execution_mode`: `enabled_stream|enabled_non_stream|disabled_stream`
- `capability_snapshot`: `{stream_tokens, tool_calling, tool_calling_in_stream}`
- `provider`, `model`, `model_source`

Пример `stream_start`:

```json
{
  "id": "msg_uuid",
  "provider": "polza",
  "model": "x-ai/grok-4.1-fast",
  "tool_execution_mode": "disabled_stream",
  "capability_snapshot": {
    "stream_tokens": true,
    "tool_calling": true,
    "tool_calling_in_stream": false
  }
}
```

## 6) Источники данных для матрицы (в проекте)

- Базовые capability провайдера: `src/elisya/provider_registry.py` (`supports_tools`, stream-функции).
- Контекст/скорость/окно: `src/elisya/llm_model_registry.py` (`context_length`, throughput профили).
- Роутинг и сложность: `src/elisya/model_router_v2.py`.

Рекомендация: не дублировать логику в хэндлерах; держать один модуль-агрегатор capability snapshot.

## 7) Правила truthfulness (анти-галлюцинация про tools)

Если `tool_execution_mode != enabled_*`, модель **не должна** утверждать, что tools были выполнены.  
Системный prompt обязан включать это правило в stream-ветке без tool-loop.

## 8) План внедрения (без ломки текущего UI)

1. `Phase A`: создать единый `capability_matrix.py` (aggregation layer).
2. `Phase B`: подключить snapshot в `user_message_handler` и `provider_registry`.
3. `Phase C`: унифицировать события socket (`tool_*` + capability snapshot).
4. `Phase D`: включить стратегию `tool loop -> final stream` для моделей без `tool_calling_in_stream`.
5. `Phase E`: добавить метрики и регрессионные тесты.

## 9) Definition of Done

- Для каждого ответа UI видит честный `tool_execution_mode`.
- Нельзя получить кейс “в чате сказано, что tools использованы”, если tool-loop не выполнялся.
- Capability snapshot доступен и для VETKA, и для Mycelium.
- Stream и tool events приходят в едином формате.

## 10) Минимальный тест-набор

1. `model supports stream+tools+tools_in_stream` -> токены + tool events в одном цикле.
2. `model supports stream but not tools_in_stream` -> tool-phase fallback + корректный mode.
3. `model supports tools only non-stream` -> non-stream loop + финальный ответ.
4. `provider outage/retry` -> mode и события остаются консистентными.

---

MARKER_152.CAP_MATRIX.UNIFIED_STREAM_TOOLS.READY_FOR_IMPL
