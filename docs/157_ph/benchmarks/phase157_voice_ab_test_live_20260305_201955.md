# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260305_201955.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.25 | 3794.4 | 14877.59 | 16495.49 | 26938.0 | 58101.77 | 0.2625 |
| E_ollama_jepa_tts | 4 | 1.0 | 3434.93 | 10283.45 | 3434.93 | 10283.45 | 32911.26 | 0.8625 |

## Response Samples

### D_ollama_tts

- Prompt: `long_1`
- Tokens: `68`
- Audio chunks: `5`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_201612_764325_D_ollama_tts_long_1_run1/merged.wav`
- Audio QC: score=38.75, pauses=24, longest_pause_ms=1600, stretch=0
- Preview: `В предоставленном контексте нет информации о "interrupt + restart stream protocol" или его влиянии на voice handoff/tool-loop transparency. Упоминается только capability matrix и реконструкция гипотезы для аудио-пайплайна, но нет деталей протокола.`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `86`
- Audio chunks: `4`
- Merged WAV: `docs/157_ph/benchmarks/audio/20260305_201748_421118_E_ollama_jepa_tts_short_1_run1/merged.wav`
- Audio QC: score=27.5, pauses=36, longest_pause_ms=2500, stretch=0
- Preview: `На основе предоставленного контекста:

1. **File**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/PHASE_52_6_SIMPLE_SMOOTH_CAMERA.md`  
   **Пояснение**: Содержит спецификации для реализации плавного движения камеры в 3D-сцене.

2. **`
