# Phase 157.3.1 Speculative Pair Benchmark (gemma1b_to_gemma4b)

## Summary

- Runs: 4
- Success runs: 4
- Success rate: 1.0
- Draft TTFT p50: 230.04 ms
- Target TTFT p50: 313.53 ms
- Target audio-ready p50: 487.05 ms
- TTFT gain p50 (target-draft): 110.59 ms
- Acceptance mean: 0.0778
- Correction mean: 0.9222

## Rows

| prompt_id | run | success | draft_ttft | target_ttft | target_audio_ready | acceptance | correction | compared_tokens |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| `short_1` | 1 | `True` | 268.78 | 2929.14 | 3158.7 | 0.0 | 1.0 | 10 |
| `context_1` | 1 | `True` | 174.44 | 367.25 | 482.5 | 0.1111 | 0.8889 | 9 |
| `long_1` | 1 | `True` | 231.46 | 259.82 | 476.22 | 0.0 | 1.0 | 20 |
| `interrupt_1` | 1 | `True` | 228.61 | 249.16 | 491.6 | 0.2 | 0.8 | 10 |