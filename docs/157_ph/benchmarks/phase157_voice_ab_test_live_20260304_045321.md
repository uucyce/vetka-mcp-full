# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_045321.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 3 | 0.0 | None | None | None | 0.0 |
| E_ollama_jepa_tts | 3 | 0.0 | None | None | None | 0.0 |

## Response Samples

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `[empty]`
- Error: `TimeoutError: per-run timeout 20.0s`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `98`
- Audio chunks: `1`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_045208_868395_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=54.25, pauses=3, longest_pause_ms=2040, stretch=0
- Preview: `1. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/95_ph/HAIKU_TEST_4_WATCHER_MARKERS.md`: Для проверки маркеров в watcher_routes.py.
2. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/139_ph/вкладка **Playground_GROK.txt`: Создание API для работы вк`
- Error: `TimeoutError: per-run timeout 20.0s`
