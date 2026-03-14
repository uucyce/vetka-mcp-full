# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260305_210453.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.25 | 5953.44 | 16515.55 | 22070.69 | 39250.29 | 66197.16 | 0.2375 |
| E_ollama_jepa_tts | 4 | 0.75 | 6264.61 | 19676.48 | 6679.39 | 21696.12 | 36969.35 | 0.575 |

## Response Samples

### D_ollama_tts

- Prompt: `long_1`
- Tokens: `25`
- Audio chunks: `3`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_210039_458815_D_ollama_tts_long_1_run1/merged.wav`
- Audio QC: score=43.75, pauses=17, longest_pause_ms=1200, stretch=0
- Preview: `The provided context does not explain the interrupt + restart stream protocol or its influence on voice handoff/tool-loop transparency.`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `58`
- Audio chunks: `3`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_210228_109340_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=43.25, pauses=35, longest_pause_ms=1240, stretch=0
- Preview: `1. `/U/d/D/V/v/d/1/вкладка **Playground_GROK.txt`: Содержит готовый backend-код для эндпоинта `/api/debug/playground/proposals`.
2. ``
