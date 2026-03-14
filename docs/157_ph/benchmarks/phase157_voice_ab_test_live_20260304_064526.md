# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_064526.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.25 | 7104.71 | None | 9159.44 | 0.2125 |
| E_ollama_jepa_tts | 4 | 1.0 | 2408.17 | None | 4275.62 | 0.75 |

## Response Samples

### D_ollama_tts

- Prompt: `long_1`
- Tokens: `73`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `В предоставленном контексте не найдено информации о протоколе interrupt + restart stream и его влиянии на прозрачность передачи голоса (voice handoff) и tool-loop. Следовательно, нельзя дать пошаговое объяснение этой темы ссылаясь на данный контекст.`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `98`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `1. **ANTI_GRAVITY_FORMULAS_CHEATSHEET.md** - Этот файл содержит формулы для решения проблемы с перекрытиями веток в интерактивной структуре VETKA Tree.

2. **Not explicitly mentioned in the context, but inferred from the 3D viewport context:** A file related to the `google_maps_f`
