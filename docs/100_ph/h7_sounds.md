# H7: Sounds Report - VETKA Phase 100 Tauri Migration

## Summary

No custom audio files in source. Full real-time voice system with PCM streaming, VAD, STT/TTS.

## Audio Files Found

| File | Path | Purpose |
|------|------|---------|
| audio_health_check.wav | `.venv/.../litellm/` | Dev dependency only |
| test-*.wav | `.venv/.../scipy/` | Test data only |

**No production audio files in source directories.**

## Audio Code Components

### Frontend (TypeScript/React)

| File | Component | Purpose |
|------|-----------|---------|
| AudioStreamManager.ts | Class | PCM streaming, VAD at 16kHz |
| VoiceButton.tsx | Component | Mic button, wave animation |
| SmartVoiceInput.tsx | Component | Smart voice/text switching |
| VoiceWave.tsx | Component | Canvas wave animation |
| useRealtimeVoice.ts | Hook | Real-time voice conversation |
| useTTS.ts | Hook | Browser speechSynthesis |

### Backend (Python)

| File | Function | Purpose |
|------|----------|---------|
| voice_handler.py | tts_elevenlabs() | ElevenLabs TTS |
| voice_handler.py | tts_piper_local() | Piper local TTS |
| voice_realtime_providers.py | stt_whisper_local() | Whisper STT |
| voice_realtime_providers.py | stt_deepgram() | Deepgram STT |
| voice_router.py | VoiceRouter | State machine |
| voice_socket_handler.py | Socket handlers | Real-time streaming |

## Audio Technology Stack

### Input/Capture
- Web Audio API (AudioContext, MediaStreamSource)
- MediaRecorder API (WebM/MP4)
- Web Speech API fallback

### Voice Activity Detection (VAD)
- RMS threshold: 0.015
- Silence duration: 400ms
- Real-time audio level monitoring

### Output/Playback
- HTML5 Audio API (`new Audio()`)
- Web Speech API (speechSynthesis)
- Browser TTS with language auto-detection

## Socket.IO Voice Events

### Client → Server
| Event | Purpose |
|-------|---------|
| voice_stream_start | Begin PCM stream |
| voice_pcm | Raw PCM frame |
| voice_utterance_end | VAD end detection |
| voice_stream_end | Stop stream |
| voice_interrupt | User interrupt |

### Server → Client
| Event | Purpose |
|-------|---------|
| voice_partial | Partial STT result |
| voice_final | Final STT result |
| voice_llm_token | LLM streaming |
| voice_tts_chunk | TTS audio chunk |
| voice_tts_browser | Browser TTS fallback |

## Audio Specifications

| Parameter | Value |
|-----------|-------|
| Sample Rate | 16kHz |
| Channels | 1 (mono) |
| Format | Int16 PCM |
| Frame Size | 2048 samples (~128ms) |
| VAD Threshold | 0.015 RMS |
| Silence Duration | 400ms |

## STT/TTS Providers

### STT (Speech-to-Text)
- Whisper (local, no API limits)
- Deepgram Nova 2 (cloud)
- Web Speech API (browser fallback)

### TTS (Text-to-Speech)
- ElevenLabs (cloud, premium)
- Piper (local offline)
- speechSynthesis (browser)

## Language Support

Auto-detection for:
- Russian (Cyrillic)
- Chinese (characters)
- Japanese
- German (umlauts)
- French (accents)
- English (default)

## Voice CSS Animations

| Animation | Purpose | Duration |
|-----------|---------|----------|
| mic-pulse | Active mic | 1.5s |
| mic-glow | Recording glow | 1s |
| speaker-pulse | TTS indicator | 1s |
| sound-wave | Audio ripple | 1s |
| wave-glow | Wave canvas | 2s |

## Tauri Notifications

Location: `src-tauri/src/heartbeat.rs`
- Task reminders every 5 minutes
- Uses system default sounds
- No custom sound files configured

## Markers

[SOUND_FILE] None in production
[SOUND_CODE] AudioStreamManager.ts, useRealtimeVoice.ts, useTTS.ts
[SOUND_NOTIFICATION] heartbeat.rs (system default)
[AUDIO_PROVIDERS] Whisper, Deepgram, ElevenLabs, Piper

## Missing for Tauri

- [ ] Custom notification sounds
- [ ] Volume control UI
- [ ] Audio device selection
- [ ] Recording playback preview
- [ ] Audio file export

---
Generated: 2026-01-29 | Agent: H7 Haiku | Phase 100
