# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_221159.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.0 | None | None | 456.66 | 5214.22 | 27.21 | 0.0625 |
| E_ollama_jepa_tts | 4 | 0.0 | None | None | 276.09 | 10837.63 | 12.67 | 0.0625 |

## Response Samples

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `[empty]`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `[empty]`
