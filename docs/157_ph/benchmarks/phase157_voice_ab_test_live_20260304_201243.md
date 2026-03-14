# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_201243.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.5 | 12947.28 | None | 14854.48 | 0.4125 |
| F_mimo_short | 1 | 1.0 | 3169.64 | None | 3825.85 | 0.8 |

## Response Samples

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `128`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `Базовый ответ не получается, но я могу предоставить обобщенное описание.

В контексте задачи с созданием файла данных `data/playground_proposals.json` и предоставленного текста на основе переданного контекста, я не могу определить конкретные файлы или фразы, которые необходимы дл`

### F_mimo_short

- Prompt: `short_live`
- Tokens: `14`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `Да, я здесь — в контексте проекта VETKA, где интегрирован Hostess Agent для быстрых ответов.`
