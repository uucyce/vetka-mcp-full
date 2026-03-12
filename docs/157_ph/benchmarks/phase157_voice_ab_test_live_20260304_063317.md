# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_063317.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| C_api_jepa_tts | 4 | 0.5 | 11673.13 | None | 13357.7 | 0.4375 |
| D_ollama_tts | 4 | 1.0 | 1146.87 | None | 3535.53 | 0.8 |
| F_mimo_short | 1 | 1.0 | 2862.42 | None | 3678.25 | 0.8 |

## Response Samples

### C_api_jepa_tts

- Prompt: `short_1`
- Tokens: `34`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `1. **HAIKU_TEST_4_WATCHER_MARKERS.md** — Проверяет корректность маркеров BYPASS в watcher_routes.py, чтобы обеспечить правильную интеграцию с TripleWriteManager.
2. **HAIKU_1_BACKEND_STOP.md** — Описывает механизм остановки бэкенда, включая API endpoint для graceful shutdown скан`

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `128`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `Базовый ответ:

2 конкретных файла:

1. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py` - нужен для анализа watcher_routes.py и проверки маркеров.
2. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/95_ph/HAIKU_TEST_4_WATC`

### F_mimo_short

- Prompt: `short_live`
- Tokens: `19`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `Да, я здесь! В контексте есть файлы VETKA и MYCELIUM, но конкретно о том, "ты тут?" — информации нет.`
