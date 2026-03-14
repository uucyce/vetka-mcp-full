# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260303_034146.json`
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
- Preview: `[ERROR] OpenRouter: 429 - {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"qwen/qwen3-coder:free is temporarily rate-limited upstream. Please retry shortly, or add your own key to accumulate your rate limits: https://openrouter.ai/settings/integrations"`

### C_api_jepa_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Preview: `[empty]`
- Error: `TimeoutError: per-run timeout 20.0s`

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `1`
- Audio chunks: `1`
- Preview: `[STREAM ERROR]:  (status code: 503)`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `1`
- Audio chunks: `1`
- Preview: `[STREAM ERROR]:  (status code: 503)`
