# MARKER 157: Qwen3.5 Warm-Run Profile (2026-03-05)

## Goal
Проверить, решает ли прогрев (`warm-run`) проблему задержки `qwen3.5:latest` для голосового Jarvis.

## What was tested

1) Direct Ollama `/api/generate` warmup x2 (non-stream)
- warmup #1: `38995 ms`
- warmup #2: `24305 ms`
- Оба ответа успешные (`status=200`, короткий ответ).

2) Stream behavior check (`/api/chat`, stream=true)
- первые чанки содержат только `thinking`
- первый **контент** (`message.content`) появился только через `~15609 ms`
- завершение запроса: `~16226 ms`

3) Benchmark harness warm profile
- command: `D/E` modes, `qwen3.5:latest`, `stream-timeout=60`, `per-run-timeout=70`
- artifact: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260305_000822.json`
- result: по 4 ранка на режим, но `tokens_out=0` во всех строках в этом наборе (для текущих benchmark-prompts).

## Interpretation

- Прогрев уменьшает latency (с ~39s до ~24s на non-stream), но это все еще слишком долго для "живого" voice UX.
- В stream режиме модель долго находится в скрытом этапе reasoning (`thinking`) и не отдает speech-friendly контент до ~15-16s.
- Для target (реакция около 1s, допустимо до ~5s) `qwen3.5:latest` в текущем локальном профиле **не подходит** как primary Jarvis model.

## Practical decision now

- Оставить `qwen2.5:7b + E_ollama_jepa_tts` как основной локальный профиль (лучший баланс speed/quality в наших тестах).
- `qwen3.5` держать как "deep quality" режим/ручной выбор, не realtime default.

## Repro commands

```bash
# warmup non-stream
.venv/bin/python - <<'PY'
import time, httpx
u='http://127.0.0.1:11434/api/generate'
p={'model':'qwen3.5:latest','prompt':'Привет. Ответь одним коротким предложением по-русски.','stream':False}
for i in (1,2):
    t=time.perf_counter()
    with httpx.Client(timeout=180, trust_env=False) as c:
        r=c.post(u,json=p)
    print(i, r.status_code, round((time.perf_counter()-t)*1000,2))
PY

# stream timing
.venv/bin/python - <<'PY'
import httpx, json, time
u='http://127.0.0.1:11434/api/chat'
p={'model':'qwen3.5:latest','messages':[{'role':'user','content':'Привет'}],'stream':True}
start=time.perf_counter(); first=None
with httpx.Client(timeout=240, trust_env=False) as c:
  with c.stream('POST',u,json=p) as r:
    for line in r.iter_lines():
      if not line: continue
      o=json.loads(line); m=(o.get('message') or {}).get('content','')
      if m and first is None:
        first=(time.perf_counter()-start)*1000; print('first_content_ms',round(first,2))
      if o.get('done'):
        print('total_ms',round((time.perf_counter()-start)*1000,2)); break
PY
```
