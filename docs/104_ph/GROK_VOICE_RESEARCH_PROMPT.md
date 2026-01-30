# GROK Research Prompt: VETKA Voice System Optimization

## Context

VETKA is a 3D knowledge management system with a voice interface called JARVIS. We've implemented Phase 104 voice integration but are facing latency and reliability issues.

## Current Architecture

```
Pipeline: Microphone → PCM 16kHz → Socket.IO → Server
         → mlx_whisper STT (~1-2s)
         → Ollama LLM qwen2.5vl:3b (~2-4s)
         → TTS (~1-6s depending on provider)
         → Base64 audio → Client playback
```

## Problem Statement

We have two TTS implementations:
1. **FastTTSClient (Edge-TTS)** - Microsoft Azure Neural voices, ~1s latency, MP3 output
   - ISSUE: `edge_tts` package imports successfully but `synthesize()` returns empty bytes
   - No errors, just empty response

2. **Qwen3TTSClient** - Local MLX server on port 5003, ~5-6s latency, WAV output
   - WORKING but too slow for conversational UX

## Technical Details

### Edge-TTS Implementation (Not Working)
```python
# src/voice/tts_engine.py:467-512
async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice=voice_name)
    audio_data = b''
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data  # Returns empty b''
```

### Environment
- macOS (Apple Silicon)
- Python 3.13 in .venv
- edge-tts 7.2.7 installed
- Internet connection available

## Questions for Research

1. **Edge-TTS Debugging**
   - Why might edge_tts.Communicate().stream() yield no audio chunks?
   - Are there known issues with edge-tts 7.2.7 on Python 3.13?
   - Does Edge-TTS require specific network configuration (proxy, DNS)?
   - Is Microsoft blocking certain regions/IPs?

2. **Alternative Fast TTS Solutions**
   - What are the fastest local TTS options for macOS Apple Silicon?
   - Piper TTS - performance on M1/M2/M3?
   - Coqui TTS - still maintained? MLX support?
   - OpenAI TTS API - latency characteristics?
   - ElevenLabs - streaming latency?

3. **Latency Optimization Strategies**
   - Streaming TTS while LLM is still generating (parallel pipeline)
   - Sentence-by-sentence TTS generation
   - Audio caching for common phrases
   - WebRTC for lower latency audio transport?

4. **Voice Model Selection UI**
   - Best practices for voice selector UI
   - How to preview voices without full synthesis?
   - Storing user voice preferences

5. **Production Considerations**
   - Rate limiting for cloud TTS APIs
   - Fallback chains (local → cloud → browser)
   - Cost optimization for cloud TTS

## Current Performance Targets

| Stage | Current | Target |
|-------|---------|--------|
| VAD | 1.5s | 1.0s |
| STT | 1-2s | 1s |
| LLM | 2-4s | 1-2s |
| TTS | 5-6s (Qwen3) | <1s |
| **Total** | **10-13s** | **<5s** |

## Constraints

- Must work offline (local fallback required)
- Must support English and Russian
- Must run on macOS Apple Silicon
- Prefer open-source solutions
- Budget for cloud APIs: minimal (dev/testing only)

## Deliverable Request

Please provide:
1. Diagnosis of Edge-TTS issue with potential fixes
2. Ranked list of alternative TTS solutions with pros/cons
3. Implementation recommendations for <5s total latency
4. Code snippets for recommended solutions
5. Architecture diagram for optimal voice pipeline

## Related Files in Codebase

```
src/voice/
├── tts_engine.py           # Qwen3TTSClient (line 216), FastTTSClient (line 437)
├── jarvis_llm.py           # LLM integration (Ollama)
├── streaming_pipeline.py   # Experimental streaming
├── tts_server_manager.py   # Qwen3 server management
└── __init__.py

src/api/handlers/
├── jarvis_handler.py       # Main voice socket handler, TTS_MODE (line 66)
├── voice_socket_handler.py # Legacy + Realtime voice events
└── voice_realtime_providers.py  # STT/TTS providers

client/src/hooks/
├── useJarvis.ts            # Main voice hook
└── useRealtimeVoice.ts     # Alternative realtime hook
```

## Phase Status

Phase 104.7 is being frozen for now. We need to:
1. Fix the immediate TTS issue (Edge-TTS or fallback to Qwen3)
2. Document everything for future continuation
3. Return to main development track

Voice development will resume in Phase 105+ with your research findings.
