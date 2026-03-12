# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260303_051214.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| A_qwen_only | 3 | 0.0 | None | None | None | 0.0 |
| B_api_tts | 3 | 0.0 | None | None | None | 0.0 |
| C_api_jepa_tts | 3 | 0.0 | None | None | None | 0.0 |
| D_ollama_tts | 3 | 0.0 | None | None | None | 0.0 |
| E_ollama_jepa_tts | 3 | 0.3333 | 490.85 | 5793.58 | 9315.73 | 0.3333 |

## Response Samples

### A_qwen_only

- Prompt: `short_1`
- Tokens: `29`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260303_050715_347582_A_qwen_only_short_1_run1/merged.wav`
- Preview: `VETKA - это система, которая специализируется на автоматизации процессов управления проектами и бизнесом с использованием искусств

[Stream stopped: timeout]`

### B_api_tts

- Prompt: `short_1`
- Tokens: `16`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260303_050816_407380_B_api_tts_short_1_run1/merged.wav`
- Preview: `VETKA — это российский онлайн-сервис для быстрой проверки контрагентов и подготовки налоговых документов. Он

[Stream stopped: timeout]`

### C_api_jepa_tts

- Prompt: `short_1`
- Tokens: `26`
- Audio chunks: `5`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260303_050917_966887_C_api_jepa_tts_short_1_run1/merged.wav`
- Preview: `VETKA — это российская IT-компания, специализирующаяся на разработке и внедрении комплексных цифровых решений для бизнеса. Она создает корпоративные информационные системы, мобильные при

[Stream stopped: timeout]`

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `31`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Preview: `ВЕТКА (Всероссийский экспортно-торговый центр алкогольной продукции) - это государственная компания, которая`
- Error: `TimeoutError: per-run timeout 20.0s`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `23`
- Audio chunks: `3`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260303_051123_009254_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Preview: `Vetka производит и распространяет алкогольные напитки, в основном водку и коньяк.`
