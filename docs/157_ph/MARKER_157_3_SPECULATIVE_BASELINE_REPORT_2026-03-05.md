# MARKER_157_3_SPECULATIVE_BASELINE_REPORT_2026-03-05

Phase: 157.3.1  
Date: 2026-03-05  
Harness: `scripts/voice_speculative_benchmark.py`

## Run configuration

- Pair: `gemma3:1b -> llama3.2:3b`
- Sources: `ollama / ollama`
- Prompt set: `short_1`, `context_1`, `long_1`, `interrupt_1`
- Runs per prompt: `1`
- Timeout: `per-run 45s`, `stream 35s`
- Max output tokens: `96`
- Grounded context: `off` (isolated baseline)

Artifacts:
- JSON: `docs/157_ph/benchmarks/phase157_speculative_pair_20260305_222343.json`
- CSV: `docs/157_ph/benchmarks/phase157_speculative_pair_20260305_222343.csv`
- MD: `docs/157_ph/benchmarks/phase157_speculative_pair_20260305_222343.md`

## Summary (observed)

- `runs=4`, `success_runs=4`, `success_rate=1.0`
- `draft_ttft_p50_ms=231.23`
- `target_ttft_p50_ms=197.56`
- `target_audio_ready_p50_ms=404.44`
- `ttft_gain_p50_ms=-49.12` (negative: target first token came earlier than draft median)
- `acceptance_rate_mean=0.0833`
- `correction_rate_mean=0.9167`
- `compared_tokens_mean=11.0`

## Interpretation

1. Harness works end-to-end and exports required metrics.
2. This specific pair is not a good speculative pair in current policy:
- very low prefix acceptance,
- high correction pressure,
- no measured draft TTFT advantage over target.
3. Despite low acceptance, target remains fast enough in this isolated run (`~198ms TTFT p50`), which indicates warm local performance can be excellent when runtime noise is minimized.

## Technical notes

- For Ollama stream, `think=false` is now respected in stream path (`src/elisya/provider_registry.py`), so reasoning overhead is controlled.
- Baseline intentionally ran without grounded context to isolate model-pair behavior before full-stack latency pressure.

## Decision for Phase 157.3.1

Status: **COMPLETE** (harness + first baseline + report)

Go forward to pair-race batch (Phase 157.3.1 extension / 157.3.5 prep):
- `qwen2.5:3b -> qwen2.5:7b`
- `gemma3:1b -> deepseek-r1:8b`
- `phi4-mini:latest -> llama3.2:3b`

Acceptance threshold for promotion into runtime-integration candidate:
- `acceptance_rate_mean >= 0.35`
- `ttft_gain_p50_ms >= 120`
- `success_rate >= 0.95`

Pairs failing these thresholds remain non-promoted and should rely on Plan B fillers + direct target streaming.
