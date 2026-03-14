# MARKER 157 Model Leaderboard (2026-03-05)

- Source: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/157_ph/benchmarks/local_model_race_20260304_new_models.jsonl`
- Benchmark profile: local voice D/E modes, runs-per-prompt=1, per-run-timeout=20s, stream-timeout=15s

## Primary Leaderboard (E: `ollama + JEPA + TTS`)

| Rank (TTFA) | Model | TTFT p50 all (ms) | TTFA p50 all (ms) | Quality mean | Success rate |
|---:|---|---:|---:|---:|---:|
| 1 | `qwen2.5:7b` | 170.34 | 4474.42 | 0.2125 | 0.25 |
| 2 | `phi4-mini:latest` | 162.54 | 5168.68 | 0.0625 | 0.0 |
| 3 | `gemma3:12b` | 307.52 | 6318.24 | 0.2125 | 0.25 |
| 4 | `gemma3:4b` | 219.42 | 6882.46 | 0.0625 | 0.0 |
| 5 | `gemma3:1b` | 158.0 | 7231.93 | 0.0375 | 0.0 |
| 6 | `mistral-nemo:latest` | 197.3 | 15569.59 | 0.0625 | 0.0 |
| - | `qwen3.5:latest` | n/a | n/a | 0.0125 | 0.0 |

## Reference (D: `ollama + TTS`, no JEPA)

| Model | TTFT p50 all (ms) | TTFA p50 all (ms) | Quality mean | Success rate |
|---|---:|---:|---:|---:|
| `gemma3:4b` | 420.59 | 5204.42 | 0.0625 | 0.0 |
| `gemma3:12b` | 607.37 | 7528.27 | 0.0625 | 0.0 |
| `phi4-mini:latest` | 260.08 | 10145.46 | 0.0625 | 0.0 |
| `gemma3:1b` | 358.77 | 14428.45 | 0.0125 | 0.0 |
| `mistral-nemo:latest` | 485.9 | 17217.53 | 0.0625 | 0.0 |
| `qwen2.5:7b` | n/a | n/a | 0.0 | 0.0 |
| `qwen3.5:latest` | n/a | n/a | 0.0125 | 0.0 |

## Decision (Current)

- **Best balance speed + quality**: `qwen2.5:7b + E_ollama_jepa_tts`
- **Fast but weaker quality**: `phi4-mini:latest + E_ollama_jepa_tts`
- `qwen3.5:latest` currently not suitable as realtime default (see warm-run).

## Notes

- `ttfa_all`/`ttft_all` are full metrics across all runs (not only success-gated).
- Quality is benchmark heuristic (`quality_proxy_mean`) for relative comparison in this phase.