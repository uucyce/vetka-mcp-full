# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260306_005544.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.5 | 1807.42 | 4758.88 | 5355.81 | 9844.14 | 26273.8 | 0.3375 |
| E_ollama_jepa_tts | 4 | 0.5 | 863.86 | 6303.52 | 649.31 | 4932.51 | 26366.65 | 0.4125 |

## Response Samples

### D_ollama_tts

- Prompt: `long_1`
- Tokens: `66`
- Audio chunks: `7`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260306_005317_626052_D_ollama_tts_long_1_run1/merged.wav`
- Audio QC: score=39.15, pauses=32, longest_pause_ms=1620, stretch=0
- Preview: `Okay, let's break down how to interrupt and restart the stream protocol, focusing on voice handoff and transparency, referencing the provided context.

**Understanding the Issue**

The core problem is that the current implementation of the stream protocol isn't correctly handling`

### E_ollama_jepa_tts

- Prompt: `context_1`
- Tokens: `55`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260306_005435_481948_E_ollama_jepa_tts_context_1_run1/merged.wav`
- Audio QC: score=51.71, pauses=20, longest_pause_ms=1280, stretch=0
- Preview: `1.  Optimize `jepa_runtime.py` for faster trigger calculations.
2.  Reduce the number of `pack_latency_ms` metrics in the recent stats API.
3.  Implement a more efficient memory management strategy for the probe tool.`
