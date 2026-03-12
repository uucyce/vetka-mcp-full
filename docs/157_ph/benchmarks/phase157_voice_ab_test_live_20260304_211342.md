# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_211342.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.0 | None | None | None | None | 26.96 | 0.0125 |
| E_ollama_jepa_tts | 4 | 0.25 | 3064.39 | 9923.76 | 3064.39 | 9923.76 | 6.87 | 0.1625 |

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
- Tokens: `13`
- Audio chunks: `3`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_211316_998992_E_ollama_jepa_tts_interrupt_1_run1/merged.wav`
- Audio QC: score=65.64, pauses=14, longest_pause_ms=900, stretch=0
- Preview: `Определите проблему. Найдите возможные решения.`
