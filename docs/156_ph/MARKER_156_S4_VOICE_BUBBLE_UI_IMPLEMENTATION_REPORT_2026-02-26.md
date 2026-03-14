# MARKER_156.S4_VOICE_BUBBLE_UI_IMPLEMENTATION_REPORT

Дата: 2026-02-26  
Фаза: 156 / S4 (chat UI voice bubble)

## Что реализовано

### 1) Voice bubble в MessageBubble
Для `message.type === 'voice'` добавлен отдельный UI блок:
- Play/Pause
- Скорость: `1x / 1.5x / 2x`
- Прогресс playback + длительность (`mm:ss`)
- Waveform визуализация (`metadata.audio.waveform`)
- Плашка voice identity (`voice_id · tts_provider`)
- Ошибка воспроизведения (если есть)
- Текстовая подложка (transcript)

**Маркер:** `MARKER_156.VOICE.S4_UI_BUBBLE`  
**Файл:** `client/src/components/chat/MessageBubble.tsx`

### 2) Playback режимы
- Если есть `metadata.audio.url` (или `storage_id`) -> используется `HTMLAudioElement`.
- Если аудио еще не прикреплено -> fallback на browser `speechSynthesis` (через `useTTS`).

### 3) UX-интеграция
- Для voice message скрыт старый общий “Read aloud” button, чтобы не дублировать controls.
- Обычные text/code/plan/compound сообщения работают как раньше.

## Технические детали
- Добавлен локальный playback state per bubble:
  - `voicePlaying`
  - `voiceRate`
  - `voiceCurrentMs`
  - `voiceDurationMs`
  - `voiceError`
- Добавлена безопасная очистка audio ref при unmount.
- Assistant-content рендер переведен на `renderAssistantContent()` (без вложенного ternary), чтобы упростить сопровождение.

## Проверка
- Попытка `npm run build` в client показывает множественные существующие TS ошибки в других модулях проекта.
- По текущей задаче: синтаксическая ошибка в `MessageBubble.tsx`, возникшая в процессе, устранена.

## Что остается после S4
- S5: policy-переключатель `text_only | voice_auto | voice_forced` в настройках/сессии.
- S6: emotion layer + CAM enrichment.
