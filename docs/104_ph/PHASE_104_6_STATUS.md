# Phase 104.6 - Jarvis Voice AI Integration

## Status: IMPLEMENTED

### What's Done

#### 1. LLM Integration (Ollama qwen2.5vl:3b)
- **File**: `src/voice/jarvis_llm.py`
- Uses Ollama with optimized voice parameters:
  - `num_predict: 150` - Short responses for voice
  - `temperature: 0.7` - Natural but focused
  - `num_ctx: 2048` - Smaller context for speed
- Streaming support for perceived lower latency
- Tested: ~3.5s for first response (cold), ~1-2s warm

#### 2. VETKA Memory Integration
- **STM Buffer**: Recent conversation context injected into prompts
- **JARVISPromptEnricher**: User preferences (language, formality) applied
- **HostessMemory**: File interaction context available
- Conversation history stored for continuity

#### 3. Pipeline Timing
All stages now measured:
- STT (Whisper): ~1-2s
- LLM (Ollama): ~2-4s
- TTS (Qwen3): ~5-6s
- **Total**: ~8-12s (target: <4s)

### Files Modified

```
src/voice/
├── jarvis_llm.py          # NEW - LLM integration module
├── tts_engine.py          # Added streaming TTS support
└── __init__.py            # Updated exports

src/api/handlers/
└── jarvis_handler.py      # Integrated LLM, added timing

scripts/
└── test_jarvis_llm.py     # NEW - LLM test script
```

### Testing

```bash
# Check Ollama
python scripts/test_jarvis_llm.py --check

# Test generation
python scripts/test_jarvis_llm.py --prompt "Hello!"

# Test streaming
python scripts/test_jarvis_llm.py --stream

# Test with memory context
python scripts/test_jarvis_llm.py --context

# Benchmark
python scripts/test_jarvis_llm.py --benchmark
```

### Current Latency Breakdown

| Stage | Current | Target |
|-------|---------|--------|
| VAD   | 1.5s    | 1.0s   |
| STT   | 1-2s    | 1s     |
| LLM   | 2-4s    | 1-2s   |
| TTS   | 5-6s    | 1-2s   |
| **Total** | **10-13s** | **<4s** |

### Remaining Optimizations (Grok Recommendations)

1. **TTS Speed** (70% of latency):
   - Try Piper TTS (0.5-1s latency, 8/10 quality)
   - Quantize Qwen3 to 4-bit
   - Use 16kHz instead of 24kHz sample rate

2. **LLM Speed**:
   - Try `phi3:mini` or `llama3.2:1b` for faster responses
   - Use streaming LLM → streaming TTS pipeline

3. **Parallel Processing**:
   - Start preparing TTS while LLM is still generating
   - Pre-load models in memory (partially done)

### Voice Commands Tested

- "Hello, how are you?" - Works
- "What is VETKA?" - Works with context
- Russian input - STT works, response in English (expected)

### Next Phase (104.7)

1. Try Piper TTS for faster synthesis
2. Implement streaming LLM → TTS pipeline
3. Add interruption support (stop TTS when user speaks)
4. Multilingual TTS (Russian support)
