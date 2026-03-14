# Phase 157.3.1 Speculative Pair Benchmark (gemma1b_to_llama32_3b)

## Summary

- Runs: 4
- Success runs: 4
- Success rate: 1.0
- Draft TTFT p50: 872.07 ms
- Target TTFT p50: 746.59 ms
- Target audio-ready p50: 1005.2 ms
- TTFT gain p50 (target-draft): -150.03 ms
- Acceptance mean: 0.0278
- Correction mean: 0.9722

## Rows

| prompt_id | run | success | draft_ttft | target_ttft | target_audio_ready | acceptance | correction | compared_tokens |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| `short_1` | 1 | `True` | 5648.53 | 2387.18 | 2775.63 | 0.0 | 1.0 | 9 |
| `context_1` | 1 | `True` | 613.14 | 400.27 | 729.25 | 0.1111 | 0.8889 | 9 |
| `long_1` | 1 | `True` | 1130.99 | 1092.9 | 1281.15 | 0.0 | 1.0 | 15 |
| `interrupt_1` | 1 | `True` | 336.3 | 249.11 | 444.05 | 0.0 | 1.0 | 10 |