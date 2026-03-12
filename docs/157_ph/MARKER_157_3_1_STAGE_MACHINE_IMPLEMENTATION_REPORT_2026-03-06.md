# MARKER 157.3.1 — Stage-Machine Implementation Report (2026-03-06)

## What Was Implemented

### 1) Critical runtime fix (blocking)
Файл: `src/api/handlers/jarvis_handler.py`
- Исправлена структура `JarvisSession`: методы `add_audio_chunk()` и `get_full_audio()` возвращены в класс.
- Проверка импортом после фикса: оба метода доступны.

### 2) Stage-machine orchestration added to Jarvis stop pipeline
Файл: `src/api/handlers/jarvis_handler.py` (`jarvis_listen_stop`)

Добавлен staged runtime path:
- **Chunk1 (Plan B filler)**: `_emit_planb_filler_if_slow(...)`
  - асинхронный delayed emit (`status="filler"`) если ответ не готов в заданный SLA-дельта интервал.
- **Chunk2 (fast local)**: модель `JARVIS_STAGE2_MODEL` (по умолчанию `gemma3:1b`).
- **Chunk3 (smart local)**: primary/secondary (`deepseek-r1:8b` / `llama3.2:3b`).
- **Chunk4 (deep)**: опционально (при deep query), модель из `JARVIS_STAGE4_MODEL`/user-selected `llm_model`.

Добавлены helper-функции:
- `_is_deep_query(...)`
- `_generate_stage_response(...)`
- адаптивный filler-bank loader/saver/select/learn:
  - `_load_filler_bank`, `_save_filler_bank`, `_select_filler_phrase`, `_learn_filler_phrase`

### 3) Language hint for TTS path
Файл: `src/api/handlers/jarvis_handler.py`
- TTS language теперь выбирается по языковому хинту (`Russian/English`) на основе входа/ответа.
- FastTTS voice также переключается по языковому хинту.

## Elisya / Memory Participation
- **Сохранено**: stage-machine не обходит memory/Elisya контур.
- Контекст по-прежнему идет через `get_jarvis_context(...)`:
  - STM, CAM, Engram + live `viewport_context`, `pinned_files`, `open_chat_context`.
- Stage-machine использует этот контекст как source-of-truth для всех chunk-стадий.

## Tests

### New tests
Файл: `tests/test_phase157_3_1_stage_machine_basics.py`
- Проверка методов `JarvisSession`.
- Проверка deep-query trigger.
- Проверка получения Plan-B filler phrase.

### Existing tests re-run
- `tests/test_phase157_planb_filler.py` ✅
- `tests/jarvis_live/test_jarvis_live_context.py` ✅
- `tests/test_phase157_3_1_stage_machine_basics.py` ✅

## Benchmarks (Before vs After snapshot)

### Baseline before changes
- Артефакт: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260306_005544.*`
- `D_ollama_tts`: success_rate `0.5`, ttfa_audio_p50 `4758.88ms`
- `E_ollama_jepa_tts`: success_rate `0.5`, ttfa_audio_p50 `6303.52ms`

### Snapshot after implementation
- Артефакт: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260306_010855.*`
- `D_ollama_tts`: success_rate `0.5`, ttfa_audio_p50 `9602.13ms` (нестабильно)
- `E_ollama_jepa_tts`: success_rate `0.75`, ttfa_audio_p50 `3933.48ms` (улучшение по этому профилю)

## Interpretation
- Наблюдается нестабильность локального стрим-пути между прогонами (таймауты `STREAM_V2` остаются фактором).
- Stage-machine + filler теперь есть в runtime и может скрывать паузы UX-уровнем.
- Для decision-grade вывода нужны 3-run/per-prompt и фиксированные thermal/runtime условия.

## Non-regression note
- Chat-panel voice mode path отдельно не трогался (изменения ограничены `jarvis_handler` для Jarvis voice button flow).
