# TASK A: VETKA Voice Module

**Phase:** 102 → 103
**Assignee:** Vetka Spawn (Group Chat Agents)
**Supervisor:** Claude Code (integration only)
**Status:** Ready to Start

---

## Objective

Создать **изолированный** голосовой модуль `src/voice/` для VETKA AI.

## Requirements

### Input
- Аудио от пользователя (микрофон)
- Текст от LLM для озвучки

### Output
- Транскрипция речи → текст для LLM
- Синтезированный голос ← ответ LLM

### Target Latency
- STT: < 500ms
- TTS: < 300ms
- **Total round-trip: < 1.5s**

---

## Recommended Stack (Grok's Research)

| Component | Tool | Why |
|-----------|------|-----|
| STT | **Whisper** (уже в MCP) | Точность, Metal оптимизация |
| TTS | **Qwen3-TTS** | Быстрее на M4, рекомендация Grok |
| Fallback TTS | ElevenLabs API | Voice cloning если нужно |

---

## Module Structure

```
src/voice/
├── __init__.py
├── stt_engine.py      # Whisper integration
├── tts_engine.py      # Qwen3-TTS / fallback
├── voice_pipeline.py  # Main orchestrator
├── audio_utils.py     # Format conversion, streaming
└── config.py          # Model paths, settings
```

---

## API Contract

### voice_pipeline.py

```python
class VoicePipeline:
    async def listen(self) -> str:
        """Record and transcribe user speech"""
        pass

    async def speak(self, text: str) -> bytes:
        """Synthesize speech from text"""
        pass

    async def conversation_turn(self, audio_input: bytes) -> bytes:
        """Full turn: listen → LLM → speak"""
        pass
```

### Integration Points (DO NOT MODIFY - Claude Code will integrate)

| Existing File | What Spawn Creates | Claude Code Integrates |
|---------------|-------------------|----------------------|
| `src/mcp/vetka_mcp_bridge.py` | - | Voice MCP tools |
| `src/api/chat_routes.py` | - | `/api/voice/speak` endpoint |
| `client/src/` | - | Voice button UI |

---

## Existing Dependencies

### MCP Whisper (Already Available)
```
~/.config/mcp/servers/vetka_claude_code/venv/
```
- Location confirmed
- Can be imported from voice module

### Audio Format
- Input: WebM/Opus from browser, WAV from desktop
- Output: MP3 or WAV for playback

---

## Acceptance Criteria

- [ ] `VoicePipeline` class works standalone
- [ ] Unit tests pass: `pytest src/voice/tests/`
- [ ] Latency benchmarks documented
- [ ] No modifications to existing VETKA files
- [ ] Clear docstrings and type hints

---

## Spawn Instructions

```
@Dev создай src/voice/ модуль по спецификации TASK_A_VOICE_MODULE.md
@Researcher найди оптимальные параметры Qwen3-TTS для M4 Mac
@QA напиши тесты для voice_pipeline.py
```

---

## Timeline

| Day | Milestone |
|-----|-----------|
| 1 | stt_engine.py + tts_engine.py stubs |
| 2 | voice_pipeline.py integration |
| 3 | Tests + benchmarks |

---

*Task created: 2025-01-30*
*For: Vetka Spawn Team Test*
