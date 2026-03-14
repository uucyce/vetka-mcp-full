# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_030852.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 3 | 0.0 | None | None | None | 0.0 |
| E_ollama_jepa_tts | 3 | 0.6667 | 8431.44 | 14302.17 | 25686.59 | 0.6667 |

## Response Samples

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `[empty]`
- Error: `TimeoutError: per-run timeout 25.0s`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `37`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_030733_883065_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=62.58, pauses=16, longest_pause_ms=1600, stretch=0
- Preview: `Okay, here’s a concise description of what VETKA does, suitable for a user who might be new to the project:

“VETKA is a knowledge management`
