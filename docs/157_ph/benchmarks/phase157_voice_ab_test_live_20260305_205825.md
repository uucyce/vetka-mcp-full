# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260305_205825.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.25 | 2820.6 | 10857.93 | 16831.76 | 27850.71 | 59036.68 | 0.2625 |
| E_ollama_jepa_tts | 4 | 1.0 | 1673.31 | 8790.82 | 1673.31 | 8790.82 | 29199.65 | 0.7375 |

## Response Samples

### D_ollama_tts

- Prompt: `long_1`
- Tokens: `92`
- Audio chunks: `6`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_205447_358982_D_ollama_tts_long_1_run1/merged.wav`
- Audio QC: score=40.75, pauses=48, longest_pause_ms=1440, stretch=0
- Preview: `Here’s a breakdown of the interrupt and restart stream protocol, referencing the provided context:

1.  **Stream Start:** The `chat_voice_stream_start` socket contract initiates the stream. A `voice_pending` bubble is created on the `stream_start`.

2.  **Stream Chunks:**  `chat_`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `65`
- Audio chunks: `3`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_205630_186486_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=33.0, pauses=20, longest_pause_ms=2060, stretch=0
- Preview: `1.  `108_knowledg_directed_chat_artefacts.txt`: “Мы работаем по такому алгоритму - Ты архитектор, командир…”
2.  `open_router_bridge.py`: “Мост для взаимодействия с OpenRouter через VETKA MCP.”`
