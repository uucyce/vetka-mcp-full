# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_055743.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| F_mimo_short | 2 | 0.0 | None | None | None | 0.45 |

## Response Samples

### F_mimo_short

- Prompt: `short_live`
- Tokens: `8`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `Привет! Да, я тут — в контексте проекта VETKA с ин`
- Error: `TypeError: ProgressiveTtsService.stream_sentences() got an unexpected keyword argument 'session_key'`
