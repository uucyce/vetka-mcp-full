# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_042949.json`
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
- Tokens: `90`
- Audio chunks: `2`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_042526_636946_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=57.41, pauses=9, longest_pause_ms=1260, stretch=0
- Preview: `По предоставленному контексту я могу определить два конкретных файла:

1. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/74_ph/CHAT_HISTORY_AUDIT.md`
2. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/81_ph_mcp_fixes/81_PHASE_COMPLETE.md`

По этим ф`
- Error: `TimeoutError: per-run timeout 25.0s`
