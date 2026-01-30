# VETKA Voice System - Full Audit Report
## Phase 104.7 - Voice Interface Audit & Freeze Documentation

**Generated:** 2026-01-31
**Status:** AUDIT COMPLETE - Ready for freeze

---

## 📊 EXECUTIVE SUMMARY

| Metric | Value |
|--------|-------|
| Total Socket.IO Events | 32 (Jarvis: 8, Legacy Voice: 6, Realtime: 13, Common: 5) |
| STT Providers | 4 (Whisper local, Deepgram, Gemini, OpenAI) |
| LLM Providers | 2 (Ollama local, OpenRouter fallback) |
| TTS Providers | 4 (Edge-TTS, Qwen3-TTS, ElevenLabs, Piper) |
| Active Implementations | 2 TTS modes working |
| Known Issues | 15 client-side, 3 backend |
| Lines of Code | ~3000 (voice-specific) |

### Current Pipeline Status
```
[WORKING] Microphone → PCM (16kHz) → Socket.IO
[WORKING] VAD silence detection (1.5s threshold)
[WORKING] STT via mlx_whisper (whisper-base-mlx)
[WORKING] Hallucination detection (7 patterns)
[WORKING] LLM via Ollama (qwen2.5vl:3b)
[WORKING] STM context (5 recent messages)
[DISABLED] Engram user memory (Qdrant 400 error)
[ISSUE] TTS FastTTS - edge-tts installed but not responding
[FALLBACK] TTS Qwen3 - working but slow (~5-6s)
```

---

## 🎯 FILE MARKERS & LINE REFERENCES

### Backend Files

#### src/api/handlers/jarvis_handler.py
| Line | Marker/Function | Status | Description |
|------|-----------------|--------|-------------|
| 66 | `TTS_MODE = "fast"` | CONFIG | Switch between "fast" (Edge-TTS) and "quality" (Qwen3) |
| 78-124 | `_is_hallucination()` | WORKING | STT hallucination detection |
| 135-152 | VAD_* constants | CONFIG | Voice Activity Detection settings |
| 210-244 | `jarvis_listen_start` | WORKING | Socket handler - start listening |
| 247-321 | `jarvis_audio_chunk` | WORKING | Socket handler - receive audio |
| 324-540 | `jarvis_listen_stop` | WORKING | Socket handler - process pipeline |
| 375-384 | STT transcription | WORKING | mlx_whisper.transcribe() call |
| 408-432 | LLM generation | WORKING | jarvis_llm.generate() call |
| 452-503 | TTS synthesis | ISSUE | FastTTS not responding, Qwen3 fallback |

#### src/voice/jarvis_llm.py
| Line | Marker/Function | Status | Description |
|------|-----------------|--------|-------------|
| 30 | `DEFAULT_MODEL` | CONFIG | "qwen2.5vl:3b" - Ollama model |
| 33-39 | `VOICE_OPTIONS` | CONFIG | Token limits, temperature |
| 53-298 | `JarvisLLM` class | WORKING | Main LLM integration |
| 100-129 | `_build_system_prompt()` | WORKING | Dynamic system prompt |
| 131-144 | `_enrich_prompt()` | DISABLED | JARVISPromptEnricher (not called) |
| 303-337 | `get_jarvis_context()` | PARTIAL | STM only, Engram disabled |

#### src/voice/tts_engine.py
| Line | Marker/Function | Status | Description |
|------|-----------------|--------|-------------|
| 10-207 | `QwenTTS` class | DEAD | Placeholder, not functional |
| 216-400 | `Qwen3TTSClient` | WORKING | HTTP client for TTS server |
| 303-340 | `_fallback_edge_tts()` | ISSUE | Edge-TTS fallback in Qwen3 |
| 437-577 | `FastTTSClient` | ISSUE | Edge-TTS direct client |
| 467-512 | `synthesize()` | ISSUE | edge_tts import works but no response |
| 545-561 | `detect_language()` | WORKING | Cyrillic detection |

#### src/voice/streaming_pipeline.py
| Line | Marker/Function | Status | Description |
|------|-----------------|--------|-------------|
| 1-225 | Full file | EXPERIMENTAL | LLM→TTS streaming (not in main pipeline) |

#### src/api/handlers/voice_socket_handler.py
| Line | Marker/Function | Status | Description |
|------|-----------------|--------|-------------|
| 80-136 | Legacy voice events | WORKING | voice_start, voice_audio, voice_stop |
| 237-311 | Realtime events | WORKING | voice_stream_start, voice_pcm, etc. |

#### src/api/handlers/voice_realtime_providers.py
| Line | Marker/Function | Status | Description |
|------|-----------------|--------|-------------|
| 58-95 | `stt_whisper_local()` | WORKING | Local Whisper STT |
| 95-212 | `stt_deepgram/gemini/openai()` | AVAILABLE | Cloud STT providers |
| 318-379 | `llm_stream_grok()` | AVAILABLE | X.AI Grok streaming |
| 509-603 | `tts_elevenlabs/piper()` | AVAILABLE | Alternative TTS |

### Client Files

#### client/src/hooks/useJarvis.ts
| Line | Marker/Function | Status | Description |
|------|-----------------|--------|-------------|
| 32-33 | SAMPLE_RATE, CHUNK_SIZE | CONFIG | 16000 Hz, 4096 samples |
| 56-60 | Socket connection | WORKING | localhost:5001 |
| 148-155 | `float32ToInt16()` | WORKING | Audio conversion |
| 167-203 | Audio recording | WORKING | ScriptProcessorNode |
| 211 | `jarvis_listen_start` emit | ISSUE | Hardcoded user_id |
| 321-368 | `playAudio()` | WORKING | WAV/MP3 playback |

#### client/src/hooks/useRealtimeVoice.ts
| Line | Marker/Function | Status | Description |
|------|-----------------|--------|-------------|
| 275-301 | AudioStreamManager | WORKING | PCM streaming with VAD |
| 250 | Browser TTS lang | ISSUE | Hardcoded Russian |

#### client/src/components/jarvis/JarvisWave.tsx
| Line | Marker/Function | Status | Description |
|------|-----------------|--------|-------------|
| 1-160 | Full component | WORKING | Waveform visualization |

---

## 🔴 KNOWN ISSUES

### Critical (Blocking)

1. **Edge-TTS Not Responding** (jarvis_handler.py:459-473)
   - edge_tts package installed in .venv
   - Import succeeds but `synthesize()` returns empty bytes
   - No audio sent to client, connection drops
   - **Workaround:** Switch TTS_MODE to "quality" (line 66)

### High Priority

2. **Engram Qdrant 400 Error** (jarvis_llm.py:333-335)
   - Vector format mismatch with Qdrant REST API
   - Integer ID fix applied but still disabled as precaution
   - User memory/preferences not available in voice

3. **Hardcoded user_id** (useJarvis.ts:211, 234)
   - Always sends "default_user"
   - Multi-user scenarios broken

4. **STM-only context** (jarvis_llm.py:303-337)
   - Only 5 recent messages available
   - No long-term memory, no user preferences

### Medium Priority

5. **ScriptProcessorNode deprecated** (useJarvis.ts:184)
   - Should migrate to AudioWorklet
   - Still works but future browser versions may break

6. **Russian hardcoded in browser TTS** (useRealtimeVoice.ts:250)
   - Fallback TTS always uses ru-RU

7. **No rate limiting on audio chunks** (useJarvis.ts:198)
   - Could overwhelm backend

8. **Audio format validation missing** (useJarvis.ts:102)
   - Blindly plays whatever server sends

---

## 📁 TTS IMPLEMENTATION COMPARISON

| Feature | FastTTSClient (Edge-TTS) | Qwen3TTSClient | ElevenLabs | Piper |
|---------|-------------------------|----------------|------------|-------|
| Location | tts_engine.py:437-577 | tts_engine.py:216-400 | voice_realtime_providers.py:509 | voice_realtime_providers.py:571 |
| Status | ISSUE | WORKING | AVAILABLE | AVAILABLE |
| Latency | ~1s (expected) | ~5-6s | ~1-2s | ~1s |
| Output | MP3 | WAV (24kHz PCM) | MP3 | WAV |
| Requires | Internet, edge-tts pkg | localhost:5003 server | API key | Local install |
| Languages | EN, RU, many | EN, RU | Many | Limited |
| Voice Quality | Good (Azure Neural) | Excellent (Custom) | Premium | Good |

### TTS Mode Switch
```python
# In src/api/handlers/jarvis_handler.py:66
TTS_MODE = "fast"    # Edge-TTS (~1s) - CURRENTLY BROKEN
TTS_MODE = "quality" # Qwen3-TTS (~5-6s) - WORKING
```

---

## 📁 STT IMPLEMENTATION

| Provider | Location | Status | Latency | Notes |
|----------|----------|--------|---------|-------|
| mlx_whisper | jarvis_handler.py:375 | WORKING | 1-2s | Default for Jarvis |
| whisper_local | voice_realtime_providers.py:58 | WORKING | 1-2s | Realtime fallback |
| Deepgram | voice_realtime_providers.py:95 | AVAILABLE | <1s | Requires API key |
| Gemini | voice_realtime_providers.py:141 | AVAILABLE | <1s | KeyManager rotation |
| OpenAI | voice_realtime_providers.py:212 | AVAILABLE | <1s | KeyManager rotation |

---

## 📁 LLM INTEGRATION

| Model | Location | Status | Latency | Context |
|-------|----------|--------|---------|---------|
| qwen2.5vl:3b | jarvis_llm.py:30 | DEFAULT | 2-4s | 2048 tokens |
| Ollama local | jarvis_llm.py:53-298 | WORKING | 2-4s | STM context |
| Grok (X.AI) | voice_realtime_providers.py:318 | AVAILABLE | 1-2s | Streaming |
| OpenRouter | voice_realtime_providers.py:379 | FALLBACK | 2-3s | Streaming |

### LLM Parameters (jarvis_llm.py:33-39)
```python
VOICE_OPTIONS = {
    "num_predict": 150,      # Max tokens (short responses)
    "temperature": 0.7,      # Natural but focused
    "top_p": 0.9,
    "repeat_penalty": 1.1,
    "num_ctx": 2048,         # Smaller context = faster
}
```

---

## 🔄 PIPELINE FLOW

```
┌─────────────────────────────────────────────────────────────────┐
│                     JARVIS VOICE PIPELINE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CLIENT (useJarvis.ts)                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ Microphone  │───▶│ Float32→Int16│───▶│ Socket.IO   │        │
│  │ 16kHz mono  │    │ Conversion   │    │ Emit chunks │        │
│  └─────────────┘    └─────────────┘    └──────┬──────┘        │
│                                                │                │
├────────────────────────────────────────────────┼────────────────┤
│                                                ▼                │
│  SERVER (jarvis_handler.py)                                    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ Accumulate  │───▶│ VAD Check   │───▶│ Auto-stop   │        │
│  │ PCM chunks  │    │ Energy-based│    │ 1.5s silence│        │
│  └─────────────┘    └─────────────┘    └──────┬──────┘        │
│                                                │                │
│  ┌─────────────┐    ┌─────────────┐    ┌──────▼──────┐        │
│  │ Hallucin.   │◀───│ Transcribe  │◀───│ PCM→WAV     │        │
│  │ Detection   │    │ mlx_whisper │    │ Conversion  │        │
│  └──────┬──────┘    └─────────────┘    └─────────────┘        │
│         │                                                      │
│  ┌──────▼──────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ Get Context │───▶│ LLM Generate│───▶│ STM Store   │        │
│  │ STM (5 msgs)│    │ Ollama qwen │    │ User+Agent  │        │
│  └─────────────┘    └──────┬──────┘    └─────────────┘        │
│                            │                                   │
│  ┌─────────────┐    ┌──────▼──────┐    ┌─────────────┐        │
│  │ Base64      │◀───│ TTS Synth   │◀───│ Mode Select │        │
│  │ Encode      │    │ Fast/Quality│    │ TTS_MODE    │        │
│  └──────┬──────┘    └─────────────┘    └─────────────┘        │
│         │                                                      │
├─────────┼──────────────────────────────────────────────────────┤
│         ▼                                                      │
│  CLIENT (useJarvis.ts)                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ Receive     │───▶│ Decode      │───▶│ Play Audio  │        │
│  │ jarvis_audio│    │ Base64→PCM  │    │ Web Audio   │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ QUICK FIX: Revert to Working Qwen3-TTS

If Edge-TTS continues to fail, switch to Qwen3-TTS:

```python
# Edit: src/api/handlers/jarvis_handler.py line 66
TTS_MODE = "quality"  # Was "fast"
```

This will use the slower but working Qwen3-TTS server (~5-6s latency).

---

## 📋 FREEZE CHECKLIST

Before freezing Phase 104 voice development:

- [x] Full endpoint audit completed
- [x] All TTS implementations documented
- [x] All STT implementations documented
- [x] LLM integration documented
- [x] Client hooks documented
- [x] Known issues cataloged
- [x] Line markers added
- [x] Pipeline flow documented
- [ ] Edge-TTS issue investigated
- [ ] Decision: Keep fast TTS or revert to quality

---

## 🎯 RECOMMENDED ACTIONS

### Immediate (Tonight)
1. **Switch TTS_MODE to "quality"** to restore voice functionality
2. Test full pipeline with Qwen3-TTS

### Short-term (Next Session)
1. Debug Edge-TTS - why synthesize() returns empty bytes
2. Check network connectivity for Azure TTS
3. Consider adding timeout/retry logic

### Long-term (Phase 105+)
1. Implement voice model UI selector
2. Add user preference storage for voice settings
3. Re-enable Engram after Qdrant fix
4. Migrate from ScriptProcessorNode to AudioWorklet
5. Add proper multi-user support

---

## 📝 GROK RESEARCH PROMPT

See: `docs/104_ph/GROK_VOICE_RESEARCH_PROMPT.md`
