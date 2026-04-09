"""
Phase 60.5.1: Voice Socket.IO Handlers.

Real-time voice streaming for VETKA with PCM streaming and interruption support.

@status: active
@phase: 96
@depends: voice_handler, voice_router, voice_realtime_providers
@used_by: main.py socket registration

Socket.IO events (Legacy - Phase 60.5):
- voice_start: User started speaking
- voice_audio: Audio chunk from user (STT)
- voice_stop: User stopped speaking
- tts_request: Request TTS for text
- voice_transcribed: STT result
- tts_response: TTS audio/browser instruction
- voice_status: Status updates (listening/speaking/idle)
- voice_error: Error notifications

NEW Socket.IO events (Phase 60.5.1 - Realtime):
- voice_stream_start: Start PCM audio stream
- voice_pcm: Raw PCM audio frame (Int16 array)
- voice_utterance_end: VAD detected end of speech
- voice_stream_end: Stop audio stream
- voice_interrupt: User interrupted model response
- voice_config: Update session config (model, voice, etc)
- voice_partial: Partial STT result (streaming)
- voice_final: Final STT result
- voice_llm_token: LLM streaming token
- voice_model_speaking: Model TTS playback state
- voice_tts_chunk: TTS audio chunk (base64)
- voice_interrupted: Acknowledgement of interruption
"""

import logging
import asyncio
from typing import Optional

from .voice_handler import get_voice_service
from .voice_router import VoiceRouter, set_voice_router, get_voice_router
from .voice_realtime_providers import (
    stt_from_pcm_bytes,
    llm_stream_response,
    tts_sentence_to_base64,
)

logger = logging.getLogger(__name__)


def register_voice_socket_handlers(sio, app=None):
    """
    Register voice-related Socket.IO handlers

    Args:
        sio: python-socketio AsyncServer instance
        app: Optional FastAPI app for key manager access
    """

    voice_service = get_voice_service()

    # ============================================
    # CONNECTION HANDLERS
    # ============================================

    @sio.on('voice_connect')
    async def handle_voice_connect(sid):
        """Client connected to voice namespace"""
        logger.info(f"[Voice Socket] Client connected: {sid}")
        await sio.emit('voice_status', {'status': 'idle', 'connected': True}, to=sid)

    @sio.on('voice_disconnect')
    async def handle_voice_disconnect(sid):
        """Client disconnected from voice namespace"""
        logger.info(f"[Voice Socket] Client disconnected: {sid}")

    # ============================================
    # STT HANDLERS (Speech-to-Text)
    # ============================================

    @sio.on('voice_start')
    async def handle_voice_start(sid, data=None):
        """
        User started speaking - begin STT session

        data (optional):
            provider: STT provider (whisper|deepgram|openai)
        """
        provider = data.get('provider', 'whisper') if data else 'whisper'
        logger.info(f"[Voice] Recording started: {sid}, provider: {provider}")

        await sio.emit('voice_status', {
            'status': 'listening',
            'provider': provider
        }, to=sid)

    @sio.on('voice_audio')
    async def handle_voice_audio(sid, data):
        """
        Received audio chunk from user - transcribe

        data:
            audio: Base64 encoded audio (WAV/WebM)
            provider: STT provider (optional)
            final: Is this the final chunk? (default True for single-shot)
        """
        audio_base64 = data.get('audio')
        provider = data.get('provider')
        is_final = data.get('final', True)
        request_id = data.get('request_id')
        timeout_ms_raw = data.get('timeout_ms')
        try:
            timeout_ms = int(timeout_ms_raw) if timeout_ms_raw is not None else 45000
        except Exception:
            timeout_ms = 45000
        timeout_ms = max(5000, min(300000, timeout_ms))

        if not audio_base64:
            await sio.emit(
                'voice_error',
                {'error': 'No audio data received', 'request_id': request_id},
                to=sid,
            )
            return

        try:
            # Transcribe audio
            text = await asyncio.wait_for(
                voice_service.speech_to_text(audio_base64, provider),
                timeout=timeout_ms / 1000.0,
            )

            if text:
                await sio.emit('voice_transcribed', {
                    'text': text,
                    'final': is_final,
                    'provider': provider or 'whisper',
                    'request_id': request_id,
                }, to=sid)
                logger.info(f"[Voice] Transcribed: '{text[:50]}...'")
            else:
                await sio.emit('voice_transcribed', {
                    'text': '',
                    'final': is_final,
                    'error': 'No speech detected',
                    'request_id': request_id,
                }, to=sid)

        except asyncio.TimeoutError:
            logger.warning(f"[Voice] STT timeout after {timeout_ms}ms")
            await sio.emit(
                'voice_error',
                {'error': f'Voice transcription timeout ({timeout_ms}ms)', 'request_id': request_id},
                to=sid,
            )
        except Exception as e:
            logger.error(f"[Voice] STT error: {e}")
            await sio.emit(
                'voice_error',
                {'error': str(e), 'request_id': request_id},
                to=sid,
            )

    @sio.on('voice_stop')
    async def handle_voice_stop(sid):
        """User stopped speaking"""
        logger.info(f"[Voice] Recording stopped: {sid}")
        await sio.emit('voice_status', {'status': 'idle'}, to=sid)

    # ============================================
    # TTS HANDLERS (Text-to-Speech)
    # ============================================

    @sio.on('tts_request')
    async def handle_tts_request(sid, data):
        """
        Request TTS for text

        data:
            text: Text to speak
            provider: TTS provider (browser|elevenlabs|piper)
            voice_id: Voice ID for ElevenLabs (optional)
        """
        text = data.get('text', '')
        provider = data.get('provider', 'browser')
        voice_id = data.get('voice_id')

        if not text:
            await sio.emit('voice_error', {'error': 'No text provided'}, to=sid)
            return

        try:
            # Update status
            await sio.emit('voice_status', {
                'status': 'speaking',
                'provider': provider
            }, to=sid)

            # Generate TTS
            result = await voice_service.text_to_speech(text, provider, voice_id)

            # Send response
            await sio.emit('tts_response', result, to=sid)
            logger.info(f"[Voice] TTS generated: {len(text)} chars via {provider}")

            # Reset status after browser gets response
            await sio.emit('voice_status', {'status': 'idle'}, to=sid)

        except Exception as e:
            logger.error(f"[Voice] TTS error: {e}")
            await sio.emit('voice_error', {'error': str(e)}, to=sid)
            await sio.emit('voice_status', {'status': 'idle'}, to=sid)

    # ============================================
    # CONFIG HANDLERS
    # ============================================

    @sio.on('voice_get_providers')
    async def handle_get_providers(sid):
        """Get available TTS/STT providers"""
        providers = voice_service.get_available_providers()
        await sio.emit('voice_providers', providers, to=sid)

    @sio.on('voice_set_provider')
    async def handle_set_provider(sid, data):
        """
        Set preferred provider

        data:
            tts: TTS provider name
            stt: STT provider name
        """
        if 'tts' in data:
            voice_service.config.tts_provider = data['tts']
            logger.info(f"[Voice] TTS provider set to: {data['tts']}")

        if 'stt' in data:
            voice_service.config.stt_provider = data['stt']
            logger.info(f"[Voice] STT provider set to: {data['stt']}")

        await sio.emit('voice_config_updated', {
            'tts_provider': voice_service.config.tts_provider,
            'stt_provider': voice_service.config.stt_provider
        }, to=sid)

    # ============================================
    # PHASE 60.5.1: REALTIME VOICE HANDLERS
    # PCM streaming with VAD and interruption support
    # ============================================

    # Create emit callback for voice router
    async def emit_to_session(session_id: str, event: str, data: dict):
        """Emit event to specific session"""
        await sio.emit(event, data, to=session_id)

    # Initialize voice router with providers
    voice_router = VoiceRouter(
        stt_provider=stt_from_pcm_bytes,
        llm_provider=llm_stream_response,
        tts_provider=tts_sentence_to_base64,
        emit_callback=emit_to_session,
    )
    set_voice_router(voice_router)

    @sio.on('voice_stream_start')
    async def handle_stream_start(sid, data=None):
        """
        Start PCM audio stream from client

        Phase 60.5.1: Real-time voice streaming
        """
        logger.info(f"[Voice Realtime] Stream start: {sid}")
        await voice_router.handle_stream_start(sid)

    @sio.on('voice_pcm')
    async def handle_pcm_frame(sid, data):
        """
        Receive raw PCM audio frame

        data:
            audio: List of Int16 samples
            sampleRate: Sample rate (usually 16000)
        """
        pcm_data = data.get('audio', [])
        sample_rate = data.get('sampleRate', 16000)

        if not pcm_data:
            return

        await voice_router.handle_audio_frame(sid, pcm_data, sample_rate)

    @sio.on('voice_utterance_end')
    async def handle_utterance_end(sid, data=None):
        """
        VAD detected end of speech - process utterance

        Phase 60.5.1: Triggers STT → LLM → TTS pipeline
        """
        logger.info(f"[Voice Realtime] Utterance end: {sid}")
        await voice_router.handle_utterance_end(sid)

    @sio.on('voice_stream_end')
    async def handle_stream_end(sid, data=None):
        """
        Stop PCM audio stream

        Phase 60.5.1: Cleanup and process remaining audio
        """
        logger.info(f"[Voice Realtime] Stream end: {sid}")
        await voice_router.handle_stream_end(sid)

    @sio.on('voice_interrupt')
    async def handle_interrupt(sid, data=None):
        """
        User interrupted model response

        Phase 60.5.1: Cancel current generation, stop TTS playback
        """
        logger.info(f"[Voice Realtime] Interrupt: {sid}")
        await voice_router.handle_interrupt(sid)

    @sio.on('voice_config')
    async def handle_voice_config(sid, data):
        """
        Update session voice configuration

        data:
            model: LLM model to use (e.g., 'grok-beta')
            tts_voice: TTS voice ID (e.g., 'bella')
            stt_provider: STT provider (whisper/deepgram/openai)
        """
        if not data:
            return

        await voice_router.handle_config(sid, data)
        logger.info(f"[Voice Realtime] Config updated: {sid}")

    # Cleanup session on disconnect
    @sio.on('disconnect')
    async def handle_voice_disconnect_cleanup(sid):
        """Cleanup voice session on disconnect"""
        router = get_voice_router()
        if router:
            router.remove_session(sid)

    logger.info("[Voice Socket] Handlers registered (Phase 60.5.1 Realtime enabled)")
