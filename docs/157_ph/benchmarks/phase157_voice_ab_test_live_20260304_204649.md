# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_204649.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A_qwen_only | 8 | 0.25 | 163.93 | 3741.05 | 163.93 | 3741.05 | 7.91 | 0.2125 |
| B_api_tts | 8 | 0.0 | None | None | 5929.84 | 10764.49 | 7.41 | 0.0625 |
| C_api_jepa_tts | 8 | 0.0 | None | None | 2135.11 | 7536.61 | 8.5 | 0.0625 |
| D_ollama_tts | 8 | 0.0 | None | None | 203.91 | 6097.08 | 7.78 | 0.0625 |
| E_ollama_jepa_tts | 8 | 0.0 | None | None | 323.52 | 4185.82 | 15.15 | 0.0625 |
| F_mimo_short | 2 | 0.0 | None | None | None | None | 33.72 | 0.0 |

## Response Samples

### A_qwen_only

- Prompt: `interrupt_1`
- Tokens: `46`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_204220_960172_A_qwen_only_interrupt_1_run1/merged.wav`
- Audio QC: score=51.64, pauses=14, longest_pause_ms=1040, stretch=0
- Preview: `Сначала определи цель, потом составь план.Назову два шага:

1. Определить данные для передачи.
2. Упаковать данные в контекст сообщения.`

### B_api_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `[empty]`

### C_api_jepa_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `[empty]`

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `[empty]`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `0`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `[empty]`

### F_mimo_short

- Prompt: `short_live`
- Tokens: `0`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `[empty]`
