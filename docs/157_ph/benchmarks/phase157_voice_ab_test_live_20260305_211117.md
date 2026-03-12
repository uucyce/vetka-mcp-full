# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260305_211117.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.25 | 2010.81 | 10610.18 | 15890.93 | 25124.9 | 57835.42 | 0.2375 |
| E_ollama_jepa_tts | 4 | 1.0 | 1610.15 | 9119.89 | 1610.15 | 9119.89 | 40553.51 | 0.775 |

## Response Samples

### D_ollama_tts

- Prompt: `long_1`
- Tokens: `53`
- Audio chunks: `6`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_210651_022195_D_ollama_tts_long_1_run1/merged.wav`
- Audio QC: score=40.25, pauses=25, longest_pause_ms=1480, stretch=0
- Preview: `Based on the provided context, there is no explicit mention of an "interrupt + restart stream protocol" or its influence on voice handoff/tool-loop transparency. The context discusses a unified capability matrix for VETKA chat and Mycelium runtime, aiming to standard`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `55`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_210837_217001_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=25.0, pauses=26, longest_pause_ms=5680, stretch=0
- Preview: `1. **вкладка Playground_GROK.txt**: Этот файл содержит готовый backend-код для эндпоинта `/api/debug/playground/proposals`, который позволяет вкладка **Playground** в `MyceliumCommandCenter` работать сразу. Он`
