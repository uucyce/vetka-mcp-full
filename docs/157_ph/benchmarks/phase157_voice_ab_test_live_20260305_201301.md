# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260305_201301.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.25 | 3529.59 | 16551.15 | 3529.59 | 16551.15 | 52974.21 | 0.2125 |
| E_ollama_jepa_tts | 4 | 0.75 | 5166.08 | 16914.98 | 5627.07 | 21116.8 | 33457.65 | 0.6625 |

## Response Samples

### D_ollama_tts

- Prompt: `long_1`
- Tokens: `27`
- Audio chunks: `3`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_200907_704976_D_ollama_tts_long_1_run1/merged.wav`
- Audio QC: score=41.25, pauses=16, longest_pause_ms=1400, stretch=0
- Preview: `В контексте нет информации о протоколе interrupt + restart stream и его влиянии на voice handoff/tool-loop transparency.`

### E_ollama_jepa_tts

- Prompt: `context_1`
- Tokens: `50`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_201135_379968_E_ollama_jepa_tts_context_1_run1/merged.wav`
- Audio QC: score=30.5, pauses=27, longest_pause_ms=2260, stretch=0
- Preview: `1. Внедрить TAVILY в ProviderType для расширения возможностей контекста.  
2. Оптимизировать `get_recent_stats` для снижения памяти и ускорения доступ`
