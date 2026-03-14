# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260305_202718.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.25 | 2057.55 | 8950.52 | 15415.85 | 21794.39 | 53947.58 | 0.2625 |
| E_ollama_jepa_tts | 4 | 1.0 | 1372.66 | 5944.69 | 1372.66 | 5944.69 | 35374.58 | 0.7625 |

## Response Samples

### D_ollama_tts

- Prompt: `long_1`
- Tokens: `93`
- Audio chunks: `8`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_202318_247287_D_ollama_tts_long_1_run1/merged.wav`
- Audio QC: score=43.75, pauses=45, longest_pause_ms=1200, stretch=0
- Preview: `Поскольку в контексте нет подробной информации о протоколе "interrupt + restart stream", я не могу предоставить точную explanations. 

Однако, на основе предоставленного контекста, можно сделать некоторые выводы. В частности, в разделе "5.5. Voice Handoff" можно найти информацию `

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `63`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_202457_023523_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=47.54, pauses=30, longest_pause_ms=1080, stretch=0
- Preview: `Базовый файл: `src/layout/semantic_sugiyama.py`

Фраза: «DAG-based knowledge level layout»

Этот файл необходим для анализа структуры проекта и поиска скрытых файлов, поскольку он включает в себяKnowledge mode positioning + clustering.`
