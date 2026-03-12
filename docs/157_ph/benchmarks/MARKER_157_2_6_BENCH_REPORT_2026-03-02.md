# MARKER_157_2_6_BENCH_REPORT_2026-03-02

## Harness
- Script: `scripts/voice_mode_benchmark.py`
- Modes:
  - `A_qwen_only`
  - `B_api_tts`
  - `C_api_jepa_tts`
- Metrics:
  - `ttft_text_ms`
  - `ttfa_audio_ms`
  - `e2e_ms`
  - success/error per run

## Artifacts
- Dry run:
  - `docs/157_ph/benchmarks/phase157_voice_ab_test_dry_20260302_203806.json`
  - `docs/157_ph/benchmarks/phase157_voice_ab_test_dry_20260302_203806.csv`
- Live run:
  - `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260302_204331.json`
  - `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260302_204331.csv`
  - `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260302_211715.json`
  - `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260302_211715.csv`
  - `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260302_233417.json`
  - `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260302_233417.csv`
  - `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260302_234600.json`
  - `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260302_234600.csv`

## Live Summary (latest decision-grade run)
Command:
- `python scripts/voice_mode_benchmark.py --runs-per-prompt 3 --per-run-timeout-sec 25`

Results (`phase157_voice_ab_test_live_20260302_234600.*`):
- `A_qwen_only`: success_rate `1.0`, TTFT p50 `175.54ms`, TTFA p50 `3519.06ms`, E2E p50 `3519.14ms`
- `B_api_tts`: success_rate `0.1111`, TTFT p50 `2254.18ms`, TTFA p50 `null`, E2E p50 `18839.45ms`
- `C_api_jepa_tts`: success_rate `0.3333`, TTFT p50 `3271.83ms`, TTFA p50 `9955.96ms`, E2E p50 `18678.23ms`

## Critical Observations
1. Local loopback TTS stability improved after proxy-safe local routing fix (`trust_env=False` for localhost clients).
2. `A_qwen_only` now consistently produces audio chunks under current constraints.
3. API modes still fail SLO at `25s` (timeouts dominate), especially on longer prompts.
4. `C_api_jepa_tts` is better than `B_api_tts` on success rate in the same run, but still below decision threshold.
5. TTS server logs during benchmark show very long synthesis chunks on some API outputs (e.g. ~45-47s audio, ~28-30s synth), which exceeds per-run budget by itself.

## Interpretation
- The harness is working and captures failures correctly.
- Local MLX path is now benchmarkable and stable.
- API+TTS paths are still not decision-grade due to low success rate at target timeout.

## Next Calibration Steps
1. Stabilize providers before benchmark pass:
   - tighten OpenRouter output envelope for benchmark mode (short-form response budget)
   - use explicit provider-specific stream timeout guard per run
2. Re-run with `--per-run-timeout-sec 25` and `--runs-per-prompt 3` after provider tuning.
3. Require acceptance gate:
   - audio chunk presence in >=80% successful runs
   - mode success_rate >=0.9 for decision-quality comparison
