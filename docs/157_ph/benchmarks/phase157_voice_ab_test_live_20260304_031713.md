# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_031713.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| E_ollama_jepa_tts | 3 | 0.3333 | 7231.77 | 11568.8 | 24772.09 | 0.3333 |

## Response Samples

### E_ollama_jepa_tts

- Prompt: `long_1`
- Tokens: `39`
- Audio chunks: `5`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_031648_587180_E_ollama_jepa_tts_long_1_run1/merged.wav`
- Audio QC: score=41.5, pauses=28, longest_pause_ms=1380, stretch=0
- Preview: `Interrupt + Restart Stream Protocol:

1. **Interrupt**: When a user sends an interrupt message (e.g., "Stop"), the system detects this and stops the current stream.
2. **`
