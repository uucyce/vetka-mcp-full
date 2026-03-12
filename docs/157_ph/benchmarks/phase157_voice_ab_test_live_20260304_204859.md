# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_204859.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A_qwen_only | 4 | 0.25 | 170.39 | 6174.32 | 170.39 | 6174.32 | 26.32 | 0.2125 |

## Response Samples

### A_qwen_only

- Prompt: `interrupt_1`
- Tokens: `44`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260304_204830_297292_A_qwen_only_interrupt_1_run1/merged.wav`
- Audio QC: score=49.38, pauses=18, longest_pause_ms=1460, stretch=0
- Preview: `Сначала определи цель, потом составь план.Назову два шага:

1. Определить структуру данных.
2. Сerializировать данные в байты.`
