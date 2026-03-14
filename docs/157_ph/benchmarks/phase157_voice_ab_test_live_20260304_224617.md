# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_224617.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.0 | None | None | 607.37 | 7528.27 | 28.01 | 0.0625 |
| E_ollama_jepa_tts | 4 | 0.25 | 307.52 | 6318.24 | 307.52 | 6318.24 | 8.19 | 0.2125 |

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
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_224557_227572_E_ollama_jepa_tts_interrupt_1_run1/merged.wav`
- Audio QC: score=39.0, pauses=21, longest_pause_ms=3420, stretch=0
- Preview: `Сначала определите цель, а затем соберите необходимую информацию. Это поможет вам двигаться вперед.
1. Сбор информации.
2. Формирование структуры.`
