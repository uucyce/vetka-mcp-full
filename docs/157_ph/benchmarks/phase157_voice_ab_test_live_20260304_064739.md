# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_064739.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| D_ollama_tts | 4 | 0.5 | 12262.81 | None | 13585.15 | 0.3625 |
| E_ollama_jepa_tts | 4 | 1.0 | 1160.68 | None | 2547.49 | 0.7375 |

## Response Samples

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `79`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `2 конкретных файлов не указано в данном контексте. 

Необходимо сформулировать:

- "108_knowledg_directed_chat_artefacts.txt": для создания стейт диаграммы и пользовательских сценариев.
- Необходимо добавить еще один конкретный файл, но его нет в данном контексте.`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `102`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `2 конкретных файлов для этого контекста не указано. 

По 1 фразе:
- "108_knowledg_directed_chat_artefacts.txt": используется для описания работы по алгоритму и требуемых элементов в чат-артефактах.
- "108_ph/108_knowledg_directed_chat_artefacts.txt": содержит полный текст, но не `
