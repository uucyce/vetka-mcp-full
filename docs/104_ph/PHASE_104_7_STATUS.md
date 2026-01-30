# Phase 104.7 - Jarvis Voice Optimization

## Status: IMPLEMENTED

### Key Improvements

#### 1. Fast TTS (Edge-TTS) - ~1s vs ~6s
- **New**: `FastTTSClient` using Microsoft Edge-TTS
- **Latency**: ~1 second (vs 5-6s for Qwen3-TTS)
- **Quality**: Good (Azure Neural voices)
- **Tradeoff**: Requires internet, less customizable
- **Mode switch**: `TTS_MODE = "fast"` in jarvis_handler.py

#### 2. STT Hallucination Detection
- Detects repeated phrases (Whisper bug with silence)
- Known patterns: "thank you for watching", "I'm going to go to..."
- Prevents garbage responses

#### 3. Qdrant Spam Fix
- Removed Engram calls from `get_jarvis_context()`
- Only uses STM buffer (no 400 Bad Request spam)

#### 4. Streaming Pipeline (Experimental)
- `streaming_pipeline.py` for LLM → TTS streaming
- Generates audio per-sentence as LLM produces text
- Best for long responses (multiple sentences)

### Current Latency

| Stage | Before | After |
|-------|--------|-------|
| VAD   | 1.5s   | 1.5s  |
| STT   | 1-2s   | 1-2s  |
| LLM   | 2-4s   | 2-4s  |
| TTS   | **5-6s** | **~1s** |
| **Total** | **10-13s** | **~5-8s** |

### Files Changed

```
src/voice/
├── tts_engine.py           # Added FastTTSClient
├── jarvis_llm.py           # Simplified context (no Qdrant)
├── streaming_pipeline.py   # NEW - LLM→TTS streaming
└── __init__.py             # Updated exports

src/api/handlers/
└── jarvis_handler.py       # Fast TTS mode, hallucination detection

client/src/hooks/
└── useJarvis.ts            # MP3 format support
```

### TTS Modes

```python
# In jarvis_handler.py
TTS_MODE = "fast"    # Edge-TTS (~1s) - default
TTS_MODE = "quality" # Qwen3-TTS (~6s) - better voice
```

### Voice Options (FastTTS)

```python
VOICES = {
    "en-male": "en-US-GuyNeural",
    "en-female": "en-US-JennyNeural",
    "ru-male": "ru-RU-DmitryNeural",
    "ru-female": "ru-RU-SvetlanaNeural",
}
```

### Testing

```bash
# Test Fast TTS
python -c "
import asyncio
from src.voice.tts_engine import FastTTSClient

async def test():
    client = FastTTSClient()
    audio = await client.synthesize('Hello! This is a test.')
    print(f'Generated {len(audio)} bytes')

asyncio.run(test())
"

# Test streaming pipeline
python scripts/test_streaming_pipeline.py --prompt "Tell me about VETKA"

# Test LLM
python scripts/test_jarvis_llm.py --prompt "Hello!"
```

### Next Steps (Phase 104.8)

1. **Parallel LLM + TTS**: Start TTS generation while LLM still producing
2. **Interruption**: Stop TTS when user starts speaking again
3. **Voice cloning**: Use Qwen3-TTS for custom voice, Edge for speed
4. **Caching**: Cache common phrases ("I understand", "One moment")

### Known Issues

1. **First response slow**: Ollama model load on first request (~3s)
2. **MP3 playback**: Some browsers may need sample rate adjustment
3. **Russian TTS**: Edge-TTS supports Russian, but STT outputs English
