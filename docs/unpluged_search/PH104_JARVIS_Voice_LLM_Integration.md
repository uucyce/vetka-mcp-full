# Jarvis Voice Optimization - Prompt for Grok

## Текущее состояние (Phase 104.5)

### Что работает:
- **STT**: MLX Whisper (whisper-base-mlx) - ~1-2s на транскрипцию
- **TTS**: MLX Qwen3-TTS (0.6B-8bit) - ~5-6s на генерацию
- **VAD**: Energy-based auto-stop после 1.5s тишины
- **Continuous conversation**: После ответа автоматически слушает снова
- **Pipeline**: mic → PCM → backend → VAD → Whisper STT → echo → Qwen3 TTS → WAV → browser playback

### Текущие метрики:
- **Total latency**: ~8-10s (от конца речи до начала ответа)
  - VAD detection: 1.5s (настраиваемо)
  - STT: 1-2s
  - TTS: 5-6s ← **ГЛАВНЫЙ BOTTLENECK**
  - Network/encoding: ~0.5s
- **Качество голоса**: Отличное, эмоциональное
- **CPU температура**: 70-80°C во время TTS

### Проблема:
Пользователь говорит на русском → STT переводит в английский → echo на английском.
Нужен **реальный AI response** через LLM с контекстом из VETKA memory systems.

---

## Задачи оптимизации

### 1. TTS Speed (КРИТИЧНО - 70% latency)

**Текущее**: Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit, ~5-6s на фразу

**Вопросы к Гроку:**
1. Есть ли более быстрые MLX TTS модели? (Piper-MLX? Bark-MLX? Parler-TTS?)
2. Можно ли снизить quality для speed? (sample rate 24kHz → 16kHz? bitrate?)
3. Стриминг TTS - начать playback до окончания генерации?
4. Parallel processing - генерить по предложениям?

**Требования:**
- Latency TTS < 2s
- Качество: приемлемое для диалога (не робот)
- Локальный (MLX на M4)

### 2. LLM Integration с VETKA Memory (КРИТИЧНО - AI Brain)

**Текущее**: Простой echo "I heard you say: ..."

**VETKA Memory Systems (уже реализованы):**
```
src/memory/
├── arc_memory.py          # ARC - Adaptive Resonance Context
├── hope_memory.py         # HOPE - Hierarchical Optimized Persistent Embeddings
├── cam_memory.py          # CAM - Context Awareness Module
├── engram_manager.py      # ENGRAM - Episode/Semantic memory
├── stm_manager.py         # STM - Short Term Memory (working memory)
├── hostess_memory.py      # Hostess agent memory integration
└── memory_types.py        # Memory type definitions
```

**Вопросы к Гроку:**
1. Какую LLM использовать для voice responses? (Быстрая, локальная)
   - Qwen2.5:3b? Phi-3-mini? Mistral-7B? Gemma-2B?
   - Ollama vs MLX inference?
2. Как интегрировать VETKA memory в prompt?
   - STM для текущего диалога
   - CAM для контекста (какой файл открыт, что выделено)
   - ENGRAM для долгосрочной памяти пользователя
3. Streaming LLM response → streaming TTS?

**Требования:**
- LLM latency < 2s для короткого ответа
- Контекст из memory systems
- Русский + English support

### 3. Multilingual Support

**Текущее**: Whisper распознаёт русский, но выдаёт английский текст

**Вопросы:**
1. Как настроить Whisper для русского output? (language="ru"?)
2. Qwen3-TTS поддерживает русский?
3. Или нужна отдельная RU TTS модель?

### 4. Further Latency Optimizations

**Идеи:**
1. **Preload models** - держать в памяти (уже частично)
2. **Shorter VAD** - 1.5s → 1.0s? (риск false positives)
3. **Parallel STT+Context** - пока STT работает, готовить memory context
4. **Response caching** - частые фразы ("I understand", "One moment")
5. **Interruption** - если пользователь начал говорить, прервать TTS

---

## Код для контекста

### jarvis_handler.py (где вставить LLM)
```python
# Текущее (echo):
if not transcript or transcript.startswith("["):
    response_text = "I didn't catch that. Could you please repeat?"
else:
    response_text = f"I heard you say: {transcript}"

# TODO: Заменить на LLM call с memory context
# response_text = await jarvis_llm_respond(transcript, session, memory_context)
```

### Memory integration example
```python
from src.memory.stm_manager import STMManager
from src.memory.cam_memory import CAMMemory
from src.memory.engram_manager import EngramManager

async def get_jarvis_context(user_id: str, transcript: str) -> dict:
    """Build context from VETKA memory systems."""
    stm = STMManager()
    cam = CAMMemory()
    engram = EngramManager()

    return {
        "working_memory": stm.get_recent(user_id, limit=5),
        "current_context": cam.get_active_context(user_id),
        "user_profile": engram.get_user_profile(user_id),
        "relevant_memories": engram.search(transcript, user_id, limit=3)
    }
```

---

## Ожидаемый output от Грока

1. **Конкретная TTS модель** для замены Qwen3 (с бенчмарками)
2. **LLM рекомендация** для voice (модель + quantization + config)
3. **Code snippets** для интеграции LLM с memory
4. **Multilingual setup** (RU STT + RU/EN TTS)
5. **Streaming pipeline** если возможно

---

## Файлы проекта для reference

- `src/api/handlers/jarvis_handler.py` - main voice handler
- `scripts/voice_tts_server.py` - TTS microservice
- `src/voice/tts_engine.py` - TTS client
- `client/src/hooks/useJarvis.ts` - frontend hook
- `src/memory/*.py` - memory systems
- `src/agents/hostess_agent.py` - может пригодиться как reference

## Constraints

- **Локальное выполнение** - Mac M4, MLX preferred
- **Без внешних API** - всё offline (кроме fallback)
- **Память ~16GB** - нужно учитывать
- **Latency target**: < 4s total (от конца речи до начала ответа)
