# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260305_203423.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.25 | 4699.69 | 20046.33 | 20455.27 | 36662.88 | 60219.82 | 0.2375 |
| E_ollama_jepa_tts | 4 | 1.0 | 4506.41 | 15391.31 | 4506.41 | 15391.31 | 41713.92 | 0.8125 |

## Response Samples

### D_ollama_tts

- Prompt: `long_1`
- Tokens: `36`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_202944_089772_D_ollama_tts_long_1_run1/merged.wav`
- Audio QC: score=46.25, pauses=17, longest_pause_ms=1000, stretch=0
- Preview: `В предоставленном контексте **нет информации** о пошаговом протоколе `interrupt + restart stream`, а также о влиянии этих операций на `voice handoff` или прозра`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `64`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_203130_555571_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=25.0, pauses=36, longest_pause_ms=6720, stretch=0
- Preview: `1. **HAIKU_TEST_4_WATCHER_MARKERS.md** — подтверждает корректное размещение маркеров `MARKER_COHERENCE_BYPASS` в файле `watcher_routes.py`.  
2. **81_PHASE_COMPLETE.md** — завершающий файл проекта (факты о`
