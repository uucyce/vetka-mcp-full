# Phase 157 Voice Bench Report

- Source JSON: `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_062919.json`
- Dry run: `False`

## Summary

| Mode | Runs | Success Rate | Text p50 (ms) | Audio p50 (ms) | E2E p50 (ms) | Quality |
|---|---:|---:|---:|---:|---:|---:|
| B_api_tts | 8 | 0.75 | 2216.28 | None | 4237.45 | 0.6062 |
| C_api_jepa_tts | 8 | 1.0 | 1613.84 | None | 3825.75 | 0.8063 |
| D_ollama_tts | 8 | 1.0 | 567.45 | None | 2893.75 | 0.7875 |
| E_ollama_jepa_tts | 8 | 1.0 | 609.33 | None | 3306.36 | 0.775 |
| F_mimo_short | 2 | 1.0 | 2322.18 | None | 3212.74 | 0.8 |

## Response Samples

### B_api_tts

- Prompt: `short_1`
- Tokens: `35`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `На основе контекста:

1. **PHASE_52_6_SIMPLE_SMOOTH_CAMERA.md** — Описывает упрощённую анимацию камеры для плавного подлёта к объекту без рывков.
2. **вкладка **Playground_GROK.txt** — Содержит backend-код для эндпоинта Playground в MyceliumCommandCenter.`

### C_api_jepa_tts

- Prompt: `short_1`
- Tokens: `39`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `Based on the provided context, here are two specific files and their purposes:

1. **PHASE_52_6_SIMPLE_SMOOTH_CAMERA.md** - This file documents the simplified camera movement system, replacing complex 3-phase animations with a single, smooth interpolation for user-friendly naviga`

### D_ollama_tts

- Prompt: `short_1`
- Tokens: `128`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `Из предоставленного контекста я не могу определить два конкретных файла, но я могу предложить два файла на основе общих тем и ключевых слов:

1. `PHASE_52_6_SIMPLE_SMOOTH_CAMERA.md` - Этот файл содержит описание проблемы с камерой и основной задачи пользователя.
	* Фраза: "Нам на`

### E_ollama_jepa_tts

- Prompt: `short_1`
- Tokens: `128`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `Базовый ответ:

Из предоставленного контекста я можу определить два конкретных файла:

1. `PHASE_52_6_SIMPLE_SMOOTH_CAMERA.md` - это файл с пинкой, в котором пользователь жаловался на проблемы с камерой.
2. `src/memory/engram.py` - этот файл является частью предложения для улучше`

### F_mimo_short

- Prompt: `short_live`
- Tokens: `17`
- Audio chunks: `0`
- Merged WAV: `[none]`
- Audio QC: score=None, pauses=None, longest_pause_ms=None, stretch=None
- Preview: `Привет! Да, я здесь, и в контексте есть файлы VETKA и MYCELIUM, но конкретно о том, "ты тут?" — информации нет.`
