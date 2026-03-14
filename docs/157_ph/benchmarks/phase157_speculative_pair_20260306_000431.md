# Phase 157.3.1 Speculative Pair Benchmark (gemma1b_to_qwen25_7b)

## Summary

- Runs: 4
- Success runs: 4
- Success rate: 1.0
- Draft TTFT p50: 344.76 ms
- Target TTFT p50: 236.82 ms
- Target audio-ready p50: 738.48 ms
- TTFT gain p50 (target-draft): -34.12 ms
- Acceptance mean: 0.0
- Correction mean: 1.0

## Rows

| prompt_id | run | success | draft_ttft | target_ttft | target_audio_ready | acceptance | correction | compared_tokens |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| `short_1` | 1 | `True` | 395.12 | 8084.99 | 8282.58 | 0.0 | 1.0 | 4 |
| `context_1` | 1 | `True` | 1307.72 | 234.59 | 915.88 | 0.0 | 1.0 | 8 |
| `long_1` | 1 | `True` | 294.4 | 239.06 | 561.07 | 0.0 | 1.0 | 18 |
| `interrupt_1` | 1 | `True` | 181.03 | 168.12 | 536.93 | 0.0 | 1.0 | 6 |