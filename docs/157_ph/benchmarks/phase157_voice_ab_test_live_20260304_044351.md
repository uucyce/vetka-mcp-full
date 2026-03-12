# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_044351.json`
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
- Tokens: `41`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `2 конкретных файла:

* `101_ph_eval_reactions/chat_into_vetka_grok.txt`: Этот файл необходим для понимания интеграции чатов с VETKA, поскольку в н`
- Error: `TimeoutError: per-run timeout 20.0s`
