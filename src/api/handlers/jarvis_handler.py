"""
JARVIS Voice Interface Socket.IO Handler
Handles real-time voice interaction with AI assistant (SEPARATE from chat).

State Machine: idle -> listening -> thinking -> speaking -> idle

MARKER_104.3: Jarvis voice interface handler
MARKER_105_EDGE_CASES: T9 prediction edge case handling
"""

import logging
import base64
import io
import wave
import tempfile
import asyncio
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple, Callable, Any
from enum import Enum
from pathlib import Path
from functools import wraps

logger = logging.getLogger(__name__)


# =============================================================================
# MARKER_105_EDGE_CASES: T9 Prediction Edge Case Handling
# =============================================================================

# Edge case thresholds
T9_LOW_CONFIDENCE_THRESHOLD = 0.3      # Below this: wait for more input
T9_MODERATE_CONFIDENCE_THRESHOLD = 0.5  # Below this: show with disclaimer
T9_STT_CONFIDENCE_THRESHOLD = 0.5       # Below this: ask to repeat
T9_MODEL_TIMEOUT_MS = 2000              # For T9 draft prediction (fast, 2s OK)
T9_MIN_WORDS = 2                        # Minimum words before prediction

# MARKER_105_JARVIS_TIMEOUT_FIX: Separate timeout for full LLM generation
JARVIS_LLM_TIMEOUT_MS = 30000           # Full LLM response (30s, matches Ollama)


class T9PredictionStatus(str, Enum):
    """Status codes for T9 prediction edge cases"""
    CONFIDENT = "confident"                  # Full prediction, proceed
    LOW_CONFIDENCE_DRAFT = "low_confidence_draft"  # Weak prediction, show warning
    WAITING_FOR_INPUT = "waiting_for_input"  # Too few words, wait
    STT_RETRY = "stt_retry"                  # Audio unclear, ask to repeat
    INTERRUPTED = "interrupted"              # User interrupted, cancel
    TIMEOUT_FALLBACK = "timeout_fallback"    # Model slow, use template


# Template responses for timeout fallback
TIMEOUT_FALLBACK_TEMPLATES = {
    "greeting": "Hello! How can I help you today?",
    "question": "Let me think about that for a moment.",
    "command": "I'll process that request.",
    "default": "I'm here to help. What would you like to do?"
}


def _classify_input_type(partial_input: str) -> str:
    """
    Classify input type for fallback template selection.

    Args:
        partial_input: The partial user input

    Returns:
        Input type: 'greeting', 'question', 'command', or 'default'
    """
    input_lower = partial_input.lower().strip()

    # Greeting patterns (EN + RU)
    greeting_patterns = [
        "hello", "hi", "hey", "good morning", "good evening",
        "привет", "здравствуй", "добрый", "доброе", "добрый день"
    ]
    if any(input_lower.startswith(p) for p in greeting_patterns):
        return "greeting"

    # Question patterns
    question_words = ["what", "how", "why", "when", "where", "who", "which",
                      "что", "как", "почему", "когда", "где", "кто", "какой"]
    if any(input_lower.startswith(w) for w in question_words) or input_lower.endswith("?"):
        return "question"

    # Command patterns
    command_words = ["open", "show", "create", "delete", "find", "search",
                     "открой", "покажи", "создай", "удали", "найди"]
    if any(input_lower.startswith(w) for w in command_words):
        return "command"

    return "default"


async def handle_prediction_edge_cases(
    partial_input: str,
    prediction_confidence: float,
    stt_confidence: float,
    is_interrupted: bool = False,
    prediction_response: Optional[str] = None
) -> Tuple[Optional[str], T9PredictionStatus]:
    """
    Handle edge cases in T9 prediction.

    MARKER_105_EDGE_CASES: Core edge case handling function.

    Args:
        partial_input: Partial user input from STT
        prediction_confidence: Confidence score of T9 prediction (0.0-1.0)
        stt_confidence: Confidence score of STT transcription (0.0-1.0)
        is_interrupted: Whether user interrupted during TTS playback
        prediction_response: The predicted response text (if any)

    Returns:
        Tuple of (response_or_none, status_code)

    Status codes:
        - "confident": Full prediction, proceed
        - "low_confidence_draft": Weak prediction, show with warning
        - "waiting_for_input": Too few words, wait
        - "stt_retry": Audio unclear, ask to repeat
        - "interrupted": User interrupted, cancel
        - "timeout_fallback": Model slow, use template
    """
    # Case 1: Too few words - need more input
    word_count = len(partial_input.split()) if partial_input else 0
    if word_count < T9_MIN_WORDS:
        logger.debug(f"[T9 Edge] Waiting for input: only {word_count} word(s)")
        return None, T9PredictionStatus.WAITING_FOR_INPUT

    # Case 2: Noisy audio - STT confidence too low
    if stt_confidence < T9_STT_CONFIDENCE_THRESHOLD:
        logger.info(f"[T9 Edge] STT confidence too low: {stt_confidence:.2f}")
        return "Не расслышал, повтори?", T9PredictionStatus.STT_RETRY

    # Case 3: User interrupt during TTS
    if is_interrupted:
        logger.info("[T9 Edge] User interrupted TTS playback")
        return None, T9PredictionStatus.INTERRUPTED

    # Case 4: Very low prediction confidence - wait for more
    if prediction_confidence < T9_LOW_CONFIDENCE_THRESHOLD:
        logger.debug(f"[T9 Edge] Prediction confidence too low: {prediction_confidence:.2f}")
        return None, T9PredictionStatus.WAITING_FOR_INPUT

    # Case 5: Moderate confidence - proceed with disclaimer
    if prediction_confidence < T9_MODERATE_CONFIDENCE_THRESHOLD:
        logger.info(f"[T9 Edge] Moderate confidence: {prediction_confidence:.2f}")
        return prediction_response, T9PredictionStatus.LOW_CONFIDENCE_DRAFT

    # Case 6: High confidence - full prediction
    logger.debug(f"[T9 Edge] Confident prediction: {prediction_confidence:.2f}")
    return prediction_response, T9PredictionStatus.CONFIDENT


def with_timeout_fallback(timeout_ms: int = T9_MODEL_TIMEOUT_MS):
    """
    Decorator for model calls with timeout fallback.

    MARKER_105_EDGE_CASES: Timeout handling wrapper.

    If the model takes longer than timeout_ms, returns a template response
    instead and logs a warning.

    Args:
        timeout_ms: Maximum time to wait in milliseconds

    Usage:
        @with_timeout_fallback(2000)
        async def predict_response(input_text: str) -> str:
            # LLM call here
            return response
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            timeout_sec = timeout_ms / 1000.0

            try:
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_sec
                )
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(f"[T9 Timeout] Model responded in {elapsed_ms:.0f}ms")
                return result

            except asyncio.TimeoutError:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.warning(f"[T9 Timeout] Model timeout after {elapsed_ms:.0f}ms, using fallback")

                # Try to extract input for template selection
                partial_input = ""
                if args:
                    partial_input = str(args[0]) if args[0] else ""
                elif "partial_input" in kwargs:
                    partial_input = kwargs["partial_input"]
                elif "transcript" in kwargs:
                    partial_input = kwargs["transcript"]

                input_type = _classify_input_type(partial_input)
                fallback = TIMEOUT_FALLBACK_TEMPLATES.get(input_type, TIMEOUT_FALLBACK_TEMPLATES["default"])

                return fallback, T9PredictionStatus.TIMEOUT_FALLBACK

        return wrapper
    return decorator


async def timeout_wrapped_prediction(
    predict_func: Callable,
    partial_input: str,
    timeout_ms: int = T9_MODEL_TIMEOUT_MS,
    **kwargs
) -> Tuple[Optional[str], T9PredictionStatus]:
    """
    Wrap a prediction function with timeout handling.

    MARKER_105_EDGE_CASES: Alternative to decorator for dynamic timeout.

    Args:
        predict_func: Async function that returns prediction response
        partial_input: User's partial input
        timeout_ms: Timeout in milliseconds
        **kwargs: Additional arguments for predict_func

    Returns:
        Tuple of (response, status)
    """
    start_time = time.perf_counter()
    timeout_sec = timeout_ms / 1000.0

    try:
        result = await asyncio.wait_for(
            predict_func(partial_input, **kwargs),
            timeout=timeout_sec
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(f"[T9 Timeout] Prediction completed in {elapsed_ms:.0f}ms")

        # If result is a tuple (response, confidence), use it
        if isinstance(result, tuple):
            response, confidence = result
            if confidence >= T9_MODERATE_CONFIDENCE_THRESHOLD:
                return response, T9PredictionStatus.CONFIDENT
            elif confidence >= T9_LOW_CONFIDENCE_THRESHOLD:
                return response, T9PredictionStatus.LOW_CONFIDENCE_DRAFT
            else:
                return None, T9PredictionStatus.WAITING_FOR_INPUT
        else:
            # Simple string response, assume confident
            return result, T9PredictionStatus.CONFIDENT

    except asyncio.TimeoutError:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.warning(f"[T9 Timeout] Prediction timeout after {elapsed_ms:.0f}ms")

        input_type = _classify_input_type(partial_input)
        fallback = TIMEOUT_FALLBACK_TEMPLATES.get(input_type, TIMEOUT_FALLBACK_TEMPLATES["default"])

        return fallback, T9PredictionStatus.TIMEOUT_FALLBACK


# Interrupt handling state
_active_tts_tasks: Dict[str, asyncio.Task] = {}


async def handle_jarvis_interrupt(
    sio,
    sid: str,
    user_id: str,
    new_input: Optional[str] = None
) -> bool:
    """
    Handle user interrupt during TTS playback.

    MARKER_105_EDGE_CASES: Interrupt handling for TTS.

    Cancels current TTS playback, emits interrupt event,
    and optionally restarts with new input.

    Args:
        sio: SocketIO instance
        sid: Socket session ID
        user_id: User identifier
        new_input: New input to process after cancellation

    Returns:
        True if interrupt was handled, False if no active TTS
    """
    # Check for active TTS task
    task_key = f"{sid}:{user_id}"
    active_task = _active_tts_tasks.get(task_key)

    if active_task and not active_task.done():
        logger.info(f"[T9 Interrupt] Cancelling TTS for {user_id}")
        active_task.cancel()

        try:
            await active_task
        except asyncio.CancelledError:
            logger.debug(f"[T9 Interrupt] TTS task cancelled successfully")

        # Remove from active tasks
        _active_tts_tasks.pop(task_key, None)

        # Emit interrupt event to client
        await sio.emit('jarvis_interrupt', {
            'user_id': user_id,
            'reason': 'user_interrupt',
            'new_input': new_input
        }, to=sid)

        return True

    return False


def register_tts_task(sid: str, user_id: str, task: asyncio.Task):
    """
    Register an active TTS task for interrupt handling.

    Args:
        sid: Socket session ID
        user_id: User identifier
        task: The asyncio Task running TTS
    """
    task_key = f"{sid}:{user_id}"
    _active_tts_tasks[task_key] = task
    logger.debug(f"[T9 Interrupt] Registered TTS task for {user_id}")


def unregister_tts_task(sid: str, user_id: str):
    """
    Unregister a TTS task after completion.

    Args:
        sid: Socket session ID
        user_id: User identifier
    """
    task_key = f"{sid}:{user_id}"
    _active_tts_tasks.pop(task_key, None)
    logger.debug(f"[T9 Interrupt] Unregistered TTS task for {user_id}")


# =============================================================================
# End of MARKER_105_EDGE_CASES
# =============================================================================


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
        stt_confidence: STT transcription confidence (MARKER_105_EDGE_CASES)
        prediction_confidence: T9 prediction confidence (MARKER_105_EDGE_CASES)
        is_interrupted: Whether session was interrupted (MARKER_105_EDGE_CASES)
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
    # MARKER_105_EDGE_CASES: Additional fields for edge case handling
    stt_confidence: float = 1.0
    prediction_confidence: float = 1.0
    is_interrupted: bool = False

    def reset_buffer(self):
        """Clear audio buffer and VAD state"""
        self.audio_buffer = []
        self.silence_start = None
        self.has_speech = False
        self.total_duration = 0.0
        # MARKER_105_EDGE_CASES: Reset edge case fields
        self.stt_confidence = 1.0
        self.prediction_confidence = 1.0
        self.is_interrupted = False

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

            # MARKER_105_EDGE_CASES: Track STT confidence
            stt_confidence = 1.0  # Default high confidence

            if len(audio_data) < 1000:
                logger.warning(f"[JARVIS] Audio buffer too small: {len(audio_data)} bytes")
                transcript = ""
                stt_confidence = 0.0
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

                    # MARKER_105_EDGE_CASES: Extract STT confidence from Whisper
                    # Whisper returns segments with avg_logprob, use that as confidence
                    segments = result.get("segments", [])
                    if segments:
                        # Average the no_speech_prob inverse as confidence
                        # Lower no_speech_prob = higher confidence
                        avg_no_speech = sum(s.get("no_speech_prob", 0.5) for s in segments) / len(segments)
                        stt_confidence = 1.0 - avg_no_speech

                        # Also factor in compression ratio (too high = likely garbage)
                        avg_compression = sum(s.get("compression_ratio", 1.0) for s in segments) / len(segments)
                        if avg_compression > 2.4:  # Whisper's hallucination threshold
                            stt_confidence *= 0.5

                        logger.info(f"[JARVIS] STT confidence: {stt_confidence:.2f} (no_speech: {avg_no_speech:.2f})")
                    else:
                        stt_confidence = 0.8 if transcript else 0.0

                    logger.info(f"[JARVIS] STT transcript: {transcript}")

                    # Cleanup temp file
                    Path(tmp_path).unlink(missing_ok=True)

                except Exception as e:
                    logger.error(f"[JARVIS] STT failed: {e}")
                    transcript = "[STT Error]"
                    stt_confidence = 0.0
            else:
                logger.warning("[JARVIS] No STT engine available")
                transcript = "[No STT available]"
                stt_confidence = 0.0

            session.transcript = transcript
            session.stt_confidence = stt_confidence

            logger.info(f"[JARVIS] STT transcript: {transcript} (confidence: {stt_confidence:.2f})")

            # MARKER_105_EDGE_CASES: Check STT edge cases before proceeding
            edge_response, edge_status = await handle_prediction_edge_cases(
                partial_input=transcript,
                prediction_confidence=1.0,  # Will be updated after LLM
                stt_confidence=stt_confidence,
                is_interrupted=session.is_interrupted
            )

            if edge_status == T9PredictionStatus.STT_RETRY:
                # Audio unclear, ask to repeat
                logger.info(f"[JARVIS] Edge case: {edge_status.value}")
                await sio.emit('jarvis_transcript', {
                    'text': transcript,
                    'user_id': session.user_id,
                    'confidence': stt_confidence,
                    'status': edge_status.value
                }, to=sid)
                await sio.emit('jarvis_response', {
                    'text': edge_response,
                    'user_id': session.user_id,
                    'status': edge_status.value
                }, to=sid)
                # Reset and return to idle
                session.state = JarvisState.IDLE
                session.reset_buffer()
                await sio.emit('jarvis_state', {
                    'state': JarvisState.IDLE,
                    'user_id': session.user_id
                }, to=sid)
                return

            if edge_status == T9PredictionStatus.WAITING_FOR_INPUT:
                # Too few words, notify client but don't respond
                logger.info(f"[JARVIS] Edge case: waiting for more input")
                await sio.emit('jarvis_transcript', {
                    'text': transcript,
                    'user_id': session.user_id,
                    'confidence': stt_confidence,
                    'status': edge_status.value
                }, to=sid)
                # Reset and return to idle
                session.state = JarvisState.IDLE
                session.reset_buffer()
                await sio.emit('jarvis_state', {
                    'state': JarvisState.IDLE,
                    'user_id': session.user_id
                }, to=sid)
                return

            await sio.emit('jarvis_transcript', {
                'text': transcript,
                'user_id': session.user_id,
                'confidence': stt_confidence,
                'status': 'processing'
            }, to=sid)

            # AI Response: Phase 104.7 - Streaming LLM → TTS pipeline
            # MARKER_105_EDGE_CASES: Integrated timeout handling
            response_status = T9PredictionStatus.CONFIDENT  # Default

            # Detect hallucination (repeated phrases) from STT
            if _is_hallucination(transcript):
                logger.warning(f"[JARVIS] Detected STT hallucination, ignoring")
                response_text = "I couldn't understand that clearly. Could you try again?"
            elif not transcript or transcript.startswith("["):
                response_text = "I didn't catch that. Could you please repeat?"
            elif HAS_LLM:
                # Real LLM response with VETKA memory context
                # MARKER_105_EDGE_CASES: Use timeout wrapper
                try:
                    llm_start = time.perf_counter()

                    llm = get_jarvis_llm()
                    context = await get_jarvis_context(session.user_id, transcript)

                    # Define the prediction function for timeout wrapper
                    async def _generate_llm_response(text: str) -> str:
                        return await llm.generate(text, session.user_id, context)

                    # MARKER_105_JARVIS_TIMEOUT_FIX: Use LLM timeout (30s), not T9 (2s)
                    result = await timeout_wrapped_prediction(
                        predict_func=_generate_llm_response,
                        partial_input=transcript,
                        timeout_ms=JARVIS_LLM_TIMEOUT_MS  # 30s for full LLM, not 2s T9
                    )

                    if isinstance(result, tuple):
                        response_text, response_status = result
                    else:
                        response_text = result
                        response_status = T9PredictionStatus.CONFIDENT

                    llm_duration = time.perf_counter() - llm_start

                    if response_status == T9PredictionStatus.TIMEOUT_FALLBACK:
                        logger.warning(f"[JARVIS] LLM timeout after {llm_duration:.2f}s, using fallback")
                    else:
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
                    response_status = T9PredictionStatus.TIMEOUT_FALLBACK
            else:
                # Fallback to echo if no LLM
                response_text = f"I heard you say: {transcript}"

            session.response_text = response_text

            logger.info(f"[JARVIS] AI response ({response_status.value}): {response_text}")
            await sio.emit('jarvis_response', {
                'text': response_text,
                'user_id': session.user_id,
                'status': response_status.value,
                'is_draft': response_status == T9PredictionStatus.LOW_CONFIDENCE_DRAFT
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


    # MARKER_105_EDGE_CASES: Interrupt handling event
    @sio.event
    async def jarvis_interrupt_request(sid, data):
        """
        Client requests to interrupt current TTS playback.

        MARKER_105_EDGE_CASES: Handle user interrupts during TTS.

        Expected data: {user_id: str, new_input?: str}
        Emits: jarvis_interrupt with cancellation confirmation
        """
        try:
            session = _active_sessions.get(sid)
            if not session:
                logger.warning(f"[JARVIS] No session for interrupt request from {sid}")
                return

            user_id = data.get('user_id', session.user_id)
            new_input = data.get('new_input')

            logger.info(f"[JARVIS] Interrupt requested by {user_id}")

            # Mark session as interrupted
            session.is_interrupted = True

            # Handle the interrupt
            was_interrupted = await handle_jarvis_interrupt(
                sio=sio,
                sid=sid,
                user_id=user_id,
                new_input=new_input
            )

            if was_interrupted:
                # If we had new input, start processing it
                if new_input:
                    logger.info(f"[JARVIS] Restarting with new input: {new_input[:50]}...")
                    # The client should trigger jarvis_listen_start with new input
                    await sio.emit('jarvis_ready_for_input', {
                        'user_id': user_id,
                        'reason': 'interrupt_complete'
                    }, to=sid)
            else:
                logger.debug(f"[JARVIS] No active TTS to interrupt for {user_id}")
                await sio.emit('jarvis_interrupt', {
                    'user_id': user_id,
                    'reason': 'no_active_tts',
                    'new_input': new_input
                }, to=sid)

        except Exception as e:
            logger.error(f"[JARVIS] Error in jarvis_interrupt_request: {e}", exc_info=True)
            await sio.emit('jarvis_error', {
                'error': str(e),
                'event': 'jarvis_interrupt_request'
            }, to=sid)


    @sio.event
    async def disconnect(sid):
        """
        Clean up Jarvis session on client disconnect
        """
        if sid in _active_sessions:
            session = _active_sessions.pop(sid)
            logger.info(f"[JARVIS] Session cleaned up for user {session.user_id}, sid={sid}")
            # MARKER_105_EDGE_CASES: Clean up any active TTS tasks
            unregister_tts_task(sid, session.user_id)


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


# =============================================================================
# MARKER_105_PREDICT_DRAFT: T9-like Predictive Response Generation
# =============================================================================

async def _predict_draft(
    partial_input: str,
    context: dict,
    workflow_id: str,
    stream_manager=None
) -> Tuple[str, float]:
    """
    Generate draft response from partial user input (T9-style).

    This function attempts to predict what the user will say and pre-generate
    a response, reducing perceived latency for voice interactions.

    Args:
        partial_input: First 2-3 words from user speech
        context: Dict with stm_summary, arc_suggestions, viewport
        workflow_id: Current workflow ID
        stream_manager: For emitting prediction via Socket.IO

    Returns:
        (predicted_response, confidence) tuple

    Model selection (in order of preference):
        1. Local transformers pipeline (distilgpt2) - fastest
        2. ModelRegistry for fast local Ollama model
        3. Simple template-based prediction - fallback

    Target latency: <1500ms
    """
    start = time.time()

    # Only predict if we have at least 2 words
    words = partial_input.strip().split()
    if len(words) < 2:
        logger.debug(f"[JARVIS_T9] Skipping prediction - only {len(words)} word(s)")
        return ("", 0.0)

    predicted_response = ""
    confidence = 0.0

    try:
        # Build prompt with context
        prompt = _build_prediction_prompt(partial_input, context)

        # Try Option 1: Local transformers pipeline (fastest)
        predicted_response, confidence = await _predict_with_transformers(prompt)

        # If transformers failed or low confidence, try Option 2: Ollama
        if confidence < 0.3:
            predicted_response, confidence = await _predict_with_ollama(prompt)

        # If Ollama also failed, try Option 3: Template-based
        if confidence < 0.3:
            predicted_response, confidence = _predict_with_templates(partial_input, context)

        # Emit prediction via stream_manager if confidence is high enough
        if stream_manager and confidence >= 0.5:
            try:
                await stream_manager.emit_jarvis_prediction(
                    workflow_id=workflow_id,
                    partial_input=partial_input,
                    predicted_response=predicted_response,
                    confidence=confidence
                )
            except Exception as e:
                logger.warning(f"[JARVIS_T9] Failed to emit prediction: {e}")

    except Exception as e:
        logger.error(f"[JARVIS_T9] Prediction error: {e}", exc_info=True)
        predicted_response = ""
        confidence = 0.0

    elapsed_ms = (time.time() - start) * 1000
    logger.info(f"[JARVIS_T9] Draft predicted in {elapsed_ms:.0f}ms, confidence={confidence:.2f}")

    return (predicted_response, confidence)


def _build_prediction_prompt(partial_input: str, context: dict) -> str:
    """
    Build a prompt for draft prediction using context.

    Args:
        partial_input: First few words from user
        context: Dict with stm_summary, arc_suggestions, viewport

    Returns:
        Formatted prompt string
    """
    # Extract context components
    stm_summary = context.get("stm_summary", "")
    arc_suggestions = context.get("arc_suggestions", [])
    viewport = context.get("viewport", {})

    prompt_parts = [
        "You are a voice assistant predicting what the user wants.",
        "User started saying:",
        f'"{partial_input}..."',
        "",
        "Based on context, complete their request and provide a SHORT response (1-2 sentences).",
    ]

    if stm_summary:
        prompt_parts.append(f"\nRecent conversation:\n{stm_summary}")

    if arc_suggestions:
        suggestions_str = ", ".join(arc_suggestions[:3])
        prompt_parts.append(f"\nPossible topics: {suggestions_str}")

    if viewport and viewport.get("current_file"):
        prompt_parts.append(f"\nUser is viewing: {viewport.get('current_file')}")

    prompt_parts.append("\nPredicted response:")

    return "\n".join(prompt_parts)


async def _predict_with_transformers(prompt: str) -> Tuple[str, float]:
    """
    Attempt prediction using local transformers pipeline.

    Uses distilgpt2 for fast local inference.

    Args:
        prompt: The prediction prompt

    Returns:
        (predicted_response, confidence) tuple
    """
    try:
        # Lazy import to avoid startup overhead
        from transformers import pipeline as hf_pipeline

        # Use cached pipeline if available
        if not hasattr(_predict_with_transformers, "_pipeline"):
            logger.info("[JARVIS_T9] Loading distilgpt2 pipeline...")
            _predict_with_transformers._pipeline = hf_pipeline(
                "text-generation",
                model="distilgpt2",
                max_length=50,
                num_return_sequences=1,
                pad_token_id=50256  # Suppress warnings
            )
            logger.info("[JARVIS_T9] distilgpt2 pipeline loaded")

        generator = _predict_with_transformers._pipeline

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: generator(prompt, max_new_tokens=30, do_sample=True, temperature=0.7)
        )

        if result and len(result) > 0:
            generated = result[0].get("generated_text", "")
            # Extract only the new part after our prompt
            if prompt in generated:
                response = generated[len(prompt):].strip()
            else:
                response = generated.strip()

            # Clean up response
            response = response.split("\n")[0].strip()  # Take first line only

            # Calculate confidence based on response quality
            confidence = 0.0
            if len(response) > 10:
                confidence = 0.5
            if len(response) > 20:
                confidence = 0.6

            return (response[:150], confidence)  # Limit length

    except ImportError:
        logger.debug("[JARVIS_T9] transformers not available")
    except Exception as e:
        logger.warning(f"[JARVIS_T9] Transformers prediction failed: {e}")

    return ("", 0.0)


async def _predict_with_ollama(prompt: str) -> Tuple[str, float]:
    """
    Attempt prediction using Ollama local model.

    Uses fast local models (qwen2.5:3b, phi3:mini) via ModelRegistry.

    Args:
        prompt: The prediction prompt

    Returns:
        (predicted_response, confidence) tuple
    """
    try:
        import aiohttp

        # Fast models for prediction (in order of preference)
        fast_models = ["qwen2.5:3b", "phi3:mini", "qwen2.5vl:3b", "llama3.2:1b"]

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2.0)) as session:
            # Check which model is available
            try:
                async with session.get("http://localhost:11434/api/tags") as resp:
                    if resp.status != 200:
                        return ("", 0.0)
                    data = await resp.json()
                    available = [m.get("name", "") for m in data.get("models", [])]
            except Exception:
                return ("", 0.0)

            # Find first available fast model
            selected_model = None
            for model in fast_models:
                if any(model in m for m in available):
                    selected_model = model
                    break

            if not selected_model:
                # Fallback to any available model
                if available:
                    selected_model = available[0]
                else:
                    return ("", 0.0)

            # Generate prediction
            payload = {
                "model": selected_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 40,  # Very short for speed
                    "temperature": 0.7,
                    "num_ctx": 512,  # Minimal context
                }
            }

            async with session.post(
                "http://localhost:11434/api/generate",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response = data.get("response", "").strip()

                    # Clean up response
                    response = response.split("\n")[0].strip()

                    # Calculate confidence
                    confidence = 0.0
                    if len(response) > 10:
                        confidence = 0.5
                    if len(response) > 20:
                        confidence = 0.65

                    return (response[:150], confidence)

    except Exception as e:
        logger.warning(f"[JARVIS_T9] Ollama prediction failed: {e}")

    return ("", 0.0)


def _predict_with_templates(partial_input: str, context: dict) -> Tuple[str, float]:
    """
    Template-based prediction fallback.

    Uses pattern matching for common queries.

    Args:
        partial_input: First few words from user
        context: Context dict

    Returns:
        (predicted_response, confidence) tuple
    """
    partial_lower = partial_input.lower().strip()

    # Common patterns and their template responses
    templates = {
        "what is": ("I can explain that for you. What specifically would you like to know?", 0.5),
        "how do": ("I can help you with that. Let me explain the steps.", 0.5),
        "can you": ("Yes, I can help with that. What would you like me to do?", 0.55),
        "tell me": ("Sure, I'd be happy to tell you about that.", 0.5),
        "show me": ("I can show you that. Let me pull up the relevant information.", 0.5),
        "help me": ("Of course, I'm here to help. What do you need assistance with?", 0.55),
        "where is": ("Let me find that for you.", 0.5),
        "why is": ("That's a good question. Let me explain.", 0.5),
        "create a": ("I can help you create that. Let me set it up.", 0.55),
        "open the": ("Opening that for you now.", 0.6),
        "close the": ("Closing that for you.", 0.6),
        "search for": ("Searching for that now.", 0.6),
        "find the": ("Looking for that in the codebase.", 0.55),
    }

    for pattern, (response, confidence) in templates.items():
        if partial_lower.startswith(pattern):
            return (response, confidence)

    # Check context for more specific predictions
    stm_summary = context.get("stm_summary", "")
    if stm_summary:
        # If user seems to be continuing previous topic
        if "continue" in partial_lower or "more" in partial_lower:
            return ("Continuing from where we left off.", 0.5)
        if "again" in partial_lower or "repeat" in partial_lower:
            return ("Let me repeat that for you.", 0.5)

    # Generic fallback
    return ("I'm listening. Please continue.", 0.35)
