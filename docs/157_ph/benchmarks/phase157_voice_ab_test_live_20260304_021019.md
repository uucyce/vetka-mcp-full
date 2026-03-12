# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_021019.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 6 | 0.6667 | 182.03 | 4707.54 | 19098.9 | 0.6667 |
| E_ollama_jepa_tts | 6 | 1.0 | 198.47 | 5339.32 | 22759.99 | 1.0 |

## Response Samples

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `32`
- Audio chunks: `3`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_020556_026731_D_ollama_tts_short_1_run1/merged.wav`
- Audio QC: score=76.87, pauses=13, longest_pause_ms=920, stretch=0
- Preview: `VETKA - это платформа для инвестирования в криптовалюту, предлагающая автоматизированные торговые стратегии и доступ к широкому спектру активов.`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `37`
- Audio chunks: `3`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_020817_056605_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=58.99, pauses=16, longest_pause_ms=1900, stretch=0
- Preview: `VETKA – это платформа для инвестирования в криптовалюту, предлагающая автоматизированные торговые боты, которые используют алгоритмы для торговли на различных криптовалютных биржах.`
