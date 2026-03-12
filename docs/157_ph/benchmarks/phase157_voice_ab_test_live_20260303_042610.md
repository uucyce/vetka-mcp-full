# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260303_042610.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| A_qwen_only | 3 | 0.3333 | 3767.56 | None | 12565.68 | 0.3333 |
| B_api_tts | 3 | 0.0 | None | None | None | 0.0 |
| C_api_jepa_tts | 3 | 0.0 | None | None | None | 0.0 |
| D_ollama_tts | 3 | 0.3333 | 4939.28 | None | 13837.28 | 0.3333 |
| E_ollama_jepa_tts | 3 | 0.3333 | 5544.86 | None | 15113.77 | 0.3333 |

## Response Samples

### A_qwen_only

- Prompt: `short_1`
- Tokens: `54`
- Audio chunks: `0`
- Preview: `VETKA - это платформа для управления проектами, которая помогает командам эффективно планировать, организовывать и контролировать проекты, обеспечивая прозрачность и координацию между всеми участниками.`

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
- Tokens: `35`
- Audio chunks: `0`
- Preview: `Vetka - российская компания, производящая алкогольные напитки, известная своими крепкими напитками и ликёром "Ветка".`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `45`
- Audio chunks: `0`
- Preview: `Vetka - российская компания, производящая алкогольные напитки, особенно известна своей продукцией из ягод и фруктов, таких как клюква, черника и вишня.`
