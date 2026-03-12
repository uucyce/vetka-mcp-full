# Phase 157.3.1 Speculative Pair Benchmark (gemma1b_to_phi4mini)

## Summary

- Runs: 4
- Success runs: 4
- Success rate: 1.0
- Draft TTFT p50: 1431.36 ms
- Target TTFT p50: 2679.84 ms
- Target audio-ready p50: 2886.09 ms
- TTFT gain p50 (target-draft): 1248.48 ms
- Acceptance mean: 0.0
- Correction mean: 1.0

## Rows

| prompt_id | run | success | draft_ttft | target_ttft | target_audio_ready | acceptance | correction | compared_tokens |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| `short_1` | 1 | `True` | 300.21 | 5896.26 | 6100.65 | 0.0 | 1.0 | 10 |
| `context_1` | 1 | `True` | 9196.03 | 280.72 | 503.96 | 0.0 | 1.0 | 9 |
| `long_1` | 1 | `True` | 485.47 | 4911.77 | 5142.9 | 0.0 | 1.0 | 21 |
| `interrupt_1` | 1 | `True` | 2377.25 | 447.9 | 629.29 | 0.0 | 1.0 | 17 |