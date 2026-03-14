# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_065028.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.25 | 3200.18 | None | 7299.5 | 0.2125 |
| E_ollama_jepa_tts | 4 | 1.0 | 2662.84 | None | 6472.84 | 0.7 |

## Response Samples

### D_ollama_tts

- Prompt: `long_1`
- Tokens: `128`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `<think>
Хорошо, пользователь спрашивает о пошаговом объяснении протокола прерывания и повторного запуска потока (interrupt + restart stream protocol) и его влиянии на voice handoff и tool-loop transparency. Вижу, что в предоставленном контексте есть файл "CAPABILITY_MATRIX_UNIFIE`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `128`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `<think>
Okay, let's break this down based on the provided context. 

First, I see there's only one current file mentioned in the dependency context: `GROK_ANTI_GRAVITY_COLLISION_AVOIDANCE.md`. That seems to be about camera movement issues (like sudden lateral movements) and a use`
