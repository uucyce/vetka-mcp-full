# Phase 157.3.1 Speculative Pair Benchmark (gemma1b_to_llama32_3b)

## Summary

- Runs: 4
- Success runs: 4
- Success rate: 1.0
- Draft TTFT p50: 231.23 ms
- Target TTFT p50: 197.56 ms
- Target audio-ready p50: 404.44 ms
- TTFT gain p50 (target-draft): -49.12 ms
- Acceptance mean: 0.0833
- Correction mean: 0.9167

## Rows

| prompt_id | run | success | draft_ttft | target_ttft | target_audio_ready | acceptance | correction | compared_tokens |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| `short_1` | 1 | `True` | 3593.86 | 2366.8 | 2524.37 | 0.2222 | 0.7778 | 9 |
| `context_1` | 1 | `True` | 245.78 | 212.23 | 437.38 | 0.1111 | 0.8889 | 9 |
| `long_1` | 1 | `True` | 216.68 | 182.9 | 371.49 | 0.0 | 1.0 | 13 |
| `interrupt_1` | 1 | `True` | 177.58 | 113.13 | 276.93 | 0.0 | 1.0 | 13 |