"""
JARVIS Voice Interface Socket.IO Handler
Handles real-time voice interaction with AI assistant (SEPARATE from chat).

State Machine: idle -> listening -> thinking -> speaking -> idle

MARKER_104.3: Jarvis voice interface handler
"""

import logging
import base64
import io
import wave
import tempfile
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


def pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
    """
    Convert raw PCM data to WAV format with proper header.

    Args:
        pcm_data: Raw PCM audio bytes (int16)
        sample_rate: Audio sample rate (TTS uses 24000)
        channels: Number of audio channels (1 = mono)
        sample_width: Bytes per sample (2 = 16-bit)

    Returns:
        WAV formatted audio bytes
    """
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    return wav_buffer.getvalue()


# Import STT and TTS engines
try:
    import mlx_whisper
    HAS_MLX_WHISPER = True
    logger.info("[JARVIS] mlx_whisper available")
except ImportError:
    HAS_MLX_WHISPER = False
    logger.warning("[JARVIS] mlx_whisper not available, STT disabled")

try:
    from src.voice.tts_engine import Qwen3TTSClient, FastTTSClient
    HAS_TTS = True
    HAS_FAST_TTS = True
    logger.info("[JARVIS] TTS clients available (Qwen3 + Fast)")
except ImportError:
    HAS_TTS = False
    HAS_FAST_TTS = False
    logger.warning("[JARVIS] TTS client not available")

# TTS Mode: 'fast' (Edge-TTS, ~1s) or 'quality' (Qwen3-TTS, ~5-6s)
# PHASE_104.7_FREEZE: Reverted to quality - Edge-TTS needs debugging
TTS_MODE = "quality"  # Phase 104.7: Reverted to quality for stability

# Phase 104.6: LLM Integration
try:
    from src.voice.jarvis_llm import get_jarvis_llm, get_jarvis_context
    HAS_LLM = True
    logger.info("[JARVIS] LLM integration available")
except ImportError as e:
    HAS_LLM = False
    logger.warning(f"[JARVIS] LLM integration not available: {e}")


def _is_hallucination(transcript: str) -> bool:
    """
    Detect Whisper hallucination patterns.

    Whisper sometimes generates repeated phrases when given silence or noise.
    Common patterns: "I'm going to...", "Thank you for watching", etc.

    Args:
        transcript: STT output to check

    Returns:
        True if likely hallucination
    """
    if not transcript:
        return False

    # Check for repeated phrases (split by sentence markers)
    import re
    sentences = re.split(r'[.!?]', transcript)
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) >= 3:
        # If same sentence repeats 3+ times, it's hallucination
        from collections import Counter
        counts = Counter(sentences)
        most_common = counts.most_common(1)
        if most_common and most_common[0][1] >= 3:
            logger.warning(f"[JARVIS] Hallucination detected: '{most_common[0][0]}' repeated {most_common[0][1]} times")
            return True

    # Check for known hallucination phrases
    hallucination_patterns = [
        "thank you for watching",
        "please subscribe",
        "like and subscribe",
        "see you in the next",
        "i'm going to go to the next",
        "transcribed by",
        "subtitles by",
    ]
    transcript_lower = transcript.lower()
    for pattern in hallucination_patterns:
        if pattern in transcript_lower:
            logger.warning(f"[JARVIS] Known hallucination pattern: '{pattern}'")
            return True

    return False


class JarvisState(str, Enum):
    """Jarvis session states"""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


# VAD Configuration
VAD_SILENCE_THRESHOLD = 500  # RMS energy threshold (lower = more sensitive)
VAD_SILENCE_DURATION = 1.5   # Seconds of silence to trigger auto-stop
VAD_MIN_SPEECH_DURATION = 0.5  # Minimum speech before allowing auto-stop


def calculate_audio_energy(pcm_bytes: bytes) -> float:
    """Calculate RMS energy of PCM audio chunk."""
    if len(pcm_bytes) < 2:
        return 0.0
    # Convert bytes to int16 array
    audio_array = np.frombuffer(pcm_bytes, dtype=np.int16)
    if len(audio_array) == 0:
        return 0.0
    # Calculate RMS
    rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
    return rms


@dataclass
class JarvisSession:
    """
    Jarvis voice session state

    Attributes:
        user_id: Unique user identifier
        state: Current state in the state machine
        audio_buffer: Accumulated PCM audio chunks during listening
        sample_rate: Audio sample rate (default 16000 Hz)
        transcript: Latest STT transcript
        response_text: Latest AI response text
        silence_start: Timestamp when silence started (for VAD)
        has_speech: Whether speech has been detected
        total_duration: Total audio duration in seconds
    """
    user_id: str
    state: JarvisState = JarvisState.IDLE
    audio_buffer: List[bytes] = field(default_factory=list)
    sample_rate: int = 16000
    transcript: str = ""
    response_text: str = ""
    silence_start: Optional[float] = None
    has_speech: bool = False
    total_duration: float = 0.0

    def reset_buffer(self):
        """Clear audio buffer and VAD state"""
        self.audio_buffer = []
        self.silence_start = None
        self.has_speech = False
        self.total_duration = 0.0

    def add_audio_chunk(self, chunk: bytes):
        """Add audio chunk to buffer"""
        self.audio_buffer.append(chunk)
        # Update duration (16-bit = 2 bytes per sample)
        self.total_duration += len(chunk) / 2 / self.sample_rate

    def get_full_audio(self) -> bytes:
        """Get concatenated audio buffer"""
        return b''.join(self.audio_buffer)


# Active sessions: sid -> JarvisSession
_active_sessions: Dict[str, JarvisSession] = {}


def register_jarvis_handlers(sio):
    """
    Register Jarvis voice interface Socket.IO event handlers

    Args:
        sio: SocketIO instance from main API setup
    """

    @sio.event
    async def jarvis_listen_start(sid, data):
        """
        Client starts voice input session

        Expected data: {user_id: str}
        Emits: jarvis_state with state='listening'
        """
        try:
            user_id = data.get('user_id')
            if not user_id:
                logger.error(f"[JARVIS] Missing user_id in jarvis_listen_start from {sid}")
                return

            # Create or reset session
            session = JarvisSession(user_id=user_id)
            session.state = JarvisState.LISTENING
            session.reset_buffer()

            _active_sessions[sid] = session

            logger.info(f"[JARVIS] Listen started for user {user_id}, sid={sid}")

            # Notify client of state change
            await sio.emit('jarvis_state', {
                'state': JarvisState.LISTENING,
                'user_id': user_id
            }, to=sid)

        except Exception as e:
            logger.error(f"[JARVIS] Error in jarvis_listen_start: {e}", exc_info=True)
            await sio.emit('jarvis_error', {
                'error': str(e),
                'event': 'jarvis_listen_start'
            }, to=sid)


    @sio.event
    async def jarvis_audio_chunk(sid, data):
        """
        Receive audio chunk during listening

        Expected data: {audio: bytes, sample_rate: int}
        Accumulates audio in session buffer
        """
        try:
            session = _active_sessions.get(sid)
            if not session:
                logger.warning(f"[JARVIS] No active session for sid={sid} in jarvis_audio_chunk")
                return

            if session.state != JarvisState.LISTENING:
                logger.warning(
                    f"[JARVIS] Received audio chunk in wrong state: {session.state} for sid={sid}"
                )
                return

            audio_bytes = data.get('audio')
            sample_rate = data.get('sample_rate', 16000)

            if not audio_bytes:
                logger.warning(f"[JARVIS] Empty audio chunk from sid={sid}")
                return

            # Update sample rate if provided
            if sample_rate != session.sample_rate:
                session.sample_rate = sample_rate

            # Add to buffer
            session.add_audio_chunk(audio_bytes)

            # VAD: Check audio energy for silence detection
            import time
            energy = calculate_audio_energy(audio_bytes)
            current_time = time.time()

            if energy > VAD_SILENCE_THRESHOLD:
                # Speech detected
                session.has_speech = True
                session.silence_start = None
                logger.debug(f"[JARVIS VAD] Speech detected, energy={energy:.0f}")
            else:
                # Silence detected
                if session.silence_start is None:
                    session.silence_start = current_time
                    logger.debug(f"[JARVIS VAD] Silence started, energy={energy:.0f}")

                # Check if silence duration exceeded threshold
                silence_duration = current_time - session.silence_start
                if (session.has_speech and
                    session.total_duration >= VAD_MIN_SPEECH_DURATION and
                    silence_duration >= VAD_SILENCE_DURATION):
                    # Auto-stop: User finished speaking
                    logger.info(f"[JARVIS VAD] Auto-stop triggered after {silence_duration:.1f}s silence, "
                               f"total duration: {session.total_duration:.1f}s")

                    # Emit auto-stop event to client
                    await sio.emit('jarvis_auto_stop', {
                        'user_id': session.user_id,
                        'silence_duration': silence_duration
                    }, to=sid)

                    # Trigger the same pipeline as manual stop
                    await jarvis_listen_stop(sid, {'user_id': session.user_id})
                    return

        except Exception as e:
            logger.error(f"[JARVIS] Error in jarvis_audio_chunk: {e}", exc_info=True)
            await sio.emit('jarvis_error', {
                'error': str(e),
                'event': 'jarvis_audio_chunk'
            }, to=sid)


    @sio.event
    async def jarvis_listen_stop(sid, data):
        """
        Client stops voice input - trigger STT -> AI -> TTS pipeline

        Expected data: {user_id: str}
        Emits: jarvis_state, jarvis_transcript, jarvis_response, jarvis_audio
        """
        try:
            session = _active_sessions.get(sid)
            if not session:
                logger.warning(f"[JARVIS] No active session for sid={sid} in jarvis_listen_stop")
                return

            user_id = data.get('user_id')
            if user_id != session.user_id:
                logger.warning(
                    f"[JARVIS] User ID mismatch: session={session.user_id}, data={user_id}"
                )

            logger.info(
                f"[JARVIS] Listen stopped for user {session.user_id}, "
                f"buffer size: {len(session.get_full_audio())} bytes, sid={sid}"
            )

            # Transition to THINKING state
            session.state = JarvisState.THINKING
            await sio.emit('jarvis_state', {
                'state': JarvisState.THINKING,
                'user_id': session.user_id
            }, to=sid)

            # STT: Convert PCM buffer to WAV and transcribe with Whisper
            audio_data = session.get_full_audio()

            if len(audio_data) < 1000:
                logger.warning(f"[JARVIS] Audio buffer too small: {len(audio_data)} bytes")
                transcript = ""
            elif HAS_MLX_WHISPER:
                # Convert Int16 PCM to WAV file for Whisper
                try:
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                        tmp_path = tmp_file.name
                        with wave.open(tmp_file, 'wb') as wav_file:
                            wav_file.setnchannels(1)
                            wav_file.setsampwidth(2)  # 16-bit
                            wav_file.setframerate(session.sample_rate)
                            wav_file.writeframes(audio_data)

                    # Transcribe with MLX Whisper
                    logger.info(f"[JARVIS] Transcribing {len(audio_data)} bytes of audio...")
                    result = mlx_whisper.transcribe(
                        tmp_path,
                        path_or_hf_repo="mlx-community/whisper-base-mlx",
                        language="en"  # Auto-detect or set based on user preference
                    )
                    transcript = result.get("text", "").strip()
                    logger.info(f"[JARVIS] STT transcript: {transcript}")

                    # Cleanup temp file
                    Path(tmp_path).unlink(missing_ok=True)

                except Exception as e:
                    logger.error(f"[JARVIS] STT failed: {e}")
                    transcript = "[STT Error]"
            else:
                logger.warning("[JARVIS] No STT engine available")
                transcript = "[No STT available]"

            session.transcript = transcript

            logger.info(f"[JARVIS] STT transcript (placeholder): {transcript}")
            await sio.emit('jarvis_transcript', {
                'text': transcript,
                'user_id': session.user_id
            }, to=sid)

            # AI Response: Phase 104.7 - Streaming LLM → TTS pipeline
            # Detect hallucination (repeated phrases) from STT
            if _is_hallucination(transcript):
                logger.warning(f"[JARVIS] Detected STT hallucination, ignoring")
                response_text = "I couldn't understand that clearly. Could you try again?"
            elif not transcript or transcript.startswith("["):
                response_text = "I didn't catch that. Could you please repeat?"
            elif HAS_LLM:
                # Real LLM response with VETKA memory context
                try:
                    import time
                    llm_start = time.perf_counter()

                    llm = get_jarvis_llm()
                    context = await get_jarvis_context(session.user_id, transcript)
                    response_text = await llm.generate(transcript, session.user_id, context)

                    llm_duration = time.perf_counter() - llm_start
                    logger.info(f"[JARVIS] LLM response in {llm_duration:.2f}s: {response_text[:100]}...")

                    # Store in STM for conversation continuity
                    try:
                        from src.memory.stm_buffer import get_stm_buffer
                        stm = get_stm_buffer()
                        stm.add_message(f"User: {transcript}", source="user")
                        stm.add_message(f"Jarvis: {response_text}", source="agent")
                    except Exception as e:
                        logger.warning(f"[JARVIS] Could not store in STM: {e}")

                except Exception as e:
                    logger.error(f"[JARVIS] LLM failed: {e}", exc_info=True)
                    response_text = f"I heard you say: {transcript}. I'm having trouble with my language model."
            else:
                # Fallback to echo if no LLM
                response_text = f"I heard you say: {transcript}"

            session.response_text = response_text

            logger.info(f"[JARVIS] AI response: {response_text}")
            await sio.emit('jarvis_response', {
                'text': response_text,
                'user_id': session.user_id
            }, to=sid)

            # Transition to SPEAKING state
            session.state = JarvisState.SPEAKING
            await sio.emit('jarvis_state', {
                'state': JarvisState.SPEAKING,
                'user_id': session.user_id
            }, to=sid)

            # TTS: Synthesize response
            # Phase 104.7: Fast TTS (Edge-TTS ~1s) or Quality TTS (Qwen3 ~5-6s)
            if HAS_TTS and response_text:
                try:
                    import time
                    tts_start = time.perf_counter()

                    if TTS_MODE == "fast" and HAS_FAST_TTS:
                        # Fast mode: Edge-TTS (~1s latency)
                        fast_tts = FastTTSClient(voice="en-male")
                        audio_bytes = await fast_tts.synthesize_auto(response_text)

                        tts_duration = time.perf_counter() - tts_start

                        if audio_bytes:
                            # Edge-TTS returns MP3, encode directly
                            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                            audio_format = 'mp3'
                            logger.info(f"[JARVIS] FastTTS in {tts_duration:.2f}s, {len(audio_bytes)} bytes")
                        else:
                            audio_base64 = ""
                            audio_format = 'mp3'
                    else:
                        # Quality mode: Qwen3-TTS (~5-6s latency, better voice)
                        tts_client = Qwen3TTSClient(server_url="http://127.0.0.1:5003")
                        audio_bytes = await tts_client.synthesize(
                            text=response_text,
                            language="English",
                            speaker="ryan"
                        )
                        await tts_client.close()

                        tts_duration = time.perf_counter() - tts_start

                        if audio_bytes:
                            # Qwen3 returns PCM, convert to WAV
                            wav_bytes = pcm_to_wav(audio_bytes, sample_rate=24000)
                            audio_base64 = base64.b64encode(wav_bytes).decode('utf-8')
                            audio_format = 'wav'
                            logger.info(f"[JARVIS] Qwen3TTS in {tts_duration:.2f}s, {len(audio_bytes)} bytes")
                        else:
                            audio_base64 = ""
                            audio_format = 'wav'

                except Exception as e:
                    logger.error(f"[JARVIS] TTS failed: {e}")
                    audio_base64 = ""
                    audio_format = 'mp3'
            else:
                logger.warning("[JARVIS] No TTS available or empty response")
                audio_base64 = ""
                audio_format = 'mp3'

            # Only emit audio if we have it
            if audio_base64:
                await sio.emit('jarvis_audio', {
                    'audio': audio_base64,
                    'format': audio_format,  # 'mp3' for FastTTS, 'wav' for Qwen3
                    'user_id': session.user_id
                }, to=sid)
            else:
                logger.info("[JARVIS] No audio to emit, skipping jarvis_audio event")

            # Transition back to IDLE state
            session.state = JarvisState.IDLE
            session.reset_buffer()

            logger.info(f"[JARVIS] Session complete, returning to idle for user {session.user_id}")
            await sio.emit('jarvis_state', {
                'state': JarvisState.IDLE,
                'user_id': session.user_id
            }, to=sid)

        except Exception as e:
            logger.error(f"[JARVIS] Error in jarvis_listen_stop: {e}", exc_info=True)

            # Reset to idle on error
            if session:
                session.state = JarvisState.IDLE
                session.reset_buffer()

            await sio.emit('jarvis_error', {
                'error': str(e),
                'event': 'jarvis_listen_stop'
            }, to=sid)
            await sio.emit('jarvis_state', {
                'state': JarvisState.IDLE,
                'user_id': session.user_id if session else 'unknown'
            }, to=sid)


    @sio.event
    async def disconnect(sid):
        """
        Clean up Jarvis session on client disconnect
        """
        if sid in _active_sessions:
            session = _active_sessions.pop(sid)
            logger.info(f"[JARVIS] Session cleaned up for user {session.user_id}, sid={sid}")


    logger.info("[JARVIS] Voice interface handlers registered successfully")


def get_session(sid: str) -> Optional[JarvisSession]:
    """
    Get active Jarvis session by socket ID

    Args:
        sid: Socket.IO session ID

    Returns:
        JarvisSession if exists, None otherwise
    """
    return _active_sessions.get(sid)


def get_all_sessions() -> Dict[str, JarvisSession]:
    """
    Get all active Jarvis sessions (for debugging/monitoring)

    Returns:
        Dictionary of sid -> JarvisSession
    """
    return _active_sessions.copy()
