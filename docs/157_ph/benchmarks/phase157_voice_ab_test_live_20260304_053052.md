# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_053052.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 3 | 0.0 | None | None | None | 0.0 |
| E_ollama_jepa_tts | 3 | 0.0 | None | None | None | 0.0 |

## Response Samples

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `10`
- Audio chunks: `1`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_052752_836197_D_ollama_tts_short_1_run1/merged.wav`
- Audio QC: score=51.0, pauses=4, longest_pause_ms=2300, stretch=0
- Preview: `Базовые 2 файла:

1. `/`
- Error: `TimeoutError: per-run timeout 25.0s`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `72`
- Audio chunks: `1`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_052929_267129_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=71.0, pauses=11, longest_pause_ms=700, stretch=0
- Preview: `2 конкретных файла:

1. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/101_ph_eval_reactions/chat_into_vetka_grok.txt` - Этот файл необходим для понимания интеграции чатов в VETKA как "динамических артефактов".
2. `/`
- Error: `TimeoutError: per-run timeout 25.0s`
