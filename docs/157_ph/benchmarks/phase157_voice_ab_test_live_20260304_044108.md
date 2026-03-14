# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_044108.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 3 | 0.0 | None | None | None | 0.0 |
| E_ollama_jepa_tts | 3 | 0.0 | None | None | None | 0.0 |

## Response Samples

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `[empty]`
- Error: `TimeoutError: per-run timeout 20.0s`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `42`
- Audio chunks: `2`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_043958_445931_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=35.0, pauses=11, longest_pause_ms=2460, stretch=0
- Preview: `Okay, based on the provided context, here’s a response to the user’s question:

**File 1: `knowledge_layout.py`**

*   **Purpose:** This file`
- Error: `TimeoutError: per-run timeout 20.0s`
