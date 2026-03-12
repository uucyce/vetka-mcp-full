# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_221249.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.0 | None | None | 307.69 | 18313.89 | 29.43 | 0.0625 |
| E_ollama_jepa_tts | 4 | 0.25 | 332.07 | 5302.02 | 332.07 | 5302.02 | 8.91 | 0.2125 |

## Response Samples

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `[empty]`

### E_ollama_jepa_tts

- Prompt: `interrupt_1`
- Tokens: `36`
- Audio chunks: `5`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_221227_462910_E_ollama_jepa_tts_interrupt_1_run1/merged.wav`
- Audio QC: score=51.64, pauses=16, longest_pause_ms=1100, stretch=0
- Preview: `Сначала определите задачу, затем соберите необходимую информацию. Всё, это основные шаги!
1. Подготовка данных.
2. Формирование контекста.`
