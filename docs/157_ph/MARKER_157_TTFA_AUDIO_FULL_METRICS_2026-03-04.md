# MARKER 157: TTFA Audio Full Metrics (2026-03-04)

- Source benchmark JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_204649.json`
- Generated at: `2026-03-04T17:46:49.422009+00:00`
- Profile: all modes `A/B/C/D/E/F`, `runs-per-prompt=2`, timeout=25s, stream timeout=20s, max tokens=120

## Full Metrics (including non-success runs)

| Mode | Runs | Success Rate | TTFT p50 all (ms) | TTFA p50 all (ms) | Reaction Audio p50 all (ms) | Quality mean |
|---|---:|---:|---:|---:|---:|---:|
| A_qwen_only | 8 | 0.25 | 163.93 | 3741.05 | 3741.05 | 0.2125 |
| B_api_tts | 8 | 0.0 | 5929.84 | 10764.49 | 10764.49 | 0.0625 |
| C_api_jepa_tts | 8 | 0.0 | 2135.11 | 7536.61 | 7536.61 | 0.0625 |
| D_ollama_tts | 8 | 0.0 | 203.91 | 6097.08 | 6097.08 | 0.0625 |
| E_ollama_jepa_tts | 8 | 0.0 | 323.52 | 4185.82 | 4185.82 | 0.0625 |
| F_mimo_short | 2 | 0.0 | None | None | None | 0.0 |

## Token-bearing rows check

- `A_qwen_only`: token-bearing runs `2/8`
- `B_api_tts`: token-bearing runs `2/8`
- `C_api_jepa_tts`: token-bearing runs `2/8`
- `D_ollama_tts`: token-bearing runs `2/8`
- `E_ollama_jepa_tts`: token-bearing runs `2/8`
- `F_mimo_short`: token-bearing runs `0/2`

## Key Observations

- `ttfa_audio_ms` now recorded through fallback path and surfaced in summary as `ttfa_audio_ms_p50_all`.
- Fastest text reaction in this run: `A_qwen_only` (~163.93 ms p50 all), then `D_ollama_tts` (~203.91 ms).
- Best audio reaction among populated modes: `A_qwen_only` (~3741.05 ms), then `E_ollama_jepa_tts` (~4185.82 ms).
- API paths (`B/C`) remain slower on TTFT/TTFA in this run; `C` improved over `B` but still above local TTFA.
- `F_mimo_short` produced no token-bearing rows in this run (needs focused diagnosis).

## Artifacts to listen (sample merged WAV)

- `A_qwen_only`: `docs/157_ph/benchmarks/audio/20260304_204220_960172_A_qwen_only_interrupt_1_run1/merged.wav`
- `B_api_tts`: `docs/157_ph/benchmarks/audio/20260304_204259_911741_B_api_tts_interrupt_1_run1/merged.wav`
- `C_api_jepa_tts`: `docs/157_ph/benchmarks/audio/20260304_204352_999137_C_api_jepa_tts_interrupt_1_run1/merged.wav`
- `D_ollama_tts`: `docs/157_ph/benchmarks/audio/20260304_204450_220714_D_ollama_tts_interrupt_1_run1/merged.wav`
- `E_ollama_jepa_tts`: `docs/157_ph/benchmarks/audio/20260304_204552_962902_E_ollama_jepa_tts_interrupt_1_run1/merged.wav`