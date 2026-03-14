# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260303_033731.json`
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
- Tokens: `1`
- Audio chunks: `1`
- Preview: `[STREAM ERROR]:  (status code: 503)`

### B_api_tts

- Prompt: `short_1`
- Tokens: `1`
- Audio chunks: `0`
- Preview: `[ERROR] OpenRouter: 404 - {"error":{"message":"The free Solar Pro 3 period has ended. To continue using this model, please migrate to the paid slug: upstage/solar-pro-3","code":404},"user_id":"user_2waFSRUC6TUUEboLToQUdmlI5Vf"}`

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
- Tokens: `1`
- Audio chunks: `1`
- Preview: `[STREAM ERROR]:  (status code: 503)`
