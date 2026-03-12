# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_045030.json`
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
- Tokens: `63`
- Audio chunks: `1`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_044905_682795_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=98.14, pauses=3, longest_pause_ms=440, stretch=0
- Preview: `1. **Файл:** /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/PHASE_14/GROK_ANTI_GRAVITY_COLLISION_AVOIDANCE.md  
   **Назначение:** Описывает алгоритмы для пред`
- Error: `TimeoutError: per-run timeout 20.0s`
