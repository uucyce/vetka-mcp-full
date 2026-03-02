"""
Phase 60.5.1: Voice Router - Realtime Pipeline.

State machine for voice conversations with interruption support.

@status: active
@phase: 96
@depends: asyncio, voice_realtime_providers
@used_by: voice_socket_handler.py

Flow:
    User speaks -> VAD end -> STT -> LLM (stream) -> TTS (stream) -> Play
                    ^                                               |
                    +-------------- User interrupts <---------------+
"""

import asyncio
import logging
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, AsyncGenerator, List

logger = logging.getLogger(__name__)


class VoiceState(Enum):
    """Voice conversation states"""
    IDLE = "idle"               # Waiting for user
    LISTENING = "listening"     # User speaking (audio streaming in)
    PROCESSING = "processing"   # STT finalizing
    GENERATING = "generating"   # LLM streaming
    SPEAKING = "speaking"       # TTS playing
    INTERRUPTED = "interrupted" # User interrupted model


@dataclass
class VoiceSession:
    """Per-connection voice session state"""
    session_id: str
    state: VoiceState = VoiceState.IDLE

    # Audio buffer for STT (list of Int16 samples)
    audio_buffer: List[int] = field(default_factory=list)

    # Current generation task (for cancellation on interrupt)
    current_task: Optional[asyncio.Task] = None

    # Timing
    last_speech_time: float = 0
    utterance_start_time: float = 0

    # Config (can be updated per-session)
    model: str = "grok-3-mini"  # Updated: grok-beta retired, use grok-3-mini
    tts_voice: str = "bella"
    stt_provider: str = "whisper"  # Default to local Whisper (no API limits!)
    chat_mode: bool = False  # Chat input mode: only STT, LLM/TTS handled by chat pipeline

    # Conversation context
    conversation_history: List[dict] = field(default_factory=list)

    def add_user_message(self, text: str):
        """Add user message to history"""
        self.conversation_history.append({
            "role": "user",
            "content": text
        })
        # Keep last 10 messages for context
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    def add_assistant_message(self, text: str):
        """Add assistant message to history"""
        self.conversation_history.append({
            "role": "assistant",
            "content": text
        })


class VoiceRouter:
    """
    Manages voice conversation flow with state machine

    Pipeline:
        User audio → VAD detects silence → STT → LLM → TTS → Playback
                                                    ↑
                        User interrupt ─────────────┘
    """

    def __init__(
        self,
        stt_provider: Callable,
        llm_provider: Callable,
        tts_provider: Callable,
        emit_callback: Callable,
    ):
        """
        Initialize voice router with provider callbacks

        Args:
            stt_provider: async (audio_bytes) -> str
            llm_provider: async (prompt, model, history) -> AsyncGenerator[str]
            tts_provider: async (text, voice) -> str (base64)
            emit_callback: async (session_id, event, data) -> None
        """
        self.stt = stt_provider
        self.llm = llm_provider
        self.tts = tts_provider
        self.emit = emit_callback

        self.sessions: dict[str, VoiceSession] = {}

    def get_session(self, session_id: str) -> VoiceSession:
        """Get or create session for connection"""
        if session_id not in self.sessions:
            self.sessions[session_id] = VoiceSession(session_id=session_id)
            logger.info(f"[Voice:{session_id}] New session created")
        return self.sessions[session_id]

    def remove_session(self, session_id: str):
        """Remove session on disconnect"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            # Cancel any running task
            if session.current_task and not session.current_task.done():
                session.current_task.cancel()
            del self.sessions[session_id]
            logger.info(f"[Voice:{session_id}] Session removed")

    async def handle_stream_start(self, session_id: str):
        """Handle start of audio stream"""
        session = self.get_session(session_id)
        session.state = VoiceState.IDLE
        session.audio_buffer.clear()
        logger.info(f"[Voice:{session_id}] Stream started")
        await self.emit(session_id, 'voice_status', {'status': 'listening'})

    async def handle_audio_frame(self, session_id: str, pcm_data: List[int], sample_rate: int):
        """
        Process incoming PCM audio frame

        Args:
            session_id: Connection ID
            pcm_data: List of Int16 samples
            sample_rate: Audio sample rate (usually 16000)
        """
        session = self.get_session(session_id)

        # Buffer audio
        session.audio_buffer.extend(pcm_data)
        session.last_speech_time = time.time()

        if session.state == VoiceState.IDLE:
            session.state = VoiceState.LISTENING
            session.utterance_start_time = time.time()
            logger.debug(f"[Voice:{session_id}] Started listening")

    async def handle_utterance_end(self, session_id: str):
        """
        Handle end of user utterance (VAD detected silence)
        Triggers the STT → LLM → TTS pipeline
        """
        session = self.get_session(session_id)

        if session.state != VoiceState.LISTENING:
            logger.debug(f"[Voice:{session_id}] Utterance end ignored (state: {session.state})")
            return

        # Check minimum audio length (avoid processing noise)
        min_samples = 16000 * 0.3  # 300ms minimum
        if len(session.audio_buffer) < min_samples:
            logger.debug(f"[Voice:{session_id}] Utterance too short ({len(session.audio_buffer)} samples), ignoring")
            session.audio_buffer.clear()
            session.state = VoiceState.IDLE
            return

        session.state = VoiceState.PROCESSING
        logger.info(f"[Voice:{session_id}] Processing utterance ({len(session.audio_buffer)} samples)")

        # Process pipeline in background task
        session.current_task = asyncio.create_task(
            self._process_utterance(session)
        )

    async def handle_interrupt(self, session_id: str):
        """
        Handle user interruption (user started speaking while model responding)
        """
        session = self.get_session(session_id)

        logger.info(f"[Voice:{session_id}] INTERRUPTED! (was: {session.state})")

        # Cancel current generation
        if session.current_task and not session.current_task.done():
            session.current_task.cancel()
            try:
                await session.current_task
            except asyncio.CancelledError:
                pass

        session.state = VoiceState.INTERRUPTED

        # Notify frontend to stop TTS playback
        await self.emit(session_id, 'voice_model_speaking', {'speaking': False})
        await self.emit(session_id, 'voice_interrupted', {})

        # Ready for new input
        session.state = VoiceState.IDLE
        session.audio_buffer.clear()

    async def handle_stream_end(self, session_id: str):
        """Handle end of audio stream (user stopped listening)"""
        session = self.get_session(session_id)

        # Process any remaining audio
        if session.state == VoiceState.LISTENING and len(session.audio_buffer) > 0:
            await self.handle_utterance_end(session_id)

        logger.info(f"[Voice:{session_id}] Stream ended")

    async def handle_config(self, session_id: str, config: dict):
        """Update session configuration"""
        session = self.get_session(session_id)

        if 'model' in config and config['model']:
            session.model = config['model']
        if 'tts_voice' in config and config['tts_voice']:
            session.tts_voice = config['tts_voice']
        if 'stt_provider' in config and config['stt_provider']:
            session.stt_provider = config['stt_provider']
        if 'chat_mode' in config:
            session.chat_mode = bool(config['chat_mode'])

        logger.info(
            f"[Voice:{session_id}] Config: model={session.model}, voice={session.tts_voice}, "
            f"stt={session.stt_provider}, chat_mode={session.chat_mode}"
        )

    async def _process_utterance(self, session: VoiceSession):
        """
        Full pipeline: STT → LLM → TTS

        This runs as a background task and can be cancelled on interrupt.
        """
        try:
            # 1. Convert buffer to bytes
            audio_bytes = self._int16_list_to_bytes(session.audio_buffer)
            session.audio_buffer.clear()

            # 2. STT
            logger.info(f"[Voice:{session.session_id}] STT processing ({len(audio_bytes)} bytes)...")
            await self.emit(session.session_id, 'voice_status', {'status': 'processing'})

            transcript = await self.stt(audio_bytes, session.stt_provider)
            logger.info(f"[Voice:{session.session_id}] STT result: '{transcript}' (len={len(transcript) if transcript else 0})")

            if not transcript or not transcript.strip():
                logger.warning(f"[Voice:{session.session_id}] Empty transcript, returning to idle")
                await self.emit(session.session_id, 'voice_error', {'error': 'STT returned empty - check API keys'})
                session.state = VoiceState.IDLE
                return

            # Emit final transcript
            logger.info(f"[Voice:{session.session_id}] Transcript: '{transcript[:50]}...'")
            await self.emit(session.session_id, 'voice_final', {'text': transcript})

            # Add to conversation history
            session.add_user_message(transcript)

            # Chat mode: stop here (STT only). Chat pipeline handles LLM/TTS.
            if session.chat_mode:
                session.state = VoiceState.IDLE
                await self.emit(session.session_id, 'voice_status', {'status': 'idle'})
                return

            # 3. LLM (streaming)
            session.state = VoiceState.GENERATING
            logger.info(f"[Voice:{session.session_id}] LLM generating with {session.model}...")
            await self.emit(session.session_id, 'voice_status', {'status': 'generating'})

            full_response = ""
            token_count = 0

            async for token in self.llm(transcript, session.model, session.conversation_history):
                token_count += 1
                if session.state == VoiceState.INTERRUPTED:
                    logger.info(f"[Voice:{session.session_id}] LLM interrupted")
                    return

                full_response += token

                # Emit token for text display
                await self.emit(session.session_id, 'voice_llm_token', {'token': token})

            # Check for error responses - DON'T speak them to avoid voice loop!
            # Error patterns from LLM providers when they fail
            error_patterns = [
                "sorry, i couldn't process",
                "sorry, something went wrong",
                "i couldn't process that",
                "an error occurred",
                "couldn't process your request",
            ]
            is_error_response = any(pattern in full_response.lower() for pattern in error_patterns)

            if is_error_response:
                logger.warning(f"[Voice:{session.session_id}] LLM returned error response, NOT speaking to avoid loop")
                # Send error to frontend (shown as text, not spoken)
                await self.emit(session.session_id, 'voice_error', {
                    'error': 'LLM failed to respond. Check API keys.',
                    'silent': True  # Flag to show in UI but don't speak
                })
                session.state = VoiceState.IDLE
                return

            # Add to conversation history (only successful responses)
            session.add_assistant_message(full_response)

            # 4. TTS (streaming by sentences)
            session.state = VoiceState.SPEAKING
            await self.emit(session.session_id, 'voice_model_speaking', {'speaking': True})

            logger.info(f"[Voice:{session.session_id}] TTS starting ({len(full_response)} chars)...")

            # Split into sentences for natural TTS
            sentences = self._split_sentences(full_response)

            for sentence in sentences:
                if session.state == VoiceState.INTERRUPTED:
                    logger.info(f"[Voice:{session.session_id}] TTS interrupted")
                    return

                if not sentence.strip():
                    continue

                audio_chunk = await self.tts(sentence, session.tts_voice)

                if audio_chunk:
                    await self.emit(session.session_id, 'voice_tts_chunk', {
                        'audio': audio_chunk,  # base64
                        'format': 'wav'
                    })
                else:
                    await self.emit(session.session_id, 'voice_error', {
                        'error': 'Qwen TTS unavailable',
                        'silent': True,
                    })
                    logger.warning(f"[Voice:{session.session_id}] Qwen TTS unavailable, sentence skipped")

            # Done
            await self.emit(session.session_id, 'voice_model_speaking', {'speaking': False})
            session.state = VoiceState.IDLE

            duration = time.time() - session.utterance_start_time
            logger.info(f"[Voice:{session.session_id}] Pipeline complete ({duration:.2f}s)")

        except asyncio.CancelledError:
            logger.info(f"[Voice:{session.session_id}] Pipeline cancelled")
            session.state = VoiceState.IDLE
            raise

        except Exception as e:
            logger.error(f"[Voice:{session.session_id}] Pipeline error: {e}", exc_info=True)
            await self.emit(session.session_id, 'voice_error', {'error': str(e)})
            session.state = VoiceState.IDLE

    def _int16_list_to_bytes(self, int16_list: List[int]) -> bytes:
        """Convert list of Int16 values to raw bytes"""
        import struct
        result = bytearray()
        for sample in int16_list:
            # Clamp to Int16 range
            sample = max(-32768, min(32767, sample))
            result.extend(struct.pack('<h', sample))
        return bytes(result)

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences for natural TTS chunking"""
        import re

        # Split on sentence boundaries (., !, ?, with optional whitespace)
        # Keep punctuation with the sentence
        sentences = re.split(r'(?<=[.!?])\s+', text)

        # Filter empty and strip
        return [s.strip() for s in sentences if s.strip()]


# Singleton instance (created in socket handlers)
_voice_router: Optional[VoiceRouter] = None


def get_voice_router() -> Optional[VoiceRouter]:
    """Get singleton voice router"""
    return _voice_router


def set_voice_router(router: VoiceRouter):
    """Set singleton voice router"""
    global _voice_router
    _voice_router = router
