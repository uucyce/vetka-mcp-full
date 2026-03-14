# MARKER_156.S3_TTS_STREAM_IMPLEMENTATION_REPORT

Дата: 2026-02-26  
Фаза: 156 / S3 (agent -> TTS -> voice stream)

## Что реализовано

### 1) Реальный backend voice-stream
В `group_message_handler` S1/S2 voice emitter upgraded до реального потока:
- `group_voice_stream_start`
- `group_voice_stream_chunk`
- `group_voice_stream_end`
- затем финальный `group_voice_message`

Источник аудио:
- `TTSEngine` (`primary=qwen3`, fallback chain: qwen3 -> edge -> piper)
- посентенсная генерация через `split_into_sentences(...)`

**Маркер:** `MARKER_156.VOICE.S3_TTS_STREAM`  
**Файл:** `src/api/handlers/group_message_handler.py`

### 2) S2 assignment используется в S3 stream
Перед TTS запрашивается persistent assignment (`provider:model_id -> voice_id`),
после чего этот `voice_id` идет в `tts_engine.synthesize_with_result(...)`.

### 3) Stream chunk payload расширен
Chunk теперь содержит:
- `audio_chunk_b64`
- `seq`
- `format`
- `duration_ms`
- `waveform`

End событие содержит:
- `audio`
- `voice`
- `text_preview`
- `reason`

Контракт отражен во frontend socket type:
- `client/src/hooks/useSocket.ts`

## Маркеры S3
1. `MARKER_156.VOICE.S3_TTS_STREAM`

## Технические детали
- Язык выбирается автоматически по тексту (кириллица -> `ru`, иначе `en`).
- Waveform для stream/UI вычисляется как легкий proxy из аудиобайтов (не DSP-perfect, но пригодно для preview).
- При неудаче отдельного sentence stream продолжается для остальных sentence.
- При total-failure:
  - `voice_enabled=false`
  - `voice_reason=S3_tts_stream_error:*` или `S3_tts_stream_no_audio`
  - чат не ломается, финальный `group_voice_message` все равно эмитится.

## Проверка
- `python3 -m py_compile src/api/handlers/group_message_handler.py` -> OK

## Что осталось
- S4: полноценный playback UX в bubble (controls/autoplay/speed + прогресс по stream chunk).
- S5: policy switch `text_only | voice_auto | voice_forced` через настройки сессии.
- S6: emotion layer + CAM enrichment.
