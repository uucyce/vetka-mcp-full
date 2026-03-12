# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_032031.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| E_ollama_jepa_tts | 3 | 0.3333 | 5944.15 | 12057.41 | 25713.73 | 0.3333 |

## Response Samples

### E_ollama_jepa_tts

- Prompt: `long_1`
- Tokens: `40`
- Audio chunks: `5`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_032005_690966_E_ollama_jepa_tts_long_1_run1/merged.wav`
- Audio QC: score=36.5, pauses=24, longest_pause_ms=1780, stretch=0
- Preview: `Interrupt + Restart Stream Protocol:

1. **Interrupt**: When the `tool_execution_mode` is not set to `enabled_stream`, the model should not claim that tools were executed.
2. **`
