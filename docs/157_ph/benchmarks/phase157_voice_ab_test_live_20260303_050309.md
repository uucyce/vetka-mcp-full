# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260303_050309.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| A_qwen_only | 3 | 0.0 | None | None | None | 0.0 |
| B_api_tts | 3 | 0.0 | None | None | None | 0.0 |
| C_api_jepa_tts | 3 | 0.0 | None | None | None | 0.0 |
| D_ollama_tts | 3 | 0.0 | None | None | None | 0.0 |
| E_ollama_jepa_tts | 3 | 0.0 | None | None | None | 0.0 |

## Response Samples

### A_qwen_only

- Prompt: `short_1`
- Tokens: `40`
- Audio chunks: `5`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260303_045808_247184_A_qwen_only_short_1_run1/merged.wav`
- Preview: `VETKA - это система, которая специализируется на автоматизации процессов управления проектами и ресурсами. Она помогает организациям эффективно планировать, контрол

[Stream stopped: timeout]`

### B_api_tts

- Prompt: `short_1`
- Tokens: `21`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260303_045907_595447_B_api_tts_short_1_run1/merged.wav`
- Preview: `VETKA — это российский сервис для поиска и бронирования ветеринарных клиник, работающий по модели маркетплейса. При

[Stream stopped: timeout]`

### C_api_jepa_tts

- Prompt: `short_1`
- Tokens: `25`
- Audio chunks: `6`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260303_050005_662610_C_api_jepa_tts_short_1_run1/merged.wav`
- Preview: `VETKA — это российский сервис для поиска и бронирования туров, который агрегирует предложения от туроператоров в одном месте. Он позволяет пользователям сравнивать цены, ч

[Stream stopped: timeout]`

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `34`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260303_050104_100828_D_ollama_tts_short_1_run1/merged.wav`
- Preview: `Vetka - это российская компания, которая производит и продает алкогольные напитки, такие как водка, коньяк и другие креп

[Stream stopped: timeout]`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `36`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260303_050208_999581_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Preview: `Vetka - это российская компания, которая производит и продает алкогольные напитки на основе фруктовых соков, в частности, на

[Stream stopped: timeout]`
