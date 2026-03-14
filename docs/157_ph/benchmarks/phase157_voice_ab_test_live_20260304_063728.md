# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_063728.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.5 | 13887.9 | None | 16128.78 | 0.4125 |
| E_ollama_jepa_tts | 4 | 1.0 | 1615.97 | None | 3282.49 | 0.7375 |

## Response Samples

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `91`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `1.  `GROK_ANTI_GRAVITY_COLLISION_AVOIDANCE.md`: "Найти формулы для anti-gravity и collision avoidance между файлами/ветками"
2.  `GROK_ANTI_GRAVITY_COLLISION_AVOIDANCE.md`: "Использовать Sugiyama layered layout с Y-ось: слои (по глубине), файлы распределяются вертикально по време`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `91`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `1.  `GROK_ANTI_GRAVITY_COLLISION_AVOIDANCE.md`: "Найти формулы для anti-gravity и collision avoidance между файлами/ветками"
2.  `GROK_ANTI_GRAVITY_COLLISION_AVOIDANCE.md`: "Использовать Sugiyama layered layout с Y-ось: слои (по глубине), файлы распределяются вертикально по време`
