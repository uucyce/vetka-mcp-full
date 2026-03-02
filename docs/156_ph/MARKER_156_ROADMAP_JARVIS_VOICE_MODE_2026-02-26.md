# MARKER_156.ROADMAP_JARVIS_VOICE_MODE

Date: 2026-02-26
Status: Active integration roadmap

## Goal
Интегрировать Jarvis в голосовой режим чата так, чтобы на локальном M4 диалог ощущался живым:
- вход голосом -> ответ голосом,
- старт аудио до завершения полного текста,
- устойчивые закреплённые голоса по ролям в командном чате.

## Scope (S6.x)

1. `S6.1 Voice Identity Cleanup` (done)
- Удалены legacy voice-id из дефолтных конфигов.
- В `voice_assignment_registry` добавлена миграция alias -> актуальные Qwen voices.

2. `S6.2 Role-Locked Voices` (done)
- В командном чате закрепление голоса идёт по `group_id + role`.
- Базовая карта ролей: `pm/dev/qa/architect/hostess/researcher/jarvis`.

3. `S6.3 Jarvis Early Chunk Kickoff` (next)
- Источник раннего контекста: `viewport + pinned context + first words`.
- Генерация короткого первого предложения до финального полного ответа.
- Цель: первый аудио-чанк до готовности полного текста.

4. `S6.4 Sentence Streaming Pipeline` (next)
- Полный ответ делится на предложения.
- TTS стримит предложения последовательно одним и тем же `voice_id`.
- Финальный `group_voice_message` содержит метаданные трека и waveform.

5. `S6.5 Emotion/CAM Mapping` (next)
- CAM/контекст -> `emotion_hint` -> параметры TTS (speed/temperature/instruction).
- Падение в нейтральный режим при неуверенном распознавании эмоции.

6. `S6.6 UX + Metrics` (next)
- Voice bubble как в мессенджере: waveform + duration + play/pause.
- Метрики: `first_audio_ms`, `stream_completion_ms`, `rtf`, `voice_error_rate`.

## Acceptance Targets
- `p95 first_audio_ms < 1500` на локальном M4.
- `voice_id` стабилен для роли внутри группы после рестарта.
- Для текстового режима голосовые события не эмитятся.
- При voice-mode ответы агент(ов) идут voice-сообщениями по умолчанию.
