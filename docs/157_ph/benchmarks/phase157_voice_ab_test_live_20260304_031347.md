# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_031347.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 3 | 0.0 | None | None | None | 0.0 |
| E_ollama_jepa_tts | 3 | 1.0 | 6643.9 | 12820.15 | 26337.73 | 1.0 |

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
- Tokens: `21`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_031227_974128_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=25.0, pauses=18, longest_pause_ms=3400, stretch=0
- Preview: `I can't provide a direct answer to your question. However, I can offer some guidance on how`
