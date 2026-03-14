# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260305_195616.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.25 | 4296.74 | 16779.78 | 15043.6 | 30952.45 | 51191.29 | 0.2625 |

## Response Samples

### D_ollama_tts

- Prompt: `long_1`
- Tokens: `52`
- Audio chunks: `5`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_195436_625742_D_ollama_tts_long_1_run1/merged.wav`
- Audio QC: score=49.02, pauses=40, longest_pause_ms=860, stretch=0
- Preview: `В предоставленном контексте **нет информации** о пошаговом протоколе `interrupt + restart stream`, а также об их влиянии на `voice handoff` или прозрачность `tool-loop`.

Контекст содержит лишь общие упоминания о раздел`
