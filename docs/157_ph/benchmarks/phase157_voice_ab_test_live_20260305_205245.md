# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260305_205245.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.25 | 1208.45 | 5833.78 | 15430.25 | 20377.33 | 55115.76 | 0.2125 |
| E_ollama_jepa_tts | 4 | 1.0 | 521.1 | 5088.56 | 521.1 | 5088.56 | 40045.94 | 0.65 |

## Response Samples

### D_ollama_tts

- Prompt: `long_1`
- Tokens: `90`
- Audio chunks: `10`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_204837_957395_D_ollama_tts_long_1_run1/merged.wav`
- Audio QC: score=43.75, pauses=63, longest_pause_ms=1200, stretch=0
- Preview: `Okay, let’s break down the problem and how to address it, focusing on the context provided.

Here’s a breakdown of the issue and the steps to resolve it:

1. **The Core Problem:** The current system has a fragmented approach to the TTS pipeline – the `stream` and `tool calling` l`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `99`
- Audio chunks: `8`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_205019_378623_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=45.5, pauses=53, longest_pause_ms=1060, stretch=0
- Preview: `Here are two specific files and one phrase explaining their purpose, based on the provided context:

*   **PHASE\_52\_6\_SIMPLE\_SMOOTH\_CAMERA.md:** This file contains the core code for the camera movement, specifically the smooth camera effect.
*   **ПроБЛЕМА:** This file descr`
