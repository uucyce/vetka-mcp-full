# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_063941.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.5 | 10314.62 | None | 11730.17 | 0.3375 |
| E_ollama_jepa_tts | 4 | 1.0 | 1116.43 | None | 3418.2 | 0.775 |

## Response Samples

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `24`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `Базовый ответ не могу предоставить, поскольку falta информация о конкретных файлах и их содержимyah.`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `128`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `Базовые файлы:

* `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/92_ph/HAIKU_3_SOCKET_STOP.md` - `scan_progress` с `{progress, status}` для frontend.
* `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/92_ph/watcher_routes.py` - Emit `scan_complete` с`
