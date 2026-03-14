# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260303_043532.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| A_qwen_only | 3 | 0.3333 | 2948.52 | None | 11624.92 | 0.3333 |
| B_api_tts | 3 | 0.0 | None | None | None | 0.0 |
| C_api_jepa_tts | 3 | 0.0 | None | None | None | 0.0 |
| D_ollama_tts | 3 | 0.3333 | 4197.1 | 12613.59 | 12615.14 | 0.3333 |
| E_ollama_jepa_tts | 3 | 0.3333 | 9374.05 | None | 18822.25 | 0.3333 |

## Response Samples

### A_qwen_only

- Prompt: `short_1`
- Tokens: `40`
- Audio chunks: `0`
- Preview: `VETKA - это платформа для создания и продажи виртуальных товаров, таких как игры, косметика и одежда, используя технологию NFT.`

### B_api_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Preview: `[empty]`

### C_api_jepa_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Preview: `[empty]`

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `39`
- Audio chunks: `1`
- Preview: `ВЕТКА - российская компания, которая производит и продает алкогольные напитки, такие как водка, коньяк и другие крепкие спиртные напитки.`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `43`
- Audio chunks: `0`
- Preview: `ВЕТКА - российская компания, которая производит и продает алкогольные напитки, такие как водка, коньяк и другие спиртные напитки под собственными брендами.`
