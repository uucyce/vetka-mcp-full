# MARKER_156_S6_RUNTIME_RECON_VOICE_CHAT_FAILURE_2026-02-27

Дата: 2026-02-27  
Скоуп: Solo voice runtime (user voice input -> model text -> Qwen TTS -> assistant voice bubble)  
Цель: расследование причин нестабильности/задержек и фиксация маркеров для устранения.

## 1) Подтверждённые факты

1. Qwen TTS действительно запущен на 4bit:
- `GET http://127.0.0.1:5003/health` ->
  - `profile: "4bit"`
  - `model: "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit"`

2. Пайплайн голосового ответа не realtime, а post-pipeline:
- сначала LLM завершает текстовый ответ (`stream_end`),
- потом запускается `_emit_solo_voice_message` и синтез Qwen.

3. В runtime есть жалобы на очень долгий TTS и “зависания”:
- пользователь ждёт минуты, иногда bubble появляется поздно/не проигрывается.

4. Ранее уже пойман и исправлен контейнерный баг:
- часть payload приходила как raw PCM, сохранялась как `.wav` без RIFF,
- вызывало `Qwen audio playback failed`.

## 2) Критические причины деградации (по вероятности)

### RC-1: TTS стартует только после завершения LLM stream
Маркер: `RUNTIME_RC1_POST_STREAM_SERIAL`  
Эффект: даже быстрый TTS не может начаться “через 3 секунды” от отправки voice input, если LLM отвечает дольше.

### RC-2: Синтез выполняется синхронно внутри хендлера user_message
Маркер: `RUNTIME_RC2_HANDLER_BLOCK`  
Эффект: блокируется завершение полного цикла ответа в этом сокет-запросе; при нагрузке/долгом Qwen пользователь видит “висит”.

### RC-3: Нет потоковой загрузки assistant audio в bubble (только готовый blob/storage)
Маркер: `RUNTIME_RC3_NO_CHUNKED_AUDIO_DELIVERY`  
Эффект: UX ждёт весь TTS до first-play, нет поведения “как аудио из мессенджера”.

### RC-4: Возможный конфуз порта 5003 в кодовой базе
Маркер: `RUNTIME_RC4_PORT_5003_COLLISION_RISK`  
Факт: `5003` используется TTS и фигурирует в MCP/прокси коде.  
Эффект: риск неправильного владельца порта в отдельных режимах запуска.

### RC-5: Watcher/Qdrant noise маскирует первичные ошибки voice runtime
Маркер: `RUNTIME_RC5_LOG_NOISE_MASKING`  
Эффект: в логах много вторичных сообщений (`agent_voice_assignments.json`, qdrant 404), что мешает быстро видеть root-cause TTS.

## 3) SLA, который требуется закрепить

`SLA-S6-VOICE-FIRST-AUDIO`:
- Цель: первый playable assistant audio <= 3-5 секунд после отправки user voice.
- При деградации: <= 8 секунд (degraded), с явным статусом “генерируется аудио...”.

## 4) Обязательная трассировка (добавить маркеры в логи)

1. `MARKER_156.VOICE.S6_TRACE_T0_USER_SEND`
- timestamp отправки user voice в backend.

2. `MARKER_156.VOICE.S6_TRACE_T1_LLM_STREAM_END`
- timestamp окончания LLM stream.

3. `MARKER_156.VOICE.S6_TRACE_T2_TTS_START`
- timestamp старта запроса к `5003/tts/generate`.

4. `MARKER_156.VOICE.S6_TRACE_T3_TTS_DONE`
- timestamp получения audio payload.

5. `MARKER_156.VOICE.S6_TRACE_T4_STORAGE_DONE`
- `storage_id`, size, format, duration_ms.

6. `MARKER_156.VOICE.S6_TRACE_T5_UI_BUBBLE_EMIT`
- emit `chat_voice_message`.

7. `MARKER_156.VOICE.S6_TRACE_T6_UI_FIRST_PLAY`
- frontend timestamp первого успешного play.

## 5) План расследования/фикса (runtime-only, без UI перегруза)

### Phase R1 — Тайминг-аудит
- Проставить T0..T6 и собрать 20 прогонов.
- Построить p50/p95 для сегментов:
  - `LLM`, `TTS`, `storage`, `UI-first-play`.

### Phase R2 — Разделение текста и TTS по доставке
- Текст отдавать сразу как сейчас.
- TTS вынести в фоновую task-ветку (не блокировать основной user_message flow).
- В UI статус: `Генерирую голос...`.

### Phase R3 — Fast first audio
- Опция “short first chunk”:
  - сначала синтез короткого preview (1-я фраза),
  - затем full audio (замена/дополнение).

### Phase R4 — Port hygiene
- Жёстко закрепить TTS-порт отдельной переменной (`QWEN_TTS_PORT`) и исключить совместное использование с MCP.
- Добавить health assertion на startup.

### Phase R5 — Noise quarantine
- Понизить/фильтровать watcher/qdrant noise для `agent_voice_assignments.json`.
- Оставить отдельный канал логов для voice runtime.

## 6) Критерии успеха

1. Assistant voice bubble появляется стабильно.
2. Первое воспроизведение <= 5 секунд в normal path.
3. Нет “вечной генерации”.
4. Нет silent-fail: при ошибке показывается конкретный `voice_error_code`.
5. Все маршруты сохраняют strict provider/model lock.
