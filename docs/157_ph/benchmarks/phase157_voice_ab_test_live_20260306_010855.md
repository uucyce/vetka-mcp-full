# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260306_010855.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.5 | 5479.56 | 9602.13 | 5642.6 | 10522.45 | 24821.62 | 0.4375 |
| E_ollama_jepa_tts | 4 | 0.75 | 528.63 | 3933.48 | 530.26 | 3614.82 | 24872.62 | 0.5625 |

## Response Samples

### D_ollama_tts

- Prompt: `context_1`
- Tokens: `56`
- Audio chunks: `3`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260306_010601_032003_D_ollama_tts_context_1_run1/merged.wav`
- Audio QC: score=48.75, pauses=25, longest_pause_ms=800, stretch=0
- Preview: `1.  Optimize `jepa_runtime.py` for faster trigger handling.
2.  Reduce unnecessary data collection in the `get_recent_stats(limit=...)` API call.
3.  Implement a more efficient memory management strategy for recent data.`

### E_ollama_jepa_tts

- Prompt: `context_1`
- Tokens: `82`
- Audio chunks: `5`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260306_010740_449323_E_ollama_jepa_tts_context_1_run1/merged.wav`
- Audio QC: score=25.0, pauses=36, longest_pause_ms=2940, stretch=0
- Preview: `1.  Optimize `pack_latency_ms` and `jepa_latency_ms` thresholds in `context_packer_probe.py` to reduce processing time.
2.  Implement a more granular memory tracking system to pinpoint latency bottlenecks within the `context_packer_probe.py` script.
3.  Reduce the number of `get_`
