# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_064240.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.25 | 3207.24 | None | 7397.7 | 0.1875 |
| E_ollama_jepa_tts | 4 | 0.75 | 2671.23 | None | 6632.18 | 0.6125 |

## Response Samples

### D_ollama_tts

- Prompt: `long_1`
- Tokens: `128`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `<think>
Okay, let's tackle this user question. They want a step-by-step explanation of the interrupt + restart stream protocol and its impact on voice handoff and tool-loop transparency, referencing the provided context. If the context doesn't cover it, I need to state that clear`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `128`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `<think>
Okay, let's tackle this user question. The user wants two specific files from the provided context and a one-line reason for each. If there's no info, I should say so.

First, I'll check the pinned_context. There are two files listed. The first one is "PHASE_52_6_SIMPLE_S`
