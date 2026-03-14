# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_211303.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.25 | 287.37 | 4963.94 | 287.37 | 4963.94 | 34.44 | 0.2125 |
| E_ollama_jepa_tts | 4 | 0.25 | 194.0 | 3476.21 | 194.0 | 3476.21 | 15.58 | 0.2125 |

## Response Samples

### D_ollama_tts

- Prompt: `interrupt_1`
- Tokens: `41`
- Audio chunks: `3`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_211218_758197_D_ollama_tts_interrupt_1_run1/merged.wav`
- Audio QC: score=53.38, pauses=16, longest_pause_ms=1840, stretch=0
- Preview: `Сначала определи цель, затем составь план.Начните с определения структуры данных, затем сформируйте битовую последовательность.`

### E_ollama_jepa_tts

- Prompt: `interrupt_1`
- Tokens: `38`
- Audio chunks: `3`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_211244_978803_E_ollama_jepa_tts_interrupt_1_run1/merged.wav`
- Audio QC: score=56.74, pauses=15, longest_pause_ms=980, stretch=0
- Preview: `Сначала определи цель, потом составь план.Начни с определения переменных, затем сформируй структуру для пакетирования.`
