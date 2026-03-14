# MARKER 157.3.1 — Stage-Machine Audit + Baseline (2026-03-06)

## Scope
Проверка текущего Jarvis voice-пайплайна перед внедрением stage-machine:
- что уже есть в код-базе,
- что уже покрывает часть требований,
- что ломает runtime,
- baseline-метрики до правок.

## Audit Findings (Current State)

### 1) Runtime state-machine в Jarvis уже есть, но только UI/state
Файлы:
- `client/src/hooks/useJarvis.ts`
- `src/api/handlers/jarvis_handler.py`

Наблюдение:
- frontend/backend уже работают с состояниями `idle -> listening -> thinking -> speaking -> idle`;
- VAD auto-stop есть;
- interrupt event `jarvis_interrupt_request` есть.

Ограничение:
- это state-machine состояния UI/сессии, а не stage-machine генерации ответа (Chunk1/2/3/4).

### 2) Элесья/память уже участвует в цепи
Файл:
- `src/voice/jarvis_llm.py`

Наблюдение:
- `get_jarvis_context()` подмешивает STM/CAM/Engram + live client context (`viewport_context`, `pinned_files`, `open_chat_context`);
- `resolve_jarvis_text_model()` уже поддерживает preferred/favorites/free/local/default маршрутизацию.

Вывод:
- stage-machine не должен заменять Elisya/memory path; он должен оркестрировать этапы поверх существующего контекстного контура.

### 3) Критичный runtime bug в `jarvis_handler.py`
Файл:
- `src/api/handlers/jarvis_handler.py`

Факт:
- у `JarvisSession` отсутствуют методы `add_audio_chunk/get_full_audio` из-за неверной индентации (методы оказались внутри `_extract_client_context` после `return`).
- проверка импортом: `hasattr(JarvisSession, 'add_audio_chunk') == False`, `hasattr(JarvisSession, 'get_full_audio') == False`.

Влияние:
- pipeline `jarvis_audio_chunk -> jarvis_listen_stop` может срываться на сборке аудио-сессии.

### 4) Генерация/озвучка сейчас монолитная
Файл:
- `src/api/handlers/jarvis_handler.py` (`jarvis_listen_stop`)

Наблюдение:
- после STT выполняется один LLM вызов и один TTS синтез;
- нет staged/handoff оркестрации (Chunk1/2/3/4) как отдельного runtime layer.

## Baseline Bench (Before Stage-Machine)

Прогон:
- `python scripts/voice_mode_benchmark.py --modes D_ollama_tts,E_ollama_jepa_tts --ollama-model gemma3:1b --runs-per-prompt 1 --per-run-timeout-sec 25 --stream-timeout-sec 20 --max-output-tokens 96 --grounded-limit 6`
- артефакт: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260306_005544.{json,csv,md}`

Сводка:
- `D_ollama_tts`:
  - success_rate: `0.5`
  - ttft_text_ms_p50: `1807.42`
  - ttfa_audio_ms_p50: `4758.88`
  - e2e_ms_p50: `25187.48`
  - quality_proxy_mean: `0.3375`
- `E_ollama_jepa_tts`:
  - success_rate: `0.5`
  - ttft_text_ms_p50: `863.86`
  - ttfa_audio_ms_p50: `6303.52`
  - e2e_ms_p50: `21575.25`
  - quality_proxy_mean: `0.4125`

## Conclusion (Before Changes)
- Elisya/memory already in flow: **yes**.
- Runtime stage-machine (Chunk1/2/3/4): **no**.
- Есть блокирующий баг с методами `JarvisSession`: **yes**.
- Baseline зафиксирован, можно внедрять stage-machine и сравнивать «до/после».
