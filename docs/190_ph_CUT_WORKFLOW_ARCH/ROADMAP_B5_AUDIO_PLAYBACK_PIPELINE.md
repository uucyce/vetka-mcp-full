# ROADMAP B5: Audio Playback Pipeline
**Agent:** Beta (Media Pipeline)
**Branch:** claude/cut-media
**Date:** 2026-03-23

## Goal
Audio playback synchronized with video preview. Монтажёр слышит audio при воспроизведении.

## Architecture

```
Timeline clips → GET /cut/audio/clip-segment?source_path=...&start=...&duration=...
               → PCM/WAV response
               → Web Audio API (AudioBuffer → AudioBufferSourceNode)
               → Synced to video playhead via currentTime
```

## What Exists
- `cut_ffmpeg_waveform.py`: extract_pcm_mono_16bit / extract_pcm_stereo_16bit (FFmpeg→PCM)
- `cut_audio_engine.py`: mixer state → FFmpeg filters, LUFS analysis
- `cut_render_engine.py`: full audio render in export pipeline
- AudioRubberBand.tsx (B30): per-clip volume UI
- WaveformOverlay.tsx: visual waveform on clips

## What's Missing

| # | Task | Priority | Complexity | Description |
|---|------|----------|------------|-------------|
| B5.1 | Audio clip segment endpoint | P0 | Medium | GET /cut/audio/clip-segment → WAV bytes for a clip's audio range |
| B5.2 | useAudioPlayback hook | P0 | Medium | Web Audio API hook: load clip audio, sync to playhead, apply volume |
| B5.3 | Audio cache manager | P1 | Low | Cache decoded AudioBuffers per source_path+range to avoid re-fetching |

## B5.1: Audio Clip Segment Endpoint
- GET /cut/audio/clip-segment?source_path=...&start_sec=0&duration_sec=10&sample_rate=44100
- Returns: WAV file (PCM 16-bit stereo, 44.1kHz)
- Uses existing extract_pcm_stereo_16bit with offset support
- Max 30 seconds per request (prevent memory issues)
- Content-Type: audio/wav

## B5.2: useAudioPlayback Hook (frontend)
- Creates AudioContext on first interaction
- Fetches clip segment WAV from B5.1
- Decodes to AudioBuffer
- Plays synced to video currentTime
- Applies clip volume from store
- Stops/pauses with video

## B5.3: Audio Cache
- LRU cache of AudioBuffers by (source_path, start_sec, duration_sec)
- Max ~50MB decoded audio in memory
- Pre-fetch adjacent clips during playback
