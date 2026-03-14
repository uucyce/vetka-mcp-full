# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_060301.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| B_api_tts | 8 | 0.75 | 2425.75 | None | 4293.4 | 0.6062 |
| C_api_jepa_tts | 8 | 1.0 | 1597.3 | None | 3583.22 | 0.8125 |
| D_ollama_tts | 8 | 0.0 | None | None | None | 0.3 |
| E_ollama_jepa_tts | 8 | 0.0 | None | None | None | 0.3 |
| F_mimo_short | 2 | 1.0 | 2442.62 | None | 3397.45 | 0.8 |

## Response Samples

### B_api_tts

- Prompt: `short_1`
- Tokens: `43`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `Based on the provided context, here are 2 specific files and their purposes:

1. **GROK_ANTI_GRAVITY_COLLISION_AVOIDANCE.md** - Contains formulas for dynamic collision avoidance and repulsion forces between files/branches during manual dragging in the VETKA tree layout.

2. **GRO`

### C_api_jepa_tts

- Prompt: `short_1`
- Tokens: `41`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `Based on the provided context, here are 2 specific files and their purposes:

1. **GROK_ANTI_GRAVITY_COLLISION_AVOIDANCE.md**  
   Needed for defining dynamic formulas to prevent file collisions and repulsion forces during interactive dragging in the VETKA tree layout.

2. **GROK`

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `1`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `[STREAM ERROR]:  (status code: 503)`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `1`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `[STREAM ERROR]:  (status code: 503)`

### F_mimo_short

- Prompt: `short_live`
- Tokens: `18`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `Привет! Да, я тут, но в контексте нет информации о том, что вы хотели обсудить — пожалуйста, уточните ваш вопрос.`
