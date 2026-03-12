# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_042048.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 9 | 0.0 | None | None | None | 0.0 |
| E_ollama_jepa_tts | 9 | 0.0 | None | None | None | 0.0 |

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
- Tokens: `53`
- Audio chunks: `3`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_041638_844989_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=55.0, pauses=21, longest_pause_ms=1420, stretch=0
- Preview: `Okay, based on the provided context, here's a response to the user's question:

**File 1: `data/playground_proposals.json`**

*   **Purpose:** This file stores a collection of research prompts and their`
- Error: `TimeoutError: per-run timeout 25.0s`
