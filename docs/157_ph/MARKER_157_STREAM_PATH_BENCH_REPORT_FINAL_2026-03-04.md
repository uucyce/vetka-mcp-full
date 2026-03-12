# MARKER 157 Final: Stream-Path Debug + Full Bench Matrix (2026-03-04)

## Что было исправлено перед прогонами
1. **Stream-path Ollama**: в `provider_registry._stream_ollama` заменен SDK-путь на прямой `httpx` NDJSON (`trust_env=False`) — это сняло массовый `ResponseError 503`.
2. **Stream stability**: в `call_model_v2_stream` добавлен безопасный close источника (`aclose`) и маркер TTFT (`[STREAM_V2] first token in ...ms`).
3. **Benchmark harness** (`scripts/voice_mode_benchmark.py`):
   - добавлен сценарий `interrupt_1` (пользователь перебивает и задает follow-up),
   - добавлена расширенная quality-оценка (`quality_proxy` + `quality_notes`),
   - добавлена совместимость с текущими сигнатурами (`ContextPacker.pack`, `ProgressiveTtsService.stream_sentences`),
   - локальный prompt budget для grounded режима (`BENCH_LOCAL_PROMPT_CHAR_BUDGET`).

## Главный смешанный прогон (API + local)
Артефакты:
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_062919.json`
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_062919.csv`
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_062919.md`

Итоги (p50):
- `B_api_tts`: success `0.75`, reaction_text `2216ms`, quality `0.6062`
- `C_api_jepa_tts`: success `1.00`, reaction_text `1614ms`, quality `0.8063`
- `D_ollama_tts` (`llama3.2:3b`): success `1.00`, reaction_text `567ms`, quality `0.7875`
- `E_ollama_jepa_tts` (`llama3.2:3b`): success `1.00`, reaction_text `609ms`, quality `0.7750`
- `F_mimo_short`: success `1.00`, reaction_text `2322ms`, quality `0.8000`

## Полный локальный забег по всем моделям (D/E)
Каждый прогон: `runs-per-prompt=1`, prompts=`short_1/context_1/long_1/interrupt_1` (итого 4 runs на mode).

### gemma3:latest
- Артефакт: `phase157_voice_ab_test_live_20260304_063728.json`
- `D`: success `0.50`, reaction_text p50 `13888ms`, quality `0.4125`
- `E`: success `1.00`, reaction_text p50 `1616ms`, quality `0.7375`

### llama3.2:3b
- Артефакт: `phase157_voice_ab_test_live_20260304_063941.json`
- `D`: success `0.50`, reaction_text p50 `10315ms`, quality `0.3375`
- `E`: success `1.00`, reaction_text p50 `1116ms`, quality `0.7750`

### qwen3:8b
- Артефакт: `phase157_voice_ab_test_live_20260304_064240.json`
- `D`: success `0.25`, reaction_text p50 `3207ms`, quality `0.1875`
- `E`: success `0.75`, reaction_text p50 `2671ms`, quality `0.6125`

### qwen2.5:7b
- Артефакт: `phase157_voice_ab_test_live_20260304_064526.json`
- `D`: success `0.25`, reaction_text p50 `7105ms`, quality `0.2125`
- `E`: success `1.00`, reaction_text p50 `2408ms`, quality `0.7500`

### qwen2.5:3b
- Артефакт: `phase157_voice_ab_test_live_20260304_064739.json`
- `D`: success `0.50`, reaction_text p50 `12263ms`, quality `0.3625`
- `E`: success `1.00`, reaction_text p50 `1161ms`, quality `0.7375`

### deepseek-r1:8b
- Артефакт: `phase157_voice_ab_test_live_20260304_065028.json`
- `D`: success `0.25`, reaction_text p50 `3200ms`, quality `0.2125`
- `E`: success `1.00`, reaction_text p50 `2663ms`, quality `0.7000`

## Interrupt / перебивание (проверка диалога)
В mixed run (`...062919.json`) prompt `interrupt_1`:
- Follow-up после перебивания отрабатывается в `C/D/E`.
- Лучшие наблюдаемые TTFT post-interrupt:
  - `E_ollama_jepa_tts`: ~`116ms` (лучший кейс)
  - `D_ollama_tts`: ~`123ms` (лучший кейс)
- Типичный штраф качества: `too_long_after_interrupt` (модель отвечает слишком развернуто после перебивания).

## Главный вывод по скорости + качеству
1. **Самый устойчивый и быстрый контур сейчас**: локальные `E_ollama_jepa_tts` с `llama3.2:3b` или `qwen2.5:3b`.
2. API-контур с JEPA (`C`) дает хорошее качество, но медленнее локального fast-path.
3. Для многих локальных моделей режим `D` (без JEPA-assist) заметно хуже по success/quality в grounded сценарию.
4. `ttfa_audio_ms` в текущем harness остаётся `null`: это ограничение именно bench-пути отдачи аудиочанков (не endpoint health; `/tts/generate` возвращает валидный audio).

## Что делать дальше (технически)
1. Дожать benchmark audio-chunk path до валидного `ttfa_audio` (align с прод voice-route).
2. Для interrupt-mode ввести жесткий post-interrupt короткий шаблон (1-2 фразы) перед полным разворотом, чтобы убрать `too_long_after_interrupt`.
3. В runtime выбрать default local voice model: `llama3.2:3b` (fallback: `qwen2.5:3b`) для минимальной реакционной задержки.
