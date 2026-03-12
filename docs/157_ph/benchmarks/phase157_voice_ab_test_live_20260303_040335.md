# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260303_040335.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| A_qwen_only | 3 | 0.0 | None | None | None | 0.0 |
| B_api_tts | 3 | 0.0 | None | None | None | 0.0 |
| C_api_jepa_tts | 3 | 0.0 | None | None | None | 0.0 |
| D_ollama_tts | 3 | 0.0 | None | None | None | 0.0 |
| E_ollama_jepa_tts | 3 | 0.3333 | 447.99 | None | 17668.57 | 0.3333 |

## Response Samples

### A_qwen_only

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Preview: `[empty]`
- Error: `TimeoutError: per-run timeout 20.0s`

### B_api_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Preview: `[empty]`
- Error: `TimeoutError: per-run timeout 20.0s`

### C_api_jepa_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Preview: `[empty]`
- Error: `TimeoutError: per-run timeout 20.0s`

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Preview: `[empty]`
- Error: `TimeoutError: per-run timeout 20.0s`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `42`
- Audio chunks: `0`
- Preview: `ВЕТКА - российская компания, производящая алкогольные напитки, включая водку и коньяк. Основной продукцией является водка «Водка Ветка».`
