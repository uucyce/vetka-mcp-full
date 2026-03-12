# Phase 157.3.1 Speculative Pair Benchmark (gemma1b_to_deepseekr1_8b)

## Summary

- Runs: 4
- Success runs: 4
- Success rate: 1.0
- Draft TTFT p50: 291.18 ms
- Target TTFT p50: 254.15 ms
- Target audio-ready p50: 751.81 ms
- TTFT gain p50 (target-draft): -51.36 ms
- Acceptance mean: 0.0
- Correction mean: 1.0

## Rows

| prompt_id | run | success | draft_ttft | target_ttft | target_audio_ready | acceptance | correction | compared_tokens |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| `short_1` | 1 | `True` | 4296.37 | 3624.91 | 4020.51 | 0.0 | 1.0 | 7 |
| `context_1` | 1 | `True` | 291.56 | 283.59 | 875.57 | 0.0 | 1.0 | 9 |
| `long_1` | 1 | `True` | 290.79 | 224.72 | 628.05 | 0.0 | 1.0 | 15 |
| `interrupt_1` | 1 | `True` | 191.49 | 154.83 | 481.02 | 0.0 | 1.0 | 6 |