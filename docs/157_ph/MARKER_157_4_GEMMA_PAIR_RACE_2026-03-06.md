# MARKER_157_4_GEMMA_PAIR_RACE_2026-03-06

Goal: choose the best pair for `gemma3:1b` before locking Phase 157.4 handoff plan.

## Speculative pair race (fresh)

Draft model: `gemma3:1b`  
Runs: 4 prompts x 1 run (short/context/long/interrupt)  
Source: `ollama`

| Pair | target_ttft_p50_ms | target_audio_ready_p50_ms | ttft_gain_p50_ms (target-draft) | acceptance_rate_mean | success_rate | JSON |
|---|---:|---:|---:|---:|---:|---|
| gemma1b -> qwen2.5:7b | 236.82 | 738.48 | -34.12 | 0.0 | 1.0 | `phase157_speculative_pair_20260306_000431.json` |
| gemma1b -> deepseek-r1:8b | 254.15 | 751.81 | -51.36 | 0.0 | 1.0 | `phase157_speculative_pair_20260306_000355.json` |
| gemma1b -> gemma3:4b | 313.53 | 487.05 | 110.59 | 0.0778 | 1.0 | `phase157_speculative_pair_20260306_000437.json` |
| gemma1b -> llama3.2:3b | 746.59 | 1005.2 | -150.03 | 0.0278 | 1.0 | `phase157_speculative_pair_20260306_000341.json` |
| gemma1b -> phi4-mini:latest | 2679.84 | 2886.09 | 1248.48 | 0.0 | 1.0 | `phase157_speculative_pair_20260306_000419.json` |

## Practical interpretation for our roadmap (handoff-first)

Important: speculative acceptance is near-zero for almost all pairs, so strict speculative decoding is not the winning production path now.

For handoff (`fast chunk -> smart continuation`) we should prioritize:
1. stage-2 quality/coherence,
2. stable response time,
3. low dead-air risk.

Using previous voice quality measurements (`E_ollama_jepa_tts`) as quality anchor:
- `deepseek-r1:8b` quality ≈ `0.8625` (highest among tested)
- `llama3.2:3b` quality ≈ `0.7625`
- `gemma3:4b` quality ≈ `0.7375`
- `phi4-mini:latest` quality ≈ `0.775`

## Decision (pair lock for plan)

Primary pair (quality-first):
- `Stage 1 fast`: `gemma3:1b`
- `Stage 2 smart`: `deepseek-r1:8b`

Secondary fallback (latency/balance):
- `Stage 1 fast`: `gemma3:1b`
- `Stage 2 smart`: `llama3.2:3b`

Tertiary low-latency local fallback:
- `Stage 1 fast`: `gemma3:1b`
- `Stage 2 smart`: `gemma3:4b`

## Why this lock is consistent

- `gemma3:1b` remains the best starter for immediate reaction.
- `deepseek-r1:8b` gives the best semantic quality for continuation.
- strict speculative acceptance is weak, so we proceed with handoff-first architecture plus Plan B fillers.

