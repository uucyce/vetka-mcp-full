# MARKER_156.S2_VOICE_ASSIGNMENT_IMPLEMENTATION_REPORT

Дата: 2026-02-26  
Фаза: 156 / S2 (persistent voice assignment)

## Что реализовано

### 1) Новый persistent registry
Добавлен модуль:
- `src/voice/voice_assignment_registry.py`

Функция:
- атомарный (в рамках процесса) `get_or_assign(provider, model_id)`;
- ключ идентичности: `provider:model_id`;
- сохранение в `data/agent_voice_assignments.json`;
- lock: `asyncio.Lock` + atomic write (`.tmp` -> `replace`).

**Маркер:** `MARKER_156.VOICE.S2_REGISTRY`

### 2) Интеграция в group voice payload
В `group_message_handler` S1-stub теперь запрашивает assignment из registry:
- `voice_id`
- `tts_provider`
- `model_identity_key`
- `persona_tag`

И кладет их в `metadata.voice` для `group_voice_message`.

**Маркер:** `MARKER_156.VOICE.S2_ASSIGNMENT_INTEGRATION`

## Маркеры S2
1. `MARKER_156.VOICE.S2_REGISTRY`
2. `MARKER_156.VOICE.S2_ASSIGNMENT_INTEGRATION`

## Проверка
1. `python3 -m py_compile`:
- `src/voice/voice_assignment_registry.py`
- `src/api/handlers/group_message_handler.py`
- статус: OK

2. Мини-тест assignment логики (через временный файл `/tmp/...`):
- одинаковый `provider:model_id` получает тот же `voice_id`;
- разные identity получают разные/детерминированные голоса из пула.

## Что это дает
- Появился базовый lock+persist слой для закрепления голоса за моделью.
- `group_voice_message` уже содержит стабильную voice identity, готовую для S3 (реальный TTS stream).

## Нужны ли дополнительные исследования сейчас
Для S2 — нет, пробелов нет.  
Research остается для S6 (эмоции/просодия Qwen TTS API).
