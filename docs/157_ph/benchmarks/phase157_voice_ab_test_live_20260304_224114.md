# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_224114.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.0 | None | None | None | None | 35.1 | 0.0 |
| E_ollama_jepa_tts | 4 | 0.25 | 170.34 | 4474.42 | 170.34 | 4474.42 | 8.46 | 0.2125 |

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
- Audio chunks: `3`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_224057_390583_E_ollama_jepa_tts_interrupt_1_run1/merged.wav`
- Audio QC: score=74.0, pauses=9, longest_pause_ms=1100, stretch=0
- Preview: `Сначала определите цель, потом составьте план.Начни с определения контекста, затем упакуй его в структуру.`
