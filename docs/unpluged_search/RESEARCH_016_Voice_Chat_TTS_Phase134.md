# Voice Chat & TTS Integration
**Рекомендуемая фаза:** 134
**Статус:** Не имплементировано
**Приоритет:** СРЕДНИЙ
**Источник:** Беседы агентов, todo_dream_117

## Описание
Голосовой чат Telegram-style с persistent waveforms, model-specific voice profiles, real-time TTS.

## Текущее состояние
- Текстовый чат работает
- TTS/STT НЕ интегрированы
- Voice UI НЕ существует
- Grok Voice research начат

## Технические детали
- TTS consistency per model ID
- Low-quality mode для 3x скорости
- Waveform SVG generation
- T9 prediction + fillers ("Дай подумать...")
- RTF 0.2x для Qwen3 ultra-low
- Emotional voice modulation (anger > 0.5 → calm tone)
- Surprise-based vocab из Qdrant

## Шаги имплементации
1. Интегрировать TTS engine (Qwen3 TTS или OpenAI)
2. Добавить STT input (whisper)
3. Создать voice UI с waveform visualization
4. Настроить per-model voice profiles
5. Добавить emotional modulation

## Ожидаемый результат
Hands-free взаимодействие с VETKA, voice-first workflow
