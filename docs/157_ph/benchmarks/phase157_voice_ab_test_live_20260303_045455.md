# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260303_045455.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| A_qwen_only | 3 | 0.3333 | 3880.26 | None | 20796.18 | 0.3333 |
| B_api_tts | 3 | 0.3333 | 10972.43 | None | 27992.93 | 0.3333 |
| C_api_jepa_tts | 3 | 0.0 | None | None | None | 0.0 |
| D_ollama_tts | 3 | 0.3333 | 14344.85 | None | 23294.38 | 0.3333 |
| E_ollama_jepa_tts | 3 | 0.3333 | 4820.73 | None | 13674.33 | 0.3333 |

## Response Samples

### A_qwen_only

- Prompt: `short_1`
- Tokens: `89`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Preview: `VETKA специализируется на разработке и внедрении инновационных решений для автоматизации бизнес-процессов, управления данными и аналитики. Компания предлагает услуги по цифровой трансформации, помогая организациям улучшить эффективность, снизить затраты и увеличить конкурентоспос`

### B_api_tts

- Prompt: `short_1`
- Tokens: `73`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Preview: `VETKA — это российский сервис для поиска и бронирования туров, который агрегирует предложения от туроператоров и турагентств. Он позволяет пользователям сравнивать цены, читать отзывы и находить горящие туры, а также помогает турагентам управлять заявками и вести клиентскую базу `

### C_api_jepa_tts

- Prompt: `short_1`
- Tokens: `21`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Preview: `VETKA — это российский сервис для **создания и продажи онлайн-курсов**. Он`
- Error: `TimeoutError: per-run timeout 25.0s`

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `37`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Preview: `Vetka - российская компания, производящая напитки на основе фруктового сока (красный перец, лимонад и т.п.).`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `29`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Preview: `Vetka - российская компания, производящая алкогольные напитки, в частности, водку и коньяк.`
