# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_dry_20260304_030426.json`
- Dry run: `True`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| A_qwen_only | 3 | 1.0 | 20.0 | 50.0 | 52.15 | 1.0 |
| B_api_tts | 3 | 1.0 | 20.0 | 50.0 | 52.2 | 1.0 |
| C_api_jepa_tts | 3 | 1.0 | 20.0 | 50.0 | 51.26 | 1.0 |
| D_ollama_tts | 3 | 1.0 | 20.0 | 50.0 | 51.24 | 1.0 |
| E_ollama_jepa_tts | 3 | 1.0 | 20.0 | 50.0 | 52.22 | 1.0 |
| F_mimo_short | 1 | 1.0 | 20.0 | 50.0 | 52.18 | 1.0 |

## Response Samples

### A_qwen_only

- Prompt: `short_1`
- Tokens: `20`
- Audio chunks: `1`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `DRY_RUN_SYNTHETIC`

### B_api_tts

- Prompt: `short_1`
- Tokens: `20`
- Audio chunks: `1`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `DRY_RUN_SYNTHETIC`

### C_api_jepa_tts

- Prompt: `short_1`
- Tokens: `20`
- Audio chunks: `1`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `DRY_RUN_SYNTHETIC`

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `20`
- Audio chunks: `1`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `DRY_RUN_SYNTHETIC`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `20`
- Audio chunks: `1`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `DRY_RUN_SYNTHETIC`

### F_mimo_short

- Prompt: `short_live`
- Tokens: `20`
- Audio chunks: `1`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `DRY_RUN_SYNTHETIC`
